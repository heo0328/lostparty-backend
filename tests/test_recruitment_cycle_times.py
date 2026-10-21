"""W4-A1 target submissions/consent; restricted synthetic PostgreSQL only."""
import os,subprocess,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import inspect,select,func,text
from sqlalchemy.exc import DBAPIError
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_times as times,cycle_wire as wire,cycle_schemas as inputs
from app.raid_rooms import cycle_schedule as schedule,cycle_member_reads as reads,readiness,availability
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleSubmission
from app.raid_rooms.cycle_consent_models import CycleConsent
from app.raid_rooms.source_models import TimeReservation as Reservation,SessionParticipation as Participation,PersonalAvailability
from tests.test_recruitment_cycle_lifecycle import (lifecycle,candidate,ready,sources,imported,people,worlds,
    preflight,request,creation,commands,cycles,actor,denied,next_key,add_member,cancel_member,change_body,character)
from tests.test_raid_room_migrations import table_digests


def upgrade(engine):
    tables=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,tables)
    done=subprocess.run(['alembic','upgrade','0027_cycle_consents'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert done.returncode==0,done.stderr.decode()[-2200:]
    assert table_digests(engine,tables)==before
    with session() as db,db.begin():
        readiness.require_ready(db,integrated=True)
        with pytest.raises(GameError):readiness.require_active(db)
        with pytest.raises(GameError):readiness.require_legacy_worker(db)


@pytest.fixture
def consent(lifecycle):
    engine,a,b=lifecycle;upgrade(engine)
    return engine,a,b


def scheduled(w,*,bundle=True,alternatives=1):
    ctx=preflight(w,continuation=True,bundle=bundle)
    with session() as db,db.begin():
        stamp=now(db);bounds=commands.raids.cycle(stamp)
        start=schedule.graph.time.ceil_tick(max(stamp+timedelta(minutes=60),bounds.starts_at+timedelta(hours=4)))
    if start+timedelta(hours=1)>=bounds.ends_at:pytest.skip('Insufficient safe interval before real cycle boundary')
    local=start.astimezone(commands.raids.KST)
    groups=[dict(client_group_key='consent-manual',existing_group_id=None,expected_group_revision=None,
        occurrence_mode='each',planning_mode='manual',required=True,auto_confirm_additional_members=None,
        day_scope='selected_weekdays',alternatives=[dict(client_alternative_key='one',existing_session_id=None,
            expected_session_revision=None,weekday=local.isoweekday(),starts_local=local.strftime('%H:%M'),
            leader_latest_start_local=None,item_order=[t['raid_id'] for t in ctx['data']['targets']])])]
    original=groups[0]['alternatives'][0]
    groups[0]['alternatives']=[original|dict(client_alternative_key=f'choice-{i}') for i in range(alternatives)]
    room=creation.create(actor(w['uid']),uuid.uuid4(),request(ctx,schedule_groups=groups))[1]['data']
    return uuid.UUID(room['room_id']),room['created_cycles'][0]['target_cycle_key'],next_key()


def plan(w,rid,key):return reads.plan(actor(w['uid']),rid,key)


def confirmation(w,rid,key,index=0):
    view=plan(w,rid,key);sess=view['data']['sessions'][index]
    part=next(p for p in view['data']['my_participations'] if p['session_id']==sess['session_id'])
    return uuid.UUID(sess['session_id']),inputs.Confirm.model_validate(dict(expected_cycle_key=view['scope']['current_cycle_key'],
        target_cycle_key=key,expected_target_revision=view['scope']['target_revision'],
        expected_cycle_member_revision=view['data']['my_membership']['cycle_member_revision'],
        expected_participation_revision=part['revision'],expected_schedule_revision=sess['schedule_revision']))


def confirm(w,rid,key,command=None):
    sid,data=confirmation(w,rid,key)
    return times.confirm(actor(w['uid']),sid,command or uuid.uuid4(),data)


def save_personal(w,*,intervals=None):
    view=availability.get(actor(w['uid']))
    body=dict(expected_version=view['version'],timezone='Asia/Seoul',intervals=intervals if intervals is not None else [
        dict(weekday=d,start='00:00',end='00:00',end_day_offset=1) for d in range(1,8)])
    return availability.put(actor(w['uid']),uuid.uuid4(),body)[1]


def submission(w,rid,key):
    ctx=times.get_submission(actor(w['uid']),rid,key)
    personal=availability.get(actor(w['uid']))
    return inputs.Submission.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=ctx['scope']['target_revision'],expected_cycle_member_revision=ctx['data']['cycle_member_revision'],
        expected_submission_revision=ctx['data']['revision'],expected_personal_version=personal['version']))


