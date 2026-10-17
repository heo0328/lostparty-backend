import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import profiles, presentation, lifecycle
from app.game_accounts.models import (Account, Character, Registration, NameClaim, CharacterRoleSummary,
    CharacterPersonalPreferences, AccountCharacterPresentation, RequestResult, CharacterRetirement,
    Configuration, Activity)
from app.game_accounts.support import GameError, lock
from tests.test_role_summaries import get as profile, put as put_role
from tests.test_game_accounts import world, register, verify, page, change, another_user, BASE


@pytest.fixture
def owned(client,world):
    h,state=world
    r=register(client,h,main=True)
    verify(client,h,state,r['registration_id'])
    # Verification changes registration.version; use the current server fence.
    r=next(row for row in client.get(BASE,headers=h).json()['items'] if row['registration_id']==r['registration_id'])
    cid=page(client,h,r['registration_id'])['characters']['items'][0]['character_id']
    return h,r,cid


def prefs_path(cid): return '/v2/me/characters/'+str(cid)+'/personal-preferences'
def presentation_path(r): return '/v2/me/game-accounts/'+r['registration_id']+'/presentation-settings'
def pref_body(**changes):
    return dict(expected_version=1,expected_ownership_revision=1,expected_lifecycle_revision=1,
                preferred_role=None,visible=True,display_order=None,**changes)
def display_body(r, count=6):
    return dict(expected_version=1,expected_ownership_revision=1,expected_registration_version=r['version'],visible_count=count)
def put_pref(client,h,cid,body=None,key=None):
    return change(client,h,'put',prefs_path(cid),pref_body() if body is None else body,key)
def put_display(client,h,r,body=None,key=None):
    return change(client,h,'put',presentation_path(r),display_body(r) if body is None else body,key)
def display(client,h,r): return client.get(presentation_path(r),headers=h)


def test_default_get_and_noop_no_rows_or_provider_io(client,owned,monkeypatch):
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as keys
    h,r,cid=owned
    def forbidden(*a,**kw): raise AssertionError('Provider/credential forbidden')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden);monkeypatch.setattr(keys,'capture',forbidden)
    out=display(client,h,r)
    assert out.status_code==200 and out.headers['Cache-Control']=='no-store'
    assert len(out.json())==7 and out.json()['visible_count']==6 and out.json()['saved_at'] is None
    assert put_display(client,h,r).json()==out.json()
    pref=put_pref(client,h,cid)
    assert pref.status_code==200 and pref.json()['version']==1 and pref.json()['saved_at'] is None
    assert profile(client,h,cid).json()['preferences']==dict(version=1,preferred_role=None,visible=True,display_order=None,saved_at=None)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(CharacterPersonalPreferences))==0
        assert db.scalar(select(func.count()).select_from(AccountCharacterPresentation))==0
        before=db.scalar(select(func.count()).select_from(RequestResult))
    profile(client,h,cid);display(client,h,r)
    with session() as db: assert db.scalar(select(func.count()).select_from(RequestResult))==before


def test_real_restore_independent_versions_hidden_rep_and_rank(client,owned):
    from tests.test_game_accounts import save_data
    h,r,cid=owned
    current=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(current)).status_code==200
    assert put_role(client,h,cid).status_code==200
    before=page(client,h,r['registration_id']); role=profile(client,h,cid).json()['dealer']
    b=pref_body();b.update(preferred_role='support',visible=False,display_order=0)
    response=put_pref(client,h,cid,b)
    assert response.status_code==200 and len(response.json())==8 and response.json()['version']==2
    out=profile(client,h,cid).json()
    assert out['preferences']['visible'] is False and out['preferences']['preferred_role']=='support'
    assert out['dealer']==role and out['support']['version']==1
    d=display_body(r,1);a=put_display(client,h,r,d)
    assert a.status_code==200 and a.json()['version']==2
    assert page(client,h,r['registration_id'])==before  # No implicit representative/activity edits.
    assert profile(client,h,cid).json()['preferences']['version']==2
    d['expected_version']=2; assert put_display(client,h,r,d).json()==a.json()
    b['expected_version']=2;assert put_pref(client,h,cid,b).json()==response.json()
    # Reset defaults is a real change, retaining version history (no ABA row deletion).
    reset=pref_body();reset['expected_version']=2
    assert put_pref(client,h,cid,reset).json()['version']==3
    assert profile(client,h,cid).json()['preferences']['visible'] is True


