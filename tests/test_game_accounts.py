import uuid
from datetime import timedelta, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select, func, text
from app.core.database import session, now
from app.game_accounts import service, observations
from app.game_accounts.models import Account, Registration, Character, Configuration, Verification, RequestResult, Audit, Activity
from app.game_accounts.equipment import parse_equipment, SLOTS
from app.game_accounts.provider import ProviderUnavailable

class PrivateHeaders(dict):
    def __repr__(self):
        return '<redacted test authorization>'


BASE='/v1/me/game-accounts'
VERIFY='/v1/me/game-account-verifications'


@pytest.fixture
def world(monkeypatch, login):
    auth,_=login()
    headers=PrivateHeaders(Authorization='Bearer '+auth['access_token'])
    state={'removed':(), 'validated':True, 'missing':(), 'count':3, 'group':'a', 'calls':0}
    def fetch(name, proof=False):
        state['calls']+=1
        rows=[dict(server_name='sample-server',character_name=f"{state['group']}{i}",class_name='sample-class',
                   character_level=60,item_level='1700.00',combat_power=None) for i in range(state['count']) if i not in state['missing']]
        gear=parse_equipment([dict(Type=s,Name='sample-'+s,Grade='고대') for s in SLOTS if s not in state['removed']]) if proof else None
        return observations.Observation(rows,datetime.now(timezone.utc),gear,state['validated'])
    monkeypatch.setattr(observations,'fetch',fetch)
    return headers,state


def change(client,headers,method,path,data=None,key=None):
    h={**headers,'Idempotency-Key':str(key or uuid.uuid4())}
    return getattr(client,method)(path,headers=h,**({'json':data} if data is not None else {}))


def register(client,headers,name='a0',main=False):
    r=change(client,headers,'post',BASE,dict(lookup_character_name=name,label='sample',is_main=main))
    assert r.status_code==201,r.text
    return r.json()


def start(client,headers,rid=None,name='a0'):
    data=dict(source='registration',registration_id=rid) if rid else dict(source='direct_input',character_name=name)
    r=change(client,headers,'post',VERIFY,data)
    assert r.status_code==201,r.text
    return r.json()


