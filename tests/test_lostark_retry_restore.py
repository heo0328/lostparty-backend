from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json
import uuid
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.lostark_keys import rate_limits, service
from app.lostark_keys.models import ProviderLimit, Credential
from app.game_accounts.models import PowerCache, RequestResult
from app.game_accounts.support import GameError
from app.game_accounts import power_service
from app.game_accounts.provider import LostArkProvider
from tests.test_lostark_keys import member, put, delete, TOKEN, URL
from tests.test_game_accounts import world, change, BASE, register, page, PrivateHeaders

RESTORE=URL+'/restore'


def restore(client,h,version=2,body=None):
    return client.post(RESTORE,headers=h,json=body if body is not None else {'expected_version':version})


def test_restore_readonly_no_dedup_no_secret_logs(client,member,monkeypatch,caplog):
    monkeypatch.setattr(LostArkProvider,'_fetch',lambda *a: (_ for _ in ()).throw(AssertionError('no network')))
    assert restore(client,member).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'
    put(client,member)
    with session() as db: before=db.scalar(select(func.count()).select_from(RequestResult))
    a=restore(client,member); b=restore(client,member)
    assert a.status_code==200 and a.json()=={'token':TOKEN,'version':2} and b.json()==a.json()
    assert a.headers['Cache-Control']=='no-store'
    assert TOKEN not in client.get(URL,headers=member).text and TOKEN not in caplog.text
    assert restore(client,member,1).json()['error']['code']=='LOSTARK_KEY_CHANGED'
    assert put(client,member,token='new.personal.signature',version=2).status_code==200
    assert restore(client,member,2).json()['error']['code']=='LOSTARK_KEY_CHANGED'
    assert delete(client,member,3).status_code==200
    assert restore(client,member,3).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(RequestResult))==before+2
        assert all(TOKEN not in str(r.result) for r in db.scalars(select(RequestResult)))


@pytest.mark.parametrize('body',[{}, {'expected_version':True},{'expected_version':0},{'expected_version':'2'},
                                {'expected_version':2,'user_id':'other'}, {'expected_version':None}])
def test_restore_strict_and_guest(client,member,body):
    assert restore(client,{},body=body).status_code in (400,401)
    assert restore(client,member,body=body).status_code==400
    assert client.post(RESTORE+'?user_id=other',headers=member,json={'expected_version':2}).status_code==400


def test_restore_member_session_and_corruption(client,member,login,monkeypatch):
    from app.auth import service as auth
    from app.auth.models import Session
    put(client,member)
    monkeypatch.setattr(auth,'verify_google',lambda *args:'second-member')
    other,_=login(); second=PrivateHeaders(Authorization='Bearer '+other['access_token'])
    assert restore(client,second).json()['error']['code']=='LOSTARK_KEY_NOT_CONFIGURED'
    with session() as db,db.begin():
        c=db.scalar(select(Credential)); c.ciphertext=b'bad'
    assert restore(client,member).json()['error']['code']=='LOSTARK_KEY_UNAVAILABLE'
    with session() as db,db.begin():
        for s in db.scalars(select(Session)): s.revoked_at=now(db)
    assert restore(client,member).status_code==401
    assert restore(client,second).status_code==401


@pytest.mark.parametrize('reset',[None,'bad','-1','0','1668659557000','9'*30])
def test_invalid_reset_has_finite_60_seconds(reset):
    current=datetime(2026,10,15,tzinfo=timezone.utc)
    headers={} if reset is None else {'X-RateLimit-Reset':reset}
    assert rate_limits.observation(429,headers,current)==current+timedelta(seconds=60)


def test_official_epoch_seconds_and_success_remaining_zero():
    current=datetime(2022,11,17,5,52,17,tzinfo=timezone.utc)
    future=current+timedelta(seconds=45)
    headers={'X-RateLimit-Reset':str(int(future.timestamp())),'X-RateLimit-Limit':'100','X-RateLimit-Remaining':'0'}
    assert rate_limits.observation(429,headers,current)==future
    assert rate_limits.observation(200,headers,current)==future
    assert rate_limits.observation(200,{},current) is None
    assert rate_limits.observation(200,{**headers,'X-RateLimit-Remaining':'15'},current) is None
    assert rate_limits.observation(429,{'X-RateLimit-Reset':str(int((current+timedelta(seconds=301)).timestamp()))},current)==current+timedelta(seconds=60)


