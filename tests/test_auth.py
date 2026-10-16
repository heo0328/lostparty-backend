import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select, func, update
from app.auth import tokens, service
from app.auth.models import User, Identity, Transaction, Session, Credential, Recovery
from app.core.database import session, now
from app.core.errors import AuthError


def auth(result):
    return {'Authorization': 'Bearer '+result['access_token']}


def renew(client, result, request_id=None):
    data = {'refresh_token': result['refresh_token'], 'refresh_request_id': request_id or tokens.secret()}
    return client.post('/v1/auth/refresh', json=data), data


def test_login_and_no_guest(client, login):
    assert client.get('/v1/me').status_code == 401
    with session() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
    first, req = login()
    second, _ = login()
    assert first['is_new_user'] and not second['is_new_user']
    assert first['user']['id'] == second['user']['id']
    assert first['session']['id'] != second['session']['id']
    r = client.get('/v1/me', headers=auth(first))
    assert r.status_code == 200
    assert set(r.json()) == {'id','status','created_at'}
    assert r.headers['cache-control'] == 'no-store'
    assert client.get('/v1/auth/session', headers=auth(first)).json() == first['session']
    assert client.post('/v1/auth/google', json=req).json()['error']['code'] == 'AUTH_TRANSACTION_CONSUMED'


@pytest.mark.parametrize('remember,days,hours', [(True,30,168),(False,0,2)])
def test_ttl(login, remember, days, hours):
    from datetime import datetime
    result, _ = login(remember)
    s = result['session']
    parse=lambda x:datetime.fromisoformat(x)
    assert parse(s['absolute_expires_at'])-parse(s['created_at']) == (timedelta(days=days) if days else timedelta(hours=12))
    assert parse(s['idle_expires_at'])-parse(s['created_at']) == timedelta(hours=hours)
    assert s['expires_at'] == s['idle_expires_at'] == result['refresh_expires_at']
    assert all(v.endswith('Z') for k,v in s.items() if k.endswith('_at'))


@pytest.mark.parametrize('payload', [ {'transaction_secret_hash':'A'*64}, {'transaction_secret_hash':'0'*64,'actor':'fake'}, {'transaction_secret_hash':None} ])
def test_strict_challenge(client,payload):
    r=client.post('/v1/auth/google/challenges',json=payload)
    assert r.status_code==400
    assert set(r.json()['error'])=={'code','message','request_id'}
    assert 'input' not in r.text


@pytest.mark.parametrize('value', ['true',1,None])
def test_strict_boolean(client,login,value):
    _, req=login()
    req['remember_me']=value
    assert client.post('/v1/auth/google',json=req).status_code==400


def test_canonical(client):
    valid=tokens.secret()
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    # A nonzero padding-bit encoding of the same bytes must be rejected.
    altered=valid[:-1]+alphabet[alphabet.index(valid[-1])+1]
    r=client.post('/v1/auth/logout',json={'refresh_token':altered})
    assert r.status_code==400


def test_refresh_recovery_and_limits(client,login):
    result,_=login()
    r,data=renew(client,result)
    assert r.status_code==200
    first=r.json()
    assert first['refresh_token']!=result['refresh_token']
    for _ in range(2):
        rr=client.post('/v1/auth/refresh',json=data)
        assert rr.status_code==200 and rr.json()==first
    rr=client.post('/v1/auth/refresh',json=data)
    assert rr.status_code==409 and rr.json()['error']['code']=='REFRESH_RECOVERY_LIMITED'
    assert client.get('/v1/me',headers=auth(first)).status_code==200
    with session() as db:
        raw=set(db.scalars(select(Credential.token_digest)))
        recovery=db.scalar(select(Recovery))
        assert result['refresh_token'] not in raw
        assert first['refresh_token'].encode() not in recovery.ciphertext
        assert recovery.resend_count==2


def test_reuse_commits_revocation_only_one_device(client,login):
    first,_=login(); other,_=login()
    r,_=renew(client,first)
    rr,_=renew(client,first)
    assert rr.json()['error']['code']=='REFRESH_REUSED'
    assert client.get('/v1/me',headers=auth(r.json())).json()['error']['code']=='SESSION_REVOKED'
    assert client.get('/v1/me',headers=auth(other)).status_code==200


