"""F2-B real HTTP against isolated PostgreSQL; production routes remain untouched."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, select, func
from sqlalchemy.exc import OperationalError
from app.core.database import session, engine, now
from app.core.errors import register
from app.raid_rooms import service, core, queries
from app.raid_rooms.router import router
from app.raid_rooms.models import Room, Membership, Application
from app.game_accounts.models import RequestResult, Character
from tests.test_raid_room_foundation import people, worlds, create_command, selection
from tests.test_member_limits import change
from app.member_limits.service import Limits


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setenv("RAID_ROOM_ADMISSIONS_ENABLED", "true")
    from app.main import no_store
    candidate = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    candidate.include_router(router)
    register(candidate)
    candidate.middleware('http')(no_store)
    with TestClient(candidate, raise_server_exceptions=False) as client:
        yield client


def post(http, w, path, body, key=None):
    return http.post('/v1/'+path, json=body, headers={**w['headers'], 'Idempotency-Key': str(key or uuid.uuid4())})


def err(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()['error']['code'] == code, response.text
    assert set(response.json()['error']) == {'code', 'message', 'request_id'}
    assert response.headers['cache-control'] == 'no-store'
    if status == 401:
        assert response.headers['www-authenticate'] == 'Bearer'


def create_body(w, *, mode='direct_join', **kwargs):
    data = create_command(w, mode=mode, **kwargs).model_dump(mode='json')
    return {**data, 'expected_group_revision': None, 'expected_group_membership_id': None,
            'expected_group_membership_revision': None, 'min_combat_power': {'dealer': None, 'support': None}}


def create(http, w, *, mode='direct_join', **kwargs):
    out = post(http, w, 'raid-rooms', create_body(w, mode=mode, **kwargs))
    assert out.status_code == 201, out.text
    assert out.headers['cache-control'] == 'no-store'
    return out.json()['room_id']


def detail(http, w, rid):
    out = http.get('/v1/me/raid-rooms/'+rid, headers=w['headers'])
    assert out.status_code == 200, out.text
    return out.json()


def context(http, w, rid, *, intent='join', role='dealer', index=0):
    out = http.get('/v1/raid-rooms/'+rid+'/admission-context', headers=w['headers'],
        params=dict(character_id=w['ids'][index], selected_role=role, party_no=1, intent=intent))
    assert out.status_code == 200, out.text
    value = out.json()
    return dict(selection=value['selection'], expected_room_revision=value['room_revision'],
        expected_round_revision=value['round_revision'], expected_members_revision=value['members_revision'],
        expected_policy_snapshot=value['policy_snapshot'], expected_cycle_key=value['cycle_key'],
        expected_catalog_version=value['catalog_version'])


def membership(http, w, rid, *, target=None):
    d = detail(http, w, rid); mine = next(m for m in d['members'] if m['is_me'])
    out = dict(expected_room_revision=d['room']['revision'], expected_round_id=d['room']['round_id'],
        expected_round_revision=d['room']['round_revision'], expected_members_revision=d['room']['members_revision'],
        expected_membership_id=mine['membership_id'], expected_membership_revision=mine['revision'])
    if target is not None:
        out.update(target_membership_id=target['membership_id'], expected_target_membership_revision=target['revision'])
    return out


def decision(http, w, rid, aid):
    d = detail(http, w, rid)
    a = http.get('/v1/raid-room-applications/'+aid, headers=w['headers']).json()
    return dict(expected_application_revision=a['revision'], expected_room_revision=d['room']['revision'],
        expected_round_revision=d['room']['round_revision'], expected_members_revision=d['room']['members_revision'],
        expected_policy_snapshot=d['access']['policy_snapshot'], expected_cycle_key=d['room']['cycle_key'])


def test_complete_approval_transfer_leave_end_flow_with_minimal_ack_and_replay(http, people):
    a, b = people('a'), people('b')
    rid = create(http, a, mode='leader_only')
    err(http.get('/v1/me/raid-rooms/'+rid, headers=b['headers']), 403, 'ROOM_MEMBERSHIP_REQUIRED')
    application = post(http, b, f'raid-rooms/{rid}/applications', context(http, b, rid, intent='apply'))
    assert application.status_code == 201, application.text
    aid = application.json()['application_id']
    assert set(application.json()) == {'room_id', 'application_id', 'application_revision', 'state', 'executed_at'}
    assert http.get('/v1/me/raid-room-memberships', headers=b['headers']).json()['items'] == []
    cmd = decision(http, a, rid, aid); key = uuid.uuid4()
    approved = post(http, a, f'raid-room-applications/{aid}/approve', cmd, key)
    assert approved.status_code == 200, approved.text
    assert approved.json()['application_id'] == aid and 'members' not in approved.json()
    assert post(http, a, f'raid-room-applications/{aid}/approve', cmd, key).json() == approved.json()
    before = detail(http, a, rid)
    target = next(m for m in before['members'] if not m['is_me'])
    transferred = post(http, a, f'raid-rooms/{rid}/leadership-transfer', membership(http, a, rid, target=target))
    assert transferred.status_code == 200, transferred.text
    left_body = membership(http, a, rid); leave_key = uuid.uuid4()
    left = post(http, a, f'raid-rooms/{rid}/leave', left_body, leave_key)
    assert left.status_code == 200 and 'members' not in left.json()
    err(http.get('/v1/me/raid-rooms/'+rid, headers=a['headers']), 403, 'ROOM_MEMBERSHIP_REQUIRED')
    assert post(http, a, f'raid-rooms/{rid}/leave', left_body, leave_key).json() == left.json()
    assert post(http, a, f'raid-room-applications/{aid}/approve', cmd, key).json() == approved.json()
    end = post(http, b, f'raid-rooms/{rid}/end', membership(http, b, rid))
    assert end.status_code == 200, end.text
    history = http.get('/v1/me/raid-room-memberships?state=ended', headers=b['headers']).json()['items'][0]
    assert history['end_reason'] == 'room_ended'
    assert http.get('/v1/raid-rooms/'+rid).json()['state'] == 'ended'


def test_create_idempotency_and_entire_wire_body_digest(http, people):
    a = people('a'); body = create_body(a); key = uuid.uuid4()
    first = post(http, a, 'raid-rooms', body, key)
    assert first.status_code == 201, first.text
    assert post(http, a, 'raid-rooms', body, key).json() == first.json()
    body['min_combat_power']['dealer'] = '123'
    err(post(http, a, 'raid-rooms', body, key), 409, 'IDEMPOTENCY_CONFLICT')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room)) == 1


def test_direct_join_leave_rejoin_historical_ack_does_not_end_new_membership(http, people):
    a, b = people('a'), people('b'); rid = create(http, a)
    assert post(http, b, f'raid-rooms/{rid}/join', context(http, b, rid)).status_code == 200
    old_body = membership(http, b, rid); key = uuid.uuid4()
    left = post(http, b, f'raid-rooms/{rid}/leave', old_body, key)
    assert left.status_code == 200
    joined = post(http, b, f'raid-rooms/{rid}/join', context(http, b, rid))
    assert joined.status_code == 200, joined.text
    assert joined.json()['actor_membership_id'] != left.json()['membership_id']
    assert post(http, b, f'raid-rooms/{rid}/leave', old_body, key).json() == left.json()
    assert len(detail(http, b, rid)['members']) == 2


def test_reject_and_withdraw_do_not_require_current_character_eligibility(http, people):
    a, b, c = [people(x) for x in 'abc']; rid = create(http, a, mode='leader_only')
    ids = []
    for w in (b, c):
        out = post(http, w, f'raid-rooms/{rid}/applications', context(http, w, rid, intent='apply'))
        assert out.status_code == 201; ids.append(out.json()['application_id'])
    with session() as db, db.begin():
        db.get(Character, uuid.UUID(b['ids'][0])).lifecycle_revision += 1
        db.get(Character, uuid.UUID(c['ids'][0])).lifecycle_revision += 1
    err(post(http, a, f'raid-room-applications/{ids[0]}/approve', decision(http, a, rid, ids[0])),
        409, 'APPLICATION_CONTEXT_CHANGED')
    rejected = post(http, a, f'raid-room-applications/{ids[0]}/reject', decision(http, a, rid, ids[0]))
    assert rejected.status_code == 200 and rejected.json()['state'] == 'rejected'
    withdrawn = post(http, c, f'raid-room-applications/{ids[1]}/withdraw', {'expected_application_revision': 1})
    assert withdrawn.status_code == 200 and withdrawn.json()['state'] == 'withdrawn'
    err(http.get('/v1/raid-room-applications/'+ids[0], headers=c['headers']), 404, 'ROOM_APPLICATION_NOT_FOUND')


@pytest.mark.parametrize('query', ['limit=0', 'limit=51', 'limit=true', 'limit=1.0', 'limit=1&limit=2',
                                  'cursor=', 'state=unknown', 'scope=group', 'difficulty_id=stage1', 'q=secret'])
def test_strict_list_query(http, query):
    err(http.get('/v1/raid-rooms?'+query), 400, 'INVALID_REQUEST')


@pytest.mark.parametrize('method,path', [('get','me/raid-room-memberships'), ('get','me/raid-room-applications'),
    ('get','me/raid-rooms/00000000-0000-4000-8000-000000000001'),
    ('post','raid-rooms'), ('post','raid-rooms/00000000-0000-4000-8000-000000000001/join')])
def test_missing_authentication_is_bearer_error(http, method, path):
    err(getattr(http, method)('/v1/'+path), 401, 'ACCESS_INVALID')


@pytest.mark.parametrize('change_body', [
    lambda b: b.update(user_id=str(uuid.uuid4())),
    lambda b: b['selection'].update(expected_usage_revision=True),
    lambda b: b['selection'].update(selected_role='admin'),
    lambda b: b['selection'].update(power='999999'),
    lambda b: b['schedule'].update(starts_at=12345),
    lambda b: b['schedule'].update(starts_at='2026-10-19T12:00:00+09:00'),
    lambda b: b.update(title='bad\nname'),
    lambda b: b.update(expected_cycle_key='2026-99-99'),
    lambda b: b.pop('min_combat_power'),
    lambda b: b.update(group_id=str(uuid.uuid4())),
    lambda b: b['min_combat_power'].update(dealer='NaN'),
])
def test_strict_body_rejects_spoofing_and_invalid_types(http, people, change_body):
    a = people('a'); body = create_body(a); change_body(body)
    err(post(http, a, 'raid-rooms', body), 400, 'INVALID_REQUEST')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room)) == 0


@pytest.mark.parametrize('key', ['', 'not-uuid', str(uuid.uuid1())])
def test_invalid_command_key(http, people, key):
    a = people('a')
    out = http.post('/v1/raid-rooms', json=create_body(a), headers={**a['headers'], 'Idempotency-Key': key})
    err(out, 400, 'INVALID_REQUEST')


def test_duplicate_headers_duplicate_json_and_get_body(http, people):
    a = people('a'); body = create_body(a)
    pairs = [(k,v) for k,v in a['headers'].items()]
    out = http.post('/v1/raid-rooms', json=body, headers=pairs+[('Idempotency-Key', str(uuid.uuid4()))]*2)
    err(out, 400, 'INVALID_REQUEST')
    raw = json.dumps(body)[:-1]+',"title":"duplicate"}'
    out = http.post('/v1/raid-rooms', content=raw,
        headers={**a['headers'], 'Idempotency-Key': str(uuid.uuid4()), 'Content-Type':'application/json'})
    err(out, 400, 'INVALID_REQUEST')
    err(http.request('GET','/v1/raid-rooms', content='{}'), 400, 'INVALID_REQUEST')
    err(http.get('/v1/raid-rooms',headers={'Authorization':'Basic wrong'}), 401, 'ACCESS_INVALID')


def test_unsupported_policy_branches_remain_explicit(http, people):
    a = people('a'); body = create_body(a)
    body['min_combat_power']['dealer'] = '100'
    err(post(http, a, 'raid-rooms', body), 409, 'COMBAT_REQUIREMENT_UNAVAILABLE')
    body['min_combat_power']['dealer'] = None
    body['schedule']['ends_at'] = None
    err(post(http, a, 'raid-rooms', body), 409, 'SCHEDULE_REVIEW_REQUIRED')
    body = create_body(a)
    body.update(scope='group', group_id=str(uuid.uuid4()), expected_group_revision=1,
                expected_group_membership_id=str(uuid.uuid4()), expected_group_membership_revision=1)
    err(post(http, a, 'raid-rooms', body), 409, 'ROOM_FEATURE_UNSUPPORTED')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room)) == 0


def test_private_reads_and_context_do_not_write_or_expose_selection(http, people):
    a,b = people('a'),people('b'); rid=create(http,a)
    statements=[]
    def capture(conn,cursor,statement,*args): statements.append(statement.upper())
    event.listen(engine(),'before_cursor_execute',capture)
    try:
        public=http.get('/v1/raid-rooms/'+rid); private=http.get('/v1/me/raid-rooms/'+rid,headers=a['headers'])
        context(http,b,rid)
    finally: event.remove(engine(),'before_cursor_execute',capture)
    assert public.status_code==private.status_code==200
    assert not any(s.lstrip().startswith(('INSERT ','UPDATE ','DELETE ')) or 'FOR UPDATE' in s for s in statements)
    assert 'user_id' not in private.text and 'registration_id' not in private.text and 'members' not in public.json()
    assert private.headers['cache-control']==public.headers['cache-control']=='no-store'


def test_in_progress_and_ack_failure_rollback_are_http_errors(http, people, monkeypatch):
    a=people('a'); body=create_body(a); key=uuid.uuid4()
    from app.game_accounts.support import reserve
    from app.raid_rooms.http_schemas import RoomCreateIn
    from tests.test_group_foundation import actor
    from fastapi.encoders import jsonable_encoder
    reserve(actor(a['uid']),'room-core-create',key,jsonable_encoder(RoomCreateIn.model_validate(body)))
    out=post(http,a,'raid-rooms',body,key)
    err(out,409,'REQUEST_IN_PROGRESS'); assert out.headers['Retry-After']=='2'
    def crash(*args): raise OperationalError('test',{},Exception('injected'))
    monkeypatch.setattr(service,'commit_result',crash)
    err(post(http,a,'raid-rooms',body),503,'SERVICE_UNAVAILABLE')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room))==0


def test_last_slot_race_rechecks_shared_room_revision(http, people):
    a,b,c,d,e=[people(x) for x in 'abcde']; rid=create(http,a)
    for w in (b,c): assert post(http,w,f'raid-rooms/{rid}/join',context(http,w,rid)).status_code==200
    bodies=[context(http,w,rid,role='support') for w in (d,e)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda pair: post(http,pair[0],f'raid-rooms/{rid}/join',pair[1]),zip((d,e),bodies)))
    assert sorted(r.status_code for r in results)==[200,409]
    failure=next(r for r in results if r.status_code==409)
    assert failure.json()['error']['code']=='REVISION_CONFLICT'
    assert len(detail(http,a,rid)['members'])==4


def test_candidate_paths_and_dtos_do_not_activate_production_api(http):
    from app.main import app
    baseline=json.loads(open('openapi/openapi.yaml').read())
    assert app.openapi()==baseline
    assert all(getattr(route.endpoint,'__module__','')!='app.raid_rooms.router' for route in app.routes)
    schema=http.app.openapi()
    assert sum(len([v for v in ops if v in ('get','post')]) for ops in schema['paths'].values())==18
    models=schema['components']['schemas']
    for name in ('RoomCreateIn','RoomCommandAck','AdmissionContext','RoomDetail','Application','MembershipRecord'):
        assert set(models[name]['required'])==set(models[name]['properties'])
    assert models['RoomCreateIn']['additionalProperties'] is False
    assert schema['paths']['/v1/raid-rooms/{room_id}/join']['post']['responses']['409']['headers']['Retry-After']['schema']['const']==2


def test_group_room_existence_cannot_be_probed_through_writes_or_recovery(http, people, client):
    from tests.test_group_admissions import group as make_group
    a,b=people('a'),people('b'); gid=uuid.UUID(make_group(client,a))
    rid=create(http,a,mode='leader_only')
    body=context(http,b,rid,intent='apply')
    app=post(http,b,f'raid-rooms/{rid}/applications',body).json()['application_id']
    decide=decision(http,a,rid,app); recover=membership(http,a,rid)
    with session() as db, db.begin():
        room=db.get(Room,uuid.UUID(rid));room.scope='group';room.group_id=gid
    err(http.get('/v1/raid-rooms/'+rid),404,'ROOM_NOT_FOUND')
    err(post(http,b,f'raid-rooms/{rid}/join',body),404,'ROOM_NOT_FOUND')
    err(post(http,a,f'raid-room-applications/{app}/approve',decide),404,'ROOM_NOT_FOUND')
    err(post(http,b,f'raid-room-applications/{app}/withdraw',{'expected_application_revision':1}),404,'ROOM_NOT_FOUND')
    err(post(http,a,f'raid-rooms/{rid}/end',recover),404,'ROOM_NOT_FOUND')
    with session() as db:
        assert db.get(Application,uuid.UUID(app)).state=='pending'
        assert db.get(Room,uuid.UUID(rid)).ended_at is None


def test_response_loss_after_commit_recovers_original_ack_with_same_key(http, people, monkeypatch):
    a=people('a'); body=create_body(a); key=uuid.uuid4()
    original=service.create; lost=[]
    def drop(*args,**kwargs):
        result=original(*args,**kwargs)
        if not lost:
            lost.append(result)
            raise OperationalError('test',{},Exception('simulated response loss after commit'))
        return result
    monkeypatch.setattr(service,'create',drop)
    err(post(http,a,'raid-rooms',body,key),503,'SERVICE_UNAVAILABLE')
    replay=post(http,a,'raid-rooms',body,key)
    from app.raid_rooms.http_schemas import RoomCommandAck
    assert replay.status_code==201
    assert replay.json()==RoomCommandAck.model_validate(lost[0][1]).model_dump(mode='json')
    rid=replay.json()['room_id']
    assert len(detail(http,a,rid)['members'])==1
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room))==1
        assert db.scalar(select(func.count()).select_from(Membership))==1


def test_context_then_limit_change_rejects_http_join_without_partial_state(http, people):
    a,b=people('a'),people('b'); rid=create(http,a)
    body=context(http,b,rid)
    change(b['uid'],Limits(15,5,0))
    err(post(http,b,f'raid-rooms/{rid}/join',body),409,'POLICY_CONTEXT_CHANGED')
    assert http.get('/v1/me/raid-room-memberships',headers=b['headers']).json()['items']==[]
    assert len(detail(http,a,rid)['members'])==1


def test_header_and_identifier_errors_do_not_echo_raw_inputs(http, people):
    a=people('a'); marker='private-input-marker'
    out=http.post('/v1/raid-rooms',json=create_body(a),headers={**a['headers'],'Idempotency-Key':marker})
    err(out,400,'INVALID_REQUEST'); assert marker not in out.text
    err(http.get('/v1/raid-rooms/not-uuid'),400,'INVALID_REQUEST')
    err(http.post('/v1/raid-rooms',json=create_body(a),headers=a['headers']),400,'INVALID_REQUEST')
