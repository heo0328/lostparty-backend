"""W3 lifecycle under restricted PostgreSQL, never against a development DB."""
import os,subprocess,uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,inspect,func
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_opening as opening,cycle_wire as wire,readiness,cycles
from app.raid_rooms.cycle_models import RoomCycle,CycleGeneration,CycleMember,CycleRound,ParticipationEvent
from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentMembership as Member,RecruitmentAssignment as Assignment
from app.raid_rooms.weekly_links import WeeklyOccupancy
from tests.test_recruitment_cycle_creation import candidate,ready,sources,imported,people,worlds,preflight,request,denied,creation
from tests.test_recruitment_cycle_commands import create_room,context,admission_request,commands
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor
from app.raid_rooms import cycle_continuation as continuation,cycle_leadership as leadership,cycle_character as character
from app.raid_rooms.cycle_lifecycle_models import CycleDecision


@pytest.fixture
def lifecycle(candidate):
    target,a,b=candidate
    tables=set(inspect(target).get_table_names())-{'alembic_version'}
    before=table_digests(target,tables)
    result=subprocess.run(['alembic','upgrade','0026_cycle_lifecycle'],env={**os.environ,
        'DATABASE_URL':target.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-1800:]
    assert table_digests(target,tables)==before
    with session() as db,db.begin():
        readiness.require_ready(db,integrated=True)
        with pytest.raises(GameError):readiness.require_active(db)
    return target,a,b


def next_key():
    with session() as db,db.begin():return (cycles.target(now(db),commands.raids.cycle(now(db)).cycle_key).current+timedelta(days=7)).isoformat()


def scoped(ctx):
    return dict(expected_cycle_key=ctx['scope']['current_cycle_key'],target_cycle_key=ctx['scope']['target_cycle_key'],
        expected_target_revision=ctx['scope']['target_revision'],context_token=ctx['data']['context_token'])


def opening_body(ctx,intent='open'):
    return wire.OpeningCommand.model_validate(scoped(ctx)|dict(selection=ctx['data']['selection'],
        target_items=ctx['data']['targets'],target_session_ids=ctx['data']['target_session_ids'],intent=intent))


def continue_body(ctx):
    return wire.ContinueCommand.model_validate(scoped(ctx)|dict(selection=ctx['data']['selection'],
        target_items=ctx['data']['targets'],target_session_ids=ctx['data']['target_session_ids']))


def cancel_body(ctx):
    return wire.CancellationCommand.model_validate(scoped(ctx)|dict(expected_leadership_revision=ctx['data']['leadership']['leadership_revision']))


def add_member(w,rid,key):
    return commands.admit(actor(w['uid']),rid,uuid.uuid4(),admission_request(context(w,rid,key)))


def cancel_member(w,rid,key):
    ctx=leadership.get_cancel(actor(w['uid']),rid,key)
    return leadership.cancel(actor(w['uid']),rid,uuid.uuid4(),cancel_body(ctx))


def change_body(ctx,plan):
    c=ctx['data']
    base=admission_request(ctx).model_dump(mode='json')
    return wire.InputContract3PostV2RaidRoomsRoomIdCharacterChanges.model_validate(base|dict(
        assignments=[dict(assignment_id=a['assignment_id'],expected_revision=a['revision']) for a in plan['data']['my_assignments']],
        expected_cycle_member_revision=plan['data']['my_membership']['cycle_member_revision']))


def test_explicit_open_readonly_and_atomic_first_bundle(lifecycle):
    engine,a,b=lifecycle
    room=create_room(a,combined=False,bundle=True);rid=uuid.UUID(room['room_id']);key=next_key()
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    ctx=opening.get(actor(a['uid']),rid,key,'open')
    assert ctx['data']['permission']['allowed'] and ctx['scope']['room_cycle_id'] is None
    assert table_digests(engine,tables)==before
    command=uuid.uuid4();body=opening_body(ctx)
    result=opening.execute(actor(a['uid']),rid,command,body)
    assert opening.execute(actor(a['uid']),rid,command,body)==result
    assert result[1]['scope']['target_revision']==1
    assert result[1]['scope']['room_cycle_id']==ctx['data']['prospective_room_cycle_id']
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(result[1]['scope']['room_cycle_id']))
        assert row.state=='open' and row.generation==1
        leader=db.get(CycleMember,db.get(CycleGeneration,(row.id,1)).leader_cycle_member_id)
        assert leader.user_id==a['uid'] and leader.joined_order==1
        assert commands.admission.member_count(db,row)==1
        assert db.get(Room,rid).revision==1