def test_superseded(client,login):
    first,_=login(); r,data=renew(client,first); second=r.json()
    r,_=renew(client,second)
    old=client.post('/v1/auth/refresh',json=data)
    assert old.json()['error']['code']=='REFRESH_RESULT_SUPERSEDED'
    assert client.get('/v1/me',headers=auth(r.json())).status_code==200


def test_recovery_expired_and_cleanup(client,login):
    from app.auth.cleanup import cleanup
    first,_=login(); r,data=renew(client,first)
    with session() as db,db.begin():
        db.execute(update(Recovery).values(expires_at=now(db)))
    rr=client.post('/v1/auth/refresh',json=data)
    assert rr.json()['error']['code']=='REFRESH_RECOVERY_EXPIRED'
    cleanup()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Recovery))==0
        assert db.scalar(select(func.count()).select_from(Credential))==2
    assert client.post('/v1/auth/refresh',json=data).status_code==409


def test_logout_repeat_old_token(client,login):
    result,_=login(); fresh,data=renew(client,result)
    for _ in range(2):
        r=client.post('/v1/auth/logout',json={'refresh_token':result['refresh_token']})
        assert r.status_code==204 and r.content==b''
    assert client.get('/v1/me',headers=auth(fresh.json())).status_code==401
    assert client.post('/v1/auth/refresh',json=data).json()['error']['code']=='SESSION_REVOKED'
    with session() as db,db.begin():
        db.execute(update(Session).values(absolute_expires_at=now(db)))
    assert client.post('/v1/auth/logout',json={'refresh_token':result['refresh_token']}).json()['error']['code']=='REFRESH_INVALID'


def test_disable_and_expire(client,login):
    result,_=login()
    with session() as db,db.begin(): db.execute(update(User).values(status='disabled'))
    assert client.get('/v1/me',headers=auth(result)).status_code==403
    r,_=renew(client,result)
    assert r.json()['error']['code']=='ACCOUNT_DISABLED'
    assert client.post('/v1/auth/logout',json={'refresh_token':result['refresh_token']}).status_code==204


def test_refresh_expiration(client,login):
    result,_=login()
    with session() as db,db.begin(): db.execute(update(Session).values(idle_expires_at=now(db)))
    r,_=renew(client,result)
    assert r.json()['error']['code']=='REFRESH_EXPIRED'
    assert client.get('/v1/me',headers=auth(result)).json()['error']['code']=='SESSION_EXPIRED'


def test_missing_token(client):
    assert client.post('/v1/auth/refresh',json={'refresh_token':tokens.secret(),'refresh_request_id':tokens.secret()}).json()['error']['code']=='REFRESH_INVALID'


def test_failure_no_user(client,monkeypatch):
    def reject(*args):raise AuthError('GOOGLE_PROOF_INVALID')
    monkeypatch.setattr(service,'verify_google',reject)
    secret=tokens.secret()
    r=client.post('/v1/auth/google/challenges',json={'transaction_secret_hash':tokens.digest(secret)})
    r=client.post('/v1/auth/google',json={'transaction_id':r.json()['transaction_id'],'transaction_secret':secret,'google_id_token':'bad','remember_me':True})
    assert r.status_code==401
    with session() as db:
        assert db.scalar(select(func.count()).select_from(User))==0
        assert db.scalar(select(Transaction)).consumed_at is None


def test_atomic_encrypt_failure(client,login,monkeypatch):
    result,_=login()
    def fail(*args):raise AuthError('SERVICE_UNAVAILABLE',503)
    original=tokens.encrypt
    monkeypatch.setattr(tokens,'encrypt',fail)
    r,data=renew(client,result)
    assert r.status_code==503
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Credential))==1
        assert db.scalar(select(Credential)).consumed_at is None
    monkeypatch.setattr(tokens,'encrypt',original)
    assert client.post('/v1/auth/refresh',json=data).status_code==200


