"""Manual activity eligibility independent of initial defaults and raid levels."""
import uuid
import pytest
from sqlalchemy import select,func
from app.core.database import session
from app.game_accounts.models import Character,Configuration,Activity
from tests.test_game_accounts import world,register,verify,change,page,save_data,BASE
from tests.test_representative import selection,get,put,body as representative_body


def set_level(character_id,level):
    with session() as db,db.begin():
        character=db.get(Character,uuid.UUID(str(character_id)))
        character.summary=dict(character.summary,item_level=level)


@pytest.mark.parametrize('level', ['1699.99',None,'NaN','Infinity','bad','-1'])
def test_manual_selection_does_not_derive_authority_from_level(client,world,level):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);cid=p['characters']['items'][0]['character_id'];set_level(cid,level)
    data=save_data(p);key=uuid.uuid4()
    response=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',data,key)
    assert response.status_code==200,response.text
    assert response.json()['ineligible_character_ids']==[]
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',data,key).json()==response.json()
    restored=page(client,h,r['registration_id'])
    assert restored['settings']==response.json()
    assert next(i for i in restored['characters']['items'] if i['character_id']==cid)['eligible']
    v2=client.get('/v2/me/game-accounts/'+r['registration_id']+'/characters',headers=h)
    assert v2.status_code==200 and next(i for i in v2.json()['items'] if i['character_id']==cid)['usable']


@pytest.mark.parametrize('level', ['1699.99','1700','1700.01','1,700.00'])
def test_manual_level_independent_for_owned_subaccount(client,world,level):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);cid=p['characters']['items'][0]['character_id'];set_level(cid,level)
    response=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p,[cid],cid))
    assert response.status_code==200 and response.json()['activity_character_ids']==[cid]
    assert client.get(BASE,headers=h).json()['items'][0]['is_main'] is False


@pytest.mark.parametrize('same_target',[False,True])
def test_low_representative_change_and_noop_preserve_other_settings(client,selection,same_target):
    w=selection;target=w['ids'][0 if same_target else 1];set_level(target,'1699.99')
    before=get(client,w).json()
    response=put(client,w,representative_body(w,target))
    assert response.status_code==200,response.text
    out=response.json()
    assert out['representative_character_id']==target
    assert out['settings_version']==before['settings_version']+(0 if same_target else 1)
    assert get(client,w).json()==out
    assert set(page(client,w['headers'],w['rid'])['settings']['activity_character_ids'])==set(w['ids'][:2])


def test_existing_low_selection_is_eligible_without_replacing_or_deleting(client,selection):
    w=selection;set_level(w['ids'][0],None)
    before=get(client,w).json()
    current=page(client,w['headers'],w['rid'])
    assert current['settings']['ineligible_character_ids']==[]
    assert current['settings']['representative_character_id']==w['ids'][0]
    assert get(client,w).json()==before
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Activity))==2


def test_explicit_initial_highest_selected_is_saved_once_with_cas(client,world):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);ids=[i['character_id'] for i in p['characters']['items']]
    for cid,level in zip(ids,['1701','1799','1750']):set_level(cid,level)
    # Existing UI chooses the highest candidate within its explicit activity draft.
    payload=save_data(p,ids[:2],ids[1]);url=BASE+'/'+r['registration_id']+'/character-settings'
    first=change(client,h,'put',url,payload)
    assert first.status_code==200 and first.json()['representative_character_id']==ids[1]
    set_level(ids[0],'1900')
    current=page(client,h,r['registration_id'])
    assert current['settings']['representative_character_id']==ids[1]
    assert set(current['settings']['activity_character_ids'])==set(ids[:2])
    assert change(client,h,'put',url,payload).status_code==409 # stale initial draft cannot overwrite
    assert page(client,h,r['registration_id'])['settings']==current['settings']


def test_roster_level_drop_preserves_configuration_and_representative(client,world,monkeypatch):
    from dataclasses import replace
    from app.game_accounts import observations
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);payload=save_data(p)
    url=BASE+'/'+r['registration_id']
    assert change(client,h,'put',url+'/character-settings',payload).status_code==200
    original=observations.fetch
    def lower(*args,**kwargs):
        result=original(*args,**kwargs)
        return replace(result,roster=[dict(row,item_level='1699') if row['character_name']=='a0' else row for row in result.roster])
    monkeypatch.setattr(observations,'fetch',lower)
    assert change(client,h,'post',url+'/refresh',{}).status_code==200
    current=page(client,h,r['registration_id'])['settings']
    assert current['configuration_state']=='configured'
    assert current['settings_version']==2
    assert current['representative_character_id']==payload['representative_character_id']
    assert current['ineligible_character_ids']==[]
    assert set(current['activity_character_ids'])==set(payload['activity_character_ids'])


def test_old_level_reconfiguration_requires_explicit_save_to_normalize(client,selection):
    w=selection;set_level(w['ids'][0],'1699')
    with session() as db,db.begin():
        conf=db.get(Configuration,w['cid']);conf.state='needs_reconfiguration';conf.version=3
    current=page(client,w['headers'],w['rid'])
    assert current['settings']['configuration_state']=='needs_reconfiguration'
    assert current['settings']['settings_version']==3
    assert current['settings']['ineligible_character_ids']==[]
    assert get(client,w).json()['configuration_state']=='needs_reconfiguration'
    data=save_data(current,w['ids'][:2],w['ids'][0])
    result=change(client,w['headers'],'put',BASE+'/'+w['rid']+'/character-settings',data)
    assert result.status_code==200 and result.json()['configuration_state']=='configured'
    assert result.json()['settings_version']==4
    assert set(result.json()['activity_character_ids'])==set(w['ids'][:2])
    assert result.json()['representative_character_id']==w['ids'][0]


@pytest.mark.parametrize('state',['suspect','retired','claim_missing'])
def test_low_level_never_bypasses_identity_and_lifecycle_rollback(client,selection,state):
    from app.game_accounts.models import NameClaim
    w=selection;target=w['ids'][1];set_level(target,'1699')
    with session() as db,db.begin():
        character=db.get(Character,uuid.UUID(target))
        if state=='claim_missing':
            db.delete(db.get(NameClaim,(character.server_name,character.character_name)))
        else:
            character.lifecycle_state=state
            if state=='suspect':character.status='suspect'
    before=get(client,w).json()
    rejected=put(client,w,representative_body(w,target))
    assert rejected.status_code==409 and rejected.json()['error']['code']=='CHARACTER_UNUSABLE'
    current=page(client,w['headers'],w['rid'])
    rejected=change(client,w['headers'],'put',BASE+'/'+w['rid']+'/character-settings',save_data(current,w['ids'][:2],w['ids'][0]))
    assert rejected.status_code==404 and rejected.json()['error']['code']=='CHARACTER_NOT_FOUND'
    assert get(client,w).json()==before
    with session() as db:
        assert set(db.scalars(select(Activity.character_id).where(Activity.settings_id==w['cid'])))=={uuid.UUID(i) for i in w['ids'][:2]}


def test_manual_low_level_does_not_relax_power_or_raid_entry():
    from decimal import Decimal
    from app.core.game_policy import DEFAULT_MIN_ITEM_LEVEL
    from app.game_accounts.combat_power import default_collection_target
    from app.raids.service import difficulty,meets_item_level
    assert DEFAULT_MIN_ITEM_LEVEL==Decimal('1700')
    assert not default_collection_target('1699.99')
    assert default_collection_target('1700')
    assert not meets_item_level(Decimal('1699.99'),difficulty('serca','normal','2026.08.20'))