def submit(w,rid,key,command=None):
    return times.put_submission(actor(w['uid']),rid,command or uuid.uuid4(),submission(w,rid,key))


def fingerprints(engine):
    return table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version','game_account_requests'})


def test_migration_keeps_existing_confirmed_reservations_and_runtime_guards(lifecycle):
    engine,a,b=lifecycle
    rid,c,n=scheduled(a)
    with session() as db,db.begin():
        old=list(db.scalars(select(Reservation).where(Reservation.room_id==rid)))
        assert len(old)==2 and all(r.released_at is None for r in old)
    upgrade(engine)
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleConsent))==0
        assert len(list(db.scalars(select(Reservation).where(Reservation.room_id==rid))))==2
    # Creating a new confirmation in C is a noop, not retroactive new consent.
    assert confirm(a,rid,c)[1]['data']['outcome']=='noop'


def test_submission_is_explicit_target_snapshot_noop_and_personal_independent(consent):
    engine,a,b=consent;rid,c,n=scheduled(a)
    before=fingerprints(engine)
    value=times.get_submission(actor(a['uid']),rid,n)
    assert value['data']['state']=='missing' and value['data']['revision']==1
    times.time_context(actor(a['uid']),rid,n)
    times.overlaps(actor(a['uid']),n)
    assert fingerprints(engine)==before
    saved=save_personal(a);result=submit(a,rid,n)[1]
    assert result['data']['source_personal_version']==saved['version']
    assert result['data']['revision']==2 and len(result['data']['intervals'])==7
    assert times.get_submission(actor(a['uid']),rid,c)['data']['state']=='missing'
    before=fingerprints(engine);submit(a,rid,n)
    assert fingerprints(engine)==before
    save_personal(a,intervals=[])
    assert times.get_submission(actor(a['uid']),rid,n)['data']==result['data']
    assert submit(a,rid,n)[1]['data']['intervals']==[]
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleConsent))==0


def test_missing_personal_and_stale_versions_leave_all_tables_unchanged(consent):
    engine,a,b=consent;rid,c,n=scheduled(a)
    before=fingerprints(engine)
    denied('PERSONAL_AVAILABILITY_REQUIRED',times.put_submission,actor(a['uid']),rid,uuid.uuid4(),submission(a,rid,n))
    assert fingerprints(engine)==before
    save_personal(a);old=submission(a,rid,n);save_personal(a,intervals=[])
    before=fingerprints(engine)
    denied('REVISION_CONFLICT',times.put_submission,actor(a['uid']),rid,uuid.uuid4(),old)
    assert fingerprints(engine)==before
    submit(a,rid,n)
    before=fingerprints(engine)
    denied('TARGET_CONTEXT_STALE',times.put_submission,actor(a['uid']),rid,uuid.uuid4(),old)
    assert fingerprints(engine)==before


def test_persistent_or_other_cycle_membership_does_not_allow_private_target(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);add_member(b,rid,c)
    before=fingerprints(engine)
    for fn in (times.get_submission,times.time_context):
        denied('WEEKLY_PARTICIPANT_REQUIRED',fn,actor(b['uid']),rid,n)
    assert fingerprints(engine)==before


