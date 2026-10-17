"""Agreed target/version wire, legacy retries and live non-transfer proof flow."""
import hashlib
import json
import uuid
from urllib.parse import unquote
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import observations, provider
from app.game_accounts.models import Account, Registration, Character, Verification, Audit, RequestResult, VerificationExecution, Configuration, Activity
from app.game_accounts.equipment import SLOTS
from tests.test_game_accounts import world, register, verify, change, BASE, VERIFY, another_user, page, save_data
from tests.test_game_account_primitives import transport

LIVE_FETCH = observations.fetch
FIELDS = {'challenge_id','status','required_slots','expires_at','remaining_seconds','result_code','result_reference','registration_id'}


@pytest.fixture
def targets(client, world, monkeypatch):
    h, state = world
    r = register(client,h,main=True)
    wire = dict(removed=(),calls=[],server='sample-server',names=['a0','a1','a2'])
    monkeypatch.setattr(observations,'fetch',LIVE_FETCH)
    def get(url,**kwargs):
        siblings=url.endswith('/siblings')
        name=unquote(url.split('/')[-2 if siblings else -1])
        wire['calls'].append(('siblings' if siblings else 'armory',name))
        if siblings:
            raw=[dict(ServerName=wire['server'],CharacterName=n,CharacterClassName='sample-class',CharacterLevel=60,ItemAvgLevel='1000') for n in wire['names']]
        else:
            raw=dict(ArmoryProfile=dict(ServerName=wire['server'],CharacterName=name),
                     ArmoryEquipment=[dict(Type=s,Name='sample-'+s,Grade='고대') for s in SLOTS if s not in wire['removed']])
        return transport(body=json.dumps(raw).encode())[1]
    monkeypatch.setattr(provider.requests,'get',get)
    return h,r,wire


def body(r,name='a1'):
    return dict(source='registration',registration_id=r['registration_id'],
                target_character=dict(server_name='sample-server',character_name=name),expected_registration_version=r['version'])


def finish(client,h,wire,v,key=None):
    wire['removed']=v['required_slots']
    return change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{},key)


def test_select_preview_character_below_activity_min_and_preserve_scope(client,targets):
    h,r,wire=targets
    data=body(r)
    result=change(client,h,'post',VERIFY,data)
    assert result.status_code==201,result.text
    v=result.json();assert set(v)==FIELDS and v['registration_id']==r['registration_id']
    assert wire['calls']==[('siblings','a1'),('armory','a1')]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==0
        challenge=db.get(Verification,uuid.UUID(v['challenge_id']))
        assert challenge.lookup_name=='a1' and challenge.identity_snapshot['proof_context']['target']==['sample-server','a1']
        assert db.get(Registration,uuid.UUID(r['registration_id'])).lookup_name=='a0'
        assert db.scalar(select(VerificationExecution.lookup_name))=='a1'
    completed=finish(client,h,wire,v)
    assert completed.status_code==200 and completed.json()['status']=='verified'
    assert set(completed.json())==FIELDS
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Registration))==1
        assert db.get(Registration,uuid.UUID(r['registration_id'])).lookup_name=='a0'
        conf=db.scalar(select(Configuration))
        assert conf.state=='unconfigured' and conf.representative_id is None
        assert db.scalar(select(func.count()).select_from(Activity))==0


def test_same_owned_registration_is_blocked_without_changing_settings(client,targets):
    h,r,wire=targets
    first=change(client,h,'post',VERIFY,body(r)).json()
    assert finish(client,h,wire,first).json()['status']=='verified'
    wire['removed']=()
    # A blocked repeated start never refreshes or reconfigures saved choices.
    with session() as db,db.begin():
        for c in db.scalars(select(Character)):
            c.summary=dict(c.summary,item_level='1700')
    p=page(client,h,r['registration_id'])
    saved=change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p))
    assert saved.status_code==200
    previous=saved.json()
    current=client.get(BASE,headers=h).json()['items'][0]
    with session() as db:
        a=db.scalar(select(Account));before=(a.id,a.owner_id,a.ownership_revision)
        ids=set(db.scalars(select(Character.id)))
    calls=len(wire['calls'])
    second=change(client,h,'post',VERIFY,body(current,'a2'))
    assert second.status_code==409 and second.json()['error']['code']=='ALREADY_VERIFIED'
    assert len(wire['calls'])==calls
    with session() as db:
        a=db.scalar(select(Account));assert (a.id,a.owner_id,a.ownership_revision)==before
        assert set(db.scalars(select(Character.id)))==ids
        assert db.scalar(select(func.count()).select_from(Audit))==1
        assert db.scalar(select(func.count()).select_from(Verification))==1
        assert db.get(Registration,uuid.UUID(r['registration_id'])).lookup_name=='a0'
    settings=page(client,h,r['registration_id'])['settings']
    assert settings['activity_character_ids']==previous['activity_character_ids']
    assert settings['representative_character_id']==previous['representative_character_id']
    assert settings['configuration_state']=='configured'