def test_existing_open_is_noop_and_non_source_rejected(lifecycle):
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);key=next_key()
    denied('SOURCE_PARTICIPATION_REQUIRED',opening.get,actor(b['uid']),rid,key,'open')
    ctx=opening.get(actor(a['uid']),rid,key,'open')
    assert ctx['data']['opening_effect']=='already_open'
    assert opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx))[1]['data']['outcome']=='noop'


def test_existing_c_member_bypasses_n_approval_but_not_source_checks(lifecycle):
    _,a,b=lifecycle
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,c)
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']))
        row.settings_snapshot=row.settings_snapshot|dict(admission_mode='leader_only')
    ctx=continuation.get(actor(b['uid']),rid,n)
    assert ctx['data']['selection']['character_id']==b['ids'][0] and ctx['data']['permission']['allowed']
    result=continuation.execute(actor(b['uid']),rid,uuid.uuid4(),continue_body(ctx))
    assert result[0]==200
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid'],WeeklyOccupancy.room_id==rid))==4
        assert db.get(Room,rid).revision==1


def test_conflicting_b_preserved_and_alternate_n_character(lifecycle):
    engine,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,c)
    other=creation.create(actor(b['uid']),uuid.uuid4(),request(preflight(b,key=n)))[1]['data']
    other_id=uuid.UUID(other['room_id'])
    with session() as db,db.begin():before=[r.assignment_id for r in db.scalars(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==other_id))]
    ctx=continuation.get(actor(b['uid']),rid,n)
    assert ctx['data']['permission']['reason']=='TARGET_CHARACTER_CONFLICT'
    assert ctx['data']['conflicts'][0]['room_id']==str(other_id)
    denied('TARGET_CHARACTER_CONFLICT',continuation.execute,actor(b['uid']),rid,uuid.uuid4(),continue_body(ctx))
    alternate=continuation.get(actor(b['uid']),rid,n,cid=uuid.UUID(b['ids'][1]),role='dealer')
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),continue_body(alternate))
    with session() as db,db.begin():
        assert [r.assignment_id for r in db.scalars(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==other_id))]==before
        assert db.scalar(select(WeeklyOccupancy.character_id).where(WeeklyOccupancy.room_id==rid,
            WeeklyOccupancy.user_id==b['uid'],WeeklyOccupancy.cycle_key==cycles.target(now(db),n).key))==uuid.UUID(b['ids'][1])


def test_explicit_decline_is_audit_not_occupancy(lifecycle):
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,c)
    ctx=continuation.get(actor(b['uid']),rid,n,action='decline')
    body=wire.ScopedCommand.model_validate(scoped(ctx));key=uuid.uuid4()
    result=continuation.execute(actor(b['uid']),rid,key,body,decline=True)
    assert continuation.execute(actor(b['uid']),rid,key,body,decline=True)==result
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleDecision).where(CycleDecision.user_id==b['uid'],CycleDecision.kind=='declined'))==1
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==1