def test_submission_original_ack_after_cancel_and_week_change(consent,monkeypatch):
    engine,a,b=consent;rid,c,n=scheduled(a);save_personal(a)
    command=uuid.uuid4();body=submission(a,rid,n)
    ack=times.put_submission(actor(a['uid']),rid,command,body)
    cancel_member(a,rid,n)
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=14))
    before=fingerprints(engine)
    assert times.put_submission(actor(a['uid']),rid,command,body)==ack
    assert fingerprints(engine)==before


def test_explicit_n_confirmation_and_noop_preserve_c_and_other_members(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);add_member(b,rid,n)
    with session() as db,db.begin():
        old={r.id:r.released_at for r in db.scalars(select(Reservation).where(Reservation.room_id==rid))}
    sid,body=confirmation(b,rid,n)
    initial=plan(b,rid,n)['data']['my_participations'][0]
    assert initial['confirmation_state']=='confirmation_pending' and 'OUTSIDE_AVAILABILITY' in initial['warnings']
    assert initial['permissions']['confirm_participation']['allowed']
    command=uuid.uuid4();ack=times.confirm(actor(b['uid']),sid,command,body)
    assert ack[1]['data']['outcome']=='applied'
    with session() as db,db.begin():
        assert all(db.get(Reservation,k).released_at==v for k,v in old.items())
        consent=db.scalar(select(CycleConsent));assert consent.user_id==b['uid']
        assert len(consent.evidence['reservations'])==len(consent.evidence['assignments'])==2
        assert consent.evidence['submission']['state']=='missing'
    before=fingerprints(engine)
    assert times.confirm(actor(b['uid']),sid,command,body)==ack
    assert confirm(b,rid,n)[1]['data']['outcome']=='noop'
    assert fingerprints(engine)==before
    assert plan(a,rid,n)['data']['my_participations'][0]['confirmation_state']=='confirmation_pending'


def test_same_session_schedule_reconsent_after_cancel_rejoin_keeps_history(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);add_member(b,rid,n);save_personal(b);submit(b,rid,n)
    sid,body=confirmation(b,rid,n);command=uuid.uuid4()
    oldack=times.confirm(actor(b['uid']),sid,command,body)
    part_id=plan(b,rid,n)['data']['my_participations'][0]['participation_id']
    cancel_member(b,rid,n)
    with session() as db,db.begin():
        released=list(db.scalars(select(Reservation).where(Reservation.user_id==b['uid'])))
        old={r.id:(r.released_at,r.released_reason,r.starts_at,r.ends_at) for r in released}
        assert len(old)==2 and all(r.released_at for r in released)
    add_member(b,rid,n)
    view=plan(b,rid,n)['data']['my_participations'][0]
    assert view['participation_id']==part_id and view['confirmation_state']=='confirmation_pending'
    assert times.get_submission(actor(b['uid']),rid,n)['data']['state']=='missing'
    before=fingerprints(engine)
    assert times.confirm(actor(b['uid']),sid,command,body)==oldack
    assert fingerprints(engine)==before
    confirm(b,rid,n)
    with session() as db,db.begin():
        assert all((r.released_at,r.released_reason,r.starts_at,r.ends_at)==v for k,v in old.items() for r in [db.get(Reservation,k)])
        fresh=list(db.scalars(select(Reservation).where(Reservation.user_id==b['uid'],Reservation.released_at.is_(None))))
        assert len(fresh)==2 and not set(old)&{r.id for r in fresh}
        assert {r.schedule_revision for r in fresh}=={body.expected_schedule_revision}
        assert db.scalar(select(func.count()).select_from(CycleConsent).where(CycleConsent.user_id==b['uid']))==2


