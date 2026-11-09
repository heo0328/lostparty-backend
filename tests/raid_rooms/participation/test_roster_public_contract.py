"""Real routes and transactions on disposable PostgreSQL for #17."""
import json
import uuid
from copy import deepcopy
from datetime import date
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from sqlalchemy import select
from sqlalchemy import inspect
from app.core.database import session
from app.core.database import now
from app.core.errors import register
from app.auth.router import authenticated
from app.raid_rooms.participation import roster_participation as rp
from app.raid_rooms.participation import cycle_character
from app.raid_rooms.reads import cycle_member_reads
from app.raid_rooms.outcomes import cycle_outcomes
from app.raid_rooms.schemas import cycle_schemas
from app.raid_rooms.common import cycle_worker
from app.raid_rooms.participation import cycle_lifecycle
from app.raid_rooms.participation import character_issues
from app.raid_rooms.models.cycle_models import RoomCycle
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.game_accounts.rosters import bootstrap
from app.game_accounts.rosters import lifecycle_reads
from app.game_accounts.common.support import GameError
from tests.raid_rooms.participation.test_roster_participation_issues import presence_db
from tests.raid_rooms.participation.test_roster_participation_issues import policy_db
from tests.raid_rooms.participation.test_roster_participation_issues import group_beta
from tests.raid_rooms.participation.test_roster_participation_issues import beta
from tests.raid_rooms.participation.test_roster_participation_issues import current
from tests.raid_rooms.participation.test_roster_participation_issues import candidate
from tests.raid_rooms.participation.test_roster_participation_issues import ready
from tests.raid_rooms.participation.test_roster_participation_issues import sources
from tests.raid_rooms.participation.test_roster_participation_issues import imported
from tests.raid_rooms.participation.test_roster_participation_issues import people
from tests.raid_rooms.participation.test_roster_participation_issues import worlds
from tests.raid_rooms.participation.test_roster_participation_issues import observe
from tests.raid_rooms.participation.test_roster_participation_issues import joined
from tests.raid_rooms.participation.test_roster_participation_issues import qualified
from tests.raid_rooms.admissions.test_recruitment_cycle_creation import preflight
from tests.raid_rooms.admissions.test_recruitment_cycle_creation import request
from tests.raid_rooms.admissions.test_recruitment_cycle_creation import creation
from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import change_body
from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import complete
from tests.raid_rooms.admissions.test_recruitment_cycle_http import client
from tests.groups.test_group_foundation import actor
from tests.raid_rooms.common.test_raid_room_migrations import table_digests

Q=dict(contract_profile='beta-recruitment-1',group_policy_version='cycle-group-policy-1')
P=dict(participation_profile=rp.PROFILE)
SCHEMAS=json.loads(Path('app/raid_rooms/contracts/roster_metadata.schema.json').read_text())


def valid(name,value):
    Draft202012Validator(dict(**SCHEMAS[name],components=dict(schemas=SCHEMAS)),
        format_checker=FormatChecker()).validate(jsonable_encoder(value))