def verify(client,headers,state,rid=None):
    v=start(client,headers,rid)
    state['removed']=v['required_slots']
    r=change(client,headers,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert r.status_code==200,r.text
    assert r.json()['status']=='verified',r.text
    state['removed']=()
    return r.json()


def page(client,headers,rid,**params):
    r=client.get(BASE+'/'+rid+'/characters',headers=headers,params=params)
    assert r.status_code==200,r.text
    return r.json()


def save_data(p,selected=None,rep=None):
    ids=selected if selected is not None else [i['character_id'] for i in p['characters']['items'] if i['eligible']]
    return dict(activity_character_ids=ids,representative_character_id=rep if rep is not None else ids[0] if ids else None,
                expected_settings_version=p['settings']['settings_version'],expected_ownership_revision=p['settings']['ownership_revision'],expected_roster_revision=p['roster_revision'])


def test_empty_guest_and_no_automatic_registration(client,world):
    h,state=world
    assert client.get(BASE).status_code==401
    assert client.get(BASE,headers=h).json()['items']==[]
    r=client.post('/v1/game-accounts/preview',headers=h,json={'character_name':'a0'})
    assert r.status_code==200,r.text
    assert client.get(BASE,headers=h).json()['items']==[]
    assert 'character_id' not in r.json()['characters'][0]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==0


def test_registration_duplicate_main_delete_replay(client,world):
    h,state=world
    first=register(client,h,main=True)
    duplicate=change(client,h,'post',BASE,dict(lookup_character_name='a1',label='dup',is_main=False))
    assert duplicate.status_code==409
    state['group']='b'
    second=register(client,h,'b0',main=True)
    rows=client.get(BASE,headers=h).json()['items']
    assert sum(r['is_main'] for r in rows)==1
    old=next(r for r in rows if r['registration_id']==first['registration_id'])
    assert old['version']==2
    key=uuid.uuid4(); path=BASE+'/'+second['registration_id']+'?expected_version=1'
    assert change(client,h,'delete',path,key=key).status_code==204
    assert change(client,h,'delete',path,key=key).status_code==204
    assert not client.get(BASE,headers=h).json()['items'][0]['is_main']


def test_idempotency_payload_resource_and_expiry(client,world):
    h,state=world; key=uuid.uuid4()
    data=dict(lookup_character_name='a0',label='sample',is_main=False)
    a=change(client,h,'post',BASE,data,key); b=change(client,h,'post',BASE,data,key)
    assert a.status_code==b.status_code==201 and a.json()==b.json()
    data['label']='changed'
    assert change(client,h,'post',BASE,data,key).json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    with session() as db,db.begin():
        row=db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.completed_at=now(db)-timedelta(hours=24)
    data['label']='sample'
    assert change(client,h,'post',BASE,data,key).json()['error']['code']=='IDEMPOTENCY_EXPIRED'


@pytest.mark.parametrize('extra', [{'owner_id':str(uuid.uuid4())},{'verified':True},{'label':None},{'is_main':1}])
def test_registration_strict_input(client,world,extra):
    h,_=world
    data=dict(lookup_character_name='a0',label='sample',is_main=False); data.update(extra)
    assert change(client,h,'post',BASE,data).status_code==400


def test_ownership_first_seed_cooldown_atomicity(client,world):
    h,state=world; r=register(client,h)
    initial=page(client,h,r['registration_id'])
    assert all(i['character_id'] is None for i in initial['characters']['items'])
    v=verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id'])
    assert p['settings']['configuration_state']=='unconfigured'
    first=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p))
    assert first.status_code==200,first.text
    assert first.json()['next_change_at'] is None
    p=page(client,h,r['registration_id']); ids=p['settings']['activity_character_ids']
    original_rep=p['settings']['representative_character_id']
    replacement=next(i for i in ids if i != original_rep)
    second=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p,ids,replacement))
    assert second.status_code==200,second.text
    assert second.json()['next_change_at'] is not None
    p=page(client,h,r['registration_id'])
    attempted=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p,[original_rep],original_rep))
    assert attempted.json()['error']['code']=='REPRESENTATIVE_COOLDOWN'
    assert page(client,h,r['registration_id'])['settings']==p['settings']
    # Re-authentication does not reset a valid selection or ownership revision.
    verify(client,h,state,r['registration_id'])
    after=page(client,h,r['registration_id'])
    assert after['settings']==p['settings']


def test_full_settings_cursor_and_suspect_recovery(client,world):
    h,state=world; r=register(client,h); verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    p=page(client,h,r['registration_id'],limit=1)
    assert len(p['characters']['items'])==1 and len(p['settings']['activity_character_ids'])==3
    cursor=p['characters']['next_cursor']
    assert page(client,h,r['registration_id'],limit=1,cursor=cursor)['settings']==p['settings']
    state['missing']=(2,)
    refresh=change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{})
    assert refresh.status_code==200,refresh.text
    q=page(client,h,r['registration_id'])
    assert q['settings']['configuration_state']=='needs_reconfiguration'
    assert len(q['settings']['activity_character_ids'])==3
    assert len(q['settings']['ineligible_character_ids'])==1
    assert client.get(BASE+'/'+r['registration_id']+'/characters',headers=h,params={'cursor':cursor}).json()['error']['code']=='CURSOR_STALE'
    with session() as db,db.begin():
        from app.game_accounts.models import LimitEvent
        db.execute(__import__('sqlalchemy').delete(LimitEvent))
    state['missing']=()
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    q=page(client,h,r['registration_id'])
    assert not q['settings']['ineligible_character_ids']
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(q)).status_code==200


@pytest.mark.parametrize('kind',['empty','representative','duplicate','unknown','stale'])
def test_invalid_settings_rollback(client,world,kind):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);data=save_data(p)
    if kind=='empty': data['activity_character_ids']=[]
    if kind=='representative':data['representative_character_id']=str(uuid.uuid4())
    if kind=='duplicate':data['activity_character_ids']*=2
    if kind=='unknown':data['activity_character_ids'].append(str(uuid.uuid4()))
    if kind=='stale':data['expected_ownership_revision']+=1
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',data).status_code in (400,404,409)
    assert page(client,h,r['registration_id'])['settings']==p['settings']


