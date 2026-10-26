"""Accepted beta explicit-minute policy against disposable PostgreSQL only."""
import uuid
from datetime import date,datetime,time,timedelta,timezone
import pytest
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import (time_policy,beta_schedule,beta_schemas,beta_profile,cycle_creation,cycle_member_reads,
    cycle_opening,cycle_schemas,cycle_schedule_service as service,cycle_proposals,cycle_schedule,availability)
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_planning_models import CycleProposal
from app.raid_rooms.beta_models import BetaSchedule
from app.raid_rooms.integrated_models import RecruitmentRoom,RecruitmentSession,RecruitmentSegment
from app.raid_rooms.source_models import PersonalAvailability,TimeReservation,SessionParticipation
from app.raids.service import KST,cycle
from tests.test_beta_recruitment import beta,current,candidate,ready,sources,imported,people,worlds,preflight,request,client,PROFILE,actor,beta_join
from tests.test_recruitment_cycle_planning import response
from tests.test_recruitment_cycle_times import fingerprints,scheduled


def instant(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


def create_at(w,*,base=None,combined=False,enabled=False,http=False):
    with session() as db:
        base=base or time_policy.ceil_tick(now(db)+timedelta(hours=2)).astimezone(timezone.utc)+timedelta(minutes=3)
    key=cycle(base).cycle_key
    params=dict(base_starts_at=base.isoformat(),early_coordination_enabled='true' if enabled else 'false')
    if enabled:params['early_additional_members']='1'
    if combined:params.update(next_base_starts_at=(base+timedelta(days=7,minutes=1)).isoformat(),next_early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=preflight(w,key=key,continuation=combined)
        body=request(ctx).model_dump(mode='json');body.pop('schedule_groups');body['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        data=beta_schemas.BetaCreateRequest.model_validate(body);command=uuid.uuid4()
        if http:
            with client(w) as transport:
                result=transport.post('/v2/raid-rooms',params=PROFILE,json=body,headers={'Idempotency-Key':str(command)})
                assert result.status_code==201,result.json();ack=result.json()
        else:ack=cycle_creation.create(actor(w['uid']),command,data)[1]
    return uuid.UUID(ack['data']['room_id']),key,base,data,command,ack


def view(w,rid,key):
    with beta_profile.using():return cycle_member_reads.plan(actor(w['uid']),rid,key)


def proposal(w,rid,key,start,**changes):
    p=view(w,rid,key);d=p['data'];s=d['sessions'][0];segments=d['session_segments'][0]['segments']
    return cycle_schemas.Propose.model_validate(dict(expected_cycle_key=p['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=p['scope']['target_revision'],expected_plan_revision=d['revision'],expected_members_revision=d['members_revision'],
        expected_leadership_revision=d['leadership']['leadership_revision'],targets=[dict(session_id=s['session_id'],
            expected_schedule_revision=s['schedule_revision'],starts_at=start,
            item_durations=[dict(item_id=v['item_id'],duration_minutes=None) for v in segments])])|changes)


def outside_table(w):
    # A valid five-minute table in the distant past, outside all tested departures.
    intervals=[dict(weekday=1,start='00:00',end='00:05',end_day_offset=0)]
    with session() as db,db.begin():db.add(PersonalAvailability(user_id=w['uid'],revision=1,timezone='Asia/Seoul',
        intervals=intervals,normalized_intervals=availability.normalize(intervals),saved_at=now(db)))


def test_explicit_policy_precision_bounds_and_legacy_grid():
    start=datetime(2026,10,26,9,3,tzinfo=timezone.utc);key='2026-10-21';stamp=start-timedelta(minutes=31)
    cfg=dict(base_starts_at=start,early_coordination_enabled=False,early_additional_members=None)
    assert beta_schedule.config(cfg,key=key,capacity=4,duration=30,stamp=stamp).base_starts_at==start
    assert not time_policy.aligned(start) and time_policy.minute_aligned(start)
    for bad in [start+timedelta(seconds=1),start+timedelta(microseconds=1),start.astimezone(KST),start.replace(tzinfo=None)]:
        with pytest.raises(GameError,match='INVALID_REQUEST'):time_policy.interval(bad,bad+timedelta(minutes=30),key,minute_precision=True)
    for minutes in [0,-5,31,1445]:
        with pytest.raises(GameError,match='INVALID_REQUEST'):time_policy.interval(start,start+timedelta(minutes=minutes),key,minute_precision=True)
    with pytest.raises(GameError,match='INVALID_REQUEST'):time_policy.interval(start,start+timedelta(minutes=30),key)
    with pytest.raises(GameError,match='RECRUITMENT_CLOSED'):beta_schedule.config(cfg,key=key,capacity=4,duration=30,stamp=start-timedelta(minutes=30))
    with pytest.raises(GameError,match='SCHEDULE_BEFORE_FLOOR'):beta_schedule.config(cfg,key=key,capacity=4,duration=30,stamp=start-timedelta(minutes=29))
    first=datetime(2026,10,20,21,tzinfo=timezone.utc)
    with pytest.raises(GameError,match='MAINTENANCE_WINDOW'):time_policy.interval(first+timedelta(minutes=3),first+timedelta(minutes=33),key,minute_precision=True)
    with pytest.raises(GameError,match='CYCLE_CHANGED'):time_policy.interval(first+timedelta(days=7,minutes=-7),first+timedelta(days=7,minutes=23),key,minute_precision=True)


def test_explicit_minutes_create_c_n_http_reservations_and_ack(beta):
    engine,a,_=beta;outside_table(a);rid,key,base,data,command,ack=create_at(a,combined=True,http=True)
    with beta_profile.using():
        before=fingerprints(engine);assert cycle_creation.create(actor(a['uid']),command,data)==(201,ack);assert fingerprints(engine)==before
    with session() as db:
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)))
        assert len(rows)==2
        for i,row in enumerate(rows):
            expected=base+timedelta(days=7*i,minutes=i);saved=db.get(BetaSchedule,row.id);sess=db.get(RecruitmentSession,saved.session_id)
            assert saved.base_starts_at==sess.starts_at==expected
            segments=list(db.scalars(select(RecruitmentSegment).where(RecruitmentSegment.session_id==sess.id)))
            reservations=list(db.scalars(select(TimeReservation).where(TimeReservation.session_id==sess.id,TimeReservation.released_at.is_(None))))
            assert segments and reservations and all(v.starts_at==expected for v in segments+reservations)
            assert instant(view(a,rid,row.cycle_key.isoformat())['data']['beta_schedule']['base_starts_at'])==expected


def test_explicit_minutes_next_opening_context_post_and_replay(beta):
    engine,a,_=beta;rid,key,base,_,_,_=create_at(a);next_key=(date.fromisoformat(key)+timedelta(days=7)).isoformat();start=base+timedelta(days=7,minutes=1)
    params=dict(base_starts_at=start.isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):ctx=cycle_opening.get(actor(a['uid']),rid,next_key,'open')
    d=ctx['data'];assert instant(d['beta_schedule_config']['base_starts_at'])==start
    body=dict(expected_cycle_key=ctx['scope']['current_cycle_key'],target_cycle_key=next_key,expected_target_revision=None,
        context_token=d['context_token'],selection=d['selection'],target_items=d['targets'],target_session_ids=[],intent='open',beta_schedule=d['beta_schedule_config'])
    command=uuid.uuid4()
    with client(a) as transport:
        result=transport.post(f'/v2/raid-rooms/{rid}/recruitment-openings',params=PROFILE,json=body,headers={'Idempotency-Key':str(command)})
        assert result.status_code==200,result.json();before=fingerprints(engine)
        replay=transport.post(f'/v2/raid-rooms/{rid}/recruitment-openings',params=PROFILE,json=body,headers={'Idempotency-Key':str(command)})
        assert replay.status_code==200 and replay.json()==result.json() and fingerprints(engine)==before
    assert instant(view(a,rid,next_key)['data']['beta_schedule']['base_starts_at'])==start
    assert instant(view(a,rid,key)['data']['beta_schedule']['base_starts_at'])==base


@pytest.mark.parametrize('review',[False,True])
def test_explicit_minutes_n1_separate_acceptance_review_cas_and_replay(beta,review):
    engine,a,_=beta;outside_table(a);rid,key,base,_,_,_=create_at(a)
    if review:
        with session() as db,db.begin():
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid),row,base+timedelta(minutes=1))
    start=base+timedelta(minutes=61);command=uuid.uuid4()
    with beta_profile.using():
        data=proposal(a,rid,key,start);raw=data.model_dump(mode='json');raw['expected_plan_revision']+=1;bad=cycle_schemas.Propose.model_validate(raw);before=fingerprints(engine)
        with pytest.raises(GameError,match='REVISION_CONFLICT'):service.propose(actor(a['uid']),rid,uuid.uuid4(),bad)
        assert fingerprints(engine)==before
        status,ack=service.propose(actor(a['uid']),rid,command,data);pid=uuid.UUID(next(v['id'] for v in ack['data']['revisions'] if v['resource']=='proposal'))
        assert view(a,rid,key)['data']['beta_schedule']['confirmed_starts_at'] is None
        accept=response(a,rid,key,pid);vote=uuid.uuid4();applied=service.respond(actor(a['uid']),pid,vote,accept)
        assert applied[1]['data']['outcome']=='applied'
        before=fingerprints(engine);assert service.respond(actor(a['uid']),pid,vote,accept)==applied
        assert service.propose(actor(a['uid']),rid,command,data)==(status,ack);assert fingerprints(engine)==before
    result=view(a,rid,key)['data']['beta_schedule'];assert instant(result['confirmed_starts_at'])==start and result['coordination_state']=='proposal_confirmed'


