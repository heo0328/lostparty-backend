"""Atomic management contract on disposable PostgreSQL; legacy selection reused."""
import copy
import json
from pathlib import Path
from uuid import UUID,uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.auth.router import authenticated
from app.core.errors import register
from app.core.database import session, now
from app.game_accounts.character_profiles import management as service
from app.game_accounts.api.management_router import router
from app.game_accounts.models.models import Character,Configuration,CharacterPersonalPreferences as Preferences
from app.game_accounts.common.support import GameError
from tests.game_accounts.test_representative import selection
from tests.groups.test_group_foundation import actor

ROOT=Path('docs/features/rosters/activity-and-presentation/character-management-contract')
def client(w):
    app=FastAPI();register(app);app.include_router(router)
    app.dependency_overrides[authenticated]=lambda:actor(w['uid'])
    return TestClient(app)
def path(w):return '/v2/me/game-accounts/'+w['rid']+'/character-settings'
def body(context,**changes):
    s,d=context['scope'],context['data']
    result={('expected_'+k):s[k] for k in ('registration_version','settings_version','ownership_revision','roster_revision')}
    result.update(activity_character_ids=d['activity_character_ids'],representative_character_id=d['representative_character_id'],expected_order_digest=d['order_digest'])
    return result|changes

def validate(kind,value):
    from jsonschema import Draft202012Validator,FormatChecker
    s=json.loads((ROOT/'schema.json').read_text())
    Draft202012Validator({'$ref':'#/$defs/'+kind,'$defs':s['$defs']},format_checker=FormatChecker()).validate(value)

def test_read_noop_activation_drop_and_immutable_ack(selection):
    w=selection
    with client(w) as http:
        before=http.get(path(w));assert before.status_code==200,before.json()
        assert before.headers['cache-control']=='no-store';value=before.json();validate('Context',value)
        unchanged=http.put(path(w),json=body(value),headers={'Idempotency-Key':str(uuid4())})
        assert unchanged.status_code==200,unchanged.json()
        assert unchanged.json()['scope']['settings_version']==value['scope']['settings_version']
        assert all(c['display_order'] is None for c in unchanged.json()['data']['characters'])
        activated=http.put(path(w),json=body(value,activity_character_ids=w['ids']),headers={'Idempotency-Key':str(uuid4())})
        assert activated.status_code==200,activated.json();value=activated.json()
        assert all(c['display_order'] is None for c in value['data']['characters'])
        movable=[i for i in value['data']['ordered_all_character_ids'] if i!=value['data']['representative_character_id']]
        request=body(value,ordered_character_ids=list(reversed(movable)));validate('PutBody',request)
        key=str(uuid4());headers={'Idempotency-Key':key}
        saved=http.put(path(w),json=request,headers=headers);assert saved.status_code==200,saved.json();validate('Context',saved.json())
        expected=value['data']['ordered_all_character_ids'].copy();it=iter(reversed(movable));expected=[next(it) if i in movable else i for i in expected]
        assert saved.json()['data']['ordered_all_character_ids']==expected
        assert http.put(path(w),json=request,headers=headers).json()==saved.json()
        assert http.put(path(w),json=request|{'representative_character_id':movable[0]},headers=headers).json()['error']['code']=='IDEMPOTENCY_CONFLICT'
        stale=http.put(path(w),json=request,headers={'Idempotency-Key':str(uuid4())});assert stale.status_code==409
        # A later representative change does not rewrite stored ranks.
        updated=http.put(path(w),json=body(saved.json(),representative_character_id=movable[0]),headers={'Idempotency-Key':str(uuid4())})
        assert updated.status_code==200,updated.json()
        assert updated.json()['data']['ordered_all_character_ids']==expected
        assert http.put(path(w),json=request,headers=headers).json()==saved.json()
        assert http.get(path(w)).json()['data']['representative_character_id']==movable[0]

@pytest.mark.parametrize('state',['unconfigured','needs_reconfiguration','configured'])
def test_recovery_context_and_first_explicit_action(selection,state):
    w=selection
    with session() as db,db.begin():
        db.get(Configuration,w['cid']).state=state
        db.get(Character,UUID(w['ids'][0])).lifecycle_state='retired'
        db.get(Character,UUID(w['ids'][1])).status='suspect'
    with client(w) as http:
        response=http.get(path(w));assert response.status_code==200,response.json();ctx=response.json();validate('Context',ctx)
        assert ctx['data']['configuration_state']==state
        assert ctx['data']['representative_character_id']==w['ids'][0]
        assert w['ids'][0] not in ctx['data']['ordered_all_character_ids']
        assert any(not r['usable'] for r in ctx['data']['characters'])
        fail=http.put(path(w),json=body(ctx),headers={'Idempotency-Key':str(uuid4())});assert fail.status_code==404
        fixed=http.put(path(w),json=body(ctx,activity_character_ids=[w['ids'][2]],representative_character_id=w['ids'][2],ordered_character_ids=[]),headers={'Idempotency-Key':str(uuid4())})
        assert fixed.status_code==200,fixed.json();assert fixed.json()['data']['configuration_state']=='configured'
        assert all(c['display_order'] is None for c in fixed.json()['data']['characters'])