def bundle(w, *, continuation=True):
    from app.raid_rooms.common import beta_profile
    from app.raid_rooms.schedules import beta_schedule
    from app.raid_rooms.schemas import beta_schemas
    with session() as db:base=beta_schedule.time_policy.ceil_tick(now(db)+timedelta(hours=2))
    params=dict(base_starts_at=base.isoformat(),early_coordination_enabled='false')
    if continuation:
        params.update(next_base_starts_at=(base+timedelta(days=7)).isoformat(),next_early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=preflight(w,continuation=continuation,bundle=True)
        body=request(ctx).model_dump(mode='json')
        body.pop('schedule_groups');body['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        ack=creation.create(actor(w['uid']),uuid.uuid4(),beta_schemas.BetaCreateRequest.model_validate(body))[1]['data']
    return uuid.UUID(ack['room_id']),*[r['target_cycle_key'] for r in ack['created_cycles']]


def change(w,rid,key):
    ctx=cycle_character.get(actor(w['uid']),rid,key,uuid.UUID(w['ids'][1]),'dealer',True)
    plan=cycle_member_reads.plan(actor(w['uid']),rid,key)
    plan['data']['my_assignments']=[a for a in plan['data']['my_assignments'] if a['state']=='active']
    return change_body(ctx,plan)


def test_presence_bootstrap_http_and_page_share_scope(presence_db):
    _,a,b=presence_db
    observe(b)
    from app.main import create_two_cycle_app
    application=create_two_cycle_app()
    application.dependency_overrides[authenticated]=lambda:actor(b['uid'])
    with TestClient(application) as http:
        root=http.get('/v2/me/account-bootstrap',params=dict(include_roster_presence='true'))
        assert root.status_code==200,root.text
        all_chars=next(v['characters'] for v in root.json()['registrations'] if v['registration']['registration_id']==b['rid'])
        page=http.get(f'/v2/me/game-accounts/{b["rid"]}/characters',params=dict(include_roster_presence='true',limit=1))
        assert page.status_code==200,page.text
        value=page.json()
        assert {k:v for k,v in value['roster_presence_scope'].items() if k!='evaluated_at'}=={
            k:v for k,v in all_chars['roster_presence_scope'].items() if k!='evaluated_at'}
        assert [c for c in all_chars['items'] if c['character_id']==b['ids'][0]][0]['roster_presence']['state']=='missing'
        assert any(c['roster_presence']['state']=='present' for c in all_chars['items'])
        assert 'roster_presence_scope' not in http.get(f'/v2/me/game-accounts/{b["rid"]}/characters').json()
        assert http.get('/v2/me/account-bootstrap?include_roster_presence=invalid').status_code==400
    observe(b,absent=False)
    value=lifecycle_reads.characters(actor(b['uid']),uuid.UUID(b['rid']),50,None,True)
    assert next(c for c in value['items'] if str(c['character_id'])==b['ids'][0])['roster_presence']['state']=='present'


def test_public_issue_privacy_and_default_shape(presence_db,people):
    engine,a,b=presence_db
    rid,c,n=joined(a,b);observe(b)
    outsider=people('public-warning-outsider')
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})
    from app.main import create_two_cycle_app
    api=create_two_cycle_app().openapi()
    def wire(path,value):
        schema=api['paths'][path]['get']['responses']['200']['content']['application/json']['schema']
        Draft202012Validator(dict(schema,components=api['components']),format_checker=FormatChecker()).validate(value)
    with client(a) as http:
        summary=http.get('/v2/me/raid-room-character-issues',params=Q)
        assert summary.status_code==200,summary.text
        valid('RosterIssueSummary',summary.json());assert not summary.json()['has_issues']
        route=f'/v2/raid-rooms/{rid}/detail'
        plain=http.get(route,params=Q|dict(target_cycle_key=c))
        result=http.get(route,params=Q|P|dict(target_cycle_key=c,include_character_issues='true'))
        assert result.status_code==200,result.text
        value=result.json();assert 'character_issue_context' not in plain.json()
        wire('/v2/raid-rooms/{room_id}/detail',value)
        for reader in (None,'membership-actions-1','application-display-1'):
            for warning,profile in ((True,False),(False,True),(True,True)):
                options=Q|dict(target_cycle_key=c,include_character_issues='true' if warning else 'false',include_group_state='true')
                if reader:options['reader_profile']=reader
                if profile:options.update(P)
                response=http.get(route,params=options)
                assert response.status_code==200,response.text
                wire('/v2/raid-rooms/{room_id}/detail',response.json())
        for reader in (None,'membership-actions-1'):
            options=Q|P|dict(target_cycle_key=c,include_character_issues='true',include_group_state='true')
            if reader:options['reader_profile']=reader
            response=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=options)
            assert response.status_code==200,response.text
            wire('/v2/me/raid-rooms/{room_id}/plan',response.json())
        valid('RosterIssueRoomContext',value['character_issue_context'])
        valid('RosterParticipationReadContext',value['participation_context'])
        assert value['character_issue_context']['selected_target_issues'][0]['registration_id'] is None
    with client(b) as http:
        value=http.get('/v2/me/raid-room-character-issues',params=Q).json()
        assert value['has_issues'] and value['affected_target_count']==2
        result=http.get('/v2/me/raid-room-memberships',params=Q|P|dict(target_cycle_key=c,include_character_issues='true'))
        assert result.status_code==200,result.text
        wire('/v2/me/raid-room-memberships',result.json())
        assert result.json()['character_issues']['items'][0]['registration_id']==b['rid']
    with client(outsider) as http:
        value=http.get(f'/v2/raid-rooms/{rid}/detail',params=Q|P|dict(target_cycle_key=c,include_character_issues='true'))
        assert value.status_code==200,value.text
        ctx=value.json()['character_issue_context']
        assert ctx['selected_target_issues'] is None
        assert all(t['has_issues'] is None for t in ctx['target_summaries'])
        assert value.json()['participation_context']['members']==[]
    assert table_digests(engine,set(before))==before
    from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import cancel_member
    cancel_member(b,rid,n)
    with client(b) as http:
        result=http.get(f'/v2/raid-rooms/{rid}/detail',params=Q|P|dict(target_cycle_key=c,include_character_issues='true'))
        assert result.status_code==200,result.text
        summaries={v['target_cycle_key']:v for v in result.json()['character_issue_context']['target_summaries']}
        assert summaries[c]['state']=='ready' and summaries[c]['has_issues']
        assert summaries[n]['state']=='not_authorized' and summaries[n]['has_issues'] is None
        assert http.get('/v2/me/raid-room-character-issues',params=Q).json()['affected_target_count']==1


