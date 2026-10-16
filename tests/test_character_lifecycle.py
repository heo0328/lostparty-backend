import importlib.util
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from app.core.database import session, now, engine
from app.game_accounts import lifecycle, service, observations, power_service
from app.game_accounts.models import (Account, Character, NameClaim, CharacterRetirement, CharacterHistoryHead,
                                     ScopedPowerCache, Registration, Configuration, Activity, LimitEvent)
from app.game_accounts.support import GameError, lock
from tests.test_game_accounts import world, register, verify, page, change, save_data, BASE, VERIFY, start
from tests.test_combat_power import body as power_body, endpoint, seed_provider


def owned(client,world):
    h,state=world
    registration=register(client,h,main=True)
    verify(client,h,state,registration['registration_id'])
    return h,state,registration


def test_names_alone_cannot_attach_transfer_or_refresh(client,world):
    h,state,r=owned(client,world)
    state['binding']=False
    before=page(client,h,r['registration_id'])
    response=change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{})
    assert response.status_code==409 and response.json()['error']['code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'
    response=change(client,h,'post',VERIFY,{'source':'direct_input','character_name':'a0'})
    assert response.status_code==409 and response.json()['error']['code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'
    assert page(client,h,r['registration_id'])==before


def test_suspect_requires_continuity_and_is_blocked_everywhere(client,world):
    h,state,r=owned(client,world)
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    state['missing']=(0,)
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    p=page(client,h,r['registration_id']); suspect=next(c for c in p['characters']['items'] if c['character_name']=='a0')
    assert suspect['roster_status']=='suspect' and not suspect['eligible']
    response=change(client,h,'post',endpoint(r),power_body('a0'))
    assert response.status_code==409 and response.json()['error']['code']=='CHARACTER_UNUSABLE'
    rep=client.get(BASE+'/'+r['registration_id']+'/representative',headers=h).json()
    data=dict(character_id=suspect['character_id'],expected_registration_version=rep['registration_version'],
              expected_settings_version=rep['settings_version'],expected_ownership_revision=rep['ownership_revision'],expected_roster_revision=rep['roster_revision'])
    response=change(client,h,'put',BASE+'/'+r['registration_id']+'/representative',data)
    assert response.status_code==409 and response.json()['error']['code']=='CHARACTER_UNUSABLE'
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p,selected=p['settings']['activity_character_ids'],rep=suspect['character_id'])).status_code==404
    with session() as db,db.begin(): db.query(LimitEvent).delete()
    state['missing']=();state['continuity']=False
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    assert next(c for c in page(client,h,r['registration_id'])['characters']['items'] if c['character_name']=='a0')['roster_status']=='suspect'
    with session() as db,db.begin(): db.query(LimitEvent).delete()
    state['continuity']=True
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    recovered=next(c for c in page(client,h,r['registration_id'])['characters']['items'] if c['character_name']=='a0')
    assert recovered['character_id']==suspect['character_id'] and recovered['eligible']


def test_partial_observation_does_not_retire_even_with_legacy_boolean(client,world,monkeypatch):
    from dataclasses import replace
    h,state,r=owned(client,world); original=observations.fetch
    state['missing']=(2,)
    monkeypatch.setattr(observations,'fetch',lambda *a,**kw:replace(original(*a,**kw),disappearance_validated=True))
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==200
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Character))==3
        assert db.scalar(select(func.count()).select_from(NameClaim))==3
        assert db.scalar(select(func.count()).select_from(CharacterRetirement))==0


@pytest.mark.parametrize('kind',['empty','failure'])
def test_failed_observation_deletes_nothing(client,world,monkeypatch,kind):
    from app.game_accounts.provider import ProviderUnavailable
    h,state,r=owned(client,world)
    before=page(client,h,r['registration_id'])
    def invalid(*a,**kw):
        if kind=='empty': return observations.roster([], 'a0')
        raise ProviderUnavailable()
    monkeypatch.setattr(observations,'fetch',invalid)
    assert change(client,h,'post',BASE+'/'+r['registration_id']+'/refresh',{}).status_code==503
    assert page(client,h,r['registration_id'])==before
    with session() as db: assert db.scalar(select(func.count()).select_from(NameClaim))==3


