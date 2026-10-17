"""Real collector/fake HTTP: self block, foreign challenge, same-owner restore."""
import uuid
import pytest
from sqlalchemy import select,func
from app.core.database import session
from app.game_accounts import provider
from app.game_accounts.models import Account,Registration,Verification,Audit,Character,Configuration,Activity,VerificationExecution
from tests.test_verification_targets import targets,body,finish,FIELDS
from tests.test_game_accounts import world,change,register,page,save_data,another_user,BASE,VERIFY


def seed(client,targets):
 h,r,wire=targets
 key=uuid.uuid4(); data=body(r)
 v=change(client,h,'post',VERIFY,data,key).json()
 assert finish(client,h,wire,v).json()['status']=='verified'
 wire['removed']=();wire['calls'].clear()
 return h,r,wire,key,data,v


def delete_registration(client,h,r):
 current=next(x for x in client.get(BASE,headers=h).json()['items'] if x['registration_id']==r['registration_id'])
 assert change(client,h,'delete',BASE+'/'+r['registration_id']+'?expected_version='+str(current['version'])).status_code==204


def account_state():
 with session() as db:
  a=db.scalar(select(Account))
  return (a.id,a.owner_id,a.ownership_revision,a.roster_revision,a.verified_at,
          set(db.scalars(select(Character.id))),db.scalar(select(func.count()).select_from(Audit)))


@pytest.mark.parametrize('source',['legacy','target','direct','new_name'])
def test_self_owned_start_blocks_without_armory_or_business_writes(client,targets,source):
 h,r,wire,key,data,v=seed(client,targets)
 if source=='legacy': request=dict(source='registration',registration_id=r['registration_id'])
 elif source=='target': request=data  # Even a stale expected version cannot restart owned auth.
 else:
  name='a3' if source=='new_name' else 'a1'
  if source=='new_name': wire['names'].append(name)
  request=dict(source='direct_input',character_name=name)
 before=account_state()
 result=change(client,h,'post',VERIFY,request)
 assert result.status_code==409 and result.json()['error']['code']=='ALREADY_VERIFIED'
 assert wire['calls']==([] if source in ('legacy','target') else [('siblings',request['character_name'])])
 assert account_state()==before
 with session() as db:
  assert db.scalar(select(func.count()).select_from(Verification))==1
  event=db.scalar(select(VerificationExecution).order_by(VerificationExecution.started_at.desc()))
  assert (event.state,event.outcome_code)==('failed','ALREADY_VERIFIED')


def test_completed_start_replay_survives_current_owner_block(client,targets):
 h,r,wire,key,data,v=seed(client,targets)
 result=change(client,h,'post',VERIFY,data,key)
 assert result.status_code==201 and result.json()==v and set(v)==FIELDS
 assert wire['calls']==[]
 assert client.get(VERIFY+'/'+v['challenge_id'],headers=h).json()['status']=='verified'
 with session() as db:
  assert db.scalar(select(func.count()).select_from(VerificationExecution))==2