def test_character_change_requires_new_consent_and_original_snapshot_is_kept(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);confirm(a,rid,n)
    ctx=commands.get_context(actor(a['uid']),rid,n,uuid.UUID(a['ids'][1]),'dealer','change_character')
    character.execute(actor(a['uid']),rid,uuid.uuid4(),change_body(ctx,plan(a,rid,n)))
    assert plan(a,rid,n)['data']['my_participations'][0]['confirmation_state']=='confirmation_pending'
    confirm(a,rid,n)
    with session() as db,db.begin():
        events=list(db.scalars(select(CycleConsent).order_by(CycleConsent.effective_at)))
        assert [c.evidence['assignments'][0]['character_id'] for c in events]==[a['ids'][0],a['ids'][1]]
        assert len(list(db.scalars(select(Reservation).where(Reservation.released_at.is_(None)))))==4


def test_wrong_session_cycle_and_strict_cas_never_write(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);sid,body=confirmation(a,rid,n)
    before=fingerprints(engine)
    wrong=inputs.Confirm.model_validate(body.model_dump(mode='json')|{'target_cycle_key':c})
    denied('TARGET_SCOPE_MISMATCH',times.confirm,actor(a['uid']),sid,uuid.uuid4(),wrong)
    denied('REVISION_CONFLICT',times.confirm,actor(a['uid']),sid,uuid.uuid4(),body.model_copy(update={'expected_cycle_member_revision':99}))
    denied('TARGET_SCOPE_MISMATCH',times.time_context,actor(a['uid']),rid,c,sid)
    assert fingerprints(engine)==before


def test_confirmation_partial_failure_and_final_end_boundary_roll_back(consent,monkeypatch):
    engine,a,b=consent;rid,c,n=scheduled(a);sid,body=confirmation(a,rid,n)
    before=fingerprints(engine);real=times.CycleConsent
    def failed(**kwargs):raise GameError('SYNTHETIC_CONSENT_FAILURE')
    monkeypatch.setattr(times,'CycleConsent',failed)
    denied('SYNTHETIC_CONSENT_FAILURE',times.confirm,actor(a['uid']),sid,uuid.uuid4(),body)
    assert fingerprints(engine)==before
    monkeypatch.setattr(times,'CycleConsent',real)
    with session() as db,db.begin():end=db.get(schedule.Session,sid).ends_at
    clock=cycles.now;calls=[]
    def boundary(db):calls.append(1);return clock(db) if len(calls)==1 else end
    monkeypatch.setattr(cycles,'now',boundary)
    denied('CYCLE_CHANGED',times.confirm,actor(a['uid']),sid,uuid.uuid4(),body)
    assert fingerprints(engine)==before


def test_concurrent_confirmation_has_one_consent_and_exact_bundle(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);sid,body=confirmation(a,rid,n)
    def attempt(_):
        try:return times.confirm(actor(a['uid']),sid,uuid.uuid4(),body)[0]
        except GameError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(map(str,results))==['200','TARGET_CONTEXT_STALE']
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleConsent))==1
        assert db.scalar(select(func.count()).select_from(Reservation).where(Reservation.session_id==sid))==2


def test_released_reservations_and_consents_are_immutable(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);confirm(a,rid,n);cancel_member(a,rid,n)
    with session() as db,db.begin():
        row=db.scalar(select(Reservation).where(Reservation.released_at.is_not(None)))
        for sql in ('UPDATE recruitment_reservations SET released_at=NULL,released_reason=NULL WHERE id=:id',
                    'DELETE FROM recruitment_reservations WHERE id=:id'):
            with pytest.raises(DBAPIError):
                with db.begin_nested():db.execute(text(sql),{'id':row.id})
        consent=db.scalar(select(CycleConsent))
        with pytest.raises(DBAPIError):
            with db.begin_nested():db.execute(text("UPDATE recruitment_cycle_consents SET evidence='{}' WHERE id=:id"),{'id':consent.id})