def test_explicit_minutes_n2_votes_reevaluation_preserve_reservation_times(beta,monkeypatch):
    _,a,b=beta;rid,key,base,_,_,_=create_at(a);beta_join(b,rid,key);outside_table(b);start=base+timedelta(minutes=61)
    with beta_profile.using():
        _,ack=service.propose(actor(a['uid']),rid,uuid.uuid4(),proposal(a,rid,key,start))
        pid=uuid.UUID(next(v['id'] for v in ack['data']['revisions'] if v['resource']=='proposal'))
        original=cycle_proposals.evaluate;monkeypatch.setattr(cycle_proposals,'evaluate',lambda *args,**kw:False)
        service.respond(actor(b['uid']),pid,uuid.uuid4(),response(b,rid,key,pid))
        monkeypatch.setattr(cycle_proposals,'evaluate',original)
    assert view(a,rid,key)['data']['beta_schedule']['confirmed_starts_at'] is None
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));cycle_proposals.reevaluate(db,db.get(RecruitmentRoom,rid),row,a['uid'],uuid.uuid4(),now(db))
        saved=db.get(BetaSchedule,row.id);assert saved.confirmation_kind=='proposal_confirmed'
        values=list(db.scalars(select(TimeReservation).where(TimeReservation.session_id==saved.session_id,TimeReservation.released_at.is_(None))))
        assert len(values)==2 and all(v.starts_at==start for v in values)