def test_tamper_recovery(client,login):
    first,_=login(); r,data=renew(client,first)
    with session() as db,db.begin(): db.execute(update(Recovery).values(ciphertext=b'corrupt'))
    r=client.post('/v1/auth/refresh',json=data)
    assert r.status_code==503
    with session() as db: assert db.scalar(select(Recovery)).resend_count==0


def test_concurrent_same_identity(client,monkeypatch):
    monkeypatch.setattr(service,'verify_google',lambda *args:'concurrent-subject')
    from app.auth.schemas import ChallengeIn,GoogleIn
    requests=[]
    for _ in range(6):
        secret=tokens.secret(); c=service.challenge(ChallengeIn(transaction_secret_hash=tokens.digest(secret)))
        requests.append(GoogleIn(transaction_id=c.transaction_id,transaction_secret=secret,google_id_token='mock',remember_me=True))
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(service.login,requests))
    assert len({r.user.id for r in results})==1
    assert sum(r.is_new_user for r in results)==1
    with session() as db:assert db.scalar(select(func.count()).select_from(User))==1


def test_concurrent_same_refresh(login):
    from app.auth.schemas import RefreshIn
    first,_=login(); data=RefreshIn(refresh_token=first['refresh_token'],refresh_request_id=tokens.secret())
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(service.refresh,[data]*3))
    assert len({r.refresh_token for r in results})==1
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Credential))==2
        assert db.scalar(select(Recovery)).resend_count==2


def test_actor_extra_and_access_forgery(client,login):
    import jwt
    result,req=login(); req['role']='admin'
    assert client.post('/v1/auth/google',json=req).status_code==400
    forged=jwt.encode({'sub':result['user']['id'],'sid':result['session']['id']},'fake-key-that-is-at-least-32-bytes-long',algorithm='HS256')
    assert client.get('/v1/me',headers={'Authorization':'Bearer '+forged}).status_code==401
    # A validly signed token pointing at another user's session is still rejected.
    other_user=uuid.uuid4()
    key,_=tokens.configured_keys()
    with session() as db: current=now(db)
    forged=jwt.encode({'sub':str(other_user),'sid':result['session']['id'],'iss':'lostparty-backend','aud':'lostparty-app','iat':current,'exp':current+timedelta(minutes=1),'jti':str(uuid.uuid4())},key,algorithm='RS256',headers={'kid':'local-1'})
    assert client.get('/v1/me',headers={'Authorization':'Bearer '+forged}).status_code==401


def test_schema_contract():
    from app.main import app
    schema=app.openapi()
    assert {'/health','/v1/auth/google/challenges','/v1/auth/google','/v1/me',
            '/v1/auth/session','/v1/auth/refresh','/v1/auth/logout'} <= set(schema['paths'])
    assert sum(len(ops) for ops in schema['paths'].values()) == 30
    assert all('422' not in op['responses'] for path,ops in schema['paths'].items() if path.startswith('/v1') for op in ops.values())
    assert schema['paths']['/v1/me']['get']['security']==[{'HTTPBearer':[]}]


def test_rate_limit(client):
    for _ in range(30):assert client.post('/v1/auth/google/challenges',json={'transaction_secret_hash':'0'*64}).status_code==201
    r=client.post('/v1/auth/google/challenges',json={'transaction_secret_hash':'0'*64})
    assert r.status_code==429 and r.headers['retry-after']=='60'


def test_challenge_expiration_secret_and_rollback(client,monkeypatch):
    monkeypatch.setattr(service,'verify_google',lambda *args:'new-sub')
    raw=tokens.secret()
    c=client.post('/v1/auth/google/challenges',json={'transaction_secret_hash':tokens.digest(raw)}).json()
    data=dict(transaction_id=c['transaction_id'],transaction_secret=tokens.secret(),google_id_token='proof',remember_me=True)
    assert client.post('/v1/auth/google',json=data).json()['error']['code']=='AUTH_TRANSACTION_INVALID'
    data['transaction_secret']=raw
    with session() as db,db.begin():db.execute(update(Transaction).values(expires_at=now(db)))
    assert client.post('/v1/auth/google',json=data).json()['error']['code']=='AUTH_TRANSACTION_EXPIRED'
    with session() as db:assert db.scalar(select(func.count()).select_from(User))==0


