"""W4-D isolated cutover: exact rollover, read adapters and original ACKs."""
import uuid
from copy import deepcopy
from datetime import timedelta,datetime,time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func,text
from app.core.database import session,now
from app.raid_rooms import cycle_worker as worker,v1_compat,cycle_legacy,weekly_summary,weekly_summary_schemas,readiness
from app.raid_rooms.cycle_models import CycleGeneration,LegacyCycleEvidence
from app.raid_rooms.cycle_planning_models import CycleProposal
from app.raid_rooms.source_models import ScheduleProposal,ContinuationChoice
from tests.test_recruitment_cycle_outcomes import (outcomes,planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,plan,actor,add_member,cancel_member,fingerprints,denied,commands,cycles,preflight,request,creation,
    scoped,complete,make_proposal,respond,confirm,CycleMember,RoomCycle,Reservation,Assignment)
from tests.test_recruitment_cycle_management import transfer_body
from tests.test_recruitment_cycle_times_http import client
from tests.test_recruitment_cycle_http import validate


def rollover_stamp():
    with session() as db:return commands.raids.cycle(now(db)).ends_at


def graph_snapshot(rid,key):
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==datetime.fromisoformat(key).date()))
        members=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id)))
        values=[row,db.get(CycleGeneration,(row.id,row.generation)),*members,*worker.outcomes.assignments(db,row),
            *worker.graph.sessions(db,row,history=True),*db.scalars(select(Reservation).join(Assignment,Assignment.id==Reservation.assignment_id).where(
                Reservation.room_id==rid,Assignment.round_id.in_([r.id for _,r in worker.life.admission.rounds(db,row)])))]
        return deepcopy([worker.plan.snapshot(v) for v in values])


def test_rollover_keeps_actual_n_graph_and_proposal_without_auto_open(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);pid,_=make_proposal(a,rid,n)
    before=graph_snapshot(rid,n);stamp=rollover_stamp();monkeypatch.setattr(worker,'now',lambda db:stamp)
    worker.process_room(rid)
    assert graph_snapshot(rid,n)==before
    with session() as db,db.begin():
        old=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==datetime.fromisoformat(c).date()))
        assert old.state=='closed' and db.get(CycleGeneration,(old.id,old.generation)).state=='stopped'
        assert db.get(ScheduleProposal,pid).state=='pending'
        assert db.scalar(select(func.count()).select_from(RoomCycle).where(RoomCycle.room_id==rid))==2
    stable=fingerprints(engine);worker.process_room(rid);assert fingerprints(engine)==stable


def test_worker_duplicate_and_boundary_rollback(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);stamp=rollover_stamp();real=worker.now;calls=[];before=fingerprints(engine)
    def crossing(db):calls.append(1);return stamp if len(calls)==1 else stamp+timedelta(days=7)
    with monkeypatch.context() as m:
        m.setattr(worker,'now',crossing);denied('CYCLE_CHANGED',worker.process_room,rid)
    assert fingerprints(engine)==before
    monkeypatch.setattr(worker,'now',lambda db:stamp)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(worker.process_room,[rid,rid]))
    with session() as db,db.begin():
        from app.raid_rooms.cycle_models import ParticipationEvent
        assert db.scalar(select(func.count()).select_from(ParticipationEvent).where(ParticipationEvent.action=='stopped'))==1


def test_worker_invalid_promoted_source_review_retains_leases(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);before=graph_snapshot(rid,n)
    with session() as db,db.begin():
        from app.game_accounts.models import Character
        char=db.get(Character,uuid.UUID(a['ids'][0]));char.status='suspect'
    monkeypatch.setattr(worker,'now',lambda db:rollover_stamp());worker.process_room(rid)
    after=graph_snapshot(rid,n)
    assert after[0]['state']=='review_required' and after[1]['state']=='review_required'
    assert after[2:]==before[2:]
    with session() as db,db.begin():assert db.scalar(select(func.count()).select_from(LegacyCycleEvidence).where(LegacyCycleEvidence.room_id==rid))==2


