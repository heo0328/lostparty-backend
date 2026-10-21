"""W2 creation: real restricted PostgreSQL, synthetic accounts, no live server."""
import os
import subprocess
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import select, inspect, func
from app.core.database import session, now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_creation as creation, cycle_wire as wire, readiness, cycles
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember, ParticipationEvent
from app.raid_rooms.cycle_application_models import CycleSession, CycleSessionSegment
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentAssignment as Assignment
from app.raid_rooms.source_models import SessionParticipation, TimeReservation, RoomSettings
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from tests.test_recruitment_participation import ready, sources, imported, people, worlds
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor


@pytest.fixture
def candidate(ready):
    engine,a,b,_=ready
    old=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,old)
    result=subprocess.run(['alembic','upgrade','0025_cycle_admissions'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0, result.stderr.decode()[-2500:]
    assert table_digests(engine,old)==before
    with session() as db,db.begin():
        readiness.require_ready(db,integrated=True)
        with pytest.raises(GameError):readiness.require_active(db)
    return engine,a,b


def preflight(a, *, key=None, continuation=False, bundle=False, next_cid=None, next_role=None,gid=None):
    with session() as db,db.begin():
        key=key or raids.cycle(now(db)).cycle_key
    raids_ids=['horizon_cathedral','kazeros_act4'] if bundle else ['horizon_cathedral']
    items=[wire.BCreateTarget(raid_id=r.raid_id,difficulty_id=r.difficulties[0].difficulty_id,
        expected_weekly_revision=1) for r in raids.catalog().raids if r.raid_id in raids_ids]
    return creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',items,gid,key,
        continuation,next_cid,next_role)


def request(context, **changes):
    c=context['data']
    value=dict(title='synthetic two-cycle',scope='public',group_id=None,admission_mode='direct_join',
        app_mode='single' if len(c['targets'])==1 else 'mixed_bundle',
        items=[t|dict(duration_minutes=None,party_no=1) for t in c['targets']],selection=c['selection'],
        selection_context=dict(context_token=c['context_token']),experience_level=None,
        combat_requirement=dict(input_mode='shared',dealer_min=None,support_min=None),
        continuation=dict(enabled=c['continuation_effect']=='target_and_next',
            next_selection=c['next_cycle_creation']['selection'] if c['next_cycle_creation'] else None),
        schedule_groups=[],expected_cycle_key=c['expected_cycle_key'],expected_catalog_version=c['catalog_version'],
        expected_group_revision=c['group_revision'],target_cycle_key=c['target_cycle_key'],expected_target_revision=None)
    value.update(changes)
    return wire.InputContract3PostV2RaidRooms.model_validate(value)


def denied(code, fn, *args, **kwargs):
    with pytest.raises(GameError) as error:fn(*args,**kwargs)
    assert error.value.code==code


def test_creation_context_readonly_and_single_target(candidate):
    engine,a,b=candidate
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})
    ctx=preflight(a)
    assert table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})==before
    wire.OutputContract3GetV2MeRaidRoomCreationContext.model_validate(ctx)
    assert ctx['data']['next_cycle_creation'] is None
    status,result=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx))
    assert status==201 and result['data']['continuation_effect']=='target_only'
    rid=uuid.UUID(result['data']['room_id'])
    with session() as db,db.begin():
        assert len(list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid))))==1
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid))==1
        assert db.get(RoomSettings,rid).auto_open_enabled is False