def test_reject_null_subset_queries_and_foreign_ids(selection):
    w=selection
    with client(w) as http:
        ctx=http.get(path(w)).json()
        for request in [body(ctx,ordered_character_ids=None),body(ctx,ordered_character_ids=[]),body(ctx,activity_character_ids=w['ids'][:1]*2),body(ctx)|{'extra':1}]:
            bad=http.put(path(w),json=request,headers={'Idempotency-Key':str(uuid4())});assert bad.status_code==400,bad.json()
        assert http.get(path(w),params={'extra':1}).status_code==400
        foreign=http.put(path(w),json=body(ctx,activity_character_ids=[str(uuid4())]),headers={'Idempotency-Key':str(uuid4())})
        assert foreign.status_code==400 # representative missing is checked before eligibility
        bad=http.get('/v2/me/game-accounts/'+str(uuid4())+'/character-settings');assert bad.status_code==404

def test_individual_rank_digest_and_role_visible_preserved(selection):
    w=selection
    with session() as db,db.begin():
        db.add(Preferences(user_id=w['uid'],character_id=UUID(w['ids'][2]),ownership_revision=1,preferred_role='dealer',visible=False,display_order=None,version=1,saved_at=now(db)))
    principal=actor(w['uid']);rid=UUID(w['rid']);before=service.get(principal,rid)
    with session() as db,db.begin():db.get(Preferences,(w['uid'],UUID(w['ids'][2]),1)).display_order=0
    with pytest.raises(GameError) as error:service.put(principal,rid,uuid4(),body(before))
    assert error.value.code=='REVISION_CONFLICT'
    current=service.get(principal,rid)
    chosen=w['ids'];rep=w['ids'][0];movable=[i for i in current['data']['ordered_all_character_ids'] if i!=rep]
    service.put(principal,rid,uuid4(),body(current,activity_character_ids=chosen,ordered_character_ids=list(reversed(movable))))
    with session() as db:
        row=db.get(Preferences,(w['uid'],UUID(w['ids'][2]),1));assert row.preferred_role=='dealer' and row.visible is False


def test_two_devices_cas_and_transaction_rollback(selection,monkeypatch):
    w=selection;principal=actor(w['uid']);rid=UUID(w['rid']);ctx=service.get(principal,rid)
    requests=[body(ctx,representative_character_id=w['ids'][1]),body(ctx,activity_character_ids=w['ids'])]
    def attempt(request):
        try:return service.put(principal,rid,uuid4(),request)[0]
        except GameError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,requests))
    assert sorted(map(str,results))==['200','REVISION_CONFLICT']
    before=service.get(principal,rid)
    def broken(*args):raise RuntimeError('synthetic ACK failure')
    monkeypatch.setattr(service,'commit_result',broken)
    with pytest.raises(RuntimeError):service.put(principal,rid,uuid4(),body(before,activity_character_ids=w['ids'],representative_character_id=w['ids'][2],ordered_character_ids=list(reversed([i for i in before['data']['ordered_all_character_ids'] if i!=w['ids'][2]]))))
    after=service.get(principal,rid);assert before['scope']==after['scope'];assert before['data']['order_digest']==after['data']['order_digest'];assert before['data']['activity_character_ids']==after['data']['activity_character_ids']