def test_legacy_choices_http_missing_target_is_readonly(outcomes):
    engine,a,b=outcomes
    room=creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a)))[1]['data'];rid=uuid.UUID(room['room_id'])
    n=(datetime.fromisoformat(room['created_cycles'][0]['target_cycle_key']).date()+timedelta(days=7)).isoformat()
    before=fingerprints(engine)
    with client(a) as http:
        response=http.get(f'/v2/me/raid-rooms/{rid}/continuation-choices',params={'target_cycle_key':n})
        assert response.status_code==200,response.json();validate('/v2/me/raid-rooms/{room_id}/continuation-choices','get',200,response.json())
        assert response.json()['scope']['room_cycle_id'] is None
        assert response.json()['data']['permissions']['choose_continuation']['reason']=='CLIENT_UPGRADE_REQUIRED'
    assert fingerprints(engine)==before


def test_v1_current_reads_never_use_n_leader_or_settings(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n)
    from app.raid_rooms import cycle_leadership,cycle_management,admission_service,member_reads,management
    cycle_leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),transfer_body(a,rid,n,b))
    from tests.test_recruitment_cycle_management import settings
    cycle_management.command(actor(b['uid']),rid,uuid.uuid4(),settings(b,rid,n,experience_level='experienced'),'settings')
    before=fingerprints(engine)
    value=admission_service.plan(actor(a['uid']),rid)
    assert value['cycle_key']==c and value['my_membership']['room_role']=='leader'
    assert management.get_settings(actor(a['uid']),rid)['experience_level'] is None
    assert member_reads.summary(actor(a['uid']),rid)['app_member_count']==1
    assert len(member_reads.detail(actor(a['uid']),rid)['members'])==1
    assert fingerprints(engine)==before


def test_v1_safe_manual_guard_correction_and_original_ack(outcomes,monkeypatch):
    engine,a,b=outcomes
    from app.raid_weekly import service as weekly
    from tests.test_recruitment_cycle_outcomes import manual_body
    with session() as db:c=commands.raids.cycle(now(db)).cycle_key
    body=manual_body(a,'horizon_cathedral',c).model_dump(mode='json');body.pop('target_cycle_key')
    early=datetime.combine(datetime.fromisoformat(c).date(),time(9),commands.raids.KST)
    with monkeypatch.context() as m:
        m.setattr(weekly,'now',lambda db:early)
        denied('PLAY_NOT_STARTED',weekly.put,actor(a['uid']),uuid.UUID(a['ids'][0]),'horizon_cathedral',uuid.uuid4(),body)
        entry=weekly.get(actor(a['uid']),[uuid.UUID(a['ids'][0])])['entries'][0]
        assert not entry['can_mark_completed'] and entry['mark_blocked_reason']=='PLAY_NOT_STARTED'
    key=uuid.uuid4();result=weekly.put(actor(a['uid']),uuid.UUID(a['ids'][0]),'horizon_cathedral',key,body)
    with monkeypatch.context() as m:
        m.setattr(weekly,'now',lambda db:early+timedelta(days=7))
        assert weekly.put(actor(a['uid']),uuid.UUID(a['ids'][0]),'horizon_cathedral',key,body)==result


def test_v1_room_write_replays_ack_then_requires_upgrade(outcomes):
    _,a,b=outcomes
    from app.raid_rooms import admission_service as legacy
    from app.game_accounts.support import reserve,commit_result
    key=uuid.uuid4();payload={'synthetic':'original'};principal=actor(a['uid'])
    ticket,replay=reserve(principal,'recruitment-cutover-ack',key,payload)
    with session() as db,db.begin():original=commit_result(db,ticket,200,{'synthetic':'original'})
    forbidden=lambda *args:pytest.fail('Old mutation must not execute')
    assert legacy.execute(principal,'cutover-ack',key,payload,forbidden)==original
    denied('CLIENT_UPGRADE_REQUIRED',legacy.execute,principal,'cutover-ack',uuid.uuid4(),payload,forbidden)