def test_expiry_cancel_and_start_replay(client,world):
    h,state=world;r=register(client,h)
    key=uuid.uuid4(); data=dict(source='registration',registration_id=r['registration_id'])
    v=change(client,h,'post',VERIFY,data,key).json()
    assert change(client,h,'delete',VERIFY+'/'+v['challenge_id']).status_code==204
    replay=change(client,h,'post',VERIFY,data,key)
    assert replay.status_code==201 and replay.json()['challenge_id']==v['challenge_id']
    assert client.get(VERIFY+'/'+v['challenge_id'],headers=h).json()['status']=='cancelled'
    calls=state['calls']
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{}).status_code==409
    assert state['calls']==calls
    v=start(client,h,r['registration_id'])
    with session() as db,db.begin():
        obj=db.get(Verification,uuid.UUID(v['challenge_id']));obj.expires_at=now(db)
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{}).json()['error']['code']=='VERIFICATION_EXPIRED'
    with session() as db:
        assert db.get(Verification,uuid.UUID(v['challenge_id'])).status=='expired'


def test_live_evidence_boundary(client,world):
    h,state=world;r=register(client,h);state['validated']=False
    v=start(client,h,r['registration_id']);state['removed']=v['required_slots']
    r=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert r.json()['result_code']=='PROVIDER_EVIDENCE_PENDING'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==0


def test_concurrent_same_registration(client,world):
    h,state=world; key=uuid.uuid4()
    data=dict(lookup_character_name='a0',label='sample',is_main=False)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:change(client,h,'post',BASE,data,key),range(2)))
    assert any(r.status_code==201 for r in results)
    assert all(r.status_code in (201,409) for r in results)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Registration))==1


def test_upstream_failure_can_retry_same_key(client,world,monkeypatch):
    h,state=world; original=observations.fetch
    monkeypatch.setattr(observations,'fetch',lambda *args: (_ for _ in ()).throw(ProviderUnavailable()))
    key=uuid.uuid4();data=dict(lookup_character_name='a0',label='sample',is_main=False)
    assert change(client,h,'post',BASE,data,key).status_code==503
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Registration))==0
    monkeypatch.setattr(observations,'fetch',original)
    assert change(client,h,'post',BASE,data,key).status_code==201


def test_lease_takeover_fences_old_worker(world):
    h,_=world
    from app.auth.service import principal
    from app.game_accounts.support import reserve,commit_result,GameError
    p=principal(h['Authorization'].split()[1]);key=uuid.uuid4()
    ticket,_=reserve(p,'register',key,{'sample':1})
    with pytest.raises(GameError,match='REQUEST_IN_PROGRESS'):
        reserve(p,'register',key,{'sample':1})
    with session() as db,db.begin():
        db.get(RequestResult,ticket[0]).lease_expires_at=now(db)-timedelta(seconds=1)
    new,_=reserve(p,'register',key,{'sample':1})
    assert new[1]>ticket[1]
    with pytest.raises(GameError):
        with session() as db,db.begin():
            commit_result(db,ticket,201,{})
    with session() as db,db.begin():
        commit_result(db,new,201,{})


def test_provider_parser_does_not_accept_partial_or_duplicate():
    row=dict(ServerName='sample',CharacterName='sample',CharacterClassName='sample',CharacterLevel=60,ItemAvgLevel=None)
    assert observations.roster([row],'sample')[0]['item_level'] is None
    for raw in (None,[],[row,row],[dict(row,CharacterLevel=True)],[dict(row,ItemAvgLevel='NaN')],[row]*201):
        with pytest.raises(ProviderUnavailable):observations.roster(raw,'sample')


def another_user(login,monkeypatch):
    from app.auth import service as auth_service
    monkeypatch.setattr(auth_service,'verify_google',lambda *args:'other-subject')
    auth,_=login()
    return PrivateHeaders(Authorization='Bearer '+auth['access_token'])