def test_cancel_and_rejoin_reuses_assignment_but_new_order(lifecycle):
    _,a,b=lifecycle
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,c);continuation.execute(actor(b['uid']),rid,uuid.uuid4(),continue_body(continuation.get(actor(b['uid']),rid,n)))
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']));cm=leadership.life.actual_member(db,row,b['uid'])
        cmid,old_order=cm.id,cm.joined_order;old=[a.id for a in leadership.life.assignments(db,row,cm)]
        c_revision=db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id'])).revision
        from app.raid_rooms.cycle_models import CycleSubmission
        # Synthetic W4 submission head: cancellation archives it, rejoin does not copy it.
        db.add(CycleSubmission(cycle_member_id=cm.id,room_id=rid,cycle_id=row.id,generation=row.generation,
            membership_id=cm.membership_id,user_id=cm.user_id,revision=1,source_personal_revision=1,
            intervals=[],normalized_intervals=[],submitted_at=now(db)))
    cancel_member(b,rid,n)
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),continue_body(continuation.get(actor(b['uid']),rid,n)))
    with session() as db,db.begin():
        cm=db.get(CycleMember,cmid);row=db.get(RoomCycle,cm.cycle_id)
        assert cm.joined_order>old_order and cm.state=='participating'
        assert [a.id for a in leadership.life.assignments(db,row,cm)]==old
        assert db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id'])).revision==c_revision
        assert db.get(Member,cm.membership_id).ended_at is None
        history=list(db.scalars(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==cmid).order_by(ParticipationEvent.member_revision)))
        assert [e.action for e in history]==['joined','cancelled','joined']
        assert history[1].evidence['assignments'][0]['build'] is not None
        assert history[1].evidence['submission']['source_personal_revision']==1
        assert db.get(CycleSubmission,cmid) is None


def test_leader_cancel_chooses_first_eligible_and_preserves_c(lifecycle,people):
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,n);third=people('w3-third');add_member(third,rid,n)
    ctx=leadership.get_cancel(actor(a['uid']),rid,n)
    with session() as db,db.begin():
        nrow=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']))
        b_member=leadership.life.actual_member(db,nrow,b['uid'])
        assert ctx['data']['successor']['cycle_member_id']==str(b_member.id)
    leadership.cancel(actor(a['uid']),rid,uuid.uuid4(),cancel_body(ctx))
    with session() as db,db.begin():
        nrow=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']))
        assert db.get(CycleMember,db.get(CycleGeneration,(nrow.id,nrow.generation)).leader_cycle_member_id).user_id==b['uid']
        crow=db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id']))
        assert db.get(CycleMember,db.get(CycleGeneration,(crow.id,1)).leader_cycle_member_id).user_id==a['uid']
        assert db.get(Room,rid).ended_at is None


def test_successor_changed_after_context_requires_reconfirmation(lifecycle,people):
    from app.game_accounts.models import Activity
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key()
    add_member(b,rid,n);third=people('w3-successor-next');add_member(third,rid,n)
    ctx=leadership.get_cancel(actor(a['uid']),rid,n)
    with session() as db,db.begin():db.delete(db.get(Activity,(b['cid'],uuid.UUID(b['ids'][0]))))
    denied('SUCCESSOR_UNAVAILABLE',leadership.cancel,actor(a['uid']),rid,uuid.uuid4(),cancel_body(ctx))
    refreshed=leadership.get_cancel(actor(a['uid']),rid,n)
    leadership.cancel(actor(a['uid']),rid,uuid.uuid4(),cancel_body(refreshed))
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']))
        assert db.get(CycleMember,db.get(CycleGeneration,(row.id,1)).leader_cycle_member_id).user_id==third['uid']


def test_last_n_cancel_and_reopen_preserve_old_generation(lifecycle):
    _,a,b=lifecycle
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);n=next_key()
    old_id=uuid.UUID(room['created_cycles'][1]['room_cycle_id'])
    cancel_member(a,rid,n)
    with session() as db,db.begin():
        old=db.get(RoomCycle,old_id);assert old.state=='closed' and db.get(CycleGeneration,(old.id,1)).state=='cancelled'
        old_rounds=set(db.scalars(select(CycleRound.round_id).where(CycleRound.cycle_id==old_id)))
        old_assignments=set(db.scalars(select(Assignment.id).join(CycleRound,CycleRound.round_id==Assignment.round_id).where(CycleRound.cycle_id==old_id)))
    ordinary=opening.get(actor(a['uid']),rid,n,'open')
    assert ordinary['data']['permission']['reason']=='TARGET_REOPEN_REQUIRED'
    ctx=opening.get(actor(a['uid']),rid,n,'reopen');result=opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx,'reopen'))
    assert result[1]['scope']['room_cycle_id']==str(old_id) and result[1]['scope']['target_generation']==2
    assert result[1]['scope']['target_revision']==ctx['data']['prospective_target_revision']
    with session() as db,db.begin():
        row=db.get(RoomCycle,old_id);assert row.state=='open' and row.generation==2
        assert old_rounds.isdisjoint({r.id for i,r in commands.admission.rounds(db,row)})
        assert all(db.get(Assignment,id).state=='left' for id in old_assignments)
        assert db.get(Room,rid).revision==1 and db.get(Room,rid).ended_at is None


