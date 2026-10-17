import uuid
from sqlalchemy import select, func
import pytest
from app.core.database import session, now
from app.game_accounts import lifecycle
from app.game_accounts.models import (Account, Character, NameClaim, CharacterHistoryHead, CharacterRetirement,
                                     Configuration, Activity, Registration, RequestResult, ScopedPowerCache)
from app.game_accounts.support import lock
from tests.test_game_accounts import world, register, verify, page, change, save_data, another_user, BASE

HISTORY='/v2/me/character-retirements'


def path(r): return '/v2/me/game-accounts/'+r['registration_id']+'/characters'


def test_preview_required_nulls_strict_v1_unchanged_and_get_writes_nothing(client,world,monkeypatch):
    h,state=world;r=register(client,h)
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as credentials
    def forbidden(*a,**kw): raise AssertionError('No external/read credential access')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden)
    monkeypatch.setattr(credentials,'capture',forbidden)
    with session() as db:
        counts=[db.scalar(select(func.count()).select_from(m)) for m in (Account,Character,Configuration,RequestResult,CharacterHistoryHead)]
    response=client.get(path(r),headers=h)
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    out=response.json()
    assert out['game_account_id'] is None and out['ownership_revision'] is None
    assert out['ownership_status']=='unverified' and out['settings']['settings_version']==1
    assert all(c['character_id'] is None and c['lifecycle_revision'] is None and c['lifecycle_state']=='preview'
               and c['blocked_reason']=='OWNERSHIP_REQUIRED' and not c['usable'] for c in out['items'])
    assert out['next_cursor'] is None
    assert client.get(HISTORY,headers=h).json()=={'items':[],'next_cursor':None,'history_revision':1}
    assert all('lifecycle_revision' not in c for c in page(client,h,r['registration_id'])['characters']['items'])
    with session() as db:
        assert counts==[db.scalar(select(func.count()).select_from(m)) for m in (Account,Character,Configuration,RequestResult,CharacterHistoryHead)]


def test_current_canonical_revisions_state_and_cursor(client,world):
    h,state=world;r=register(client,h,main=True);verify(client,h,state,r['registration_id'])
    response=client.get(path(r),headers=h,params={'limit':1})
    assert response.status_code==200
    out=response.json(); cursor=out['next_cursor']; c=out['items'][0]
    assert out['ownership_status']=='owned' and out['ownership_revision']==1 and out['roster_revision']>=1
    assert c['character_id'] and c['lifecycle_revision']==1 and c['lifecycle_state']=='active'
    assert c['usable'] and c['eligible'] and c['blocked_reason'] is None
    following=client.get(path(r),headers=h,params={'limit':1,'cursor':cursor})
    assert following.status_code==200 and following.json()['items'][0]['character_id']!=c['character_id']
    p=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
    stale=client.get(path(r),headers=h,params={'cursor':cursor})
    assert stale.status_code==409 and stale.json()['error']['code']=='CURSOR_STALE'
    with session() as db,db.begin():
        character=db.get(Character,uuid.UUID(c['character_id']))
        character.status='suspect';character.lifecycle_state='suspect';character.lifecycle_revision+=1
    item=client.get(path(r),headers=h).json()['items'][0]
    assert item['lifecycle_revision']==2 and item['lifecycle_state']=='suspect'
    assert not item['usable'] and item['blocked_reason']=='CHARACTER_UNUSABLE'


@pytest.mark.parametrize('kind',['registration','ownership','claim','lifecycle'])
def test_cursor_fences_each_structure_dimension(client,world,kind):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    cursor=client.get(path(r),headers=h,params={'limit':1}).json()['next_cursor']
    with session() as db,db.begin():
        registration=db.get(Registration,uuid.UUID(r['registration_id']))
        if kind=='registration': registration.version+=1
        elif kind=='ownership': db.get(Account,registration.account_id).ownership_revision+=1
        else:
            c=db.scalar(select(Character))
            if kind=='claim': db.get(NameClaim,(c.server_name,c.character_name)).revision+=1
            else: c.lifecycle_revision+=1
    response=client.get(path(r),headers=h,params={'cursor':cursor})
    assert response.status_code==409 and response.json()['error']['code']=='CURSOR_STALE'


def test_claim_mismatch_is_visible_but_not_usable(client,world):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db,db.begin():
        c=db.scalar(select(Character).where(Character.character_name=='a0'))
        db.delete(db.get(NameClaim,(c.server_name,c.character_name)))
    item=client.get(path(r),headers=h).json()['items'][0]
    assert item['lifecycle_state']=='active' and not item['usable'] and item['blocked_reason']=='IDENTITY_CONFLICT'