def test_transfer_is_atomic_and_old_owner_cannot_save(client,world,login,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    old=page(client,h,r['registration_id']);old_save=save_data(old)
    other=another_user(login,monkeypatch)
    # No information about someone else's registration or challenge.
    assert client.get(BASE+'/'+r['registration_id']+'/characters',headers=other).status_code==404
    transferred=verify(client,other,state)
    new=page(client,other,transferred['registration_id'])
    assert new['settings']['activity_character_ids']==[]
    assert new['settings']['configuration_state']=='unconfigured'
    assert new['settings']['ownership_revision']==old['settings']['ownership_revision']+1
    lost=page(client,h,r['registration_id'])
    assert lost['ownership_status']=='ownership_lost'
    assert all(i['character_id'] is None for i in lost['characters']['items'])
    assert lost['settings']['activity_character_ids']==[]
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',old_save).status_code==403
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==1
        assert db.scalar(select(func.count()).select_from(Character))==3
        assert db.scalar(select(func.count()).select_from(Audit))==2


def test_simultaneous_challenges_only_one_revision_wins(client,world,login,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    other=another_user(login,monkeypatch)
    # Make required slots deterministic for this transaction concurrency test.
    monkeypatch.setattr(service,'required_slots',lambda _:('무기',))
    one=start(client,other);two=start(client,other)
    state['removed']=('무기',)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda v:change(client,other,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{}),(one,two)))
    assert sorted(r.status_code for r in results)==[200,409]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Audit))==2
        assert db.scalar(select(func.count()).select_from(Account))==1


def test_incomplete_roster_never_transfers(client,world,login,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    other=another_user(login,monkeypatch);v=start(client,other)
    state['missing']=(2,);state['removed']=v['required_slots']
    response=change(client,other,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.json()['result_code']=='ROSTER_EVIDENCE_PENDING'
    assert page(client,h,r['registration_id'])['ownership_status']=='owned'


def test_transaction_failure_rolls_back_entire_ownership(client,world,monkeypatch):
    h,state=world;r=register(client,h);v=start(client,h,r['registration_id'])
    state['removed']=v['required_slots']
    original=service.commit_result
    def broken(*args):raise RuntimeError('injected precommit failure')
    monkeypatch.setattr(service,'commit_result',broken)
    key=uuid.uuid4()
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{},key).status_code==500
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==0
        assert db.scalar(select(func.count()).select_from(Character))==0
        assert db.scalar(select(func.count()).select_from(Audit))==0
        assert db.get(Verification,uuid.UUID(v['challenge_id'])).status=='pending'
    monkeypatch.setattr(service,'commit_result',original)
    with session() as db,db.begin():
        from app.game_accounts.models import LimitEvent
        db.execute(__import__('sqlalchemy').delete(LimitEvent))
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{},key).json()['status']=='verified'


def test_authorization_rechecked_after_provider_wait(client,world,monkeypatch):
    from app.auth.models import Session as AuthSession
    h,_=world
    original=observations.fetch
    def revoke_then_fetch(*args):
        with session() as db,db.begin():
            for s in db.scalars(select(AuthSession)):
                s.revoked_at=now(db)
        return original(*args)
    monkeypatch.setattr(observations,'fetch',revoke_then_fetch)
    r=change(client,h,'post',BASE,dict(lookup_character_name='a0',label='sample',is_main=False))
    assert r.status_code==401,r.text
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Registration))==0


def test_cross_account_preservation_and_remove_reregister(client,world):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    expected=page(client,h,r['registration_id'])['settings']
    state['group']='b'
    b=register(client,h,'b0')
    v=start(client,h,b['registration_id']);state['removed']=v['required_slots']
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{}).json()['status']=='verified'
    state['removed']=()
    q=page(client,h,b['registration_id'])
    assert change(client,h,'put',BASE+'/'+b['registration_id']+'/character-settings',save_data(q)).status_code==200
    assert page(client,h,r['registration_id'])['settings']==expected
    rows=client.get(BASE,headers=h).json()['items'];current=next(v for v in rows if v['registration_id']==b['registration_id'])
    assert change(client,h,'delete',BASE+'/'+b['registration_id']+'?expected_version='+str(current['version'])).status_code==204
    new=register(client,h,'b0')
    assert new['settings']['configuration_state']=='unconfigured'
    # Canonical state remains intact even though registration was removed.
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==2


def test_rate_limit_and_retention_cleanup(client,world):
    h,state=world;r=register(client,h)
    first=change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{})
    assert first.status_code==200
    second=change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{})
    assert second.status_code==429 and 1<=int(second.headers['retry-after'])<=10
    v=start(client,h,r['registration_id'])
    with session() as db,db.begin():
        obj=db.get(Verification,uuid.UUID(v['challenge_id']))
        obj.status='expired';obj.terminal_at=now(db)-timedelta(hours=24)
    # Retention must end even when the scheduled cleaner has not run.
    assert client.get(VERIFY+'/'+v['challenge_id'],headers=h).status_code==404
    assert change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{}).status_code==404
    from app.game_accounts.cleanup import clean
    clean()
    assert client.get(VERIFY+'/'+v['challenge_id'],headers=h).status_code==404


