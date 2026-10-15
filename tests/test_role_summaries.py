import copy
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import profiles
from app.game_accounts.models import (Account, Character, Registration, NameClaim, CharacterRoleSummary,
                                     RequestResult, Configuration, Activity)
from app.game_accounts.support import GameError
from tests.test_game_accounts import world, register, verify, page, change, another_user, BASE

STAMP = '2026-10-15T12:00:00Z'


def summary():
    return dict(source='flutter_analysis', analysis_rules_version='flutter-v1', analyzed_at=STAMP,
                combat_power='12345.00', item_level='1700', combat_power_observed_at=STAMP,
                item_level_observed_at=STAMP, integrity_status='clean', catalog_version=None,
                issues=[], observed_lifecycle_revision=1)


def data():
    return dict(expected_version=1, expected_ownership_revision=1,
                expected_lifecycle_revision=1, summary=summary())


def path(cid): return '/v2/me/characters/'+str(cid)
def get(client, h, cid): return client.get(path(cid)+'/personal-profile', headers=h)
def put(client, h, cid, body=None, role='dealer', key=None):
    return change(client, h, 'put', path(cid)+'/role-summaries/'+role, data() if body is None else body, key)


@pytest.fixture
def owned(client, world):
    h, state = world
    r = register(client, h, main=True)
    verify(client, h, state, r['registration_id'])
    p = page(client, h, r['registration_id'])
    return h, r, p['characters']['items'][0]['character_id']


def test_defaults_no_io_and_preserve_provider_settings(client, owned, monkeypatch):
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as credentials
    h, r, cid = owned
    def forbidden(*a, **kw): raise AssertionError('No provider or credentials in profile API')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(credentials, 'capture', forbidden)
    before = page(client, h, r['registration_id'])
    response = get(client, h, cid)
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    out = response.json()
    assert out['dealer'] == out['support'] == dict(version=1, summary=None, saved_at=None)
    assert out['preferences'] == dict(version=1, preferred_role=None, visible=True, display_order=None, saved_at=None)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(CharacterRoleSummary)) == 0
        count = db.scalar(select(func.count()).select_from(RequestResult))
    assert get(client, h, cid).json() == out
    with session() as db:
        assert db.scalar(select(func.count()).select_from(RequestResult)) == count
    assert put(client, h, cid).status_code == 200
    assert page(client, h, r['registration_id']) == before
    assert get(client, h, cid).json()['support']['summary'] is None


def test_roles_noop_stale_and_historical_replay(client, owned):
    h, _, cid = owned
    key = uuid.uuid4()
    a = put(client, h, cid, key=key)
    assert a.status_code == 200 and a.json()['version'] == 2
    body = data(); body['expected_version'] = 2
    assert put(client, h, cid, body).json() == a.json()
    assert put(client, h, cid, role='support').json()['version'] == 2
    assert get(client, h, cid).json()['dealer']['summary'] == get(client, h, cid).json()['support']['summary']
    body['summary']['combat_power'] = '22222'
    b = put(client, h, cid, body)
    assert b.status_code == 200 and b.json()['version'] == 3
    assert put(client, h, cid, key=key).json() == a.json()
    assert get(client, h, cid).json()['dealer']['summary']['combat_power'] == '22222'
    stale = put(client, h, cid, body)
    assert stale.json()['error']['code'] == 'REVISION_CONFLICT'
    assert put(client, h, cid, role='support', key=key).json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


@pytest.mark.parametrize('status,issues', [
    ('clean', []), ('review', [{'code':'GEM_UNAVAILABLE','severity':'warning'}]),
    ('error', [{'code':'GEM_SLOT_COUNT','severity':'error'}, {'code':'GEM_UNAVAILABLE','severity':'warning'}]),
    ('unavailable', []), ('unavailable', [{'code':'GEM_UNAVAILABLE','severity':'warning'}])])