@pytest.mark.parametrize('bundle',[False,True])
def test_atomic_two_cycle_create_initial_revisions_and_ack(candidate,bundle):
    _,a,b=candidate
    ctx=preflight(a,continuation=True,bundle=bundle)
    key=uuid.uuid4();data=request(ctx)
    result=creation.create(actor(a['uid']),key,data)
    assert creation.create(actor(a['uid']),key,data)==result
    ack=result[1]['data'];rid=uuid.UUID(ack['room_id'])
    assert len(ack['created_cycles'])==2
    assert {c['target_revision'] for c in ack['created_cycles']}=={1}
    with session() as db,db.begin():
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid)))
        assert len(rows)==2 and all(r.state=='open' and r.revision==r.members_revision==r.plan_revision==1 for r in rows)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid))==(4 if bundle else 2)
        for r in rows:
            gen=db.get(CycleGeneration,(r.id,1));leader=db.get(CycleMember,gen.leader_cycle_member_id)
            assert leader.user_id==a['uid'] and leader.joined_order==1 and gen.next_join_order==2


def test_n_target_does_not_create_third_week(candidate):
    _,a,_=candidate
    with session() as db,db.begin():
        current=cycles.target(now(db),raids.cycle(now(db)).cycle_key).current
    unchecked=preflight(a,key=(current+timedelta(days=7)).isoformat())
    assert unchecked['data']['continuation_effect']=='target_only'
    ctx=preflight(a,key=(current+timedelta(days=7)).isoformat(),continuation=True)
    result=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx,continuation=dict(enabled=True,next_selection=None)))[1]
    assert result['data']['continuation_effect']=='target_is_next'
    assert len(result['data']['created_cycles'])==1
    assert result['data']['created_cycles'][0]['target_cycle_key']==ctx['data']['target_cycle_key']


def test_n_failure_rolls_back_c_and_original_tables(candidate,monkeypatch):
    engine,a,_=candidate
    ctx=preflight(a,continuation=True,bundle=True);data=request(ctx)
    original=creation.admission.admit_bundle;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise GameError('SYNTHETIC_N_FAILURE')
        return original(*args,**kwargs)
    monkeypatch.setattr(creation.admission,'admit_bundle',fail_second)
    tables=set(inspect(engine).get_table_names())-{'alembic_version','game_account_requests'}
    before=table_digests(engine,tables)
    denied('SYNTHETIC_N_FAILURE',creation.create,actor(a['uid']),uuid.uuid4(),data)
    assert table_digests(engine,tables)==before


def test_expired_context_and_wrong_actor_rejected(candidate,monkeypatch):
    _,a,b=candidate
    ctx=preflight(a);data=request(ctx)
    denied('CONTEXT_INVALID',creation.create,actor(b['uid']),uuid.uuid4(),data)
    real=cycles.now
    monkeypatch.setattr(cycles,'now',lambda db: real(db)+timedelta(minutes=3))
    denied('CONTEXT_EXPIRED',creation.create,actor(a['uid']),uuid.uuid4(),data)


def test_next_week_conflict_is_not_replaced(candidate):
    _,a,_=candidate
    with session() as db,db.begin():
        next_key=(cycles.target(now(db),raids.cycle(now(db)).cycle_key).current+timedelta(days=7)).isoformat()
    other=creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,key=next_key)))[1]
    ctx=preflight(a,continuation=True)
    assert ctx['data']['target_creation']['permission']['allowed']
    assert not ctx['data']['next_cycle_creation']['permission']['allowed']
    assert ctx['data']['next_cycle_creation']['conflicts'][0]['room_id']==other['data']['room_id']
    denied('WEEKLY_ALREADY_PARTICIPATING',creation.create,actor(a['uid']),uuid.uuid4(),request(ctx))