def test_registration_limit_and_concurrent_main_switch(client,world):
    h,state=world
    # Group identities are distinct, while all share the same authenticated actor.
    regs=[]
    for i in range(20):
        state['group']=str(i)+'-';regs.append(register(client,h,str(i)+'-0'))
    state['group']='extra-'
    assert change(client,h,'post',BASE,dict(lookup_character_name='extra-0',label='extra',is_main=False)).json()['error']['code']=='REGISTRATION_LIMIT'
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda r:change(client,h,'patch',BASE+'/'+r['registration_id'],dict(is_main=True,expected_version=1)),regs[:2]))
    assert all(r.status_code==200 for r in results)
    assert sum(r['is_main'] for r in client.get(BASE,headers=h).json()['items'])==1


def test_fresh_summary_requests_are_coalesced(world,monkeypatch):
    entered,finished=Event(),Event()
    original=observations.fetch
    calls=[]
    def delayed(*args):
        calls.append(1);entered.set()
        assert finished.wait(5)
        return original(*args)
    monkeypatch.setattr(observations,'fetch',delayed)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(service.lookup,'a0')
        assert entered.wait(5)
        second=pool.submit(service.lookup,'a0')
        # Wait until second observes the lease, then complete the provider call.
        import time
        time.sleep(0.15)
        finished.set()
        a,b=first.result(),second.result()
    assert a.roster==b.roster and len(calls)==1


def test_strict_query_and_rollback_character_limit(client,world):
    h,state=world
    assert client.get(BASE+'?owner_id='+str(uuid.uuid4()),headers=h).status_code==400
    assert client.get(BASE+'?limit=1&limit=2',headers=h).status_code==400
    state['count']=200
    r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db,db.begin():
        # Existing 200 canonical identities are retained; new rows cannot silently
        # push the account over the bound while an older identity becomes suspect.
        first=db.scalar(select(Character).order_by(Character.character_name))
        first.character_name='old-name'
    result=change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{})
    assert result.status_code==400 and result.json()['error']['code']=='CHARACTER_LIMIT'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Character))==200


def test_power_null_preserves_value_and_marks_stale(client,world):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db,db.begin():
        c=db.scalar(select(Character).where(Character.character_name=='a0'))
        c.summary={**c.summary,'combat_power':'12345.67'}
        c.power_fetched_at=now(db)-timedelta(minutes=1)
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    p=page(client,h,r['registration_id'])
    row=next(i for i in p['characters']['items'] if i['character_name']=='a0')
    assert row['combat_power']=='12345.67' and row['power_stale'] is True
    assert row['power_fetched_at'] is not None


@pytest.mark.parametrize('lease_failure', ['expired', 'taken_over'])
def test_lease_rejection_returns_retry_after_and_rolls_back(client, world, monkeypatch, lease_failure):
    from app.auth.service import principal
    from app.game_accounts.support import reserve

    headers, _ = world
    registration = register(client, headers)
    rid = registration['registration_id']
    actor = principal(headers['Authorization'].split()[1])
    key = uuid.uuid4()
    body = {'label': 'changed', 'expected_version': registration['version']}
    payload = {'target': rid, 'body': body}
    old_ticket, _ = reserve(actor, 'patch', key, payload)
    with session() as db, db.begin():
        db.get(RequestResult, old_ticket[0]).lease_expires_at = now(db) - timedelta(seconds=1)
    if lease_failure == 'taken_over':
        new_ticket, _ = reserve(actor, 'patch', key, payload)
        assert new_ticket[1] > old_ticket[1]
    with session() as db:
        row = db.get(RequestResult, old_ticket[0])
        generation_before = row.generation
        expiry_before = row.lease_expires_at

    # The old worker has already acquired its ticket; resume it at the actual
    # HTTP mutation path after expiry/takeover by a separate transaction.
    monkeypatch.setattr(service, 'reserve', lambda *args: (old_ticket, None))
    response = change(client, headers, 'patch', BASE + '/' + rid, body, key)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'REQUEST_IN_PROGRESS'
    assert response.headers.get('retry-after') == '2'
    assert response.headers['cache-control'] == 'no-store'
    with session() as db:
        stored = db.get(Registration, uuid.UUID(rid))
        assert stored.label == registration['label']
        assert stored.version == registration['version']
        row = db.get(RequestResult, old_ticket[0])
        assert row.generation == generation_before
        assert row.lease_expires_at == expiry_before
        assert row.completed_at is None
        if lease_failure == 'taken_over':
            assert row.state == 'running'