def test_explicit_minutes_exact_deadline_fallback_and_delayed_review(beta):
    _,a,b=beta
    with session() as db:
        stamp=now(db);base=datetime.combine(stamp.astimezone(KST).date(),time(18,3),KST).astimezone(timezone.utc)
        if base<=stamp+timedelta(minutes=30):base+=timedelta(days=1)
    rid,key,_,_,_,_=create_at(a,base=base);rid2,_,_,_,_,_=create_at(b,base=base)
    assert instant(view(a,rid,key)['data']['beta_schedule']['base_deadline_at'])==base-timedelta(minutes=30)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));room=db.get(RecruitmentRoom,rid)
        beta_schedule.reconcile(db,room,row,base-timedelta(minutes=30,seconds=1));assert db.get(BetaSchedule,row.id).confirmation_kind is None
        assert cycle_schedule.choices(db,row,base-timedelta(minutes=30))[0]['permission']['allowed'] is False
        beta_schedule.reconcile(db,room,row,base-timedelta(minutes=30));saved=db.get(BetaSchedule,row.id)
        assert saved.confirmation_kind=='base_confirmed' and db.get(RecruitmentSession,saved.session_id).starts_at==base
        row2=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid2));beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid2),row2,base+timedelta(seconds=1))
        assert db.get(BetaSchedule,row2.id).needs_review and db.get(BetaSchedule,row2.id).confirmation_kind is None


def clone(row,**changes):return type(row)(**({c.name:getattr(row,c.name) for c in row.__table__.columns}|changes))