def test_manual_schedule_n_is_pending_without_reservations(candidate):
    _,a,_=candidate
    ctx=preflight(a,continuation=True)
    with session() as db,db.begin():
        stamp=now(db)
    from app.raid_rooms import time_policy
    start=time_policy.ceil_tick(stamp+timedelta(minutes=60))
    if raids.cycle(start+timedelta(minutes=10)).cycle_key!=ctx['data']['expected_cycle_key']:
        pytest.skip('No 70-minute creation window before the actual cycle boundary')
    day=start.astimezone(raids.KST)
    clock=day.strftime('%H:%M')
    groups=[dict(client_group_key='manual',existing_group_id=None,expected_group_revision=None,
        occurrence_mode='each',planning_mode='manual',required=True,auto_confirm_additional_members=None,
        day_scope='selected_weekdays',alternatives=[dict(client_alternative_key='one',existing_session_id=None,
            expected_session_revision=None,weekday=day.isoweekday(),starts_local=clock,
            leader_latest_start_local=None,item_order=[ctx['data']['targets'][0]['raid_id']])])]
    ack=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx,schedule_groups=groups))[1]['data']
    with session() as db,db.begin():
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==uuid.UUID(ack['room_id'])).order_by(RoomCycle.cycle_key)))
        c,n=rows
        for row,state,count in ((c,'confirmed',1),(n,'confirmation_pending',0)):
            sid=db.scalar(select(CycleSession.session_id).where(CycleSession.cycle_id==row.id))
            part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==sid))
            assert part.confirmation_state==state
            assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.session_id==sid))==count
            assert db.scalar(select(func.count()).select_from(CycleSessionSegment).where(CycleSessionSegment.session_id==sid))==1


def test_alternate_next_character_and_original_ack_before_context_revalidation(candidate,monkeypatch):
    _,a,_=candidate
    ctx=preflight(a,continuation=True,next_cid=uuid.UUID(a['ids'][1]),next_role='dealer')
    data=request(ctx);command=uuid.uuid4()
    result=creation.create(actor(a['uid']),command,data)
    with session() as db,db.begin():
        rows=list(db.scalars(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(result[1]['data']['room_id']))
            .order_by(WeeklyOccupancy.cycle_key)))
        assert [str(r.character_id) for r in rows]==a['ids'][:2]
    def forbidden(*args,**kwargs):raise AssertionError('Original ACK must precede revalidation')
    monkeypatch.setattr(creation.opaque,'unseal',forbidden)
    assert creation.create(actor(a['uid']),command,data)==result


def test_creation_crossing_actual_cycle_boundary_rolls_back(candidate,monkeypatch):
    _,a,_=candidate
    ctx=preflight(a,continuation=True);data=request(ctx)
    original=cycles.now;calls=[]
    def crossed(db):
        calls.append(1)
        return original(db)+(timedelta(days=7) if len(calls)>1 else timedelta())
    monkeypatch.setattr(cycles,'now',crossed)
    denied('CYCLE_CHANGED',creation.create,actor(a['uid']),uuid.uuid4(),data)
    with session() as db,db.begin():assert db.get(Room,uuid.UUID(ctx['data']['prospective_room_id'])) is None


def test_final_deadline_rolls_back_prepared_ack_and_reports_target(candidate,monkeypatch):
    _,a,_=candidate
    ctx=preflight(a,continuation=True);data=request(ctx)
    original=creation.schedule.deadlines;calls=[]
    def closed(db,row,selected,stamp):
        calls.append(1)
        if len(calls)==3:raise GameError('RECRUITMENT_CLOSED')
        return original(db,row,selected,stamp)
    monkeypatch.setattr(creation.schedule,'deadlines',closed)
    with pytest.raises(GameError) as error:creation.create(actor(a['uid']),uuid.uuid4(),data)
    assert error.value.code=='RECRUITMENT_CLOSED'
    assert error.value.cycle_details['failed_cycle_key']==ctx['data']['target_cycle_key']
    with session() as db,db.begin():assert db.get(Room,uuid.UUID(ctx['data']['prospective_room_id'])) is None


@pytest.mark.parametrize('clock,day', [('00:00',28),('05:55',28),('06:00',21),('10:00',21)])
def test_actual_cycle_wednesday_local_start(clock,day):
    from app.raid_rooms.cycle_schedule import local_start
    result=local_start('2026-10-21',3,clock).astimezone(raids.KST)
    assert result.day==day and result.strftime('%H:%M')==clock