@pytest.mark.parametrize('provided', [{}, {'label': ''}, {'label': '   '}, {'label': '  내 이름  '}])
def test_registration_optional_label_saved_and_replayed(client, world, provided):
    h, _ = world
    key = uuid.uuid4()
    body = {'lookup_character_name': 'a0', **provided}
    expected = provided.get('label', '').strip()
    first = change(client, h, 'post', BASE, body, key)
    assert first.status_code == 201
    assert first.json()['label'] == expected
    assert change(client, h, 'post', BASE, body, key).json() == first.json()
    assert client.get(BASE, headers=h).json()['items'][0]['label'] == expected
    with session() as db:
        assert db.get(Registration, first.json()['registration_id']).label == expected
    other = {**body, 'label': 'different'}
    assert change(client, h, 'post', BASE, other, key).json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


def test_label_clear_preserve_switch_and_stale_version(client, world):
    h, state = world
    first = register(client, h, main=True)
    state['group'] = 'b'
    second = register(client, h, 'b0')
    path = BASE + '/' + first['registration_id']
    key = uuid.uuid4()
    clear = {'expected_version': first['version'], 'label': ''}
    cleared = change(client, h, 'patch', path, clear, key)
    assert cleared.status_code == 200 and cleared.json()['label'] == ''
    assert change(client, h, 'patch', path, clear, key).json() == cleared.json()
    stale = change(client, h, 'patch', path, {'expected_version': first['version'], 'label': 'stale'})
    assert stale.json()['error']['code'] == 'REVISION_CONFLICT'
    switched = change(client, h, 'patch', BASE + '/' + second['registration_id'],
                      {'expected_version': second['version'], 'is_main': True})
    assert switched.status_code == 200 and switched.json()['label'] == 'sample'
    rows = client.get(BASE, headers=h).json()['items']
    assert [row['registration_id'] for row in rows] == [first['registration_id'], second['registration_id']]
    assert [row['label'] for row in rows] == ['', 'sample']
    assert [row['is_main'] for row in rows] == [False, True]
    # Main switching also changed the old main's version; use the refreshed value.
    current = rows[0]
    renamed = change(client, h, 'patch', path, {'expected_version': current['version'], 'label': '  복원 이름  '})
    assert renamed.status_code == 200 and renamed.json()['label'] == '복원 이름'
    final = change(client, h, 'patch', path, {'expected_version': renamed.json()['version'], 'label': '  '})
    assert final.status_code == 200 and final.json()['label'] == ''


@pytest.mark.parametrize('bad', [None, 1, True, 'x' * 41])
def test_label_invalid_does_not_change_registration(client, world, bad):
    h, _ = world
    assert change(client, h, 'post', BASE, {'lookup_character_name': 'a0', 'label': bad}).status_code == 400
    r = register(client, h)
    response = change(client, h, 'patch', BASE + '/' + r['registration_id'],
                      {'expected_version': r['version'], 'label': bad})
    assert response.status_code == 400
    stored = client.get(BASE, headers=h).json()['items'][0]
    assert stored['label'] == r['label'] and stored['version'] == r['version']


def test_automatic_label_order_includes_named_rows_across_pages(client, world):
    h, state = world
    ids = []
    for group, label in [('a', ''), ('b', 'custom'), ('c', '')]:
        state['group'] = group
        response = change(client, h, 'post', BASE, {'lookup_character_name': group + '0', 'label': label})
        assert response.status_code == 201
        ids.append(response.json()['registration_id'])
    rows = []
    cursor = None
    while True:
        params = {'limit': 1, **({'cursor': cursor} if cursor else {})}
        response = client.get(BASE, headers=h, params=params)
        assert response.status_code == 200
        rows.extend(response.json()['items'])
        cursor = response.json()['next_cursor']
        if cursor is None:
            break
    assert [row['registration_id'] for row in rows] == ids
    assert [row['label'] for row in rows] == ['', 'custom', '']
    assert all(row['is_main'] is False for row in rows)