def test_explicit_minutes_automatic_grid_own_promise_and_other_reservation_edges(beta,monkeypatch):
    _,a,b=beta
    with session() as db:later=time_policy.ceil_tick(now(db)+timedelta(hours=6)).astimezone(timezone.utc)+timedelta(minutes=3)
    rid,key,base,_,_,_=create_at(a,base=later,enabled=True)
    original=beta_schedule.initial;monkeypatch.setattr(beta_schedule,'initial',lambda *args,**kw:None)
    beta_join(b,rid,key);monkeypatch.setattr(beta_schedule,'initial',original)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));room=db.get(RecruitmentRoom,rid);stamp=now(db)
        initial=beta_schedule.evaluate(db,room,row,stamp);assert initial['state']=='ready';first=initial['earliest_start'];assert first.minute%5==0 and first<base
        saved=db.get(BetaSchedule,row.id);sess=db.get(RecruitmentSession,saved.session_id)
        own=db.scalar(select(TimeReservation).where(TimeReservation.session_id==sess.id,TimeReservation.user_id==a['uid'],TimeReservation.released_at.is_(None)))
        duration=saved.base_ends_at-saved.base_starts_at;busy_start=first+duration;busy_end=busy_start+timedelta(minutes=30)
        def external_booking(start,end):
            external=clone(sess,id=uuid.uuid4(),starts_at=start,ends_at=end);db.add(external);db.flush()
            part=clone(db.get(SessionParticipation,own.participation_id),id=uuid.uuid4(),session_id=external.id);db.add(part);db.flush()
            segment=clone(db.get(RecruitmentSegment,own.segment_id),id=uuid.uuid4(),session_id=external.id,starts_at=start,ends_at=end,duration_minutes=30);db.add(segment);db.flush()
            reservation=clone(own,id=uuid.uuid4(),session_id=external.id,participation_id=part.id,segment_id=segment.id,starts_at=start,ends_at=end);db.add(reservation);db.flush()
            return reservation
        reservation=external_booking(busy_start,busy_end)
        assert beta_schedule.evaluate(db,room,row,stamp)['earliest_start']==first  # Exact adjacency is allowed.
        reservation.released_at=stamp;reservation.released_reason='schedule_changed';db.flush()
        external_booking(busy_start-timedelta(minutes=1),busy_end-timedelta(minutes=1))
        shifted=beta_schedule.evaluate(db,room,row,stamp);assert shifted['state']=='ready' and shifted['earliest_start']>=busy_end
        original(db,room,row,stamp);assert db.get(RecruitmentSession,saved.session_id).starts_at.minute%5==0 and saved.confirmation_kind=='early_confirmed'


def test_explicit_minutes_do_not_relax_legacy_proposal_or_profile_gate(beta):
    engine,a,_=beta;rid,key,_=scheduled(a,bundle=False);p=cycle_member_reads.plan(actor(a['uid']),rid,key);start=instant(p['data']['sessions'][0]['starts_at'])+timedelta(minutes=61)
    before=fingerprints(engine)
    with pytest.raises(GameError,match='INVALID_REQUEST'):service.propose(actor(a['uid']),rid,uuid.uuid4(),proposal(a,rid,key,start))
    assert fingerprints(engine)==before
    with beta_profile.using():
        with pytest.raises(GameError,match='BETA_SCHEDULE_REQUIRED'):service.propose(actor(a['uid']),rid,uuid.uuid4(),proposal(a,rid,key,start))
    assert fingerprints(engine)==before


def test_explicit_minutes_failed_install_rolls_back_business_state(beta,monkeypatch):
    engine,a,_=beta;before=fingerprints(engine);original=beta_schedule.install
    def fail_after_install(*args,**kwargs):original(*args,**kwargs);raise GameError('SERVICE_UNAVAILABLE',503)
    monkeypatch.setattr(beta_schedule,'install',fail_after_install)
    with pytest.raises(GameError,match='SERVICE_UNAVAILABLE'):create_at(a,combined=True)
    assert fingerprints(engine)==before


def test_explicit_minutes_create_final_deadline_crossing_rolls_back(beta,monkeypatch):
    from app.raid_rooms import cycles
    engine,a,_=beta;before=fingerprints(engine);real_now=cycles.now;installed=[];original=beta_schedule.install
    def after_install(*args,**kwargs):
        saved=original(*args,**kwargs);installed.append(saved.base_starts_at-timedelta(minutes=30));return saved
    monkeypatch.setattr(beta_schedule,'install',after_install)
    monkeypatch.setattr(cycles,'now',lambda db:installed[0] if installed else real_now(db))
    with pytest.raises(GameError,match='RECRUITMENT_CLOSED'):create_at(a)
    assert installed and fingerprints(engine)==before