def test_direct_transfer_retains_participants_slots_and_leases(lifecycle):
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    ctx=leadership.get_transfer(actor(a['uid']),rid,n);candidate=ctx['data']['candidates'][0]
    body=wire.TransferCommand.model_validate(scoped(ctx)|dict(expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
        candidate_cycle_member_id=candidate['cycle_member_id'],expected_candidate_revision=candidate['revision']))
    with session() as db,db.begin():before=table_digests(db.bind,{'recruitment_assignments','recruitment_weekly_occupancies','recruitment_memberships'})
    leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),body)
    with session() as db,db.begin():
        assert table_digests(db.bind,set(before))==before
        row=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']))
        assert leadership.life.actual_member(db,row,a['uid']).state=='participating'
        assert commands.leadership(db,row)['leader_cycle_member_id']==uuid.UUID(candidate['cycle_member_id'])
    denied('TARGET_LEADER_REQUIRED',leadership.get_transfer,actor(a['uid']),rid,n)


def test_character_change_only_n_preserves_ids_and_old_source(lifecycle):
    from app.raid_rooms import cycle_member_reads
    from app.game_accounts.models import Character
    _,a,b=lifecycle
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    plan=cycle_member_reads.plan(actor(a['uid']),rid,n)
    # The old character can become unusable; a new owned active choice remains valid.
    with session() as db,db.begin():
        old=db.get(Character,uuid.UUID(a['ids'][0]));old.lifecycle_revision+=1;old.status='suspect'
    ctx=commands.get_context(actor(a['uid']),rid,n,uuid.UUID(a['ids'][1]),'dealer','change_character')
    result=character.execute(actor(a['uid']),rid,uuid.uuid4(),change_body(ctx,plan));assert result[0]==200
    with session() as db,db.begin():
        nrow=db.get(RoomCycle,uuid.UUID(room['created_cycles'][1]['room_cycle_id']));cm=leadership.life.actual_member(db,nrow,a['uid'])
        assert {a.character_id for a in leadership.life.assignments(db,nrow,cm)}=={uuid.UUID(a['ids'][1])}
        crow=db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id']));c_cm=leadership.life.actual_member(db,crow,a['uid'])
        assert {a.character_id for a in leadership.life.assignments(db,crow,c_cm)}=={uuid.UUID(a['ids'][0])}
        history=db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==cm.id,ParticipationEvent.action=='character_changed'))
        assert history.evidence['assignments'][0]['character_id']==a['ids'][0]
        assert {str(a.id) for a in leadership.life.assignments(db,nrow,cm)}=={a['assignment_id'] for a in plan['data']['my_assignments']}


def close_current_fixture(rid,key,state):
    """Fabricated W4 result, not evidence that a completion API is implemented."""
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==cycles.target(now(db),key).key))
        row.state='closed';generation=db.get(CycleGeneration,(row.id,row.generation))
        generation.state=state;generation.closed_at=now(db)
        for cm in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id)):
            for a in leadership.life.assignments(db,row,cm):
                if a.state=='active':commands.admission.core.release_assignment(db,a,now(db))
                a.state='completed' if state=='completed' else 'stopped_incomplete'
            cm.state=state
        for i,r in commands.admission.rounds(db,row):r.state='completed' if state=='completed' else 'stopped_incomplete';r.ended_at=now(db)