@pytest.mark.parametrize('source',['registration','direct'])
def test_ownership_lost_can_challenge_but_cannot_transfer(client,targets,source):
 h,r,wire,key,data,v=seed(client,targets)
 with session() as db,db.begin():
  a=db.scalar(select(Account));a.owner_id=None;a.ownership_revision+=1
 before=account_state()
 current=client.get(BASE,headers=h).json()['items'][0]
 request=body(current) if source=='registration' else dict(source='direct_input',character_name='a1')
 result=change(client,h,'post',VERIFY,request)
 assert result.status_code==201
 done=finish(client,h,wire,result.json())
 assert done.status_code==200 and done.json()['result_code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'
 assert account_state()==before


def test_other_member_registration_gets_challenge_and_never_inherits_owner(client,targets,login,monkeypatch):
 h,r,wire,key,data,v=seed(client,targets)
 other=another_user(login,monkeypatch,client)
 foreign=register(client,other)
 assert foreign['ownership_status']=='unverified' and foreign['game_account_id'] is None
 wire['calls'].clear();before=account_state()
 challenge=change(client,other,'post',VERIFY,body(foreign))
 assert challenge.status_code==201
 done=finish(client,other,wire,challenge.json())
 assert done.status_code==200 and done.json()['result_code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'
 assert account_state()==before


@pytest.mark.parametrize('name',['a0','a3'])
def test_remove_reregister_restores_owner_without_equipment_or_selection(client,targets,name):
 h,r,wire,key,data,v=seed(client,targets)
 with session() as db,db.begin():
  for c in db.scalars(select(Character)): c.summary=dict(c.summary,item_level='1700')
 p=page(client,h,r['registration_id'])
 assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code==200
 before=account_state();delete_registration(client,h,r)
 if name=='a3': wire['names'].append(name)
 wire['calls'].clear()
 restored=register(client,h,name)
 assert restored['registration_id']!=r['registration_id']
 assert restored['game_account_id']==str(before[0]) and restored['ownership_status']=='owned'
 assert restored['verification_status']=='verified'
 assert restored['settings']['configuration_state']=='unconfigured'
 assert restored['settings']['activity_character_ids']==[] and restored['settings']['representative_character_id'] is None
 assert wire['calls']==[('siblings',name)] and account_state()==before
 with session() as db:
  assert db.scalar(select(func.count()).select_from(Verification))==1
  assert db.get(Registration,uuid.UUID(r['registration_id'])).deleted_at is not None


@pytest.mark.parametrize('state',['lost','no_anchor','retired_anchor'])
def test_reregister_does_not_infer_ownership_without_current_authority(client,targets,state):
 h,r,wire,key,data,v=seed(client,targets)
 delete_registration(client,h,r)
 if state=='no_anchor': wire['names']=['a3']
 else:
  with session() as db,db.begin():
   a=db.scalar(select(Account))
   if state=='lost': a.owner_id=None;a.ownership_revision+=1
   if state=='retired_anchor':
    for c in db.scalars(select(Character)): c.lifecycle_state='retired'
 restored=register(client,h,'a3' if state=='no_anchor' else 'a0')
 assert restored['ownership_status']=='unverified' and restored['game_account_id'] is None


def test_reregister_owner_changes_during_network_are_fenced(client,targets,monkeypatch):
 h,r,wire,key,data,v=seed(client,targets)
 delete_registration(client,h,r)
 original=provider.requests.get
 def changed(url,**kwargs):
  result=original(url,**kwargs)
  with session() as db,db.begin():
   a=db.scalar(select(Account));a.owner_id=None;a.ownership_revision+=1
  return result
 monkeypatch.setattr(provider.requests,'get',changed)
 response=change(client,h,'post',BASE,dict(lookup_character_name='a0',label='',is_main=False))
 assert response.status_code==409 and response.json()['error']['code']=='REVISION_CONFLICT'
 with session() as db:
  assert db.scalar(select(func.count()).select_from(Registration).where(Registration.deleted_at.is_(None)))==0


def test_start_commit_rechecks_owner_if_changed_after_siblings(client,targets,monkeypatch):
 h,r,wire,key,data,v=seed(client,targets)
 with session() as db,db.begin():
  a=db.scalar(select(Account));actor=a.owner_id;a.owner_id=None;a.ownership_revision+=1
 original=provider.requests.get
 def changed(url,**kwargs):
  result=original(url,**kwargs)
  if not url.endswith('/siblings'):
   with session() as db,db.begin():
    a=db.scalar(select(Account));a.owner_id=actor;a.ownership_revision+=1
  return result
 monkeypatch.setattr(provider.requests,'get',changed)
 response=change(client,h,'post',VERIFY,dict(source='direct_input',character_name='a1'))
 assert response.status_code==409 and response.json()['error']['code']=='ALREADY_VERIFIED'
 with session() as db:
  assert db.scalar(select(func.count()).select_from(Verification))==1
  assert db.scalar(select(func.count()).select_from(Audit))==1


def test_restore_replay_is_original_ack_and_current_get_remains_authoritative(client,targets):
 h,r,wire,key,data,v=seed(client,targets)
 delete_registration(client,h,r)
 request=dict(lookup_character_name='a0',label='',is_main=False);restore_key=uuid.uuid4()
 original=change(client,h,'post',BASE,request,restore_key)
 assert original.status_code==201 and original.json()['ownership_status']=='owned'
 wire['calls'].clear()
 with session() as db,db.begin():
  a=db.scalar(select(Account));a.owner_id=None;a.ownership_revision+=1
 replay=change(client,h,'post',BASE,request,restore_key)
 assert replay.json()==original.json() and wire['calls']==[]
 current=client.get(BASE,headers=h).json()['items'][0]
 assert current['ownership_status']=='ownership_lost'


def test_mixed_accounts_do_not_restore_or_block_a_foreign_challenge(client,targets,login,monkeypatch):
 h,r,wire,key,data,v=seed(client,targets)
 other=another_user(login,monkeypatch,client)
 wire['names']=['b0']
 foreign=change(client,other,'post',VERIFY,dict(source='direct_input',character_name='b0')).json()
 assert finish(client,other,wire,foreign).json()['status']=='verified'
 wire['removed']=()
 delete_registration(client,h,r)
 wire['names']=['a0','b0']
 restored=register(client,h)
 assert restored['game_account_id'] is None and restored['ownership_status']=='unverified'
 challenge=change(client,h,'post',VERIFY,dict(source='direct_input',character_name='a0'))
 assert challenge.status_code==201
 pending=finish(client,h,wire,challenge.json())
 assert pending.json()['result_code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'


def test_missing_member_history_never_attaches_an_observed_account(client,targets):
 h,r,wire,key,data,v=seed(client,targets)
 delete_registration(client,h,r)
 with session() as db,db.begin():
  db.get(Registration,uuid.UUID(r['registration_id'])).account_id=None
 restored=register(client,h)
 assert restored['game_account_id'] is None and restored['ownership_status']=='unverified'


def test_preexisting_pending_challenge_cannot_repeat_an_already_completed_auth(client,targets):
 h,r,wire=targets
 first=change(client,h,'post',VERIFY,body(r)).json()
 pending=change(client,h,'post',VERIFY,body(r)).json()
 assert finish(client,h,wire,first).json()['status']=='verified'
 wire['removed']=();wire['calls'].clear();before=account_state()
 result=change(client,h,'post',VERIFY+'/'+pending['challenge_id']+'/confirm',{})
 assert result.status_code==409 and result.json()['error']['code']=='ALREADY_VERIFIED'
 assert wire['calls']==[] and account_state()==before
 with session() as db:
  assert db.get(Verification,uuid.UUID(pending['challenge_id'])).attempt_count==0
 # A completed confirmation and original result recovery remain readable.
 replay=change(client,h,'post',VERIFY+'/'+first['challenge_id']+'/confirm',{})
 assert replay.status_code==200 and replay.json()['status']=='verified'
 assert wire['calls']==[]