def test_integrity_and_nullable_values_are_preserved(client, owned, status, issues):
    h, _, cid = owned; body = data()
    body['summary'].update(integrity_status=status, issues=issues, combat_power=None, combat_power_observed_at=None)
    response = put(client, h, cid, body)
    assert response.status_code == 200
    stored = get(client, h, cid).json()['dealer']['summary']
    assert stored['integrity_status'] == status and stored['issues'] == issues
    assert stored['combat_power'] is None and stored['combat_power_observed_at'] is None


@pytest.mark.parametrize('field', list(data()))
def test_each_required_input(client, owned, field):
    h, _, cid = owned; body = data(); del body[field]
    assert put(client, h, cid, body).status_code == 400


@pytest.mark.parametrize('field', list(summary()))
def test_each_summary_attribute_required(client, owned, field):
    h, _, cid = owned; body = data(); del body['summary'][field]
    assert put(client, h, cid, body).status_code == 400


@pytest.mark.parametrize('field,value', [
    ('combat_power', 1), ('combat_power', '-1'), ('combat_power', 'NaN'), ('combat_power', '1e3'),
    ('combat_power', '1,000'), ('combat_power', '1\n'), ('combat_power','1'*33),
    ('item_level', True), ('item_level', None), ('combat_power_observed_at', None),
    ('analyzed_at', 1234), ('analyzed_at', '2026-10-15'), ('analyzed_at', '2026-10-15T00:00:00+09:00'),
    ('analyzed_at', '2026-10-15T00:00:00'), ('catalog_version', 1), ('catalog_version', ''),
    ('catalog_version', 'bad catalog'), ('analysis_rules_version', None), ('source','provider'),
    ('observed_lifecycle_revision', True), ('observed_lifecycle_revision',2),
    ('issues',[{'code':'raw-slot:1','severity':'warning'}]),
    ('issues',[{'code':'GEM_SLOT_COUNT','severity':'error','raw':'forbidden'}]),
    ('issues',[{'code':'X','severity':'info'}]), ('outcome','success')])
def test_strict_summary(client, owned, field, value):
    h, _, cid = owned; body = data(); body['summary'][field] = value
    response = put(client, h, cid, body)
    assert response.status_code == 400, response.text
    assert get(client, h, cid).json()['dealer']['summary'] is None


@pytest.mark.parametrize('status,issues', [
    ('clean',[{'code':'X','severity':'warning'}]), ('review',[]),
    ('review',[{'code':'X','severity':'error'}]), ('error',[]),
    ('unavailable',[{'code':'X','severity':'error'}]),
    ('review',[{'code':'X','severity':'warning'}]*2),
    ('review',[{'code':'X'+str(i),'severity':'warning'} for i in range(21)])])
def test_forbidden_issue_combinations(client, owned, status, issues):
    h, _, cid = owned; body = data(); body['summary'].update(integrity_status=status,issues=issues)
    assert put(client, h, cid, body).status_code == 400


@pytest.mark.parametrize('value', [True, '1', 0, -1, None])
def test_strict_expected_version(client, owned, value):
    h, _, cid = owned; body = data(); body['expected_version'] = value
    assert put(client, h, cid, body).status_code == 400


def test_body_limit_chunked_and_query_and_paths(client, owned):
    h, _, cid = owned; url = path(cid)+'/role-summaries/dealer'
    headers = {**h,'Idempotency-Key':str(uuid.uuid4()),'Content-Type':'application/json'}
    raw = json.dumps(data()).encode()
    assert client.put(url, headers=headers, content=raw+b' '*(32768-len(raw))).status_code == 200
    assert client.put(url, headers=headers, content=iter([raw, b' '*32768])).status_code == 413
    assert client.put(url, headers=headers, content=b'X'*32769).json()['error']['code'] == 'REQUEST_TOO_LARGE'
    assert client.put(url+'?x=1',headers=headers,json=data()).status_code == 400
    assert client.get(path(cid)+'/personal-profile?limit=1',headers=h).status_code == 400
    assert client.request('GET',path(cid)+'/personal-profile',headers=h,json={}).status_code == 400
    assert put(client,h,cid,role='unknown').status_code == 400
    assert put(client,h,cid,key=uuid.uuid1()).status_code == 400
    assert client.put(url,headers=h,json=data()).status_code == 400
    assert get(client,h,'bad').status_code == 400
    assert get(client,h,uuid.uuid4()).status_code == 404
    assert get(client,{},cid).status_code == 401
    assert put(client,{},cid).status_code == 401