def test_retirement_history_scoped_to_original_member_and_cursor(client,world,login,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db,db.begin():
        lock(db,'game-mutations-v1')
        a=db.scalar(select(Account)); cs=list(db.scalars(select(Character).order_by(Character.character_name)))
        ids=[c.id for c in cs]
        lifecycle.retire(db,a,cs[0],lifecycle.evidence(db,a,complete=True))
        lifecycle.retire(db,a,cs[1],lifecycle.evidence(db,a,complete=True))
    out=client.get(HISTORY,headers=h,params={'limit':1}).json()
    assert out['history_revision']==3 and out['next_cursor']
    history=out['items'][0]
    assert history['character_id']==str(ids[0]) and history['lifecycle_revision']==2
    assert history['combat_power'] is None and history['power_fetched_at'] is None
    assert history['item_level']=='1700.00' and history['item_level_fetched_at'] is not None
    assert client.get(HISTORY,headers=h,params={'limit':1,'cursor':out['next_cursor']}).status_code==200
    operating=client.get(path(r),headers=h).json()
    assert len(operating['items'])==1 and operating['items'][0]['character_id']==str(ids[2])
    assert len(page(client,h,r['registration_id'])['characters']['items'])==1
    assert client.get(BASE,headers=h).json()['items'][0]['character_count']==1
    other=another_user(login,monkeypatch,client)
    assert client.get(HISTORY,headers=other).json()['items']==[]
    assert client.get(path(r),headers=other).status_code==404
    # A cursor is member-scoped and cannot be used as a history selector.
    assert client.get(HISTORY,headers=other,params={'cursor':out['next_cursor']}).status_code==400
    with session() as db,db.begin():
        lock(db,'game-mutations-v1');a=db.scalar(select(Account));c=db.get(Character,ids[2])
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
    stale=client.get(HISTORY,headers=h,params={'cursor':out['next_cursor']})
    assert stale.status_code==409 and stale.json()['error']['code']=='CURSOR_STALE'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(CharacterRetirement))==3


def test_ownership_loss_masks_canonical_ids_but_preserves_old_history(client,world):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db,db.begin():
        a=db.scalar(select(Account));a.owner_id=None;a.ownership_revision+=1
    out=client.get(path(r),headers=h).json()
    assert out['ownership_status']=='ownership_lost'
    assert all(c['character_id'] is None and c['lifecycle_revision'] is None and not c['usable'] for c in out['items'])
    assert out['settings']['activity_character_ids']==[]


@pytest.mark.parametrize('query',['limit=0','limit=51','limit=1&limit=2','user_id=someone','cursor=bad'])
def test_query_validation_and_no_body(client,world,query):
    h,state=world;r=register(client,h)
    for url in (path(r),HISTORY):
        response=client.get(url+'?'+query,headers=h)
        assert response.status_code==400 and response.headers['Cache-Control']=='no-store'
        assert client.request('GET',url,headers=h,json={}).status_code==400


def test_unauthenticated_and_deleted_registration(client,world):
    h,state=world;r=register(client,h)
    assert client.get(path(r)).status_code==401
    assert client.get(HISTORY).status_code==401
    assert change(client,h,'delete',BASE+'/'+r['registration_id']+'?expected_version=1').status_code==204
    assert client.get(path(r),headers=h).status_code==404


def test_v2_required_nullable_contract_and_legacy_schema_unchanged():
    from app.main import app
    schema=app.openapi(); definitions=schema['components']['schemas']
    for name in ('LifecycleCharacterOut','LifecycleCharactersOut','RetirementOut','RetirementPage'):
        model=definitions[name]
        assert set(model['required'])==set(model['properties'])
        assert model['additionalProperties'] is False
    for name in ('character_id','lifecycle_revision'):
        assert {'type':'null'} in definitions['LifecycleCharacterOut']['properties'][name]['anyOf']
    assert 'lifecycle_revision' not in definitions['CharacterOut']['properties']
    paths=schema['paths']
    assert '/v2/me/game-accounts/{registration_id}/refresh' not in paths
    assert '/v2/me/game-accounts/{registration_id}/lookup-recovery' not in paths
    for path in (HISTORY,'/v2/me/game-accounts/{registration_id}/characters'):
        assert set(paths[path])=={'get'}
        assert '422' not in paths[path]['get']['responses']
        assert paths[path]['get']['responses']['200']['headers']['Cache-Control']['schema']['const']=='no-store'


def test_preview_eligibility_never_grants_power_access(client,world,monkeypatch):
    from tests.test_combat_power import seed_provider,endpoint,body
    h,state=world;r=register(client,h)
    seed_provider(monkeypatch,'123')
    assert change(client,h,'post',endpoint(r),body('a0')).status_code==403
    legacy=page(client,h,r['registration_id'])['characters']['items'][0]
    current=client.get(path(r),headers=h).json()['items'][0]
    assert legacy['eligible'] is False and current['usable'] is False
    assert legacy['combat_power'] is current['combat_power'] is None
    assert legacy['power_stale'] is True and current['power_stale'] is True