@pytest.mark.parametrize('state',['completed','stopped'])
def test_closed_c_retains_valid_opening_source(lifecycle,state):
    _,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);c=room['created_cycles'][0]['target_cycle_key']
    add_member(b,rid,c)
    close_current_fixture(rid,c,state)
    ctx=opening.get(actor(a['uid']),rid,next_key(),'open')
    assert ctx['data']['permission']['allowed']
    opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx))
    nctx=continuation.get(actor(b['uid']),rid,next_key())
    assert nctx['data']['permission']['allowed']
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),continue_body(nctx))
    with session() as db,db.begin():
        assert db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id'])).state=='closed'


@pytest.mark.parametrize('state',['completed','stopped'])
def test_closed_target_transfer_keeps_historical_assignments(lifecycle,state):
    _,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);c=room['created_cycles'][0]['target_cycle_key']
    add_member(b,rid,c);close_current_fixture(rid,c,state)
    ctx=leadership.get_transfer(actor(a['uid']),rid,c);candidate=ctx['data']['candidates'][0]
    body=wire.TransferCommand.model_validate(scoped(ctx)|dict(expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
        candidate_cycle_member_id=candidate['cycle_member_id'],expected_candidate_revision=candidate['revision']))
    with session() as db,db.begin():before=table_digests(db.bind,{'recruitment_assignments','recruitment_memberships'})
    leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),body)
    with session() as db,db.begin():assert table_digests(db.bind,set(before))==before


@pytest.mark.parametrize('state',['cancelled','removed'])
def test_cancelled_or_removed_c_is_not_a_continuation_source(lifecycle,state):
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    add_member(b,rid,c)
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id']))
        cm=leadership.life.actual_member(db,row,b['uid']);stamp=now(db)
        cm.state=state;cm.ended_at=stamp;cm.revision+=1
    denied('SOURCE_PARTICIPATION_REQUIRED',continuation.get,actor(b['uid']),rid,n)


def test_concurrent_explicit_openings_commit_one_generation(lifecycle):
    _,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);n=next_key()
    bodies=[opening_body(opening.get(actor(a['uid']),rid,n,'open')) for _ in range(2)]
    def execute(body):
        try:return opening.execute(actor(a['uid']),rid,uuid.uuid4(),body)[0]
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(execute,bodies))
    assert sorted(map(str,results))==['200','TARGET_CONTEXT_STALE']
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(RoomCycle).where(RoomCycle.room_id==rid))==2
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid))==2