def test_anonymous_busy_excludes_target_session_and_exposes_no_origin(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);add_member(b,rid,n);confirm(b,rid,n)
    sid,_=confirmation(b,rid,n)
    context=times.time_context(actor(a['uid']),rid,n)
    member=next(m for m in context['data']['members'] if m['membership_id']==plan(b,rid,n)['data']['my_membership']['membership_id'])
    assert len(member['anonymous_busy']['intervals'])==1
    assert set(member['anonymous_busy']['intervals'][0])=={'starts_at','ends_at'}
    excluded=times.time_context(actor(a['uid']),rid,n,sid)
    assert not any(m['anonymous_busy']['intervals'] for m in excluded['data']['members'])
    assert times.time_context(actor(a['uid']),rid,c)['data']['members'][0]['anonymous_busy']['intervals']
    assert times.overlaps(actor(b['uid']),c)['data']['items']==[]


def test_overlapping_sessions_warn_without_veto_and_cursor_is_target_bound(consent):
    engine,a,b=consent;rid,c,n=scheduled(a,alternatives=2)
    for index in range(2):
        sid,body=confirmation(a,rid,n,index)
        times.confirm(actor(a['uid']),sid,uuid.uuid4(),body)
    view=plan(a,rid,n)
    assert all(p['overlap_warning'] for p in view['data']['my_participations'])
    page=times.overlaps(actor(a['uid']),n,1)['data']
    assert page['pair_count']==2 and page['reservation_count']==4 and page['affected_room_count']==1
    assert page['next_cursor'] and len(page['items'])==1
    other=times.overlaps(actor(a['uid']),n,1,page['next_cursor'])['data']
    assert other['items'][0]['pair_id']!=page['items'][0]['pair_id'] and other['next_cursor'] is None
    denied('CURSOR_STALE',times.overlaps,actor(a['uid']),c,1,page['next_cursor'])
    cancel_member(a,rid,n)
    denied('CURSOR_STALE',times.overlaps,actor(a['uid']),n,1,page['next_cursor'])
    assert times.overlaps(actor(a['uid']),n)['data']['reservation_count']==0


def test_invalid_current_character_blocks_confirmation_but_not_cancellation(consent):
    from app.game_accounts.models import Activity
    engine,a,b=consent;rid,c,n=scheduled(a);sid,body=confirmation(a,rid,n)
    with session() as db,db.begin():db.delete(db.get(Activity,(a['cid'],uuid.UUID(a['ids'][0]))))
    initial=plan(a,rid,n)['data']['my_participations'][0]
    assert not initial['permissions']['confirm_participation']['allowed']
    before=fingerprints(engine)
    denied(initial['permissions']['confirm_participation']['reason'],times.confirm,actor(a['uid']),sid,uuid.uuid4(),body)
    assert fingerprints(engine)==before
    cancel_member(a,rid,n)


def test_db_guards_reject_rewriting_active_reservation_and_wrong_consent_owner(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);confirm(a,rid,n)
    with session() as db,db.begin():
        reservation=db.scalar(select(Reservation).where(Reservation.room_id==rid,Reservation.released_at.is_(None)))
        with pytest.raises(DBAPIError):
            with db.begin_nested():db.execute(text('UPDATE recruitment_reservations SET ends_at=ends_at+interval \'5 minutes\' WHERE id=:id'),{'id':reservation.id})
        consent=db.scalar(select(CycleConsent))
        assert db.scalar(text('SELECT record_created_at IS NOT NULL AND record_updated_at=record_created_at FROM recruitment_cycle_consents WHERE id=:id'),{'id':consent.id})
        with pytest.raises(DBAPIError):
            with db.begin_nested():db.execute(text('''INSERT INTO recruitment_cycle_consents
                (id,room_id,cycle_id,generation,cycle_member_id,membership_id,user_id,participation_id,session_id,command_id,
                 member_revision,participation_revision,schedule_revision,effective_at,evidence)
                SELECT :id,room_id,cycle_id,generation,cycle_member_id,membership_id,:uid,participation_id,session_id,:cmd,
                 member_revision,participation_revision+1,schedule_revision,effective_at,evidence FROM recruitment_cycle_consents WHERE id=:original'''),
                {'id':uuid.uuid4(),'uid':b['uid'],'cmd':uuid.uuid4(),'original':consent.id})
