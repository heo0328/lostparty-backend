"""Integrated R2-C HTTP against a restricted-role tmpfs PostgreSQL clone."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text,select,func,event
from app.core.database import session
from app.core.errors import register
from app.raid_rooms import admission_service as service
from app.raid_rooms.admission_router import router
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentAssignment as Assignment,RecruitmentRoom as Room
from app.raid_rooms.source_models import RecruitmentApplication as Application,RoomSettings
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.groups.models import GroupMembership
from app.core.database import now
from app.member_limits.models import MemberUsageLimits
from tests.test_recruitment_participation import ready,sources,imported,people,worlds,write_power
from tests.test_raid_room_migrations import table_digests
from tests.test_raid_room_http import err

ITEMS=[dict(raid_id='horizon_cathedral',difficulty_id='stage1')]


@pytest.fixture
def http():
    from app.main import no_store
    app=FastAPI();app.include_router(router);register(app);app.middleware('http')(no_store)
    with TestClient(app,raise_server_exceptions=False) as client:yield client


def post(http,w,path,body,key=None):
    return http.post('/v1/'+path,json=body,headers={**w['headers'],'Idempotency-Key':str(key or uuid.uuid4())})


def creation(http,w):
    response=http.get('/v1/me/raid-room-creation-context',params=dict(character_id=w['ids'][0],selected_role='dealer',items=json.dumps(ITEMS)),headers=w['headers'])
    assert response.status_code==200,response.text
    return response.json()


def create_body(context,**updates):
    body=dict(title='합성 방',scope='public',group_id=None,admission_mode='direct_join',app_mode='single',
        items=[dict(i,duration_minutes=None,party_no=1) for i in context['targets']],selection=context['selection'],
        selection_context=dict(context_token=context['context_token']),experience_level=None,
        combat_requirement=dict(input_mode='shared',dealer_min=None,support_min=None),
        continuation=dict(enabled=False,auto_open_enabled=False),schedule_groups=[],
        expected_cycle_key=context['expected_cycle_key'],expected_catalog_version=context['catalog_version'],expected_group_revision=None)
    return body|updates


def create(http,w,**updates):
    response=post(http,w,'raid-rooms',create_body(creation(http,w),**updates))
    assert response.status_code==201,response.text
    return next(r['id'] for r in response.json()['revisions'] if r['resource']=='room'),response.json()


def admission(http,w,rid,intent='join'):
    response=http.get(f'/v1/raid-rooms/{rid}/admission-context',params=dict(character_id=w['ids'][0],selected_role='dealer',intent=intent),headers=w['headers'])
    assert response.status_code==200,response.text
    c=response.json()
    return dict(expected_cycle_key=c['expected_cycle_key'],expected_room_revision=c['room_revision'],
        expected_members_revision=c['members_revision'],expected_plan_revision=c['plan_revision'],
        expected_policy_snapshot=c['policy_snapshot'],expected_catalog_version=c['catalog_version'],
        selection_context=dict(context_token=c['context_token']),selection=c['selection'],target_items=c['targets'],target_session_ids=[])


def review(http,w,aid):
    response=http.get(f'/v1/raid-room-applications/{aid}',headers=w['headers'])
    assert response.status_code==200,response.text
    return response.json()


def approve_body(review,cycle):
    return dict(expected_cycle_key=cycle,expected_application_revision=review['application']['revision'],
        expected_room_revision=review['room_revision'],expected_members_revision=review['members_revision'],expected_plan_revision=review['plan_revision'])


def test_create_join_plan_and_original_ack(ready,http):
    target,a,b,_=ready
    context=creation(http,a);body=create_body(context);key=uuid.uuid4()
    created=post(http,a,'raid-rooms',body,key);assert created.status_code==201,created.text
    rid=next(r['id'] for r in created.json()['revisions'] if r['resource']=='room')
    assert post(http,a,'raid-rooms',body,key).json()==created.json()
    plan=http.get(f'/v1/me/raid-rooms/{rid}/plan',headers=a['headers'])
    assert plan.status_code==200,plan.text
    assert plan.json()['schedule_state']=='unscheduled' and plan.json()['my_participations']==[]
    assert plan.json()['revision']==1 and len(plan.json()['my_assignments'])==1
    data=admission(http,b,rid);join_key=uuid.uuid4()
    joined=post(http,b,f'raid-rooms/{rid}/join',data,join_key);assert joined.status_code==200,joined.text
    assert post(http,b,f'raid-rooms/{rid}/join',data,join_key).json()==joined.json()
    err(post(http,b,f'raid-rooms/{rid}/join',data),409,'REVISION_CONFLICT')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==2
    assert http.get(f'/v1/me/raid-rooms/{rid}/plan',headers=b['headers']).status_code==200


def test_pending_has_no_occupancy_approve_uses_current_server_sources(ready,http):
    target,a,b,_=ready;rid,_=create(http,a,admission_mode='leader_only')
    data=admission(http,b,rid,'apply');applied=post(http,b,f'raid-rooms/{rid}/applications',data)
    assert applied.status_code==201,applied.text
    aid=applied.json()['application_id']
    own=http.get(f'/v1/raid-room-applications/{aid}',headers=b['headers']).json()
    assert own['application_id']==aid and 'eligibility' not in own and 'room_revision' not in own
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==0
    write_power(b,'dealer','110','2026-10-16T10:00:00Z')
    result=review(http,a,aid)
    assert result['eligibility']['state']=='eligible'
    assert 'expected_weekly_revision' not in json.dumps(result) and 'ownership_revision' not in json.dumps(result)
    body=approve_body(result,data['expected_cycle_key']);key=uuid.uuid4()
    accepted=post(http,a,f'raid-room-applications/{aid}/approve',body,key)
    assert accepted.status_code==200,accepted.text
    with session() as db:
        app=db.get(Application,uuid.UUID(aid))
        assert app.state=='accepted' and app.selection['expected_role_summary_version']==1
        row=db.scalar(select(Assignment).where(Assignment.room_id==uuid.UUID(rid),Assignment.user_id==b['uid']))
        assert row.build['current_summary_version']==2 and row.build['actual']=='110'
    assert post(http,a,f'raid-room-applications/{aid}/approve',body,key).json()==accepted.json()


def test_public_origin_survives_group_return_and_new_external_is_hidden(ready,http):
    target,a,b,source=ready;rid,_=create(http,a,admission_mode='leader_only')
    data=admission(http,b,rid,'apply');out=post(http,b,f'raid-rooms/{rid}/applications',data)
    assert out.status_code==201,out.text
    aid=out.json()['application_id']
    with session() as db,db.begin():
        row=db.get(Room,uuid.UUID(rid));row.scope='group';row.group_id=source[6];row.revision+=1
        db.add(GroupMembership(id=uuid.uuid4(),group_id=source[6],user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),
            display={},revision=1,joined_at=now(db)))
    result=review(http,a,aid)
    assert result['application']['admission_origin']['scope']=='public'
    assert post(http,a,f'raid-room-applications/{aid}/approve',approve_body(result,data['expected_cycle_key'])).status_code==200
    outsider=source[4]
    # Existing group owner is allowed to see group room, another outside user isn't.
    outsider=source[5]
    response=http.get(f'/v1/raid-rooms/{rid}/admission-context',params=dict(character_id=outsider['ids'][0],selected_role='dealer',intent='apply'),headers=outsider['headers'])
    err(response,404,'ROOM_NOT_FOUND')


def test_context_tamper_cross_actor_and_transaction_failure_rollback(ready,http,monkeypatch):
    target,a,b,_=ready
    body=create_body(creation(http,a));body['selection_context']['context_token']='s1.'+'0'*64
    err(post(http,a,'raid-rooms',body),409,'SELECTION_CONTEXT_CHANGED')
    body=create_body(creation(http,a));assert post(http,b,'raid-rooms',body).status_code>=400
    before=table_digests(target,{'recruitment_rooms','recruitment_assignments','recruitment_weekly_occupancies','raid_weekly_states'})
    original=service.commit_result
    def fail(*args):raise RuntimeError('synthetic commit failure')
    monkeypatch.setattr(service,'commit_result',fail);key=uuid.uuid4()
    assert post(http,a,'raid-rooms',body,key).status_code==500
    assert table_digests(target,set(before))==before
    monkeypatch.setattr(service,'commit_result',original)
    assert post(http,a,'raid-rooms',body,key).status_code==201


def test_context_gets_are_readonly_and_strict_inputs(ready,http):
    target,a,b,_=ready
    seen=[]
    def record(conn,cursor,statement,parameters,context,many):seen.append(statement.strip().upper())
    event.listen(target,'before_cursor_execute',record)
    try:context=creation(http,a)
    finally:event.remove(target,'before_cursor_execute',record)
    assert 'SET TRANSACTION READ ONLY' in seen and not any(s.startswith(('INSERT','UPDATE','DELETE')) for s in seen)
    body=create_body(context);body['continuation']['enabled']='false'
    err(post(http,a,'raid-rooms',body),400,'INVALID_REQUEST')
    body=create_body(context);body['items'][0]['duration_minutes']=11
    err(post(http,a,'raid-rooms',body),400,'INVALID_REQUEST')
    err(http.get('/v1/me/raid-room-creation-context?unexpected=1',headers=a['headers']),400,'INVALID_REQUEST')
    headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4()),'Content-Type':'application/json'}
    err(http.post('/v1/raid-rooms',content='{"title":"a","title":"b"}',headers=headers),400,'INVALID_REQUEST')


def test_concurrent_join_writes_one_occupancy(ready,http):
    target,a,b,_=ready;rid,_=create(http,a)
    data=admission(http,b,rid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:post(http,b,f'raid-rooms/{rid}/join',data),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==1


def test_approval_permissions_current_threshold_and_expired_ack(ready,http):
    target,a,b,_=ready;rid,_=create(http,a,admission_mode='leader_only')
    data=admission(http,b,rid,'apply');applied=post(http,b,f'raid-rooms/{rid}/applications',data)
    aid=applied.json()['application_id'];r=review(http,a,aid);body=approve_body(r,data['expected_cycle_key'])
    err(post(http,b,f'raid-room-applications/{aid}/approve',body),403,'ROOM_MEMBERSHIP_REQUIRED')
    with session() as db,db.begin():
        settings=db.get(RoomSettings,uuid.UUID(rid));settings.dealer_min=settings.support_min='100';settings.revision+=1
    write_power(b,'dealer','99','2026-10-16T10:00:00Z')
    assert review(http,a,aid)['eligibility']['state']=='blocked'
    err(post(http,a,f'raid-room-applications/{aid}/approve',body),409,'COMBAT_POWER_REQUIRED')
    with session() as db:assert db.get(Application,uuid.UUID(aid)).state=='pending'
    write_power(b,'dealer','101','2026-10-17T10:00:00Z',3)
    key=uuid.uuid4();accepted=post(http,a,f'raid-room-applications/{aid}/approve',body,key)
    assert accepted.status_code==200,accepted.text
    with target.begin() as conn:
        conn.execute(text("UPDATE recruitment_applications SET expires_at=created_at+interval '1 microsecond' WHERE id=:id"),dict(id=uuid.UUID(aid)))
    assert post(http,a,f'raid-room-applications/{aid}/approve',body,key).json()==accepted.json()


def test_all_reads_no_writes_and_scheduling_gate_is_atomic(ready,http):
    target,a,b,_=ready;rid,_=create(http,a,admission_mode='leader_only')
    data=admission(http,b,rid,'apply');out=post(http,b,f'raid-rooms/{rid}/applications',data);aid=out.json()['application_id']
    seen=[]
    def record(conn,cursor,statement,parameters,context,many):seen.append(statement.strip().upper())
    event.listen(target,'before_cursor_execute',record)
    try:
        review(http,a,aid);admission(http,b,rid,'apply')
        assert http.get(f'/v1/me/raid-rooms/{rid}/plan',headers=a['headers']).status_code==200
    finally:event.remove(target,'before_cursor_execute',record)
    assert seen.count('SET TRANSACTION READ ONLY')==3
    assert not any(s.startswith(('INSERT','UPDATE','DELETE')) or 'FOR UPDATE' in s for s in seen)
    # A structurally valid scheduling intent must not silently become an unscheduled success.
    body=create_body(creation(http,b));body['schedule_groups']=[dict(client_group_key='days',existing_group_id=None,
        expected_group_revision=None,occurrence_mode='one_of',planning_mode='unscheduled',required=True,
        auto_confirm_additional_members=None,day_scope='selected_weekdays',alternatives=[dict(client_alternative_key='tue',
        existing_session_id=None,expected_session_revision=None,weekday=2,starts_local=None,leader_latest_start_local=None,item_order=['horizon_cathedral'])])]
    before=table_digests(target,{'recruitment_rooms','recruitment_weekly_occupancies'})
    result=post(http,b,'raid-rooms',body)
    assert result.status_code==201,result.text
    rid=next(r['id'] for r in result.json()['revisions'] if r['resource']=='room')
    restored=http.get(f'/v1/me/raid-rooms/{rid}/plan',headers=b['headers']).json()
    assert len(restored['schedule_groups'])==1 and restored['sessions']==[]


def test_draft_and_original_openapi_contracts(http):
    from pathlib import Path
    from app.main import app
    from app.raid_rooms.admission_contract import draft_openapi
    draft=draft_openapi()
    assert draft==json.loads(Path('openapi/recruitment-admission.draft.json').read_text())
    assert set(draft['paths'])==set(http.app.openapi()['paths'])
    assert app.openapi()==json.loads(Path('openapi/openapi.yaml').read_text())
    assert any(route.path=='/v1/raid-rooms' for route in app.routes)


def test_final_expiry_boundary_rolls_back_approval_and_ack(ready,http,monkeypatch):
    from datetime import timedelta
    target,a,b,_=ready;rid,_=create(http,a,admission_mode='leader_only')
    data=admission(http,b,rid,'apply');applied=post(http,b,f'raid-rooms/{rid}/applications',data)
    aid=uuid.UUID(applied.json()['application_id']);result=review(http,a,aid)
    body=approve_body(result,data['expected_cycle_key']);key=uuid.uuid4()
    with session() as db,db.begin():
        app=db.get(Application,aid);app.expires_at-=timedelta(microseconds=1)
    before=table_digests(target,{'recruitment_applications','recruitment_assignments','recruitment_memberships','recruitment_weekly_occupancies','raid_weekly_states'})
    original=service.now
    def clock(db):
        app=db.get(Application,aid)
        return app.expires_at if app and app.state=='accepted' else original(db)
    monkeypatch.setattr(service,'now',clock)
    err(post(http,a,f'raid-room-applications/{aid}/approve',body,key),409,'APPLICATION_NOT_PENDING')
    assert table_digests(target,set(before))==before
    monkeypatch.setattr(service,'now',original)
    assert post(http,a,f'raid-room-applications/{aid}/approve',body,key).status_code==200


def test_pending_does_not_reserve_limit_reject_and_withdraw(ready,http):
    target,a,b,_=ready;rid,_=create(http,a,admission_mode='leader_only')
    with session() as db,db.begin():
        db.add(MemberUsageLimits(user_id=b['uid'],revision=1,group_capacity=15,joined_groups=5,raid_rooms=0,updated_at=now(db)))
    data=admission(http,b,rid,'apply')
    applied=post(http,b,f'raid-rooms/{rid}/applications',data);assert applied.status_code==201,applied.text
    aid=applied.json()['application_id'];r=review(http,a,aid);body=approve_body(r,data['expected_cycle_key'])
    assert r['eligibility']['reasons']==['MEMBER_RAID_LIMIT_REACHED']
    err(post(http,a,f'raid-room-applications/{aid}/approve',body),409,'MEMBER_RAID_LIMIT_REACHED')
    rejected=post(http,a,f'raid-room-applications/{aid}/reject',body)
    assert rejected.status_code==200 and rejected.json()['state']=='rejected'
    applied=post(http,b,f'raid-rooms/{rid}/applications',admission(http,b,rid,'apply'))
    assert applied.status_code==201,applied.text
    aid=applied.json()['application_id'];key=uuid.uuid4();body=dict(expected_application_revision=1)
    withdrawn=post(http,b,f'raid-room-applications/{aid}/withdraw',body,key)
    assert withdrawn.status_code==200 and withdrawn.json()['state']=='withdrawn'
    assert post(http,b,f'raid-room-applications/{aid}/withdraw',body,key).json()==withdrawn.json()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==0