@pytest.mark.parametrize('patch',[
    {'expected_registration_version':None}, {'expected_registration_version':0},
    {'expected_registration_version':True}, {'expected_registration_version':1.0},
    {'target_character':None}, {'target_character':{'server_name':'','character_name':'a1'}},
    {'target_character':{'server_name':'sample-server','character_name':7}},
    {'target_character':{'server_name':'sample-server','character_name':'a1','character_id':str(uuid.uuid4())}},
    {'character_name':'a1'},
])
def test_invalid_selection_wire_is_400_without_provider(client,targets,patch):
    h,r,wire=targets;data=body(r);data.update(patch)
    response=change(client,h,'post',VERIFY,data)
    assert response.status_code==400 and response.json()['error']['code']=='INVALID_REQUEST'
    assert wire['calls']==[]


@pytest.mark.parametrize('kind',['missing_version','version_only','direct_target','direct_version'])
def test_selection_fields_are_paired_and_registration_only(client,targets,kind):
    h,r,wire=targets;data=body(r)
    if kind=='missing_version':data.pop('expected_registration_version')
    elif kind=='version_only':data.pop('target_character')
    elif kind=='direct_target':data=dict(source='direct_input',character_name='a1',target_character=data['target_character'])
    else:data=dict(source='direct_input',character_name='a1',expected_registration_version=1)
    assert change(client,h,'post',VERIFY,data).status_code==400
    assert wire['calls']==[]


@pytest.mark.parametrize('kind',['stale','outsider','wrong_server','incomplete'])
def test_selection_version_membership_and_live_equipment_rejections(client,targets,kind):
    h,r,wire=targets;data=body(r)
    if kind=='stale':data['expected_registration_version']+=1;expected=(409,'REVISION_CONFLICT')
    elif kind=='outsider':data['target_character']['character_name']='unregistered';wire['names']+=['unregistered'];expected=(404,'CHARACTER_NOT_FOUND')
    elif kind=='wrong_server':wire['server']='other-server';expected=(409,'IDENTITY_CONFLICT')
    else:wire['removed']=('무기',);expected=(400,'EQUIPMENT_INCOMPLETE')
    response=change(client,h,'post',VERIFY,data)
    assert (response.status_code,response.json()['error']['code'])==expected,response.text
    if kind in ('stale','outsider'):assert wire['calls']==[]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Verification))==0
        assert db.scalar(select(func.count()).select_from(Account))==0