@pytest.mark.parametrize('kind,code,status', [
    ('delete','CHARACTER_NOT_FOUND',404), ('ownership','OWNERSHIP_REQUIRED',403),
    ('lifetime','REVISION_CONFLICT',409), ('retired','CHARACTER_UNUSABLE',409),
    ('claim','IDENTITY_CONFLICT',409)])
def test_current_access_and_replay_fences(client, owned, kind, code, status):
    h, r, cid = owned; key = uuid.uuid4()
    assert put(client,h,cid,key=key).status_code == 200
    with session() as db,db.begin():
        c = db.get(Character,uuid.UUID(cid)); a = db.get(Account,c.account_id)
        if kind == 'delete': db.get(Registration,uuid.UUID(r['registration_id'])).deleted_at = now(db)
        elif kind == 'ownership': a.owner_id = None; a.ownership_revision += 1
        elif kind == 'lifetime': c.lifecycle_revision += 1
        elif kind == 'retired': c.lifecycle_state='retired'; c.lifecycle_revision+=1
        else: db.delete(db.get(NameClaim,(c.server_name,c.character_name)))
    response = put(client,h,cid,key=key)
    assert response.status_code == status and response.json()['error']['code'] == code
    if kind == 'lifetime':
        out = get(client,h,cid).json()
        assert out['lifecycle_revision'] == 2
        assert out['dealer']['summary']['observed_lifecycle_revision'] == 1
        assert put(client,h,cid).json()['error']['code'] == 'REVISION_CONFLICT'
    else: assert get(client,h,cid).status_code == status


def test_suspect_read_preserves_data_and_blocks_new_write(client, owned):
    h, _, cid = owned; assert put(client,h,cid).status_code == 200
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(cid)); c.lifecycle_state='suspect'; c.status='suspect'; c.lifecycle_revision+=1
    out=get(client,h,cid).json()
    assert out['lifecycle_state']=='suspect' and out['dealer']['version']==2
    assert put(client,h,cid).json()['error']['code']=='CHARACTER_UNUSABLE'


def test_member_and_ownership_lifetime_isolation(client, owned, login, monkeypatch):
    h,r,cid=owned; assert put(client,h,cid).status_code==200
    other=another_user(login,monkeypatch,client)
    assert get(client,other,cid).status_code==404
    assert put(client,other,cid).status_code==404
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(cid)); db.get(Account,c.account_id).ownership_revision+=1
    out=get(client,h,cid).json()
    assert out['ownership_revision']==2 and out['dealer']['summary'] is None
    assert put(client,h,cid).json()['error']['code']=='REVISION_CONFLICT'


def test_concurrent_devices_one_winner(client, owned):
    h,_,cid=owned
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:put(client,h,cid),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    assert get(client,h,cid).json()['dealer']['version']==2


def test_commit_fence_rollback_then_same_key_recovery(client, owned, monkeypatch):
    h,_,cid=owned; key=uuid.uuid4(); original=profiles.commit_result
    def reject(*args): raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(profiles,'commit_result',reject)
    response=put(client,h,cid,key=key)
    assert response.status_code==409 and response.headers['Retry-After']=='2'
    assert get(client,h,cid).json()['dealer']['summary'] is None
    monkeypatch.setattr(profiles,'commit_result',original)
    assert put(client,h,cid,key=key).status_code==200
    with session() as db,db.begin():
        row=db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.completed_at=now(db)-timedelta(hours=24)
    assert put(client,h,cid,key=key).json()['error']['code']=='IDEMPOTENCY_EXPIRED'


