"""Invite lookup casing and stored role display on disposable PostgreSQL only."""
import uuid
import pytest
from sqlalchemy import select,event
from app.auth.models import User
from app.core.database import session,now
from app.game_accounts.models import Character,Account,Registration,NameClaim,CharacterRoleSummary
from app.game_accounts.power_success import capture
from app.game_accounts.provider import LostArkProvider
from app.lostark_keys import service as credentials
from tests.test_group_admissions import worlds,group
from tests.test_group_display import group_features
from tests.test_role_summaries import summary
from tests.test_raid_room_migrations import isolated_app_database
from app.core import database


def rename(w,index,name):
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(w['ids'][index]))
        claim=db.get(NameClaim,(c.server_name,c.character_name));db.delete(claim);db.flush()
        c.character_name=name;c.summary=dict(c.summary,character_name=name);db.flush()
        db.add(NameClaim(server_name=c.server_name,character_name=name,character_id=c.id))
    return name


def candidates(client,a,gid,name,profile=True):
    params=dict(character_name=name)
    if profile:params['reader_profile']='group-display-1'
    response=client.get(f'/v1/groups/{gid}/invite-candidates',headers=a['headers'],params=params)
    assert response.status_code==200,response.text
    assert response.headers['Cache-Control']=='no-store'
    return response.json()


def store(w,index,role,power):
    with session() as db,db.begin():
        head=CharacterRoleSummary(user_id=w['uid'],character_id=uuid.UUID(w['ids'][index]),ownership_revision=1,
            role=role,version=2,summary=dict(summary(),combat_power=power),saved_at=now(db))
        db.add(head);db.flush();capture(db,head)


def test_case_insensitive_exact_lookup_and_default_shape(group_features,client):
    _,a,b,gid=group_features;name=rename(b,0,'MixedHero한글')
    baseline=candidates(client,a,gid,name,False)
    assert len(baseline['items'])==1
    assert set(baseline)=={'items'}
    assert set(baseline['items'][0])=={'target_character_id','display','ownership_revision','lifecycle_revision','item_level','combat_power'}
    for query in ('mixedhero한글','MIXEDHERO한글','mIxEdHeRo한글',' MixedHero한글 '):
        assert candidates(client,a,gid,query,False)==baseline
        assert candidates(client,a,gid,query)['items'][0]['display']['character_name']==name
    for query in ('MixedHero','MixedHero%','%','_','MixedHero한글x'):
        assert candidates(client,a,gid,query,False)['items']==[]
    assert client.get(f'/v1/groups/{gid}/invite-candidates',headers=b['headers'],params={'character_name':name}).status_code==403


@pytest.mark.parametrize('invalid',['preview_registration','registration_ended','disabled','owner_lost','missing_claim','retired'])
def test_both_profiles_exclude_ineligible_targets(group_features,client,invalid):
    _,a,b,gid=group_features;name=rename(b,0,'MixedHero')
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(b['ids'][0]));account=db.get(Account,b['aid'])
        if invalid=='preview_registration':db.get(Registration,uuid.UUID(b['rid'])).account_id=None
        elif invalid=='registration_ended':db.get(Registration,uuid.UUID(b['rid'])).deleted_at=now(db)
        elif invalid=='disabled':db.get(User,b['uid']).status='disabled'
        elif invalid=='owner_lost':account.owner_id=None
        elif invalid=='missing_claim':db.delete(db.get(NameClaim,(c.server_name,c.character_name)))
        else:c.lifecycle_state='retired'
    for profile in (False,True):assert candidates(client,a,gid,name.lower(),profile)['items']==[]


def test_unselected_activity_role_success_current_error_and_read_only(group_features,client,monkeypatch):
    target,a,b,gid=group_features;name=rename(b,2,'NotSelectedHero')
    store(b,2,'dealer','123.45');store(b,2,'support','987.65')
    with session() as db,db.begin():
        head=db.get(CharacterRoleSummary,(b['uid'],uuid.UUID(b['ids'][2]),1,'dealer'))
        head.summary=dict(head.summary,combat_power=None,combat_power_observed_at=None,integrity_status='error',issues=[dict(code='GEM_INVALID',severity='error')]);head.version=3
    def forbidden(*args,**kwargs):raise AssertionError('No provider or key access')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden);monkeypatch.setattr(credentials,'capture',forbidden)
    statements=[]
    def record(conn,cursor,sql,parameters,context,many):statements.append(sql.lstrip().split()[0].upper())
    event.listen(target,'before_cursor_execute',record)
    try:page=candidates(client,a,gid,name.lower())
    finally:event.remove(target,'before_cursor_execute',record)
    assert set(statements)<={'SELECT','SET'}
    assert page['profile']=='group-display-1' and page['evaluated_at']
    item=page['items'][0];spec=item['character_spec']
    assert item['combat_power'] is None and spec['dealer']['combat_power']=='123.45'
    assert spec['support']['combat_power']=='987.65'
    assert spec['dealer']['analysis']['integrity_status']=='error'
    assert spec['support']['analysis']['integrity_status']=='clean'
    assert spec['dealer']['source']=='stored_role_success' and spec['dealer']['observed_at']
    assert str(b['uid']) not in str(page) and b['rid'] not in str(page) and str(b['aid']) not in str(page)


def test_missing_and_old_role_generations_never_become_normal(group_features,client):
    _,a,b,gid=group_features;name=rename(b,0,'RoleHero')
    spec=candidates(client,a,gid,name)['items'][0]['character_spec']
    assert spec['dealer']['combat_power'] is None and spec['dealer']['analysis'] is None
    store(b,0,'dealer','123.45')
    with session() as db,db.begin():db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_revision+=1
    spec=candidates(client,a,gid,name)['items'][0]['character_spec']
    assert spec['dealer']['combat_power'] is None and spec['dealer']['analysis'] is None
    with session() as db,db.begin():
        db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_revision=1
        db.get(Account,b['aid']).ownership_revision+=1
    spec=candidates(client,a,gid,name)['items'][0]['character_spec']
    assert spec['dealer']['combat_power'] is None and spec['dealer']['analysis'] is None


@pytest.mark.parametrize('revision',['0023_recruitment_resume','0033_reapplication_history'])
def test_old_schema_default_lookup_and_explicit_profile_gate(client,worlds,monkeypatch,revision):
    with isolated_app_database() as (target,role,upgrade):
        upgrade(revision)
        with monkeypatch.context() as patch:
            patch.setattr(database,'engine',lambda:target)
            a,b=worlds('invite-old-a'),worlds('invite-old-b');gid=group(client,a);name=rename(b,0,'OldHero')
            assert candidates(client,a,gid,name.lower(),False)['items'][0]['target_character_id']==b['ids'][0]
            response=client.get(f'/v1/groups/{gid}/invite-candidates',headers=a['headers'],params=dict(character_name=name,reader_profile='group-display-1'))
            assert response.status_code==503 and response.json()['error']['code']=='GROUP_FEATURE_NOT_READY'
            assert client.get(f'/v1/groups/{gid}/invite-candidates',headers=a['headers'],params=dict(character_name=name,reader_profile='other')).status_code==400