@pytest.mark.parametrize('completed_index',[0,1])
def test_partial_change_history_capability_and_original_ack(presence_db,completed_index):
    _,a,b=presence_db
    rid,c,n=bundle(a)
    complete(a,rid,c,index=completed_index)
    original=cycle_member_reads.plan(actor(a['uid']),rid,c)['data']['my_assignments']
    preserved=next(v for v in original if v['state']=='completed')
    opposite=cycle_member_reads.plan(actor(a['uid']),rid,n)['data']['my_assignments']
    with rp.using(P):
        body=change(a,rid,c);key=uuid.uuid4()
        result=cycle_character.execute(actor(a['uid']),rid,key,body)
        assert cycle_character.execute(actor(a['uid']),rid,key,body)==result
        plan=cycle_member_reads.plan(actor(a['uid']),rid,c)
        assert next(v for v in plan['data']['my_assignments'] if v['state']=='completed')==preserved
        assert next(v for v in plan['data']['my_assignments'] if v['state']=='active')['character_id']==a['ids'][1]
        assert qualified(rid,c,a)
        cycle_worker.process_room(rid)
        assert cycle_member_reads.plan(actor(a['uid']),rid,c)['data']['target_state']=='open'
    with pytest.raises(GameError) as mismatch:
        from app.raid_rooms.common.command_context import unseal
        unseal(body.selection_context.context_token)
    assert mismatch.value.code=='CONTEXT_INVALID'
    # Original receipt precedes capability/token checks; no request rewriting.
    assert cycle_character.execute(actor(a['uid']),rid,key,body)==result
    assert cycle_member_reads.plan(actor(a['uid']),rid,n)['data']['my_assignments']==opposite
    with client(a) as http:
        route=f'/v2/raid-rooms/{rid}/detail'
        blocked=http.get(route,params=Q|dict(target_cycle_key=c))
        assert blocked.status_code==409,blocked.text
        assert blocked.json()['error']['code']=='CLIENT_UPGRADE_REQUIRED'
        for reader in ({},dict(reader_profile='membership-actions-1')):
            page=http.get('/v2/me/raid-room-memberships',params=Q|dict(target_cycle_key=c)|reader)
            assert page.status_code==200,page.text
            item=page.json()['data']['items'][0]
            assert item['content'] is None if reader else item['room'] is None
        value=http.get(route,params=Q|P|dict(target_cycle_key=c,include_character_issues='true'))
        assert value.status_code==200,value.text
        meta=value.json()['participation_context']['members'][0]
        assert meta['current_character']['character_id']==a['ids'][1]
        assert len(meta['active_assignments'])==len(meta['preserved_assignments'])==1
    with rp.using(P):complete(a,rid,c,index=1-completed_index)
    with client(a) as http:
        live=http.get(f'/v2/raid-rooms/{rid}/detail',params=Q|dict(target_cycle_key=c))
        assert live.status_code==409,live.text
        record=http.get(f'/v2/raid-rooms/{rid}/detail',params=Q|dict(target_cycle_key=c,reader_profile='membership-actions-1',
            membership_id=meta['membership_id'],cycle_member_id=meta['cycle_member_id']))
        assert record.status_code==200,record.text
        assert record.json()['data']['record'] is not None
    assert not character_issues.summary(actor(a['uid']))['has_issues']


