"""Policy2 HTTP/transaction regressions on the disposable test DB."""
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.auth.router import authenticated
from app.core.database import session, now
from app.game_accounts.character_profiles import account_representative as policy, management
from app.game_accounts.common.support import reserve, commit_result, GameError
from app.game_accounts.models.models import (Registration, Account, Character, Configuration,
    Activity, NameClaim, RequestResult, ScopedPowerCache)
from tests.game_accounts.test_representative import selection
from tests.game_accounts.test_management import body, path, validate
from tests.groups.test_group_foundation import actor

@contextmanager
def current_client(w):
    from app.main import create_app
    app=create_app()
    @asynccontextmanager
    async def no_workers(app):
        yield
    app.router.lifespan_context=no_workers
    app.dependency_overrides[authenticated]=lambda:actor(w['uid'])
    with TestClient(app) as http:
        yield http


def second_roster(w):
    with session() as db,db.begin():
        stamp=now(db);a=Account(owner_id=w['uid'],verified_at=stamp);db.add(a);db.flush()
        r=Registration(user_id=w['uid'],account_id=a.id,lookup_name='second-0',label='',is_main=False,
            preview=[],fetched_at=stamp,created_at=stamp,updated_at=stamp);db.add(r)
        chars=[Character(account_id=a.id,server_name='second',character_name=f'second-{i}',
            summary=dict(server_name='second',character_name=f'second-{i}',class_name='sample-class',character_level=60,
                         item_level='1700',combat_power=str(100+i)),power_fetched_at=stamp,fetched_at=stamp,confirmed_at=stamp) for i in range(3)]
        db.add_all(chars);db.flush()
        db.add_all([NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id) for c in chars])
        conf=Configuration(user_id=w['uid'],account_id=a.id,representative_id=chars[0].id,state='configured');db.add(conf);db.flush()
        db.add_all([Activity(settings_id=conf.id,account_id=a.id,character_id=c.id) for c in chars])
        return dict(w,rid=str(r.id),aid=a.id,cid=conf.id,ids=[str(c.id) for c in chars])


def save(http,w,ctx,**kw):
    return http.put(path(w),json=body(ctx,**kw),headers={'Idempotency-Key':str(uuid4())})


def test_subordinate_null_raw_clear_and_all_movable(selection):
    w=second_roster(selection)
    with current_client(w) as http:
        ctx=http.get(path(w)).json();validate('Context',ctx)
        assert ctx['scope']['is_main'] is False and ctx['data']['representative_character_id'] is None
        with session() as db:assert str(db.get(Configuration,w['cid']).representative_id)==w['ids'][0]
        bad=save(http,w,ctx,representative_character_id=w['ids'][0]);assert bad.json()['error']['code']=='MAIN_REGISTRATION_CHANGED'
        order=list(reversed(ctx['data']['ordered_all_character_ids']))
        response=save(http,w,ctx,ordered_character_ids=order);assert response.status_code==200,response.text
        after=response.json();assert after['scope']['settings_version']==ctx['scope']['settings_version']+1
        assert after['data']['ordered_all_character_ids']==order
        with session() as db:assert db.get(Configuration,w['cid']).representative_id is None
        assert save(http,w,after).json()['scope']['settings_version']==after['scope']['settings_version']
        # Unlike main, the old raw representative can be turned OFF.
        assert save(http,w,after,activity_character_ids=w['ids'][1:]).status_code==200
        rep=http.get('/v1/me/game-accounts/'+w['rid']+'/representative').json()
        assert rep['representative_character_id'] is None
        chars=http.get('/v2/me/game-accounts/'+w['rid']+'/characters').json()
        assert chars['settings']['representative_character_id'] is None


def test_main_switch_atomic_and_no_raw_promotion(selection):
    w=second_roster(selection)
    with current_client(w) as http:
        ctx=http.get(path(w)).json()
        request={'expected_version':ctx['scope']['registration_version'],'is_main':True}
        key=str(uuid4());url='/v1/me/game-accounts/'+w['rid']
        response=http.patch(url,json=request,headers={'Idempotency-Key':key});assert response.status_code==200,response.text
        result=response.json();assert result['settings']['representative_character_id']==w['ids'][2]
        after=http.get(path(w)).json();assert after['scope']['is_main']
        assert after['scope']['settings_version']==ctx['scope']['settings_version']+1
        with session() as db:
            assert not db.get(Registration,UUID(selection['rid'])).is_main
            assert db.get(Registration,UUID(selection['rid'])).version==2
        assert http.patch(url,json=request,headers={'Idempotency-Key':key}).json()==result
        repeat=http.patch(url,json={'expected_version':result['version'],'is_main':True},headers={'Idempotency-Key':str(uuid4())})
        assert repeat.json()['settings']['settings_version']==after['scope']['settings_version']
        assert http.get(path(selection)).json()['data']['representative_character_id'] is None