def test_opening_failure_rolls_back_assignments_and_six_boundary(lifecycle,monkeypatch):
    engine,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);n=next_key()
    ctx=opening.get(actor(a['uid']),rid,n,'open');body=opening_body(ctx)
    tables=set(inspect(engine).get_table_names())-{'alembic_version','game_account_requests'}
    before=table_digests(engine,tables)
    def broken(*args,**kwargs):raise GameError('SYNTHETIC_SCHEDULE_FAILURE')
    with monkeypatch.context() as change:
        change.setattr(opening.schedule,'install',broken)
        denied('SYNTHETIC_SCHEDULE_FAILURE',opening.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    assert table_digests(engine,tables)==before
    original=cycles.now;calls=[]
    def crossed(db):
        calls.append(1)
        return original(db)+(timedelta(days=7) if len(calls)>1 else timedelta())
    monkeypatch.setattr(cycles,'now',crossed)
    denied('CYCLE_CHANGED',opening.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    assert table_digests(engine,tables)==before


def test_context_expiry_scope_and_original_ack(lifecycle,monkeypatch):
    _,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);n=next_key()
    ctx=opening.get(actor(a['uid']),rid,n,'open');body=opening_body(ctx)
    wrong=wire.OpeningCommand.model_validate(body.model_dump(mode='json')|dict(target_cycle_key=ctx['scope']['current_cycle_key']))
    denied('TARGET_SCOPE_MISMATCH',opening.execute,actor(a['uid']),rid,uuid.uuid4(),wrong)
    original=cycles.now
    with monkeypatch.context() as changed:
        changed.setattr(cycles,'now',lambda db:original(db)+timedelta(minutes=3))
        denied('COMMAND_CONTEXT_EXPIRED',opening.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    key=uuid.uuid4();result=opening.execute(actor(a['uid']),rid,key,body)
    def forbidden(*args,**kwargs):raise AssertionError('Original ACK must precede current authority/context')
    monkeypatch.setattr(leadership.life.opaque,'unseal',forbidden)
    assert opening.execute(actor(a['uid']),rid,key,body)==result


def test_empty_n_cancels_only_its_pending_applications(lifecycle):
    from app.raid_rooms.cycle_application_models import CycleApplication
    _,a,b=lifecycle
    room=create_room(a,mode='leader_only');rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    app_ids=[]
    for key in (c,n):
        ctx=context(b,rid,key,'apply')
        result=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)[1]['data']
        app_ids.append(uuid.UUID(result['application_id']))
    cancel_member(a,rid,n)
    with session() as db,db.begin():
        assert db.get(CycleApplication,app_ids[0]).state=='pending'
        assert db.get(CycleApplication,app_ids[1]).state=='cancelled'
        assert db.get(Room,rid).ended_at is None


def test_lifecycle_decisions_cannot_be_overwritten(lifecycle):
    from sqlalchemy.exc import DBAPIError
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();cancel_member(a,rid,n)
    with session() as db,db.begin():
        decision=db.scalar(select(CycleDecision).where(CycleDecision.room_id==rid))
        with pytest.raises(DBAPIError):
            with db.begin_nested():decision.evidence={};db.flush()


def test_manual_copy_reopen_and_cancel_preserve_c_reservations(lifecycle):
    from app.raid_rooms import time_policy,cycle_schedule,cycle_member_reads
    from app.raid_rooms.source_models import SessionParticipation,TimeReservation
    _,a,b=lifecycle
    ctx=preflight(a)
    with session() as db,db.begin():start=time_policy.ceil_tick(now(db)+timedelta(minutes=60))
    if commands.raids.cycle(start+timedelta(minutes=10)).cycle_key!=ctx['data']['expected_cycle_key']:
        pytest.skip('No safe creation interval before the cycle boundary')
    local=start.astimezone(commands.raids.KST)
    groups=[dict(client_group_key='w3-manual',existing_group_id=None,expected_group_revision=None,
        occurrence_mode='each',planning_mode='manual',required=True,auto_confirm_additional_members=None,
        day_scope='selected_weekdays',alternatives=[dict(client_alternative_key='one',existing_session_id=None,
            expected_session_revision=None,weekday=local.isoweekday(),starts_local=local.strftime('%H:%M'),
            leader_latest_start_local=None,item_order=[ctx['data']['targets'][0]['raid_id']])])]
    room=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx,schedule_groups=groups))[1]['data']
    rid=uuid.UUID(room['room_id']);n=next_key()
    opened=opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(opening.get(actor(a['uid']),rid,n,'open')))[1]
    nid=uuid.UUID(opened['scope']['room_cycle_id'])
    with session() as db,db.begin():
        row=db.get(RoomCycle,nid);sess=cycle_schedule.sessions(db,row)[0]
        part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==sess.id))
        assert part.confirmation_state=='confirmation_pending'
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.session_id==sess.id))==0
        # Synthetic explicit confirmation, not a W4 HTTP implementation claim.
        cycle_schedule.graph.reserve(db,part,sess,now(db))
        old_session=sess.id
        cids=list(db.scalars(select(TimeReservation.id).where(TimeReservation.session_id!=sess.id,TimeReservation.room_id==rid)))
    cancelled=leadership.get_cancel(actor(a['uid']),rid,n)
    assert cancelled['data']['impact']['reservation_count']==1
    leadership.cancel(actor(a['uid']),rid,uuid.uuid4(),cancel_body(cancelled))
    reopen_ctx=opening.get(actor(a['uid']),rid,n,'reopen')
    assert all(v['expected_weekly_revision']>1 for v in reopen_ctx['data']['targets'])
    opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(reopen_ctx,'reopen'))
    with session() as db,db.begin():
        assert all(db.get(TimeReservation,id).released_at is None for id in cids)
        old=list(db.scalars(select(TimeReservation).where(TimeReservation.session_id==old_session)))
        assert old and all(r.released_reason=='future_cancel' for r in old)
        row=db.get(RoomCycle,nid);live=cycle_schedule.sessions(db,row)
        assert len(live)==1 and live[0].id!=old_session
        part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==live[0].id))
        assert part.confirmation_state=='confirmation_pending'
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.session_id==live[0].id))==0
    plan=cycle_member_reads.plan(actor(a['uid']),rid,n)['data']
    assert len(plan['schedule_groups'])==len(plan['sessions'])==1
    assert plan['schedule_groups'][0]['client_group_key']=='w3-manual'