def test_declined_summary_then_general_join_takes_priority(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    from app.raid_rooms import cycle_continuation as continuation
    ctx=continuation.get(actor(b['uid']),rid,n,'decline')
    from tests.test_recruitment_cycle_lifecycle import scoped as context_scoped
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),worker.life.wire.ScopedCommand.model_validate(context_scoped(ctx)),decline=True)
    body=weekly_summary_schemas.SummaryRequest(character_ids=[uuid.UUID(b['ids'][0])],target_cycle_keys=[n])
    value=weekly_summary.summary(actor(b['uid']),body)
    assert {e['continuation_state'] for e in value['entries'] if e['raid_id'] in ('horizon_cathedral','kazeros_act4')}=={'declined'}
    add_member(b,rid,n)
    value=weekly_summary.summary(actor(b['uid']),body)
    assert {e['continuation_state'] for e in value['entries'] if e['raid_id'] in ('horizon_cathedral','kazeros_act4')}=={'confirmed'}


def test_prepared_app_startup_and_full_route_contract(outcomes):
    from app.main import create_two_cycle_app,app
    from fastapi.testclient import TestClient
    candidate=create_two_cycle_app()
    with TestClient(candidate):pass
    with session() as db,db.begin():denied('SERVICE_UNAVAILABLE',readiness.require_active,db);readiness.require_two_cycle_active(db)
    spec=candidate.openapi();assert len(app.openapi()['paths'])==116
    import json
    from pathlib import Path
    fixed=json.loads(Path('docs/features/recruitment/artifacts/issue13-two-cycle.full.openapi.json').read_text())
    assert set(fixed['paths'])<=set(spec['paths'])
    assert all(method in spec['paths'][path] and spec['paths'][path][method]['operationId']==operation['operationId']
        for path,ops in fixed['paths'].items() for method,operation in ops.items())


def test_prepared_app_v1_http_projections_and_unsafe_write(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n)
    from app.main import create_two_cycle_app
    from app.auth.router import authenticated
    from app.raid_rooms.router import optional_principal
    from fastapi.testclient import TestClient
    application=create_two_cycle_app();application.dependency_overrides[authenticated]=lambda:actor(a['uid'])
    application.dependency_overrides[optional_principal]=lambda:actor(a['uid'])
    before=fingerprints(engine)
    with TestClient(application) as http:
        for path in [f'/v1/raid-rooms/{rid}',f'/v1/raid-rooms/{rid}/detail',f'/v1/me/raid-rooms/{rid}/plan',
            f'/v1/me/raid-rooms/{rid}/settings',f'/v1/me/raid-rooms/{rid}/schedule-context',
            f'/v1/me/raid-rooms/{rid}/availability-submission',f'/v1/me/raid-rooms/{rid}/continuation-choices',
            '/v1/raid-rooms','/v1/me/raid-room-memberships','/v1/me/raid-room-applications','/v1/me/raid-schedule-overlaps']:
            response=http.get(path);assert response.status_code==200,(path,response.json());assert response.headers['cache-control']=='no-store'
        assert http.get(f'/v1/raid-rooms/{rid}').json()['permissions']['view_plan']['allowed']
        value=http.get(f'/v1/me/raid-rooms/{rid}/plan').json()
        assert not value['my_participations'][0]['permissions']['confirm_participation']['allowed']
        body=dict(expected_cycle_key=c,expected_room_revision=1,expected_members_revision=value['members_revision'],
            expected_plan_revision=value['revision'],expected_membership_revision=value['my_membership']['revision'])
        response=http.post(f'/v1/raid-rooms/{rid}/leave',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==409,response.json();assert response.json()['error']['code']=='CLIENT_UPGRADE_REQUIRED'
    assert fingerprints(engine)==before


def test_decline_to_one_room_never_overrides_other_room_occupancy(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    from app.raid_rooms import cycle_continuation as continuation
    from tests.test_recruitment_cycle_lifecycle import scoped as context_scoped
    ctx=continuation.get(actor(b['uid']),rid,n,'decline')
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),worker.life.wire.ScopedCommand.model_validate(context_scoped(ctx)),decline=True)
    made=creation.create(actor(b['uid']),uuid.uuid4(),request(preflight(b,key=n,bundle=True)))[1]['data']
    body=weekly_summary_schemas.SummaryRequest(character_ids=[uuid.UUID(b['ids'][0])],target_cycle_keys=[n])
    entries=weekly_summary.summary(actor(b['uid']),body)['entries']
    assert {e['participation']['room_id'] for e in entries if e['participation']}=={uuid.UUID(made['room_id'])}
    assert all(e['continuation_state']=='confirmed' for e in entries if e['participation'])