@pytest.mark.parametrize('source',['registration','direct_input'])
def test_legacy_normalized_digest_and_lost_start_replay_are_unchanged(client,targets,source):
    h,r,wire=targets
    old=(dict(source=source,registration_id=r['registration_id'],character_name=None) if source=='registration'
         else dict(source=source,registration_id=None,character_name='a0'))
    key=uuid.uuid4()
    first=change(client,h,'post',VERIFY,old,key)
    assert first.status_code==201,first.text
    digest=hashlib.sha256(json.dumps({'target':None,'body':old},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with session() as db:
        command=db.scalar(select(RequestResult).where(RequestResult.key==key,RequestResult.operation=='start'))
        assert command.digest==digest
    count=len(wire['calls'])
    assert change(client,h,'post',VERIFY,old,key).json()==first.json()
    assert len(wire['calls'])==count
    current=client.get(VERIFY+'/'+first.json()['challenge_id'],headers=h)
    assert current.status_code==200 and set(current.json())==FIELDS
    with session() as db:assert db.scalar(select(func.count()).select_from(Verification))==1


def test_target_retry_is_immutable_and_rejects_changed_choice(client,targets):
    h,r,wire=targets;key=uuid.uuid4();data=body(r)
    v=change(client,h,'post',VERIFY,data,key)
    assert v.status_code==201
    assert change(client,h,'post',VERIFY,data,key).json()==v.json()
    response=change(client,h,'post',VERIFY,body(r,'a2'),key)
    assert response.status_code==409 and response.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert wire['calls']==[('siblings','a1'),('armory','a1')]


def test_foreign_owner_can_complete_equipment_check_but_not_transfer(client,targets,login,monkeypatch):
    h,r,wire=targets
    v=change(client,h,'post',VERIFY,body(r)).json()
    assert finish(client,h,wire,v).json()['status']=='verified'
    wire['removed']=()
    other=another_user(login,monkeypatch,client)
    challenged=change(client,other,'post',VERIFY,dict(source='direct_input',character_name='a1'))
    assert challenged.status_code==201 and challenged.json()['status']=='pending'
    with session() as db:
        a=db.scalar(select(Account));before=(a.id,a.owner_id,a.ownership_revision)
    pending=finish(client,other,wire,challenged.json())
    assert pending.status_code==200 and pending.json()['status']=='pending'
    assert pending.json()['result_code']=='ACCOUNT_BINDING_EVIDENCE_PENDING'
    assert pending.json()['result_reference'] is None
    current=client.get(VERIFY+'/'+challenged.json()['challenge_id'],headers=other).json()
    assert current['result_code']=='ACCOUNT_BINDING_EVIDENCE_PENDING' and set(current)==FIELDS
    with session() as db:
        a=db.scalar(select(Account));assert (a.id,a.owner_id,a.ownership_revision)==before
        assert db.scalar(select(func.count()).select_from(Audit))==1
        assert db.scalar(select(func.count()).select_from(Registration))==1
        stored=db.get(Verification,uuid.UUID(challenged.json()['challenge_id']))
        assert stored.identity_snapshot['equipment_control_verified_at']
        assert stored.status=='pending'


def test_other_members_registration_cannot_be_selected(client,targets,login,monkeypatch):
    h,r,wire=targets;other=another_user(login,monkeypatch,client)
    result=change(client,other,'post',VERIFY,body(r))
    assert result.status_code==404 and result.json()['error']['code']=='REGISTRATION_NOT_FOUND'
    assert wire['calls']==[]


def test_registration_version_change_during_fetch_rejects_start(client,targets,monkeypatch):
    h,r,wire=targets
    original=provider.requests.get
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        with session() as db,db.begin():db.get(Registration,uuid.UUID(r['registration_id'])).version+=1
        return result
    monkeypatch.setattr(provider.requests,'get',changed)
    result=change(client,h,'post',VERIFY,body(r))
    assert result.status_code==409 and result.json()['error']['code']=='REVISION_CONFLICT'
    with session() as db:assert db.scalar(select(func.count()).select_from(Verification))==0


def test_pending_claim_owner_change_never_grants_new_authority(client,targets,login,monkeypatch):
    h,r,wire=targets
    v=change(client,h,'post',VERIFY,body(r)).json()
    assert finish(client,h,wire,v).json()['status']=='verified'
    wire['removed']=()
    other=another_user(login,monkeypatch,client)
    pending=change(client,other,'post',VERIFY,dict(source='direct_input',character_name='a1')).json()
    with session() as db,db.begin():
        a=db.scalar(select(Account));a.owner_id=None;a.ownership_revision+=1
    result=finish(client,other,wire,pending)
    assert result.status_code==409 and result.json()['error']['code']=='REVISION_CONFLICT'
    with session() as db:
        assert db.scalar(select(Account.owner_id)) is None
        assert db.scalar(select(func.count()).select_from(Audit))==1
        assert db.get(Verification,uuid.UUID(pending['challenge_id'])).status=='pending'


def test_pending_equipment_acceptance_also_obeys_final_expiry(client,targets,login,monkeypatch):
    from datetime import timedelta
    from app.game_accounts import service, equipment_proof
    h,r,wire=targets
    first=change(client,h,'post',VERIFY,body(r)).json()
    assert finish(client,h,wire,first).json()['status']=='verified'
    wire['removed']=()
    other=another_user(login,monkeypatch,client)
    v=change(client,other,'post',VERIFY,dict(source='direct_input',character_name='a1')).json()
    original_check,original_now=equipment_proof.validated,service.now
    clock={'expired':False}
    def delayed(*args,**kwargs):
        result=original_check(*args,**kwargs);clock['expired']=True;return result
    monkeypatch.setattr(equipment_proof,'validated',delayed)
    monkeypatch.setattr(service,'now',lambda db:original_now(db)+(timedelta(minutes=11) if clock['expired'] else timedelta()))
    result=finish(client,other,wire,v)
    assert result.status_code==409 and result.json()['error']['code']=='VERIFICATION_EXPIRED'
    with session() as db:
        saved=db.get(Verification,uuid.UUID(v['challenge_id']))
        assert saved.status=='expired' and 'equipment_control_verified_at' not in saved.identity_snapshot
        assert db.scalar(select(func.count()).select_from(Audit))==1