def test_context_1000_1001_and_activity_200_distinct(selection,capsys):
    w=selection;principal=actor(w['uid']);rid=UUID(w['rid'])
    with session() as db,db.begin():
        template=db.get(Character,UUID(w['ids'][0]))
        for i in range(997):db.add(Character(account_id=w['aid'],server_name='test',character_name=f'extra-{i}',summary={},fetched_at=template.fetched_at,confirmed_at=template.confirmed_at,status='suspect',lifecycle_state='suspect'))
    import time
    from sqlalchemy import event
    from app.core.database import engine
    queries=[]
    def counted(conn,cursor,statement,params,context,many):queries.append(statement)
    event.listen(engine(),'before_cursor_execute',counted);started=time.perf_counter()
    try:value=service.get(principal,rid)
    finally:event.remove(engine(),'before_cursor_execute',counted)
    assert len(value['data']['characters'])==1000
    assert len(queries)<20
    with capsys.disabled():print('MANAGEMENT_1000_CONTEXT',json.dumps(dict(seconds=time.perf_counter()-started,queries=len(queries),bytes=len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()))),flush=True)
    with session() as db,db.begin():db.add(Character(account_id=w['aid'],server_name='test',character_name='over',summary={},fetched_at=template.fetched_at,confirmed_at=template.confirmed_at,status='suspect',lifecycle_state='suspect'))
    with pytest.raises(GameError) as err:service.get(principal,rid)
    assert err.value.code=='CHARACTER_CONTEXT_TOO_LARGE' and err.value.status==413

@pytest.mark.parametrize('case',json.loads((ROOT/'comparator-fixtures.json').read_text())['cases'])
def test_actual_comparator_matches_document(case):
    rows=[dict(character_id=r['id'],display_order=r['rank'],item_level=service.level(r['level']),character_name=r['name']) for r in case['items']]
    assert [r['character_id'] for r in sorted(rows,key=service.sort_key)]==case['expected']

@pytest.mark.parametrize('row',json.loads((ROOT/'comparator-fixtures.json').read_text())['levels'])
def test_actual_decimal_matches_document(row):assert service.level(row['raw'])==row['normalized']


def test_first_explicit_configuration_without_existing_row(selection):
    from sqlalchemy import delete
    from app.game_accounts.models.models import Activity
    w=selection
    with session() as db,db.begin():
        db.execute(delete(Activity).where(Activity.settings_id==w['cid']))
        db.execute(delete(Configuration).where(Configuration.id==w['cid']))
    with client(w) as http:
        ctx=http.get(path(w)).json();assert ctx['data']['configuration_state']=='unconfigured'
        assert ctx['data']['activity_character_ids']==[]
        with session() as db:assert db.get(Configuration,w['cid']) is None
        request=body(ctx,activity_character_ids=[w['ids'][0]],representative_character_id=w['ids'][0],ordered_character_ids=[])
        response=http.put(path(w),json=request,headers={'Idempotency-Key':str(uuid4())})
        assert response.status_code==200,response.json()
        assert response.json()['data']['configuration_state']=='configured'
        assert response.json()['scope']['settings_version']==2
        invalid=http.put(path(w),json=body(response.json(),activity_character_ids=[]),headers={'Idempotency-Key':str(uuid4())})
        assert invalid.status_code==400 and invalid.json()['error']['code']=='EMPTY_ACTIVITY_SELECTION'


def test_decimal_high_precision_keeps_exact_comparison():
    rows=[dict(character_id='a',display_order=None,item_level='1700.00000000000000000000000000001',character_name='a'),
          dict(character_id='b',display_order=None,item_level='1700.00000000000000000000000000002',character_name='z')]
    assert [r['character_id'] for r in sorted(rows,key=service.sort_key)]==['b','a']


def test_activity_200_atomic_order_and_201_rejected(selection):
    from app.game_accounts.models.models import NameClaim
    w=selection
    with session() as db,db.begin():
        stamp=now(db);added=[]
        for i in range(199):
            row=Character(account_id=w['aid'],server_name='test',character_name=f'valid-{i}',summary={'item_level':'1700'},fetched_at=stamp,confirmed_at=stamp)
            db.add(row);added.append(row)
        db.flush()
        db.add_all([NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id) for c in added])
    with client(w) as http:
        ctx=http.get(path(w)).json()
        rep=w['ids'][0];chosen=[rep]+[r['character_id'] for r in ctx['data']['characters'] if r['character_id']!=rep][:199]
        request=body(ctx,activity_character_ids=chosen,ordered_character_ids=list(reversed(chosen[1:])))
        response=http.put(path(w),json=request,headers={'Idempotency-Key':str(uuid4())})
        assert response.status_code==200,response.json()
        assert len(response.json()['data']['activity_character_ids'])==200
        extra=next(c['character_id'] for c in ctx['data']['characters'] if c['character_id'] not in chosen)
        invalid=http.put(path(w),json=body(response.json(),activity_character_ids=chosen+[extra]),headers={'Idempotency-Key':str(uuid4())})
        assert invalid.status_code==400
        assert http.get(path(w)).json()['scope']['settings_version']==response.json()['scope']['settings_version']