def test_main_switch_no_candidates_preserves_activities(selection):
    w=second_roster(selection)
    with session() as db,db.begin():
        for cid in w['ids']:db.get(Character,UUID(cid)).status='suspect'
    with current_client(w) as http:
        response=http.patch('/v1/me/game-accounts/'+w['rid'],json={'expected_version':1,'is_main':True},headers={'Idempotency-Key':str(uuid4())})
        assert response.status_code==200,response.text
        settings=response.json()['settings'];assert settings['representative_character_id'] is None
        assert settings['configuration_state']=='needs_reconfiguration' and set(settings['activity_character_ids'])==set(w['ids'])
        assert settings['settings_version']==2


def test_autofill_preserves_valid_rep_and_rank(selection):
    w=selection
    with session() as db,db.begin():db.get(Configuration,w['cid']).representative_id=None
    with current_client(w) as http:
        ctx=http.get(path(w)).json();assert ctx['data']['representative_character_id'] is None
        res=save(http,w,ctx);assert res.status_code==200,res.text
        first=res.json();assert first['data']['representative_character_id']==w['ids'][0]
        with session() as db,db.begin():
            c=db.get(Character,UUID(w['ids'][1]));c.summary=dict(c.summary,item_level='1800')
        newer=http.get(path(w)).json();assert newer['data']['order_digest']!=first['data']['order_digest']
        kept=save(http,w,newer,representative_character_id=None).json()
        assert kept['data']['representative_character_id']==w['ids'][0]
        assert kept['scope']['settings_version']==first['scope']['settings_version']
        assert all(c['display_order'] is None for c in kept['data']['characters'])


def old_request(ctx):
    return {k:v for k,v in body(ctx).items() if k!='policy_version'}

@pytest.mark.parametrize('state,code',[('absent','CONTRACT_POLICY_CHANGED'),('running','REQUEST_IN_PROGRESS'),
    ('lease_expired','CONTRACT_POLICY_CHANGED'),('retryable','CONTRACT_POLICY_CHANGED'),
    ('expired','IDEMPOTENCY_EXPIRED'),('completed_expired','IDEMPOTENCY_EXPIRED')])
def test_policy1_recovery_never_reexecutes(selection,state,code):
    w=selection;p=actor(w['uid']);key=uuid4();ctx=management.get(p,UUID(w['rid']));request=old_request(ctx)
    if state!='absent':
        ticket,_=reserve(p,'character-management-1',key,dict(target=w['rid'],body=request))
        with session() as db,db.begin():
            row=db.get(RequestResult,ticket[0])
            if state=='lease_expired':row.lease_expires_at=now(db)-timedelta(seconds=1)
            if state in ('retryable','expired'):row.state=state
            if state=='completed_expired':
                row.state='completed';row.completed_at=now(db)-timedelta(hours=25);row.status=200;row.result={}
    with current_client(w) as http:
        result=http.put(path(w),json=request,headers={'Idempotency-Key':str(key)})
        assert result.status_code==409 and result.json()['error']['code']==code,result.text
        if state=='running':assert result.headers['Retry-After']=='2'
        assert http.get(path(w)).json()['scope']==ctx['scope']
    with session() as db:
        assert db.get(Configuration,w['cid']).version==ctx['scope']['settings_version']
        rows=list(db.scalars(select(RequestResult).where(RequestResult.actor_id==w['uid'])))
        assert len(rows)==(0 if state=='absent' else 1)
        if rows:assert rows[0].generation==1