def test_character_change_failure_preserves_whole_bundle(lifecycle,monkeypatch):
    from app.raid_rooms import cycle_member_reads
    engine,a,b=lifecycle
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);n=next_key()
    plan=cycle_member_reads.plan(actor(a['uid']),rid,n)
    ctx=commands.get_context(actor(a['uid']),rid,n,uuid.UUID(a['ids'][1]),'dealer','change_character')
    body=change_body(ctx,plan)
    tables=set(inspect(engine).get_table_names())-{'alembic_version','game_account_requests'}
    before=table_digests(engine,tables)
    original=commands.admission.core.release_assignment;calls=[]
    def failed(db,a,stamp):
        calls.append(1)
        if len(calls)==2:raise GameError('SYNTHETIC_SECOND_ITEM')
        return original(db,a,stamp)
    monkeypatch.setattr(commands.admission.core,'release_assignment',failed)
    denied('SYNTHETIC_SECOND_ITEM',character.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    assert table_digests(engine,tables)==before


def test_invalid_only_successor_blocks_handoff_but_can_cancel_own_target(lifecycle):
    from app.game_accounts.models import Activity
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    with session() as db,db.begin():db.delete(db.get(Activity,(b['cid'],uuid.UUID(b['ids'][0]))))
    ctx=leadership.get_cancel(actor(a['uid']),rid,n)
    assert ctx['data']['mode']=='auto_successor'
    assert ctx['data']['permission']['reason']=='SUCCESSOR_UNAVAILABLE'
    denied('SUCCESSOR_UNAVAILABLE',leadership.cancel,actor(a['uid']),rid,uuid.uuid4(),cancel_body(ctx))
    cancel_member(b,rid,n)
    cancel_member(a,rid,n)


@pytest.mark.parametrize('operation',['open','continue'])
def test_alternate_role_power_source_is_bound_to_context(lifecycle,operation):
    from app.game_accounts.models import CharacterRoleSummary
    from app.game_accounts.power_success import capture,RolePowerSuccess
    from tests.test_role_summaries import summary
    _,a,b=lifecycle
    room=create_room(a,combined=operation=='continue');rid=uuid.UUID(room['room_id']);n=next_key()
    w=a if operation=='open' else b
    if operation=='continue':add_member(b,rid,room['created_cycles'][0]['target_cycle_key'])
    cid=uuid.UUID(w['ids'][1])
    with session() as db,db.begin():
        head=CharacterRoleSummary(user_id=w['uid'],character_id=cid,ownership_revision=1,role='support',
            version=1,summary=summary(),saved_at=now(db))
        db.add(head);db.flush();capture(db,head)
    if operation=='open':ctx=opening.get(actor(w['uid']),rid,n,'open',cid,'support');body=opening_body(ctx)
    else:ctx=continuation.get(actor(w['uid']),rid,n,cid=cid,role='support');body=continue_body(ctx)
    assert ctx['data']['permission']['allowed']
    with session() as db,db.begin():
        success=db.get(RolePowerSuccess,(w['uid'],cid,1,'support'))
        success.power_revision+=1
        success.observed_at+=timedelta(microseconds=1)
    execute=opening.execute if operation=='open' else continuation.execute
    denied('TARGET_CONTEXT_STALE',execute,actor(w['uid']),rid,uuid.uuid4(),body)