def test_internal_retirement_is_atomic_and_reused_name_gets_new_id(client,world):
    h,state,r=owned(client,world)
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    target=next(c for c in p['characters']['items'] if c['character_name']=='a0')
    with session() as db,db.begin():
        lock(db,'game-mutations-v1')
        c=db.get(Character,uuid.UUID(target['character_id'])); a=db.get(Account,c.account_id)
        with pytest.raises(GameError): lifecycle.retire(db,a,c,lifecycle.evidence(db,a))
    # Rollback after all writes must retain claim and no history.
    with pytest.raises(RuntimeError):
        with session() as db,db.begin():
            lock(db,'game-mutations-v1'); c=db.get(Character,uuid.UUID(target['character_id'])); a=db.get(Account,c.account_id)
            lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
            raise RuntimeError('synthetic rollback')
    with session() as db:
        assert db.get(NameClaim,('sample-server','a0')).character_id==uuid.UUID(target['character_id'])
        assert db.scalar(select(func.count()).select_from(CharacterRetirement))==0
    with session() as db,db.begin():
        lock(db,'game-mutations-v1'); c=db.get(Character,uuid.UUID(target['character_id'])); a=db.get(Account,c.account_id)
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
        assert c.lifecycle_state=='retired' and c.summary=={}
        # Fresh internal retry is a no-op. Tombstone remains and FK still points at it.
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
        replacement=Account(owner_id=a.owner_id,verified_at=now(db));db.add(replacement);db.flush()
        row=dict(server_name='sample-server',character_name='a0',class_name='sample-class',character_level=60,item_level='1700',combat_power=None)
        service.reconcile(db,replacement,observations.Observation([row],now(db)),fresh=True)
        new_claim=db.get(NameClaim,('sample-server','a0'))
        assert new_claim.character_id!=c.id
    with session() as db:
        assert db.get(Character,uuid.UUID(target['character_id'])).lifecycle_state=='retired'
        assert db.scalar(select(func.count()).select_from(CharacterRetirement))==1
        assert db.scalar(select(func.count()).select_from(Character))==4
        history=db.scalar(select(CharacterRetirement))
        assert history.user_id==db.get(Account,history.account_id).owner_id
        assert history.combat_power is None and history.item_level=='1700.00'
        assert db.scalar(select(CharacterHistoryHead)).revision==2
        conf=db.scalar(select(Configuration))
        assert conf.state=='needs_reconfiguration' and uuid.UUID(target['character_id']) not in set(db.scalars(select(Activity.character_id)))


@pytest.mark.parametrize('first_retired',[False,True])
def test_name_claim_both_observation_orders(client,world,first_retired):
    h,state,r=owned(client,world)
    with session() as db,db.begin():
        lock(db,'game-mutations-v1')
        c=db.scalar(select(Character).where(Character.character_name=='a0')); a=db.get(Account,c.account_id)
        b=Account(owner_id=a.owner_id,verified_at=now(db));db.add(b);db.flush()
        row=dict(c.summary)
        if first_retired: lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
        if first_retired:
            service.reconcile(db,b,observations.Observation([row],now(db)),fresh=True)
            assert db.get(NameClaim,('sample-server','a0')).character_id!=c.id
        else:
            with pytest.raises(GameError,match='IDENTITY_CONFLICT'):
                service.reconcile(db,b,observations.Observation([row],now(db)),fresh=True)
            assert a.owner_id==b.owner_id and c.lifecycle_state=='active'


def test_claim_unique_serialized_contenders(client,world):
    h,state,r=owned(client,world)
    with session() as db,db.begin():
        a=db.scalar(select(Account)); uid=a.owner_id
        accounts=[Account(owner_id=uid,verified_at=now(db)) for _ in range(2)]
        db.add_all(accounts);db.flush(); ids=[a.id for a in accounts]
    def attempt(aid):
        try:
            with session() as db,db.begin():
                lock(db,'game-mutations-v1')
                a=db.get(Account,aid)
                row=dict(server_name='sample-server',character_name='unused-name',class_name='sample-class',character_level=60,item_level='1700',combat_power=None)
                service.reconcile(db,a,observations.Observation([row],now(db)),fresh=True)
                return 200
        except GameError: return 409
    with ThreadPoolExecutor(2) as pool: assert sorted(pool.map(attempt,ids))==[200,409]


@pytest.mark.parametrize('change_kind',['main_aba','claim','lifecycle','registration'])
def test_power_late_result_never_crosses_identity_context(client,world,monkeypatch,change_kind):
    h,state,r=owned(client,world)
    entered,finish=Event(),Event()
    def delayed(*a,**kw):
        entered.set();assert finish.wait(5)
        return 'available','999',None
    monkeypatch.setattr(power_service,'fetch_power',delayed)
    with ThreadPoolExecutor(1) as pool:
        pending=pool.submit(change,client,h,'post',endpoint(r),power_body('a0'))
        assert entered.wait(3)
        with session() as db,db.begin():
            lock(db,'game-mutations-v1')
            if change_kind=='main_aba': db.get(Registration,uuid.UUID(r['registration_id'])).version+=2
            elif change_kind=='registration': db.get(Registration,uuid.UUID(r['registration_id'])).deleted_at=now(db)
            else:
                c=db.scalar(select(Character).where(Character.character_name=='a0'))
                if change_kind=='claim': db.get(NameClaim,(c.server_name,c.character_name)).revision+=1
                else: c.lifecycle_revision+=1
        finish.set(); response=pending.result()
    assert response.status_code== (404 if change_kind=='registration' else 409)
    with session() as db: assert all(c.value is None for c in db.scalars(select(ScopedPowerCache)))