def test_partial_change_stale_or_tampered_bundle_is_atomic(presence_db,monkeypatch):
    engine,a,b=presence_db
    rid,c,n=bundle(a);complete(a,rid,c,index=0)
    with rp.using(P):
        body=change(a,rid,c)
        with session() as db,db.begin():
            # Model a completion/other command winning the serialized transaction.
            assignment=db.get(Assignment,uuid.UUID(str(body.assignments[0].assignment_id)))
            assignment.revision+=1
        before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
        with pytest.raises(GameError):cycle_character.execute(actor(a['uid']),rid,uuid.uuid4(),body)
        assert table_digests(engine,set(before))==before
        body=change(a,rid,c)
        plan=cycle_member_reads.plan(actor(a['uid']),rid,c)
        historical=next(v for v in plan['data']['my_assignments'] if v['state']=='completed')
        bad=body.model_copy(deep=True)
        bad.assignments[0]=bad.assignments[0].model_copy(update=dict(assignment_id=uuid.UUID(historical['assignment_id'])))
        with pytest.raises(GameError):cycle_character.execute(actor(a['uid']),rid,uuid.uuid4(),bad)
        assert table_digests(engine,set(before))==before

        # Failure after assignment/lease/capability mutation rolls everything back.
        from app.raid_rooms.schedules import cycle_planning
        def fail_after_write(*args):raise GameError('SYNTHETIC_ROLLBACK')
        monkeypatch.setattr(cycle_planning,'refresh',fail_after_write)
        body=change(a,rid,c)
        with pytest.raises(GameError) as error:cycle_character.execute(actor(a['uid']),rid,uuid.uuid4(),body)
        assert error.value.code=='SYNTHETIC_ROLLBACK'
        assert table_digests(engine,set(before))==before