def test_historical_ack_exact_and_same_namespace_collision(selection):
    w=selection;p=actor(w['uid']);key=uuid4();ctx=management.get(p,UUID(w['rid']));request=old_request(ctx)
    historical=json.loads(Path('docs/features/rosters/activity-and-presentation/character-management-contract/examples.json').read_text())['contexts']['configured']
    # Actual stored old success can contain fields no longer valid as current representative.
    ticket,_=reserve(p,'character-management-1',key,dict(target=w['rid'],body=request))
    with session() as db,db.begin():commit_result(db,ticket,200,historical)
    with current_client(w) as http:
        response=http.put(path(w),json=request,headers={'Idempotency-Key':str(key)})
        assert response.status_code==200 and response.json()==historical,response.text
        conflict=http.put(path(w),json=body(ctx),headers={'Idempotency-Key':str(key)})
        assert conflict.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
        assert http.get(path(w)).json()['scope']['policy_version']=='character-management-2'


def test_v1_subordinate_roundtrip_and_new_null(selection):
    w=second_roster(selection)
    with current_client(w) as http:
        url='/v1/me/game-accounts/'+w['rid']+'/character-settings'
        b=dict(activity_character_ids=w['ids'][1:],representative_character_id=w['ids'][0],expected_settings_version=1,expected_ownership_revision=1,expected_roster_revision=1)
        response=http.put(url,json=b,headers={'Idempotency-Key':str(uuid4())});assert response.status_code==200,response.text
        assert response.json()['representative_character_id'] is None and response.json()['settings_version']==2
        b['expected_settings_version']=2
        stale=http.put(url,json=b,headers={'Idempotency-Key':str(uuid4())});assert stale.json()['error']['code']=='MAIN_REGISTRATION_CHANGED'
        b['representative_character_id']=None
        assert http.put(url,json=b,headers={'Idempotency-Key':str(uuid4())}).status_code==200


def test_application_policy_isolation(selection,client):
    w=second_roster(selection)
    with current_client(w) as http:
        assert http.get('/v1/me/game-accounts/'+w['rid']+'/representative').json()['representative_character_id'] is None
    response=client.get('/v1/me/game-accounts/'+w['rid']+'/representative',headers=w['headers'])
    assert response.status_code==200 and response.json()['representative_character_id']==w['ids'][0]
    assert policy.current_policy.get() is False


@pytest.mark.parametrize('case',json.loads(Path('docs/features/rosters/activity-and-presentation/character-management-contract/policy2/selection-fixtures.json').read_text())['cases'])
def test_actual_selection_matches_agreed_fixtures(case):
    rows=[dict(character_id=r['id'],character_name=r['name'],item_level=policy.number(r['level']),combat_power=policy.number(r['power']),usable=r['usable']) for r in case['items']]
    chosen=[r['id'] for r in case['items'] if r['active']]
    assert policy.choose(rows,chosen,case.get('existing'),transition=case.get('main_transition',False))==case['expected']


def test_stored_power_scope_tie_and_power_only_cas(selection):
    w=selection;p=actor(w['uid']);rid=UUID(w['rid']);cid=UUID(w['ids'][0])
    with session() as db,db.begin():
        stamp=now(db)-timedelta(days=2);c=db.get(Character,cid)
        c.summary=dict(c.summary,combat_power='10');c.power_fetched_at=stamp
        for scope,revision,power in [('a',1,'20'),('b',1,'30'),('c',2,'9999')]:
            db.add(ScopedPowerCache(actor_id=w['uid'],scope_key=scope*64,character_id=cid,lifecycle_revision=revision,
                registration_id=rid,preview_version=None,credential_version=1,server_name=c.server_name,
                character_name=c.character_name,value=power,fetched_at=stamp,checked_at=stamp,status='failed',reason='UPSTREAM_UNAVAILABLE'))
    before=management.get(p,rid);row=next(r for r in before['data']['characters'] if r['character_id']==str(cid))
    assert row['combat_power']=='20' # same timestamp cache before summary; scope a before b; wrong lifecycle ignored
    assert row['combat_power_observed_at'] is not None
    with session() as db,db.begin():db.get(ScopedPowerCache,(w['uid'],'a'*64)).value='21'
    after=management.get(p,rid);assert before['data']['order_digest']!=after['data']['order_digest']
    assert before['data']['ordered_all_character_ids']==after['data']['ordered_all_character_ids']
    with pytest.raises(GameError) as caught:management.put(p,rid,uuid4(),body(before))
    assert caught.value.code=='REVISION_CONFLICT'