def test_challenge_old_generation_or_key_cannot_confirm(client,world):
    h,state,r=owned(client,world)
    v=start(client,h,r['registration_id']); state['removed']=v['required_slots']
    with session() as db,db.begin():
        c=db.scalar(select(Character).where(Character.character_name=='a0')); c.lifecycle_revision+=1
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==409 and response.json()['error']['code']=='REVISION_CONFLICT'
    state['removed']=();v=start(client,h,r['registration_id']);state['removed']=v['required_slots']
    response=change(client,h,'put','/v1/me/lostark-api-key',{'token':'replacement.member.signature','expected_version':2})
    assert response.status_code==200
    calls=state['calls']
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==409 and response.json()['error']['code']=='LOSTARK_KEY_CHANGED'
    assert state['calls']==calls


def test_old_name_cache_not_imported_into_new_scope(client,world,monkeypatch):
    from app.game_accounts.models import PowerCache as LegacyPower
    h,state=world;r=register(client,h)
    with session() as db,db.begin():
        uid=db.scalar(select(Registration.user_id))
        db.add(LegacyPower(actor_id=uid,server_name='sample-server',character_name='a0',value='9999',status='available',generation=0,
                           fetched_at=now(db),checked_at=now(db),credential_version=2))
    assert page(client,h,r['registration_id'])['characters']['items'][0]['combat_power'] is None
    verify(client,h,state,r['registration_id'])
    seed_provider(monkeypatch,'123')
    assert change(client,h,'post',endpoint(r),power_body('a0')).status_code==200
    with session() as db:
        assert db.scalar(select(LegacyPower)).value=='9999'
        assert db.scalar(select(ScopedPowerCache)).value=='123'


@pytest.mark.parametrize('conflict',[False,True])
def test_migration_preserves_ids_fks_and_diagnoses_claim_conflicts(conflict):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from pathlib import Path
    def module(path):
        spec=importlib.util.spec_from_file_location('test_migration',path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    with engine().connect() as c:
        transaction=c.begin()
        try:
            c.execute(text('CREATE SCHEMA lifecycle_migration_test'))
            c.execute(text('SET LOCAL search_path TO lifecycle_migration_test'))
            with Operations.context(MigrationContext.configure(c)):
                for path in sorted(Path('alembic/versions').glob('000[1-6]_*.py')): module(path).upgrade()
                uid,aid,cid,config_id=[uuid.uuid4() for _ in range(4)]
                c.execute(text("INSERT INTO users VALUES (:u,'active',now(),now(),now())"),{'u':uid})
                c.execute(text('INSERT INTO game_accounts VALUES (:a,:u,1,1,now())'),{'a':aid,'u':uid})
                c.execute(text("INSERT INTO game_characters VALUES (:c,:a,'sample-server','sample','{}','missing',now(),now(),NULL)"),{'c':cid,'a':aid})
                c.execute(text("INSERT INTO character_settings VALUES (:c,:u,:a,:i,'configured',1,NULL,NULL)"),{'c':config_id,'u':uid,'a':aid,'i':cid})
                c.execute(text('INSERT INTO activity_characters VALUES (:c,:i,:a)'),{'c':config_id,'i':cid,'a':aid})
                if conflict:
                    c.execute(text('ALTER TABLE game_characters DROP CONSTRAINT game_characters_server_name_character_name_key'))
                    c.execute(text("INSERT INTO game_characters VALUES (:c,:a,'sample-server','sample','{}','missing',now(),now(),NULL)"),{'c':uuid.uuid4(),'a':aid})
                    with pytest.raises(RuntimeError,match='LIFECYCLE_CLAIM_PREFLIGHT_CONFLICT'):
                        module('alembic/versions/0007_character_lifecycle.py').upgrade()
                else:
                    module('alembic/versions/0007_character_lifecycle.py').upgrade()
                    row=c.execute(text('SELECT id,account_id,status,lifecycle_state,lifecycle_revision FROM game_characters')).one()
                    assert tuple(row)==(cid,aid,'missing','suspect',1)
                    assert c.execute(text('SELECT representative_id FROM character_settings')).scalar_one()==cid
                    assert c.execute(text('SELECT character_id FROM activity_characters')).scalar_one()==cid
                    assert c.execute(text('SELECT character_id FROM character_name_claims')).scalar_one()==cid
                    assert c.execute(text('SELECT count(*) FROM character_retirements')).scalar_one()==0
                    assert c.execute(text('SELECT count(*) FROM scoped_character_power_cache')).scalar_one()==0
        finally: transaction.rollback()
