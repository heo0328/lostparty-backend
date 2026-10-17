"""Challenge subjects cannot change during proof, even with matched equipment."""
import uuid
from dataclasses import replace
import pytest
from sqlalchemy import select,func
from app.core.database import session
from app.game_accounts import observations,verification_context
from app.game_accounts.models import Account,Character,Audit,Verification,Registration
from tests.test_game_accounts import world,register,start,verify,change,BASE,VERIFY,another_user


def assert_unverified(registration_id):
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==0
        assert db.scalar(select(func.count()).select_from(Character))==0
        assert db.scalar(select(func.count()).select_from(Audit))==0
        assert db.get(Registration,uuid.UUID(registration_id)).account_id is None


@pytest.mark.parametrize('mutation',['server','group','addition','missing','duplicate','invalid'])
def test_changed_subject_or_roster_never_creates_ownership(client,world,monkeypatch,mutation):
    h,state=world;r=register(client,h);v=start(client,h,r['registration_id'])
    state['removed']=v['required_slots'];original=observations.fetch
    def changed(*args,**kwargs):
        result=original(*args,**kwargs);rows=[dict(row) for row in result.roster]
        if mutation=='server':
            rows[0]['server_name']='other-server'
        elif mutation=='group':
            for row in rows:row['character_name']='other-'+row['character_name']
        elif mutation=='addition':
            rows.append(dict(rows[-1],character_name='new-character'))
        elif mutation=='missing':
            rows.pop()
        elif mutation=='duplicate':
            rows.append(dict(rows[0]))
        else:
            rows[0]['server_name']=None
        return replace(result,roster=rows)
    monkeypatch.setattr(observations,'fetch',changed)
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==200 and response.json()['status']=='pending'
    assert response.json()['result_code']=='ROSTER_EVIDENCE_PENDING'
    assert_unverified(r['registration_id'])


@pytest.mark.parametrize('marker',[1,'true',[True],{'valid':True},None])
def test_truthy_adapter_marker_is_not_validated_proof(client,world,marker):
    h,state=world;r=register(client,h);v=start(client,h,r['registration_id'])
    state['removed']=v['required_slots'];state['validated']=marker
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==200 and response.json()['result_code']=='PROVIDER_EVIDENCE_PENDING'
    assert_unverified(r['registration_id'])


def test_old_challenge_without_bound_context_stays_pending(client,world):
    h,state=world;r=register(client,h);v=start(client,h,r['registration_id'])
    with session() as db,db.begin():
        challenge=db.get(Verification,uuid.UUID(v['challenge_id']))
        challenge.identity_snapshot={key:value for key,value in challenge.identity_snapshot.items() if key!='proof_context'}
    state['removed']=v['required_slots']
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==200 and response.json()['result_code']=='PROVIDER_EVIDENCE_PENDING'
    assert_unverified(r['registration_id'])


def test_order_and_display_changes_do_not_masquerade_as_identity_change(client,world,monkeypatch):
    h,state=world;r=register(client,h);v=start(client,h,r['registration_id'])
    state['removed']=v['required_slots'];original=observations.fetch
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        return replace(result,roster=[dict(row,item_level='1701',character_level=61) for row in reversed(result.roster)])
    monkeypatch.setattr(observations,'fetch',changed)
    response=change(client,h,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==200 and response.json()['status']=='verified'
    # Verified here comes from the mock adapter's True marker, never roster equality.
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account))==1


def test_changed_roster_never_transfers_an_existing_owner(client,world,login,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    with session() as db:owner=db.scalar(select(Account.owner_id))
    other=another_user(login,monkeypatch,client);v=start(client,other)
    state['count']=4;state['removed']=v['required_slots']
    response=change(client,other,'post',VERIFY+'/'+v['challenge_id']+'/confirm',{})
    assert response.status_code==200 and response.json()['result_code']=='ROSTER_EVIDENCE_PENDING'
    with session() as db:
        assert db.scalar(select(Account.owner_id))==owner
        assert db.scalar(select(func.count()).select_from(Audit))==1


def test_malformed_start_has_no_challenge_or_ownership(client,world,monkeypatch):
    h,_=world;r=register(client,h);original=observations.fetch
    monkeypatch.setattr(observations,'fetch',lambda *args,**kwargs:replace(original(*args,**kwargs),roster=[]))
    response=change(client,h,'post',VERIFY,{'source':'registration','registration_id':r['registration_id']})
    assert response.status_code==503 and response.json()['error']['code']=='UPSTREAM_INVALID_RESPONSE'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Verification))==0
    assert_unverified(r['registration_id'])


def test_capture_is_order_invariant_but_not_an_authority_marker():
    rows=[dict(server_name='s',character_name='a'),dict(server_name='s',character_name='b')]
    context=verification_context.capture('a',rows)
    assert context==verification_context.capture('a',list(reversed(rows)))
    assert set(context)=={'target','roster'}
    assert verification_context.pending_code({'proof_context':context},'a',rows) is None
    assert verification_context.capture('missing',rows) is None
