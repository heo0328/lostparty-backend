"""Candidate HTTP flows against the agreed schema, isolated shadow DB only."""
import json
import uuid
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry,Resource
from referencing.jsonschema import DRAFT202012
from app.auth.router import authenticated
from app.core.errors import register
from app.raid_rooms import cycle_router,cycle_lists as lists,cycle_wire as wire,cycle_schemas as inputs
from app.raid_rooms.router import optional_principal
from tests.test_recruitment_cycle_creation import candidate,ready,sources,imported,people,worlds,preflight,request,denied
from tests.test_recruitment_cycle_commands import create_room,context,admission_request,commands,decision
from tests.test_group_foundation import actor

CONTRACT=json.loads(Path('docs/design/issue13-two-cycle.full.openapi.json').read_text())
REGISTRY=Registry().with_resource('urn:w2',Resource.from_contents(CONTRACT,default_specification=DRAFT202012))


def validate(path,method,status,value,*,input=False):
    operation=CONTRACT['paths'][path][method]
    response=operation['requestBody'] if input else operation['responses'][str(status)]
    if '$ref' in response:response=CONTRACT['components']['responses'][response['$ref'].rsplit('/',1)[1]]
    schema=response['content']['application/json']['schema']
    Draft202012Validator({'$ref':'urn:w2'+schema['$ref']},registry=REGISTRY,
        format_checker=Draft202012Validator.FORMAT_CHECKER).validate(value)


def client(w):
    app=FastAPI();register(app);app.include_router(cycle_router.router)
    app.dependency_overrides[authenticated]=lambda:actor(w['uid'])
    app.dependency_overrides[optional_principal]=lambda:actor(w['uid'])
    return TestClient(app)


def test_http_create_read_join_and_fixed_contract(candidate):
    _,a,b=candidate
    ctx=preflight(a,continuation=True,bundle=True);body=request(ctx).model_dump(mode='json')
    validate('/v2/raid-rooms','post',201,body,input=True)
    with client(a) as http:
        result=http.post('/v2/raid-rooms',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==201,result.json().get('error')
        validate('/v2/raid-rooms','post',201,result.json())
        rid=result.json()['data']['room_id'];key=ctx['data']['target_cycle_key']
        for path,spec in ((f'/v2/raid-rooms/{rid}/detail','/v2/raid-rooms/{room_id}/detail'),
                          (f'/v2/me/raid-rooms/{rid}/plan','/v2/me/raid-rooms/{room_id}/plan')):
            response=http.get(path,params={'target_cycle_key':key})
            assert response.status_code==200,response.json().get('error')
            validate(spec,'get',200,response.json())
        page=http.get('/v2/raid-rooms',params=[('target_cycle_key',key),('experience_levels','unrestricted'),('experience_levels','experienced')])
        assert page.status_code==200,page.json().get('error')
        validate('/v2/raid-rooms','get',200,page.json())
    joinctx=context(b,uuid.UUID(rid),key);join=admission_request(joinctx).model_dump(mode='json')
    validate('/v2/raid-rooms/{room_id}/join','post',200,join,input=True)
    with client(b) as http:
        response=http.post(f'/v2/raid-rooms/{rid}/join',json=join,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json().get('error')
        validate('/v2/raid-rooms/{room_id}/join','post',200,response.json())
        response=http.get('/v2/me/raid-room-memberships',params={'target_cycle_key':key})
        assert response.status_code==200,response.json().get('error')
        validate('/v2/me/raid-room-memberships','get',200,response.json())


def test_http_strict_inputs_and_error_contract(candidate):
    _,a,_=candidate
    ctx=preflight(a);body=request(ctx).model_dump(mode='json')
    invalid=[body|dict(expected_target_revision=True),body|dict(target_cycle_key='20261021'),
        body|dict(target_cycle_key=ctx['data']['target_cycle_key']+'T00:00:00'),body|dict(extra='forbidden')]
    with client(a) as http:
        for value in invalid:
            response=http.post('/v2/raid-rooms',json=value,headers={'Idempotency-Key':str(uuid.uuid4())})
            assert response.status_code==400,response.json().get('error')
            validate('/v2/raid-rooms','post',400,response.json())
        response=http.post('/v2/raid-rooms',content='{"title":"one","title":"two"}',headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==400
        response=http.get('/v2/raid-rooms',params=[('target_cycle_key',ctx['data']['target_cycle_key'])]*2)
        assert response.status_code==400


def test_membership_and_application_pages_are_target_scoped(candidate):
    _,a,b=candidate
    room=create_room(a,mode='leader_only');rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    app=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n,'apply')),applying=True)[1]['data']
    reviewed=commands.application(actor(a['uid']),uuid.UUID(app['application_id']))
    assert reviewed['data']['eligibility']['state']=='eligible'
    assert reviewed['data']['permissions']['approve']['allowed']
    validate('/v2/raid-room-applications/{application_id}','get',200,reviewed)
    for w,room_arg in ((a,rid),(b,None)):
        result=lists.applications(actor(w['uid']),n,rid=room_arg)
        assert len(result['data']['items'])==1
        validate('/v2/raid-rooms/{room_id}/applications','get',200,result)
        assert not lists.applications(actor(w['uid']),c,rid=room_arg)['data']['items']
    denied('ROOM_LEADER_REQUIRED',lists.applications,actor(b['uid']),n,rid=rid)
    commands.process(actor(a['uid']),uuid.UUID(app['application_id']),uuid.uuid4(),decision(app,context(a,rid,n,'apply')))
    page=lists.memberships(actor(b['uid']),c)
    assert page['data']['items'][0]['target_participation_state']=='not_selected'
    assert page['data']['items'][0]['permissions']['view_plan']['allowed'] is False
    assert not page['data']['items'][0]['assignments']
    validate('/v2/me/raid-room-memberships','get',200,page)
    assert lists.memberships(actor(b['uid']),n)['data']['items'][0]['target_participation_state']=='participating'


def test_candidate_not_published_in_main():
    from app.main import app
    live=app.openapi()['paths']
    assert '/v2/raid-rooms' not in live
    assert '/v2/raid-cycles' in live and len(live)==116