def test_observation_repair_and_version_once(selection):
    from app.game_accounts.rosters import service, observations
    from app.game_accounts.common.support import authorize
    w=selection;p=actor(w['uid'])
    token=policy.current_policy.set(True)
    try:
        with session() as db,db.begin():
            authorize(db,p,write=True)
            account=db.get(Account,w['aid'])
            # Missing current representative; another activity is still usable.
            remaining=[dict(db.get(Character,UUID(cid)).summary) for cid in w['ids'][1:]]
            service.reconcile(db,account,observations.Observation(remaining,now(db)),fresh=True)
            conf=db.get(Configuration,w['cid'])
            assert str(conf.representative_id)==w['ids'][1]
            assert conf.state=='needs_reconfiguration' and conf.version==2
            assert len(list(db.scalars(select(Activity).where(Activity.settings_id==conf.id))))==2
    finally:policy.current_policy.reset(token)


def test_main_switch_ack_failure_rolls_back_both_rosters(selection,monkeypatch):
    from app.game_accounts.rosters import service
    w=second_roster(selection)
    def broken(*args):raise RuntimeError('synthetic ACK failure')
    monkeypatch.setattr(service,'commit_result',broken)
    with current_client(w) as http:
        with pytest.raises(RuntimeError):
            http.patch('/v1/me/game-accounts/'+w['rid'],json={'expected_version':1,'is_main':True},headers={'Idempotency-Key':str(uuid4())})
    with session() as db:
        assert not db.get(Registration,UUID(w['rid'])).is_main
        assert db.get(Registration,UUID(selection['rid'])).is_main
        assert db.get(Registration,UUID(selection['rid'])).version==1
        assert db.get(Configuration,w['cid']).version==1
        assert str(db.get(Configuration,w['cid']).representative_id)==w['ids'][0]


def test_current_bootstrap_uses_same_main_projection(selection):
    w=second_roster(selection)
    with current_client(w) as http:
        response=http.get('/v2/me/account-bootstrap');assert response.status_code==200,response.text
        bundles=response.json()['registrations']
        subordinate=next(b for b in bundles if b['registration']['registration_id']==w['rid'])
        assert subordinate['representative']['representative_character_id'] is None
        assert subordinate['registration']['representative_summary'] is None
        assert subordinate['characters']['settings']['representative_character_id'] is None
        main=next(b for b in bundles if b['registration']['registration_id']==selection['rid'])
        assert main['representative']['representative_character_id']==selection['ids'][0]


def test_subordinate_200_movable(selection):
    w=second_roster(selection)
    with session() as db,db.begin():
        stamp=now(db)
        for i in range(197):
            c=Character(account_id=w['aid'],server_name='sub',character_name=f'extra-{i}',
                summary={'item_level':'1700'},fetched_at=stamp,confirmed_at=stamp)
            db.add(c);db.flush();db.add(NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id))
    with current_client(w) as http:
        ctx=http.get(path(w)).json();ids=ctx['data']['ordered_all_character_ids'];assert len(ids)==200
        response=save(http,w,ctx,activity_character_ids=ids,ordered_character_ids=list(reversed(ids)))
        assert response.status_code==200,response.text
        assert response.json()['data']['ordered_all_character_ids']==list(reversed(ids))
        assert response.json()['data']['representative_character_id'] is None


def test_null_autofill_and_order_are_one_atomic_command(selection):
    w=selection
    with session() as db,db.begin():
        db.get(Configuration,w['cid']).representative_id=None
        c=db.get(Character,UUID(w['ids'][2]));c.summary=dict(c.summary,item_level='1800')
    with current_client(w) as http:
        ctx=http.get(path(w)).json()
        requested=list(reversed([c for c in ctx['data']['ordered_all_character_ids'] if c!=w['ids'][2]]))
        response=save(http,w,ctx,activity_character_ids=w['ids'],representative_character_id=None,ordered_character_ids=requested)
        assert response.status_code==200,response.text
        after=response.json();validate('Context',after)
        assert after['data']['representative_character_id']==w['ids'][2]
        assert after['scope']['settings_version']==ctx['scope']['settings_version']+1
        assert [i for i in after['data']['ordered_all_character_ids'] if i!=w['ids'][2]]==requested
