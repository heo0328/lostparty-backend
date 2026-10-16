import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.lostark_keys import service
from app.lostark_keys.models import Credential
from app.game_accounts.models import ScopedRosterCache as MemberPreview, ScopedRosterLease as MemberFetch
from app.game_accounts.models import RequestResult, ScopedPowerCache as PowerCache, PreviewCache, LimitEvent
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.support import quota, GameError
from tests.test_game_accounts import PrivateHeaders, world, register, change, BASE, page, verify

URL = '/v1/me/lostark-api-key'
TOKEN = 'mock.personal.signature'

@pytest.fixture
def member(login):
    auth, _ = login()
    return PrivateHeaders(Authorization='Bearer '+auth['access_token'])


def put(client, h, token=TOKEN, version=1, key=None):
    return client.put(URL, headers={**h, 'Idempotency-Key': str(key or uuid.uuid4())},
                      json={'token': token, 'expected_version': version})


def delete(client, h, version, key=None):
    return client.delete(URL, params={'expected_version': version},
                         headers={**h, 'Idempotency-Key': str(key or uuid.uuid4())})


def test_metadata_ciphertext_delete_and_historical_replay(client, member, monkeypatch, caplog):
    def forbidden(*args): raise AssertionError('no provider on key registration')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    default={'configured':False,'version':1,'updated_at':None}
    assert client.get(URL,headers=member).json()==default
    with session() as db: assert db.scalar(select(func.count()).select_from(Credential))==0
    key=uuid.uuid4(); a=put(client,member,key=key)
    assert a.status_code==200 and a.json()['version']==2
    with session() as db:
        c=db.scalar(select(Credential)); r=db.scalar(select(RequestResult))
        assert TOKEN.encode() not in c.ciphertext and len(c.nonce)==12
        assert TOKEN not in str(r.result) and TOKEN not in r.digest
        encrypted,nonce=c.ciphertext,c.nonce
    b=put(client,member,version=2)
    assert b.json()['version']==3
    with session() as db:
        c=db.scalar(select(Credential)); assert c.nonce!=nonce and c.ciphertext!=encrypted
    assert delete(client,member,3).json()['version']==4
    assert delete(client,member,4).json()['version']==4
    assert put(client,member,key=key).json()==a.json()
    assert client.get(URL,headers=member).json()['configured'] is False
    with session() as db:
        c=db.scalar(select(Credential)); assert c.ciphertext is c.nonce is c.key_id is c.fingerprint is None
    assert put(client,member,token='other.personal.signature',key=key).json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert TOKEN not in caplog.text


@pytest.mark.parametrize('token', [None,1,True,'','Bearer '+TOKEN,TOKEN+'\n','a.b','a b.c.d','a.b.c.d','가.b.c','a.b.' , 'a'*16385+'.b.c'])
def test_invalid_input_never_returned(client, member, token):
    r=put(client,member,token=token)
    assert r.status_code==400 and set(r.json())=={'error'}
    assert set(r.json()['error'])=={'code','message','request_id'}
    assert client.get(URL,headers=member).json()['configured'] is False