def test_completion_and_change_compete_without_partial_success(presence_db):
    from contextvars import copy_context
    from concurrent.futures import ThreadPoolExecutor
    from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import context
    from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import outcome_body
    _,a,b=presence_db
    rid,c,n=bundle(a);complete(a,rid,c,index=0)
    with rp.using(P):
        body=change(a,rid,c)
        ctx=context(a,rid,c,index=1);completion=outcome_body(ctx)
        round_id=uuid.UUID(ctx['data']['target_round_id'])
        def compete(kind):
            try:
                if kind=='change':return kind,cycle_character.execute(actor(a['uid']),rid,uuid.uuid4(),body)
                return kind,cycle_outcomes.execute(actor(a['uid']),None,round_id,uuid.uuid4(),completion,'personal_completion')
            except GameError as error:return kind,error.code
        contexts=[copy_context(),copy_context()]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(cx.run,compete,kind) for cx,kind in zip(contexts,('change','complete'))]
            results=[f.result(timeout=60) for f in futures]
        assert sum(not isinstance(result,str) for _,result in results)==1,results
        assert all(result in ('ROUND_NOT_ACTIVE','TARGET_CONTEXT_STALE','REVISION_CONFLICT')
            for _,result in results if isinstance(result,str)),results
        with session() as db:
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            cm=cycle_lifecycle.actual_member(db,row,a['uid'])
            active,preserved=rp.split(db,row,cm)
            assert len(preserved)>=1
            assert preserved[0].character_id==uuid.UUID(a['ids'][0])
            assert len(active)+len(preserved)==2


def test_http_candidate_preview_post_and_ack_profile_binding(presence_db):
    _,a,b=presence_db
    rid,c,n=bundle(a);complete(a,rid,c,index=0)
    with client(a) as http:
        query=Q|P|dict(target_cycle_key=c,intent='change_character')
        candidates=http.get(f'/v2/raid-rooms/{rid}/admission-character-candidates',params=query)
        assert candidates.status_code==200,candidates.text
        preview=http.get(f'/v2/raid-rooms/{rid}/admission-context',params=query|dict(
            character_id=a['ids'][1],selected_role='dealer',include_session_display='true'))
        assert preview.status_code==200,preview.text
        candidate_actor=candidates.json()['participation_context']['actor']
        preview_actor=preview.json()['participation_context']['actor']
        assert candidate_actor==preview_actor
        plan=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=Q|P|dict(target_cycle_key=c))
        assert plan.status_code==200,plan.text
        value=plan.json();value['data']['my_assignments']=[v for v in value['data']['my_assignments'] if v['state']=='active']
        body=change_body(preview.json(),value).model_dump(mode='json')
        route=f'/v2/raid-rooms/{rid}/character-changes'
        mismatch=http.post(route,params=Q,json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert mismatch.status_code==400,mismatch.text
        assert mismatch.json()['error']['code']=='CONTEXT_INVALID'
        command=uuid.uuid4();headers={'Idempotency-Key':str(command)}
        result=http.post(route,params=Q|P,json=body,headers=headers)
        assert result.status_code==200,result.text
        replay=http.post(route,params=Q,json=body,headers=headers)
        assert replay.status_code==200 and replay.json()==result.json(),replay.text
        assert 'participation_context' not in replay.json()
        command_context=http.get(f'/v2/raid-rooms/{rid}/command-context',params=Q|dict(target_cycle_key=c,command='personal_completion',
            round_id=preview.json()['data']['targets'][0]['round_id']))
        assert command_context.status_code==409,command_context.text
        assert command_context.json()['error']['code']=='CLIENT_UPGRADE_REQUIRED'
        allowed=http.get(f'/v2/raid-rooms/{rid}/command-context',params=Q|P|dict(target_cycle_key=c,command='personal_completion',
            round_id=preview.json()['data']['targets'][0]['round_id']))
        assert allowed.status_code==200,allowed.text
        menu=http.get(f'/v2/raid-rooms/{rid}/membership-action-context',params=Q|dict(target_cycle_key=c))
        assert menu.status_code==200,menu.text
        assert menu.json()['data']['options']['leave_target']['permission']['reason']=='CLIENT_UPGRADE_REQUIRED'
        menu=http.get(f'/v2/raid-rooms/{rid}/membership-action-context',params=Q|P|dict(target_cycle_key=c))
        assert menu.status_code==200,menu.text
        assert menu.json()['data']['options']['leave_target']['permission']['allowed']
        opposite=http.get(f'/v2/raid-rooms/{rid}/detail',params=Q|dict(target_cycle_key=n))
        assert opposite.status_code==200,opposite.text