@pytest.mark.parametrize('resource',['pref','display'])
def test_historical_replay_conflict_and_stale_noop(client,owned,resource):
    h,r,cid=owned;key=uuid.uuid4()
    b=pref_body() if resource=='pref' else display_body(r,7)
    if resource=='pref':b['visible']=False
    send=lambda body,key=None:put_pref(client,h,cid,body,key) if resource=='pref' else put_display(client,h,r,body,key)
    first=send(b,key);assert first.status_code==200 and first.json()['version']==2
    second=dict(b,expected_version=2)
    if resource=='pref':second['visible']=True
    else:second['visible_count']=8
    assert send(second).json()['version']==3
    assert send(b,key).json()==first.json()
    assert send(second).json()['error']['code']=='REVISION_CONFLICT'
    assert send(second,key).json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    with session() as db,db.begin():
        db.scalar(select(RequestResult).where(RequestResult.key==key)).completed_at=now(db)-timedelta(hours=24)
    assert send(b,key).json()['error']['code']=='IDEMPOTENCY_EXPIRED'


@pytest.mark.parametrize('resource',['pref','display'])
def test_atomic_rollback_same_key_recovery_and_concurrent_winner(client,owned,monkeypatch,resource):
    h,r,cid=owned;key=uuid.uuid4();module=profiles if resource=='pref' else presentation
    original=module.commit_result
    b=pref_body() if resource=='pref' else display_body(r,7)
    if resource=='pref':b['visible']=False
    send=lambda key=None:put_pref(client,h,cid,b,key) if resource=='pref' else put_display(client,h,r,b,key)
    def reject(*a):raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(module,'commit_result',reject)
    response=send(key);assert response.status_code==409 and response.headers['Retry-After']=='2'
    assert profile(client,h,cid).json()['preferences']['version']==1 and display(client,h,r).json()['version']==1
    monkeypatch.setattr(module,'commit_result',original)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:send(),range(2)))
    assert sorted(v.status_code for v in results)==[200,409]
    assert send(key).json()['error']['code']=='REVISION_CONFLICT'


def test_suspect_read_keeps_preference_write_blocked_count_allowed(client,owned):
    h,r,cid=owned;b=pref_body();b.update(visible=False,display_order=4)
    assert put_pref(client,h,cid,b).status_code==200
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(cid));c.lifecycle_state='suspect';c.status='suspect';c.lifecycle_revision+=1
    out=profile(client,h,cid).json()
    assert out['preferences']['display_order']==4 and out['preferences']['visible'] is False
    assert put_pref(client,h,cid,b).json()['error']['code']=='CHARACTER_UNUSABLE'
    assert put_display(client,h,r,display_body(r,200)).status_code==200


@pytest.mark.parametrize('kind,code,status', [('deleted','CHARACTER_NOT_FOUND',404),
    ('ownership','OWNERSHIP_REQUIRED',403),('life','REVISION_CONFLICT',409),
    ('claim','IDENTITY_CONFLICT',409),('retired','CHARACTER_UNUSABLE',409)])
def test_preference_replay_current_access(client,owned,kind,code,status):
    h,r,cid=owned;key=uuid.uuid4();b=pref_body();b['visible']=False
    assert put_pref(client,h,cid,b,key).status_code==200
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(cid));a=db.get(Account,c.account_id)
        if kind=='deleted':db.get(Registration,uuid.UUID(r['registration_id'])).deleted_at=now(db)
        elif kind=='ownership':a.owner_id=None;a.ownership_revision+=1
        elif kind=='life':c.lifecycle_revision+=1
        elif kind=='claim':db.delete(db.get(NameClaim,(c.server_name,c.character_name)))
        else:c.lifecycle_state='retired';c.lifecycle_revision+=1
    response=put_pref(client,h,cid,b,key)
    assert response.status_code==status and response.json()['error']['code']==code


