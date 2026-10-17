"""Shared activity level boundary and explicit initial representative persistence."""
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


@pytest.mark.parametrize('level', ['1699.99',None,'NaN','Infinity','bad',True,'-1'])
def test_invalid_activity_level_rolls_back_full_selection(client,world,level):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);set_level(p['characters']['items'][0]['character_id'],level)
    data=save_data(p)
    response=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',data)
    assert response.status_code==409 and response.json()['error']['code']=='CHARACTER_UNUSABLE'
    with session() as db:
        c=db.scalar(select(Configuration))
        assert c.representative_id is None and c.version==1 and c.state=='unconfigured'
        assert db.scalar(select(func.count()).select_from(Activity))==0


@pytest.mark.parametrize('level', ['1700','1700.01','1,700.00'])
def test_minimum_inclusive_for_owned_subaccount(client,world,level):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    p=page(client,h,r['registration_id']);cid=p['characters']['items'][0]['character_id'];set_level(cid,level)
    response=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p,[cid],cid))
    assert response.status_code==200 and response.json()['activity_character_ids']==[cid]
    assert client.get(BASE,headers=h).json()['items'][0]['is_main'] is False


@pytest.mark.parametrize('same_target',[False,True])
def test_representative_command_validates_level_even_for_noop(client,selection,same_target):
    w=selection;target=w['ids'][0 if same_target else 1];set_level(target,'1699.99')
    before=get(client,w).json()
    response=put(client,w,representative_body(w,target))
    assert response.status_code==409 and response.json()['error']['code']=='CHARACTER_UNUSABLE'
    assert get(client,w).json()==before


def test_existing_low_selection_reported_without_replacing_or_deleting(client,selection):
    w=selection;set_level(w['ids'][0],None)
    before=get(client,w).json()
    current=page(client,w['headers'],w['rid'])
    assert w['ids'][0] in current['settings']['ineligible_character_ids']
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


def test_roster_level_drop_marks_reconfiguration_without_replacing_representative(client,world,monkeypatch):
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
    assert current['configuration_state']=='needs_reconfiguration'
    assert current['representative_character_id']==payload['representative_character_id']
    assert current['ineligible_character_ids']==[payload['representative_character_id']]
    assert set(current['activity_character_ids'])==set(payload['activity_character_ids'])