def test_schema_p1_only_required_nullable_and_p2_defaults():
    from app.main import app
    schema=app.openapi(); models=schema['components']['schemas']
    for name in ('RoleSummary','AnalysisIssue','RoleSummaryIn','StoredRoleSummary','RoleSummaryOut',
                 'PersonalProfileOut','PendingPersonalPreferences'):
        assert set(models[name]['required'])==set(models[name]['properties'])
        assert models[name]['additionalProperties'] is False
    assert 'outcome' not in models['RoleSummary']['properties']
    assert models['PendingPersonalPreferences']['properties']['visible']['const'] is True
    for url in schema['paths']:
        assert not url.endswith('/personal-preferences') and not url.endswith('/presentation-settings')
    put_schema=schema['paths']['/v2/me/characters/{character_id}/role-summaries/{role}']['put']
    assert '413' in put_schema['responses'] and '422' not in put_schema['responses']
    assert put_schema['responses']['409']['headers']['Retry-After']['schema']['const']==2


@pytest.mark.parametrize('kind,status', [('expired',401),('revoked',401),('disabled',403)])
def test_session_rechecked_for_reads_writes_replay(client,owned,kind,status):
    from app.auth.models import Session,User
    h,_,cid=owned; key=uuid.uuid4(); assert put(client,h,cid,key=key).status_code==200
    with session() as db,db.begin():
        s=db.scalar(select(Session))
        if kind=='expired': s.idle_expires_at=now(db)-timedelta(seconds=1)
        elif kind=='revoked': s.revoked_at=now(db)
        else: db.scalar(select(User)).status='disabled'
    assert get(client,h,cid).status_code==status
    assert put(client,h,cid).status_code==status
    assert put(client,h,cid,key=key).status_code==status


def test_same_member_relogin_and_nice_group_off_keep_summary(client,owned,login):
    from app.auth.models import Session
    from tests.test_game_accounts import PrivateHeaders
    h,_,cid=owned; key=uuid.uuid4()
    # Default member switch is OFF; storage still accepts valid summaries.
    assert client.get('/v1/me/settings',headers=h).json()['nice_group_auto_refresh_enabled'] is False
    first=put(client,h,cid,key=key); assert first.status_code==200
    with session() as db,db.begin():
        for s in db.scalars(select(Session)): s.revoked_at=now(db)
    auth,_=login(); new=PrivateHeaders(Authorization='Bearer '+auth['access_token'])
    assert get(client,new,cid).json()['dealer']['version']==2
    assert put(client,new,cid,key=key).json()==first.json()


def test_new_id_same_name_does_not_inherit_summary(client,owned):
    h,_,cid=owned; assert put(client,h,cid).status_code==200
    with session() as db,db.begin():
        old=db.get(Character,uuid.UUID(cid)); claim=db.get(NameClaim,(old.server_name,old.character_name))
        db.delete(claim); db.flush(); old.lifecycle_state='retired'; old.lifecycle_revision+=1
        new=Character(account_id=old.account_id,server_name=old.server_name,character_name=old.character_name,
                      summary=old.summary,status='confirmed',fetched_at=now(db),confirmed_at=now(db))
        db.add(new); db.flush(); new_id=new.id
        db.add(NameClaim(server_name=new.server_name,character_name=new.character_name,character_id=new.id))
    out=get(client,h,new_id).json()
    assert out['dealer']['summary'] is None and out['support']['summary'] is None
    assert get(client,h,cid).status_code==409