def test_presentation_registration_fence_replay_and_same_lifetime_reregistration(client,owned):
    h,r,cid=owned;key=uuid.uuid4();b=display_body(r,9)
    first=put_display(client,h,r,b,key);assert first.status_code==200
    with session() as db,db.begin():db.get(Registration,uuid.UUID(r['registration_id'])).version+=1
    assert put_display(client,h,r,b,key).json()==first.json() # Replay ignores historical label/version.
    assert put_display(client,h,r,b).json()['error']['code']=='REVISION_CONFLICT'
    with session() as db,db.begin():
        old=db.get(Registration,uuid.UUID(r['registration_id']));old.deleted_at=now(db);old.is_main=False
        new=Registration(user_id=old.user_id,account_id=old.account_id,lookup_name=old.lookup_name,
                         label='',is_main=False,version=1,preview=[],fetched_at=now(db),created_at=now(db),updated_at=now(db))
        db.add(new);db.flush();rid=str(new.id)
    new_r=dict(r,registration_id=rid,version=1)
    assert display(client,h,r).status_code==404 and put_display(client,h,r,b,key).status_code==404
    restored=display(client,h,new_r).json()
    assert restored['visible_count']==9 and restored['version']==2 and restored['registration_id']==rid
    assert put_display(client,h,new_r,display_body(new_r,9),key).json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    # Preferences share character/ownership lifetime, not the deleted registration path.
    assert profile(client,h,cid).status_code==200


def test_preview_other_member_account_and_ownership_lifetime(client,owned,world,login,monkeypatch):
    h,r,cid=owned;_,state=world;state['group']='b'
    preview=register(client,h,'b0')
    assert display(client,h,preview).json()['error']['code']=='OWNERSHIP_REQUIRED'
    assert put_display(client,h,preview).status_code==403
    verify(client,h,state,preview['registration_id'])
    second=display(client,h,preview).json()
    assert second['version']==1 and second['visible_count']==6
    other=another_user(login,monkeypatch,client)
    assert display(client,other,r).status_code==404 and put_pref(client,other,cid).status_code==404
    p=pref_body();p['preferred_role']='dealer';assert put_pref(client,h,cid,p).status_code==200
    assert put_display(client,h,r,display_body(r,9)).status_code==200
    with session() as db,db.begin():
        a=db.get(Account,uuid.UUID(r['game_account_id'])) if r['game_account_id'] else db.get(Account,db.get(Character,uuid.UUID(cid)).account_id)
        a.ownership_revision+=1
    assert profile(client,h,cid).json()['preferences']['version']==1
    assert display(client,h,r).json()['visible_count']==6
    assert put_pref(client,h,cid,p).json()['error']['code']=='REVISION_CONFLICT'


@pytest.mark.parametrize('field,value',[('preferred_role','healer'),('visible',None),('visible',1),('visible','true'),
    ('display_order',-1),('display_order',2147483648),('display_order',True),('display_order','1'),
    ('expected_version',True),('expected_lifecycle_revision','1'),('raw','forbidden')])
def test_preference_strict(client,owned,field,value):
    h,r,cid=owned;b=pref_body();b[field]=value
    assert put_pref(client,h,cid,b).status_code==400
    assert profile(client,h,cid).json()['preferences']['version']==1


@pytest.mark.parametrize('field',list(pref_body()))
def test_preference_required(client,owned,field):
    h,r,cid=owned;b=pref_body();del b[field]
    assert put_pref(client,h,cid,b).status_code==400


@pytest.mark.parametrize('field,value',[('visible_count',None),('visible_count',0),('visible_count',201),('visible_count',True),
    ('visible_count','6'),('expected_registration_version',None),('expected_ownership_revision',False),('user_id','x')])
def test_presentation_strict(client,owned,field,value):
    h,r,cid=owned;b=display_body(r);b[field]=value
    assert put_display(client,h,r,b).status_code==400


@pytest.mark.parametrize('field',list(display_body({'version':1})))
def test_presentation_required(client,owned,field):
    h,r,cid=owned;b=display_body(r);del b[field]
    assert put_display(client,h,r,b).status_code==400