def test_auth_stale_and_concurrent_writers(client, member):
    assert client.get(URL).status_code==401
    assert put(client,{}).status_code==401
    assert put(client,member).status_code==200
    with ThreadPoolExecutor(max_workers=2) as p:
        results=list(p.map(lambda _: put(client,member,version=2),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    assert delete(client,member,2).json()['error']['code']=='REVISION_CONFLICT'
    assert client.get(URL+'?token=bad',headers=member).status_code==400
    assert client.request('GET',URL,headers=member,content=b'{}').status_code==400
    assert client.request('DELETE',URL+'?expected_version=3',headers={**member,'Idempotency-Key':str(uuid.uuid4())},content=b'{}').status_code==400
    assert client.delete(URL+'?expected_version=3&expected_version=3',headers={**member,'Idempotency-Key':str(uuid.uuid4())}).status_code==400


def test_members_use_only_their_key_and_unconfigured_cache_never_fallback(client, member, login, monkeypatch):
    from app.auth import service as auth
    calls=[]
    def siblings(self,name):
        calls.append(self._token)
        return [{'ServerName':'sample-server','CharacterName':name,'CharacterClassName':'sample-class',
                 'CharacterLevel':60,'ItemAvgLevel':'1700'}]
    monkeypatch.setattr(LostArkProvider,'siblings',siblings)
    monkeypatch.setenv('LOSTARK_API_TOKEN','must.never.fallback')
    with session() as db,db.begin():
        db.add(PreviewCache(name='sample',roster=[],fetched_at=now(db)))
    def preview(h): return client.post('/v1/game-accounts/preview',headers=h,json={'character_name':'sample'})
    assert preview(member).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'
    assert calls==[]
    assert put(client,member).status_code==200
    assert preview(member).status_code==200 and preview(member).status_code==200
    assert calls==[TOKEN]
    monkeypatch.setattr(auth,'verify_google',lambda *a:'other-subject')
    auth2,_=login(); second=PrivateHeaders(Authorization='Bearer '+auth2['access_token'])
    assert put(client,second,token='second.personal.signature').status_code==200
    assert preview(second).status_code==200 and calls==[TOKEN,'second.personal.signature']
    assert put(client,member,token='new.personal.signature',version=2).status_code==200
    assert preview(member).status_code==200 and calls[-1]=='new.personal.signature'
    assert delete(client,member,3).status_code==200
    assert preview(member).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'
    with session() as db: assert db.scalar(select(func.count()).select_from(MemberPreview))==3


@pytest.mark.parametrize('mode',['replace','delete'])
def test_old_preview_result_discarded_on_key_change(client, member, monkeypatch, mode):
    put(client,member)
    entered,finish=Event(),Event()
    def siblings(self,name):
        entered.set(); assert finish.wait(5)
        return [{'ServerName':'s','CharacterName':name,'CharacterClassName':'c','CharacterLevel':60,'ItemAvgLevel':'1700'}]
    monkeypatch.setattr(LostArkProvider,'siblings',siblings)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(client.post,'/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
        assert entered.wait(5)
        assert (put(client,member,version=2) if mode=='replace' else delete(client,member,2)).status_code==200
        finish.set(); r=pending.result()
    assert r.status_code==409 and r.json()['error']['code']=='LOSTARK_KEY_CHANGED'
    with session() as db: assert db.scalar(select(func.count()).select_from(MemberPreview))==0


def test_crypto_failure_no_leak_and_get_still_available(client, member):
    put(client,member)
    with session() as db,db.begin():
        c=db.scalar(select(Credential)); c.ciphertext=b'invalid'
    r=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    assert r.status_code==503 and r.json()['error']['code']=='LOSTARK_KEY_UNAVAILABLE'
    assert client.get(URL,headers=member).json()['configured'] is True
    assert delete(client,member,2).status_code==200


def test_token_quota_survives_versions_and_is_separate(monkeypatch):
    a=service.fingerprint(TOKEN); b=service.fingerprint('second.personal.signature')
    for _ in range(80): quota('lostark-token:'+a,80)
    with pytest.raises(GameError) as e: quota('lostark-token:'+a,80)
    assert e.value.status==429
    quota('lostark-token:'+b,80)


def test_new_session_restores_key_without_disclosing_it(client, member, login):
    put(client,member)
    auth,_=login(); second=PrivateHeaders(Authorization='Bearer '+auth['access_token'])
    assert client.get(URL,headers=second).json()==client.get(URL,headers=member).json()
    assert TOKEN not in client.get(URL,headers=second).text


def test_power_key_change_preserves_existing_value(client, world, monkeypatch):
    h,state=world; r=register(client,h); verify(client,h,state,r['registration_id'])
    def fetch(pair,token,observer=None): return 'available','100',None
    from app.game_accounts import power_service
    monkeypatch.setattr(power_service,'fetch_power',fetch)
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    data={'characters':[{'server_name':'sample-server','character_name':'a0'}]}
    assert change(client,h,'post',path,data).status_code==200
    assert put(client,h,version=2).status_code==200
    def racing(pair,token,observer=None):
        assert delete(client,h,3).status_code==200
        return 'available','999',None
    monkeypatch.setattr(power_service,'fetch_power',racing)
    response=change(client,h,'post',path,data)
    assert response.status_code==409 and response.json()['error']['code']=='LOSTARK_KEY_CHANGED'
    assert page(client,h,r['registration_id'])['characters']['items'][0]['combat_power']=='100'
    assert change(client,h,'post',path,data).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'


def test_rejected_key_is_business_error_not_logout(client, member, monkeypatch):
    put(client,member)
    def reject(*args): raise ProviderUnavailable('LOSTARK_KEY_REJECTED')
    monkeypatch.setattr(LostArkProvider,'siblings',reject)
    r=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    assert r.status_code==409 and r.json()['error']['code']=='LOSTARK_KEY_REJECTED'
    assert client.get('/v1/me',headers=member).status_code==200


def test_all_rest_paths_inject_member_token(client, member, monkeypatch):
    from app.game_accounts.equipment import SLOTS
    seen=[]
    def siblings(self,name):
        seen.append(('siblings',self._token))
        return [{'ServerName':'sample-server','CharacterName':name,'CharacterClassName':'sample-class',
                 'CharacterLevel':60,'ItemAvgLevel':'1700'}]
    def armory(self,name):
        seen.append(('armory',self._token))
        return {'ArmoryProfile':{'ServerName':'sample-server','CharacterName':name,'CombatPower':'100'},
                'ArmoryEquipment':[{'Type':slot,'Name':'mock '+slot,'Grade':'고대'} for slot in SLOTS]}
    def profile(self,name):
        seen.append(('profile',self._token))
        return {'ServerName':'sample-server','CharacterName':name,'CombatPower':'100'}
    for method,implementation in [('siblings',siblings),('armory',armory),('profile',profile)]:
        monkeypatch.setattr(LostArkProvider,method,implementation)
    put(client,member)
    r=register(client,member,name='sample')
    assert change(client,member,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    verify='/v1/me/game-account-verifications'
    v=change(client,member,'post',verify,{'source':'registration','registration_id':r['registration_id']})
    assert v.status_code==201
    assert change(client,member,'post',verify+'/'+v.json()['challenge_id']+'/confirm',{}).status_code==200
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    response=change(client,member,'post',path,{'characters':[{'server_name':'sample-server','character_name':'sample'}]})
    assert response.status_code==403 and response.json()['error']['code']=='OWNERSHIP_REQUIRED'
    from app.game_accounts.power_service import fetch_power
    assert fetch_power(('sample-server','sample'),TOKEN)==('available','100',None)
    assert {'siblings','armory','profile'}=={method for method,_ in seen}
    assert all(token==TOKEN for _,token in seen)
    assert delete(client,member,2).status_code==200
    # Cached power and completed key replay must not authorize a fresh external command.
    assert change(client,member,'post',path,{'characters':[{'server_name':'sample-server','character_name':'sample'}]}).json()['error']['code']=='OWNERSHIP_REQUIRED'
    assert client.get(BASE,headers=member).status_code==200
    assert page(client,member,r['registration_id'])['characters']['items'][0]['combat_power'] is None


def test_aad_member_binding_and_same_token_budget(client, member, login, monkeypatch):
    from app.auth import service as auth
    put(client,member)
    monkeypatch.setattr(auth,'verify_google',lambda *a:'other-member')
    credentials2,_=login(); second=PrivateHeaders(Authorization='Bearer '+credentials2['access_token'])
    put(client,second)
    with session() as db,db.begin():
        rows=list(db.scalars(select(Credential)))
        assert rows[0].fingerprint==rows[1].fingerprint
        rows[1].ciphertext,rows[1].nonce,rows[1].key_id=rows[0].ciphertext,rows[0].nonce,rows[0].key_id
    r=client.post('/v1/game-accounts/preview',headers=second,json={'character_name':'sample'})
    assert r.json()['error']['code']=='LOSTARK_KEY_UNAVAILABLE'


def test_key_failure_partial_and_fresh_cache_not_reused_after_replace(client, world, monkeypatch):
    from app.game_accounts import power_service
    h,state=world;r=register(client,h); verify(client,h,state,r['registration_id'])
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    data={'characters':[{'server_name':'sample-server','character_name':'a0'}]}
    monkeypatch.setattr(power_service,'fetch_power',lambda pair,token,observer=None: ('available','100',None))
    assert change(client,h,'post',path,data).status_code==200
    put(client,h,version=2)
    monkeypatch.setattr(power_service,'fetch_power',lambda pair,token,observer=None: ('failed',None,'LOSTARK_KEY_REJECTED'))
    response=change(client,h,'post',path,data)
    item=response.json()['items'][0]
    assert response.status_code==200 and item['status']=='failed' and item['reason']=='LOSTARK_KEY_REJECTED'
    assert item['combat_power']=='100' and item['power_stale']
    assert client.get('/v1/me',headers=h).status_code==200


def test_key_idempotency_fencing_and_expiry(client, member, monkeypatch):
    original=service.commit_result
    def expired(*args): raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(service,'commit_result',expired)
    key=uuid.uuid4(); response=put(client,member,key=key)
    assert response.status_code==409 and response.headers['Retry-After']=='2'
    assert client.get(URL,headers=member).json()['configured'] is False
    monkeypatch.setattr(service,'commit_result',original)
    assert put(client,member,key=key).status_code==200
    with session() as db,db.begin():
        db.scalar(select(RequestResult).where(RequestResult.key==key)).completed_at=now(db)-timedelta(hours=24)
    assert put(client,member,key=key).json()['error']['code']=='IDEMPOTENCY_EXPIRED'