def test_token_deadline_max_no_extend_on_block_and_expiry():
    fp=service.fingerprint(TOKEN); second=service.fingerprint('other.personal.signature')
    current=datetime.now(timezone.utc)
    rate_limits.record(fp,current+timedelta(seconds=80))
    rate_limits.record(fp,current+timedelta(seconds=10))
    with pytest.raises(GameError) as e: rate_limits.acquire(fp)
    assert e.value.code=='UPSTREAM_RATE_LIMITED' and e.value.retry_after<=80
    rate_limits.acquire(second)
    with session() as db,db.begin():
        row=db.get(ProviderLimit,fp); assert row.blocked_until==current+timedelta(seconds=80)
        row.blocked_until=now(db)-timedelta(seconds=1)
    rate_limits.acquire(fp)


def response_transport(status=429,remaining=None):
    from unittest.mock import Mock
    class Response:
        status_code=status
        headers={'Content-Type':'application/json','X-RateLimit-Reset':str(int((datetime.now(timezone.utc)+timedelta(seconds=50)).timestamp()))}
        if remaining is not None: headers['X-RateLimit-Remaining']=str(remaining)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def iter_content(self,**kw):
            yield b'[{"ServerName":"s","CharacterName":"sample","CharacterClassName":"c","CharacterLevel":60,"ItemAvgLevel":"1700"}]'
    import requests
    return Mock(get=Mock(return_value=Response()), RequestException=requests.RequestException)


def test_single_upstream_json_header_and_no_repeated_wire(client,member,monkeypatch):
    import app.game_accounts.provider as provider
    wire=response_transport(); monkeypatch.setattr(provider,'requests',wire)
    put(client,member)
    def preview(): return client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    a=preview(); b=preview()
    for r in (a,b):
        assert r.status_code==503 and r.json()['error']['code']=='UPSTREAM_RATE_LIMITED'
        assert int(r.headers['Retry-After'])==r.json()['error']['retry_after_seconds']
        assert 1<=int(r.headers['Retry-After'])<=50
        assert datetime.fromisoformat(r.json()['error']['retry_at']).tzinfo is not None
    assert wire.get.call_count==1
    assert client.get('/v1/me',headers=member).status_code==200


def test_success_remaining_zero_keeps_current_success(client,member,monkeypatch):
    import app.game_accounts.provider as provider
    wire=response_transport(status=200,remaining=0); monkeypatch.setattr(provider,'requests',wire)
    put(client,member)
    r=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    assert r.status_code==200
    # Same cached query stays readable; a new name would require an external call.
    assert client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'}).status_code==200
    other=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'other'})
    assert other.status_code==503 and other.json()['error']['code']=='UPSTREAM_RATE_LIMITED'
    assert wire.get.call_count==1


def test_batch_partial_timing_and_original_replay(client,world,monkeypatch):
    h,_=world;r=register(client,h); fp=service.fingerprint('test.member.signature')
    def fetch(pair,token,observer=None):
        if pair[1]=='a0': return 'available','100',None
        observer(429,{})
        return 'failed',None,'UPSTREAM_RATE_LIMITED'
    monkeypatch.setattr(power_service,'fetch_power',fetch)
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    data={'characters':[{'server_name':'sample-server','character_name':f'a{i}'} for i in range(3)]}
    key=uuid.uuid4(); response=change(client,h,'post',path,data,key)
    assert response.status_code==200 and 'Retry-After' not in response.headers
    items=response.json()['items']; assert items[0]['status']=='updated' and items[0]['retry_at'] is None
    limited=[item for item in items if item['reason']=='UPSTREAM_RATE_LIMITED']
    assert limited and all(1<=i['retry_after_seconds']<=60 and i['retry_at'] for i in limited)
    assert change(client,h,'post',path,data,key).json()==response.json()
    retry=change(client,h,'post',path,data)
    assert retry.status_code==200 and any(i['retry_at'] for i in retry.json()['items'])