def test_transport_size_keys_auth_and_get_body(client,owned):
    import json
    h,r,cid=owned
    for url,b in [(prefs_path(cid),pref_body()),(presentation_path(r),display_body(r))]:
        headers={**h,'Idempotency-Key':str(uuid.uuid4()),'Content-Type':'application/json'}
        raw=json.dumps(b).encode()
        assert client.put(url,headers=headers,content=raw+b' '*(4096-len(raw))).status_code==200
        response=client.put(url,headers=headers,content=iter([raw,b' '*4096]))
        assert response.status_code==413 and response.headers['Cache-Control']=='no-store'
        assert client.put(url+'?x=1',headers=headers,json=b).status_code==400
        assert client.put(url,headers=h,json=b).status_code==400
        assert client.put(url,headers={**headers,'Idempotency-Key':str(uuid.uuid1())},json=b).status_code==400
        assert client.put(url,json=b).status_code==401
    assert client.request('GET',presentation_path(r),headers=h,json={}).status_code==400
    assert client.get(presentation_path(r)+'?limit=1',headers=h).status_code==400
    assert display(client,{},r).status_code==401


@pytest.mark.parametrize('kind,status',[('revoked',401),('disabled',403)])
def test_session_for_get_put_and_replay(client,owned,kind,status):
    from app.auth.models import Session,User
    h,r,cid=owned;key=uuid.uuid4();assert put_pref(client,h,cid,key=key).status_code==200
    dkey=uuid.uuid4();assert put_display(client,h,r,key=dkey).status_code==200
    with session() as db,db.begin():
        if kind=='revoked':db.scalar(select(Session)).revoked_at=now(db)
        else:db.scalar(select(User)).status='disabled'
    assert profile(client,h,cid).status_code==status and display(client,h,r).status_code==status
    assert put_pref(client,h,cid,key=key).status_code==status
    assert put_display(client,h,r,key=dkey).status_code==status


def test_internal_retirement_cleanup_is_atomic_targeted_and_no_live_activation(client,owned):
    h,r,cid=owned
    for role in ('dealer','support'): assert put_role(client,h,cid,role=role).status_code==200
    b=pref_body();b['display_order']=3;assert put_pref(client,h,cid,b).status_code==200
    assert put_display(client,h,r,display_body(r,9)).status_code==200
    other=page(client,h,r['registration_id'])['characters']['items'][1]['character_id']
    assert put_pref(client,h,other,b).status_code==200
    with pytest.raises(RuntimeError),session() as db,db.begin():
        lock(db,'game-mutations-v1');c=db.get(Character,uuid.UUID(cid));a=db.get(Account,c.account_id)
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
        assert db.scalar(select(func.count()).select_from(CharacterRoleSummary))==0
        assert db.get(CharacterPersonalPreferences,(a.owner_id,c.id,a.ownership_revision)) is None
        raise RuntimeError('simulate transaction abort after cleanup')
    assert profile(client,h,cid).json()['dealer']['version']==2
    assert profile(client,h,cid).json()['preferences']['display_order']==3
    with session() as db,db.begin():
        lock(db,'game-mutations-v1');c=db.get(Character,uuid.UUID(cid));a=db.get(Account,c.account_id)
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
        # Existing minimal provider history, not client analysis values.
        history=db.scalar(select(CharacterRetirement).where(CharacterRetirement.character_id==c.id))
        assert history.combat_power is None
        assert db.scalar(select(func.count()).select_from(CharacterRoleSummary))==0
        assert db.scalar(select(func.count()).select_from(CharacterPersonalPreferences))==1
        assert db.scalar(select(func.count()).select_from(AccountCharacterPresentation))==1
    assert profile(client,h,cid).status_code==409
    assert profile(client,h,other).json()['preferences']['display_order']==3
    assert display(client,h,r).json()['visible_count']==9


def test_schema_required_nullable_p1_summary_preserved():
    from app.main import app
    definitions=app.openapi()['components']['schemas']
    for name in ('PersonalPreferences','PersonalPreferencesIn','PersonalPreferencesOut','PresentationIn','PresentationOut'):
        model=definitions[name]
        assert model['additionalProperties'] is False
        assert set(model['required'])==set(model['properties'])
    assert len(definitions['PresentationOut']['properties'])==7
    assert len(definitions['PersonalPreferencesOut']['properties'])==8
    assert 'PendingPersonalPreferences' not in definitions
    assert definitions['PersonalProfileOut']['properties']['preferences']['$ref'].endswith('/PersonalPreferences')
    assert definitions['PersonalPreferences']['properties']['version']['minimum']==1
    assert 'const' not in definitions['PersonalPreferences']['properties']['visible']