def test_worker_old_implementation_cannot_run_on_cutover_storage(outcomes):
    _,a,b=outcomes
    from app.raid_rooms import continuation
    denied('SERVICE_UNAVAILABLE',continuation.process_due)
    with session() as db:readiness.require_cycle_worker(db)


def test_cycle_summary_review_has_no_executable_confirmed_default(outcomes):
    _,a,b=outcomes;rid,c,n=scheduled(a)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==datetime.fromisoformat(n).date()))
        row.state='review_required'
    body=weekly_summary_schemas.SummaryRequest(character_ids=[uuid.UUID(a['ids'][0])],target_cycle_keys=[n])
    for e in weekly_summary.summary(actor(a['uid']),body)['entries']:
        if e['participation']:assert e['participation']['status']=='review_required' and e['continuation_state']=='blocked'


def test_v1_plan_projects_current_regular_and_resume_proposals(outcomes):
    _,a,b=outcomes;rid,c,n=scheduled(a);pid,_=make_proposal(a,rid,c)
    from app.raid_rooms import admission_service as legacy
    value=legacy.plan(actor(a['uid']),rid);assert value['proposals'][0]['proposal_id']==str(pid)
    complete(a,rid,c,'close_weekly')
    from tests.test_recruitment_cycle_outcomes import propose_resume
    resumed=propose_resume(a,rid,c)
    value=legacy.plan(actor(a['uid']),rid)
    assert any(p['proposal_id']==str(resumed) and p.get('kind')=='weekly_resume' for p in value['proposals'])


def test_rollover_partial_completion_is_preserved(outcomes,monkeypatch):
    _,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c,index=0)
    with session() as db,db.begin():
        done=db.scalar(select(Assignment).where(Assignment.room_id==rid,Assignment.state=='completed'))
        original=deepcopy(worker.plan.snapshot(done));aid=done.id
    before=graph_snapshot(rid,n);stamp=rollover_stamp();monkeypatch.setattr(worker,'now',lambda db:stamp)
    worker.process_room(rid)
    assert graph_snapshot(rid,n)==before
    with session() as db,db.begin():assert worker.plan.snapshot(db.get(Assignment,aid))==original


def test_old_generation_decline_is_history_after_explicit_reopen(outcomes):
    _,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    from app.raid_rooms import cycle_continuation as continuation,cycle_opening as opening
    from tests.test_recruitment_cycle_lifecycle import scoped as context_scoped,opening_body
    ctx=continuation.get(actor(b['uid']),rid,n,'decline')
    continuation.execute(actor(b['uid']),rid,uuid.uuid4(),worker.life.wire.ScopedCommand.model_validate(context_scoped(ctx)),decline=True)
    cancel_member(a,rid,n)
    ctx=opening.get(actor(a['uid']),rid,n,'reopen')
    opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx,'reopen'))
    body=weekly_summary_schemas.SummaryRequest(character_ids=[uuid.UUID(b['ids'][0])],target_cycle_keys=[n])
    assert all(e['continuation_state']!='declined' for e in weekly_summary.summary(actor(b['uid']),body)['entries'])