def test_late_transport_limiter_keeps_old_token_only(client,world,monkeypatch):
    h,_=world;r=register(client,h)
    entered,finish,recorded=Event(),Event(),Event()
    oldfp=service.fingerprint('test.member.signature')
    def delayed(pair,token,observer=None):
        entered.set(); finish.wait(5)
        observer(429,{}); recorded.set()
        return 'failed',None,'UPSTREAM_RATE_LIMITED'
    monkeypatch.setattr(power_service,'fetch_power',delayed)
    monkeypatch.setattr(power_service,'BUDGET_SECONDS',1.2)
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    data={'characters':[{'server_name':'sample-server','character_name':'a0'}]}
    response=change(client,h,'post',path,data)
    assert entered.is_set() and response.status_code==200
    assert put(client,h,token=TOKEN,version=2).status_code==200
    finish.set(); assert recorded.wait(5)
    with session() as db:
        assert db.get(ProviderLimit,oldfp) is not None
        assert db.get(ProviderLimit,service.fingerprint(TOKEN)) is None
        assert db.scalar(select(PowerCache)).value is None
    rate_limits.acquire(service.fingerprint(TOKEN))


def test_concurrent_preview_waiter_receives_known_limit(client,member,monkeypatch):
    import app.game_accounts.provider as provider
    put(client,member)
    entered,finish=Event(),Event()
    wire=response_transport()
    response=wire.get.return_value
    def delayed(*a,**kw):
        entered.set(); assert finish.wait(5)
        return response
    wire.get.side_effect=delayed
    monkeypatch.setattr(provider,'requests',wire)
    from app.lostark_keys.models import MemberFetch
    def preview(): return client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(preview); assert entered.wait(5)
        second=pool.submit(preview)
        # Check polling waiter can join before owner's provider result.
        import time
        time.sleep(.15); finish.set()
        responses=[first.result(),second.result()]
    assert wire.get.call_count==1
    assert all(r.status_code==503 and r.json()['error']['code']=='UPSTREAM_RATE_LIMITED' and r.json()['error']['retry_at'] for r in responses)


def test_server_quota_and_upstream_max_deadline_json(client,member,monkeypatch):
    from app.game_accounts.models import LimitEvent
    put(client,member); fp=service.fingerprint(TOKEN)
    with session() as db,db.begin():
        current=now(db)
        for _ in range(80): db.add(LimitEvent(scope='lostark-token:'+fp,created_at=current))
    response=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    assert response.status_code==429 and response.json()['error']['code']=='RATE_LIMITED'
    assert response.json()['error']['retry_after_seconds']==int(response.headers['Retry-After'])
    rate_limits.record(fp,datetime.now(timezone.utc)+timedelta(seconds=15))
    response=client.post('/v1/game-accounts/preview',headers=member,json={'character_name':'sample'})
    assert response.status_code==503 and response.json()['error']['code']=='UPSTREAM_RATE_LIMITED'
    assert response.json()['error']['retry_after_seconds']>=50


def test_expired_upstream_wait_not_hidden_by_failure_cache(client,world,monkeypatch):
    h,_=world;r=register(client,h);fp=service.fingerprint('test.member.signature')
    path=BASE+'/'+r['registration_id']+'/combat-power/refresh'
    data={'characters':[{'server_name':'sample-server','character_name':'a0'}]}
    def limited(pair,token,observer=None):
        observer(429,{})
        return 'failed',None,'UPSTREAM_RATE_LIMITED'
    monkeypatch.setattr(power_service,'fetch_power',limited)
    assert change(client,h,'post',path,data).json()['items'][0]['status']=='failed'
    with session() as db,db.begin(): db.get(ProviderLimit,fp).blocked_until=now(db)-timedelta(seconds=1)
    monkeypatch.setattr(power_service,'fetch_power',lambda pair,token,observer=None: ('available','100',None))
    response=change(client,h,'post',path,data)
    assert response.status_code==200 and response.json()['items'][0]['status']=='updated'
    assert response.json()['items'][0]['retry_at'] is None