def test_new_request_id_reuse_is_invalid(client,login):
    first,_=login(); r,data=renew(client,first)
    second=r.json()
    r=client.post('/v1/auth/refresh',json={'refresh_token':second['refresh_token'],'refresh_request_id':data['refresh_request_id']})
    assert r.status_code==400 and r.json()['error']['code']=='INVALID_REQUEST'
    r,_=renew(client,second)
    assert r.status_code==200


def test_key_missing_fail_closed(client,monkeypatch):
    from app.core.config import Settings
    monkeypatch.setattr(tokens,'settings',Settings(secret_dir='/tmp/not-present'))
    r=client.post('/v1/auth/google/challenges',json={'transaction_secret_hash':'0'*64})
    assert r.status_code==503
    with session() as db:assert db.scalar(select(func.count()).select_from(Transaction))==0


def test_logout_clears_recovery(client,login):
    first,_=login(); r,data=renew(client,first)
    assert client.post('/v1/auth/logout',json={'refresh_token':r.json()['refresh_token']}).status_code==204
    with session() as db:assert db.scalar(select(func.count()).select_from(Recovery))==0
    assert client.post('/v1/auth/refresh',json=data).status_code==401


def test_cleanup_session_at_absolute_expiration(client,login):
    from app.auth.cleanup import cleanup
    result,_=login(); fresh,_=renew(client,result)
    with session() as db,db.begin():db.execute(update(Session).values(absolute_expires_at=now(db)))
    cleanup()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Session))==0
        assert db.scalar(select(func.count()).select_from(Credential))==0
        assert db.scalar(select(func.count()).select_from(User))==1
    assert client.post('/v1/auth/logout',json={'refresh_token':result['refresh_token']}).status_code==401


def test_commit_delay_is_conservative(client,login,monkeypatch):
    # DB clock timestamps were persisted before commit; a delayed commit cannot
    # extend the recovery expiration or make a rolled-back refresh durable.
    import time
    from sqlalchemy import event
    from app.core.database import engine
    first,_=login()
    def delay(connection):time.sleep(.1)
    event.listen(engine(),'commit',delay)
    try:r,data=renew(client,first)
    finally:event.remove(engine(),'commit',delay)
    assert r.status_code==200
    with session() as db:
        recovery=db.scalar(select(Recovery))
        current=now(db)
        assert timedelta(seconds=59)<recovery.expires_at-current<timedelta(seconds=60)


def test_access_expiry_and_wrong_claims(client,login):
    import jwt
    first,_=login(); key,_=tokens.configured_keys()
    with session() as db:current=now(db)
    claims={'sub':first['user']['id'],'sid':first['session']['id'],'iss':'lostparty-backend','aud':'lostparty-app','iat':current-timedelta(minutes=20),'exp':current-timedelta(seconds=1),'jti':str(uuid.uuid4())}
    token=jwt.encode(claims,key,algorithm='RS256',headers={'kid':'local-1'})
    assert client.get('/v1/me',headers={'Authorization':'Bearer '+token}).json()['error']['code']=='ACCESS_EXPIRED'
    claims['exp']=current+timedelta(minutes=1);claims['aud']='other'
    token=jwt.encode(claims,key,algorithm='RS256',headers={'kid':'local-1'})
    assert client.get('/v1/me',headers={'Authorization':'Bearer '+token}).json()['error']['code']=='ACCESS_INVALID'


def test_model_migration_consistency():
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.core.database import engine
    from app.auth.models import Base
    # Load every model even when this test runs without an API client fixture.
    from app.game_accounts import models as game_models
    from app.lostark_keys import models as key_models
    from app.member_settings import models as settings_models
    with engine().connect() as connection:
        # Application-owned external tables are absent in isolated test DB.
        assert compare_metadata(MigrationContext.configure(connection),Base.metadata)==[]