def test_real_lease_takeover_blocks_old_worker_commit(client,owned,monkeypatch):
    h,_,cid=owned; key=uuid.uuid4(); original=profiles.commit_result
    # The reserve occurs in its own transaction, before the writer lock.
    original_reserve=profiles.reserve; previous=[]
    def reserve(*args):
        ticket,replay=original_reserve(*args)
        if ticket: previous.append(ticket)
        return ticket,replay
    monkeypatch.setattr(profiles,'reserve',reserve)
    def expire(*args): raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(profiles,'commit_result',expire)
    assert put(client,h,cid,key=key).status_code==409
    with session() as db,db.begin():
        row=db.get(RequestResult,previous[0][0]); row.state='running';row.lease_expires_at=now(db)+timedelta(seconds=30)
    response=put(client,h,cid,key=key)
    assert response.status_code==409 and response.headers['Retry-After']=='2'
    with session() as db,db.begin():
        db.get(RequestResult,previous[0][0]).lease_expires_at=now(db)-timedelta(seconds=1)
    monkeypatch.setattr(profiles,'commit_result',original)
    assert put(client,h,cid,key=key).status_code==200
    with session() as db,db.begin():
        with pytest.raises(GameError): original(db,previous[0],200,{'bad':'late'})
    assert get(client,h,cid).json()['dealer']['version']==2


def test_database_error_is_sanitized(client,owned,monkeypatch):
    from sqlalchemy.exc import OperationalError
    h,_,cid=owned
    def failure(*args,**kwargs): raise OperationalError('private SQL',{},Exception('private detail'))
    monkeypatch.setattr(profiles,'owned_character',failure)
    for response in (get(client,h,cid),put(client,h,cid)):
        assert response.status_code==503 and response.json()['error']['code']=='SERVICE_UNAVAILABLE'
        assert 'private' not in response.text


def test_additive_migration_preserves_existing_rows_and_constraints():
    import importlib.util
    from pathlib import Path
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.core.database import engine
    def load(path):
        spec=importlib.util.spec_from_file_location('profile_migration',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    with engine().connect() as c:
        tx=c.begin()
        try:
            c.execute(text('CREATE SCHEMA profile_migration_test'))
            c.execute(text('SET LOCAL search_path TO profile_migration_test'))
            with Operations.context(MigrationContext.configure(c)):
                for path in sorted(Path('alembic/versions').glob('000[1-7]_*.py')): load(path).upgrade()
                uid,aid,cid=[uuid.uuid4() for _ in range(3)]
                c.execute(text("INSERT INTO users VALUES (:u,'active',now(),now(),now())"),{'u':uid})
                c.execute(text('INSERT INTO game_accounts VALUES (:a,:u,1,1,now())'),{'a':aid,'u':uid})
                c.execute(text("INSERT INTO game_characters (id,account_id,server_name,character_name,summary,status,fetched_at,confirmed_at,lifecycle_state,lifecycle_revision) VALUES (:c,:a,'server','old','{\"combat_power\":\"100\"}','confirmed',now(),now(),'active',1)"),{'c':cid,'a':aid})
                tables=['users','game_accounts','game_characters']
                before={t:c.execute(text('SELECT * FROM '+t)).all() for t in tables}
                load('alembic/versions/0008_role_summaries.py').upgrade()
                assert before=={t:c.execute(text('SELECT * FROM '+t)).all() for t in tables}
                assert c.execute(text('SELECT count(*) FROM character_role_summaries')).scalar_one()==0
                statement=text("INSERT INTO character_role_summaries VALUES (:u,:c,:revision,:role,2,'{}',now())")
                for revision,role,character_id in [(0,'dealer',cid),(1,'unknown',cid),(1,'dealer',uuid.uuid4())]:
                    with pytest.raises(IntegrityError),c.begin_nested():
                        c.execute(statement,{'u':uid,'c':character_id,'revision':revision,'role':role})
                c.execute(statement,{'u':uid,'c':cid,'revision':1,'role':'dealer'})
                c.execute(statement,{'u':uid,'c':cid,'revision':1,'role':'support'})
                with pytest.raises(IntegrityError),c.begin_nested():
                    c.execute(statement,{'u':uid,'c':cid,'revision':1,'role':'dealer'})
        finally: tx.rollback()