def test_additive_p2_migration_preserves_role_summary_and_constraints():
    import importlib.util
    from pathlib import Path
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.core.database import engine
    def load(path):
        spec=importlib.util.spec_from_file_location('p2_migration',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    with engine().connect() as c:
        tx=c.begin()
        try:
            c.execute(text('CREATE SCHEMA p2_migration_test'));c.execute(text('SET LOCAL search_path TO p2_migration_test'))
            with Operations.context(MigrationContext.configure(c)):
                for path in sorted(Path('alembic/versions').glob('000[1-8]_*.py')):load(path).upgrade()
                uid,aid,cid=[uuid.uuid4() for _ in range(3)]
                c.execute(text("INSERT INTO users VALUES (:u,'active',now(),now(),now())"),{'u':uid})
                c.execute(text('INSERT INTO game_accounts VALUES (:a,:u,1,1,now())'),{'a':aid,'u':uid})
                c.execute(text("INSERT INTO game_characters (id,account_id,server_name,character_name,summary,status,fetched_at,confirmed_at,lifecycle_state,lifecycle_revision) VALUES (:c,:a,'server','old','{}','confirmed',now(),now(),'active',1)"),{'c':cid,'a':aid})
                c.execute(text("INSERT INTO character_role_summaries VALUES (:u,:c,1,'dealer',2,'{}',now())"),{'u':uid,'c':cid})
                tables=['users','game_accounts','game_characters','character_role_summaries']
                before={t:c.execute(text('SELECT * FROM '+t)).all() for t in tables}
                load('alembic/versions/0009_personal_presentation.py').upgrade()
                assert before=={t:c.execute(text('SELECT * FROM '+t)).all() for t in tables}
                assert c.execute(text('SELECT count(*) FROM character_personal_preferences')).scalar_one()==0
                assert c.execute(text('SELECT count(*) FROM account_character_presentation')).scalar_one()==0
                pref=text("INSERT INTO character_personal_preferences VALUES (:u,:c,:revision,:role,true,:rank,2,now())")
                for revision,role,rank,character_id in [(0,'dealer',0,cid),(1,'unknown',0,cid),(1,None,-1,cid),(1,None,0,uuid.uuid4())]:
                    with pytest.raises(IntegrityError),c.begin_nested():c.execute(pref,dict(u=uid,c=character_id,revision=revision,role=role,rank=rank))
                c.execute(pref,dict(u=uid,c=cid,revision=1,role=None,rank=None))
                statement=text('INSERT INTO account_character_presentation VALUES (:u,:a,1,:count,2,now())')
                for count in (0,201):
                    with pytest.raises(IntegrityError),c.begin_nested():c.execute(statement,dict(u=uid,a=aid,count=count))
                c.execute(statement,dict(u=uid,a=aid,count=6))
                with pytest.raises(IntegrityError),c.begin_nested():c.execute(statement,dict(u=uid,a=aid,count=6))
        finally:tx.rollback()


@pytest.mark.parametrize('resource',['pref','display'])
def test_same_key_retry_after_rollback(client,owned,monkeypatch,resource):
    h,r,cid=owned;key=uuid.uuid4();module=profiles if resource=='pref' else presentation
    original=module.commit_result
    b=pref_body() if resource=='pref' else display_body(r,8)
    if resource=='pref':b['preferred_role']='support'
    send=lambda:put_pref(client,h,cid,b,key) if resource=='pref' else put_display(client,h,r,b,key)
    def reject(*a):raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(module,'commit_result',reject)
    assert send().status_code==409
    monkeypatch.setattr(module,'commit_result',original)
    recovered=send();assert recovered.status_code==200 and recovered.json()['version']==2
    assert send().json()==recovered.json()


@pytest.mark.parametrize('kind,code,status',[('lost','OWNERSHIP_REQUIRED',403),('lifetime','REVISION_CONFLICT',409)])
def test_presentation_replay_checks_current_ownership_lifetime(client,owned,kind,code,status):
    h,r,cid=owned;key=uuid.uuid4();b=display_body(r,8)
    assert put_display(client,h,r,b,key).status_code==200
    with session() as db,db.begin():
        account=db.get(Account,uuid.UUID(r['game_account_id']))
        account.ownership_revision+=1
        if kind=='lost':account.owner_id=None
    response=put_display(client,h,r,b,key)
    assert response.status_code==status and response.json()['error']['code']==code
    if kind=='lifetime':assert display(client,h,r).json()['visible_count']==6
