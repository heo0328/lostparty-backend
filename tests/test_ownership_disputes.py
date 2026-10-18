"""V2 product disputes with real collector/schema proof and isolated PostgreSQL."""
import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select,func,text
from app.core.database import session,now
from app.game_accounts.models import Account,Registration,Character,Configuration,Audit
from app.ownership_disputes.models import Proof,Dispute,AccountHead,Event as DisputeEvent
from app.ownership_disputes import commands,core,worker
from app.game_accounts import observations
from app.game_accounts.support import GameError
from tests.test_game_accounts import world,another_user,change,BASE,PrivateHeaders
from tests.test_live_equipment_proof import live

VERIFY='/v2/me/game-account-verifications'
DISPUTE='/v2/me/ownership-disputes'


@pytest.fixture
def environment(client,live,login,monkeypatch):
    owner,state=live
    # Exercise business concurrency without the independent per-minute UI quotas.
    monkeypatch.setattr(commands,'quota',lambda *args:None)
    state['canonical']='ExampleHero'
    from app.auth import service as auth_service
    users=[owner]
    for i in range(4):
        monkeypatch.setattr(auth_service,'verify_google',lambda *args, subject=f'v2-member-{i}', **kwargs:subject)
        auth,_=login();h=PrivateHeaders(Authorization='Bearer '+auth['access_token'])
        assert change(client,h,'put','/v1/me/lostark-api-key',dict(token='other.member.signature',expected_version=1)).status_code==200
        users.append(h)
    return users,state


def start(client,h,name='examplehero'):
    r=change(client,h,'post',VERIFY,{'source':'direct_input','character_name':name})
    assert r.status_code==201,r.text
    return r.json()


def confirm(client,h,p,key=None):
    return change(client,h,'post',VERIFY+'/'+p['verification_id']+'/confirm',{'expected_version':p['version']},key)


def claim_owner(client,env):
    users,state=env;p=start(client,users[0]);state['removed']=p['required_slots']
    r=confirm(client,users[0],p);assert r.status_code==200,r.text
    assert r.json()['ownership_outcome']=='verified'
    state['removed']=()
    return r.json()


def open_dispute(client,env,index=1):
    users,state=env;p=start(client,users[index]);state['removed']=p['required_slots']
    r=confirm(client,users[index],p);assert r.status_code==200,r.text
    assert r.json()['ownership_outcome']=='dispute_opened',r.text
    state['removed']=()
    return r.json()


def expire_all():
    with session() as db,db.begin():
        # Keep the invariant deadline = start+24h; do not weaken the real constraint.
        for d in db.scalars(select(Dispute)):
            d.started_at-=timedelta(hours=25);d.deadline-=timedelta(hours=25)


def defense_data(owner,did):
    with session() as db:
        d=db.get(Dispute,uuid.UUID(did));a=db.get(Account,d.account_id)
        r=db.scalar(select(Registration).where(Registration.account_id==a.id,Registration.user_id==a.owner_id,Registration.deleted_at.is_(None)))
        c=db.scalar(select(Character).where(Character.account_id==a.id))
        return dict(expected_dispute_version=d.version,selection=dict(registration_id=str(r.id),character_id=str(c.id),
            expected_registration_version=r.version,expected_ownership_revision=a.ownership_revision,
            expected_roster_revision=a.roster_revision,expected_lifecycle_revision=c.lifecycle_revision))


def test_new_claim_preview_discovery_replay_and_self_guard(client,environment):
    users,state=environment
    preview=client.post('/v2/game-accounts/preview',headers=users[0],json={'character_name':'examplehero'})
    assert preview.status_code==200 and preview.json()['ownership_context']['relation']=='unverified'
    p=start(client,users[0]);listed=client.get(VERIFY,headers=users[0]).json()
    assert listed['items'][0]['verification_id']==p['verification_id']
    assert client.get(VERIFY+'/'+p['verification_id'],headers=users[1]).status_code==404
    state['removed']=p['required_slots'];key=uuid.uuid4();r=confirm(client,users[0],p,key)
    assert r.status_code==200 and r.json()['ownership_outcome']=='verified'
    calls=len(state['calls']);assert confirm(client,users[0],p,key).json()==r.json()
    assert len(state['calls'])==calls
    assert client.get(VERIFY,headers=users[0]).json()['items']==[]
    state['removed']=()
    calls=len(state['calls'])
    again=change(client,users[0],'post',VERIFY,{'source':'direct_input','character_name':'EXAMPLEHERO'})
    assert again.status_code==409 and again.json()['error']['code']=='ALREADY_VERIFIED'
    assert state['calls'][calls:]==['siblings']


def test_three_disputes_one_defense_closes_all_and_fences_old_proof(client,environment):
    users,state=environment;claim_owner(client,environment)
    stale=start(client,users[4])
    proofs=[open_dispute(client,environment,i) for i in (1,2,3)]
    blocked=change(client,users[4],'post',VERIFY,{'source':'direct_input','character_name':'ExampleHero'})
    assert blocked.status_code==409 and blocked.json()['error']['code']=='DISPUTE_CAPACITY_REACHED'
    listed=client.get(DISPUTE,headers=users[0],params={'role':'owner'}).json()
    assert len(listed['items'])==3
    did=proofs[0]['dispute_id']
    data=defense_data(users[0],did)
    r=change(client,users[0],'post',DISPUTE+'/'+did+'/defenses',data)
    assert r.status_code==201,r.text
    p=r.json();state['removed']=p['required_slots'];result=confirm(client,users[0],p)
    assert result.status_code==200 and result.json()['ownership_outcome']=='defended',result.text
    state['removed']=stale['required_slots'];late=confirm(client,users[4],stale)
    assert late.status_code==200 and late.json()['equipment_status']=='invalidated'
    assert client.get(DISPUTE,headers=users[0]).json()['items']==[]
    with session() as db:
        assert set(db.scalars(select(Dispute.state)))=={'defended'}
        assert db.scalar(select(func.count()).select_from(Account))==1
        assert db.scalar(select(func.count()).select_from(Audit))==1
    # No separate repeat cooldown: a genuinely new baseline may start immediately.
    state['removed']=();assert start(client,users[1])['equipment_status']=='pending'


def test_fourth_inflight_equipment_pass_does_not_open_dispute(client,environment):
    users,state=environment;claim_owner(client,environment)
    fourth=start(client,users[4])
    for i in (1,2,3):open_dispute(client,environment,i)
    state['removed']=fourth['required_slots'];r=confirm(client,users[4],fourth)
    assert r.status_code==200 and r.json()['equipment_status']=='passed'
    assert r.json()['ownership_outcome']=='blocked' and r.json()['dispute_id'] is None
    with session() as db:assert db.scalar(select(func.count()).select_from(Dispute))==3


def test_worker_transfers_first_atomically_invalidates_others_and_is_idempotent(client,environment):
    users,state=environment;claim_owner(client,environment)
    first=open_dispute(client,environment,1);second=open_dispute(client,environment,2)
    with session() as db:
        before=db.scalar(select(Account));aid=before.id;old=before.owner_id
        ids=list(db.scalars(select(Character.id)))
    expire_all();ticket=worker.claim();assert ticket[0]==uuid.UUID(first['dispute_id'])
    worker.process(ticket);worker.process(ticket)
    with session() as db:
        a=db.get(Account,aid);assert a.owner_id!=old and a.ownership_revision==2
        assert list(db.scalars(select(Character.id)))==ids
        assert db.get(Dispute,uuid.UUID(first['dispute_id'])).state=='transferred'
        assert db.get(Dispute,uuid.UUID(second['dispute_id'])).state=='invalidated'
        assert db.scalar(select(func.count()).select_from(Audit))==2
        cfg=db.scalar(select(Configuration).where(Configuration.ended_at.is_(None)))
        assert cfg.user_id==a.owner_id and cfg.state=='unconfigured' and cfg.representative_id is None
    assert worker.claim() is None
    assert client.get(DISPUTE+'/'+first['dispute_id'],headers=users[1]).json()['my_registration_id']
    assert client.get(DISPUTE+'/'+first['dispute_id'],headers=users[3]).status_code==404


def test_settle_is_single_200_reservation_and_never_immediate_transfer(client,environment):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    did=p['dispute_id'];r=change(client,users[1],'post',DISPUTE+'/'+did+'/settle',{'expected_version':1})
    assert r.status_code==409
    expire_all();calls=len(state['calls'])
    r=change(client,users[1],'post',DISPUTE+'/'+did+'/settle',{'expected_version':1})
    assert r.status_code==200 and r.json()['state']=='defending' and r.json()['phase']=='settlement_due'
    assert len(state['calls'])==calls
    with session() as db:assert db.scalar(select(Account.ownership_revision))==1


def test_worker_failure_and_lost_lease_do_not_transfer(client,environment,monkeypatch):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    expire_all();ticket=worker.claim();original=worker.fetch
    monkeypatch.setattr(worker,'fetch',lambda did:(_ for _ in ()).throw(RuntimeError('private')))
    worker.process(ticket)
    with session() as db,db.begin():
        d=db.get(Dispute,ticket[0]);assert d.reason=='UPSTREAM_UNAVAILABLE' and d.next_retry_at
        d.next_retry_at=None
    monkeypatch.setattr(worker,'fetch',original)
    ticket=worker.claim()
    with session() as db,db.begin():db.get(Dispute,ticket[0]).lease_until=now(db)-timedelta(seconds=1)
    worker.process(ticket)
    with session() as db:assert db.scalar(select(Account.ownership_revision))==1


def test_expiry_and_cancel_do_not_create_disputes(client,environment):
    users,state=environment;claim_owner(client,environment);p=start(client,users[1]);pid=uuid.UUID(p['verification_id'])
    with session() as db,db.begin():
        proof=db.get(Proof,pid);proof.created_at-=timedelta(minutes=11);proof.expires_at-=timedelta(minutes=11)
    calls=len(state['calls']);r=confirm(client,users[1],p)
    assert r.status_code==200 and r.json()['equipment_status']=='expired'
    assert len(state['calls'])==calls
    fresh=start(client,users[1]);r=change(client,users[1],'post',VERIFY+'/'+fresh['verification_id']+'/cancel',{'expected_version':1})
    assert r.status_code==200 and r.json()['equipment_status']=='cancelled'
    with session() as db:assert db.scalar(select(func.count()).select_from(Dispute))==0


def test_other_member_cannot_defend_or_cancel_and_post_deadline_defense_is_blocked(client,environment):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    did=p['dispute_id'];data=defense_data(users[0],did)
    assert change(client,users[1],'post',DISPUTE+'/'+did+'/defenses',data).status_code==403
    assert change(client,users[0],'post',DISPUTE+'/'+did+'/cancel',{'expected_version':1}).status_code==403
    expire_all()
    assert change(client,users[0],'post',DISPUTE+'/'+did+'/defenses',data).json()['error']['code']=='DEFENSE_WINDOW_CLOSED'


@pytest.mark.parametrize('path', [VERIFY,DISPUTE])
def test_lists_strict_read_only_and_cursor(client,environment,path):
    users,state=environment;claim_owner(client,environment)
    for i in (1,2):open_dispute(client,environment,i)
    h=users[0] if path==DISPUTE else users[1]
    assert client.get(path,headers=h,params={'unknown':'x'}).status_code==400
    assert client.request('GET',path,headers=h,json={}).status_code==400
    assert client.get(path,headers=h,params={'cursor':''}).status_code==400
    response=client.get(path,headers=h,params={'limit':1,'view':'all'})
    assert response.status_code==200
    if path==DISPUTE:
        cursor=response.json()['next_cursor'];assert cursor
        assert client.get(path,headers=users[1],params={'limit':1,'view':'all','cursor':cursor}).status_code==400


def test_concurrent_four_equipment_successes_admit_three(client,environment,monkeypatch):
    from threading import Barrier
    from app.game_accounts import service as accounts
    users,state=environment;claim_owner(client,environment)
    proofs=[start(client,users[i]) for i in (1,2,3,4)]
    prepared={}
    for p in proofs:
        state['removed']=p['required_slots']
        prepared[p['verification_id']]=observations.fetch('ExampleHero',True,token='test-only-token')
    state['removed']=();barrier=Barrier(4)
    def lookup(*args,**kwargs):
        barrier.wait(timeout=15)
        return prepared[kwargs['context'][1]]
    monkeypatch.setattr(accounts,'lookup',lookup)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda i:confirm(client,users[i+1],proofs[i]),range(4)))
    assert all(r.status_code==200 for r in results)
    assert sorted(r.json()['ownership_outcome'] for r in results)==['blocked','dispute_opened','dispute_opened','dispute_opened']
    with session() as db:
        assert sorted(db.scalars(select(Dispute.slot)))==[1,2,3]


def test_defend_with_another_character_without_activity_or_level_filter(client,environment):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    state['extra_rows']=[dict(ServerName='sample-server',CharacterName='AltHero',CharacterClassName='sample-class',CharacterLevel=10,ItemAvgLevel='10')]
    rid=client.get(BASE,headers=users[0]).json()['items'][0]['registration_id']
    refreshed=change(client,users[0],'post',BASE+'/'+rid+'/refresh',{})
    assert refreshed.status_code==200,refreshed.text
    data=defense_data(users[0],p['dispute_id'])
    with session() as db:
        c=db.scalar(select(Character).where(Character.character_name=='AltHero'))
        data['selection']['character_id']=str(c.id);data['selection']['expected_lifecycle_revision']=c.lifecycle_revision
    state['profile_name']='AltHero'
    response=change(client,users[0],'post',DISPUTE+'/'+p['dispute_id']+'/defenses',data)
    assert response.status_code==201,response.text
    defense=response.json();assert defense['target']['character_name']=='AltHero'
    state['removed']=defense['required_slots'];result=confirm(client,users[0],defense)
    assert result.status_code==200 and result.json()['ownership_outcome']=='defended',result.text


def test_final_proof_deadline_rolls_back_dispute_creation(client,environment,monkeypatch):
    users,state=environment;claim_owner(client,environment);p=start(client,users[1]);state['removed']=p['required_slots']
    original=commands.confirm
    def crossing(db,uid,proof,obs,current):
        original(db,uid,proof,obs,current)
        monkeypatch.setattr(commands,'now',lambda db:proof.expires_at+timedelta(microseconds=1))
    monkeypatch.setattr(commands,'confirm',crossing)
    result=confirm(client,users[1],p)
    assert result.status_code==200 and result.json()['equipment_status']=='expired',result.text
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Dispute))==0
        assert db.scalar(select(Account.ownership_revision))==1


def test_worker_final_failure_rolls_back_owner_settings_events(client,environment,monkeypatch):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment);expire_all()
    ticket=worker.claim();original=worker.apply_transfer
    def crash(*args):
        original(*args)
        raise RuntimeError('simulated process interruption')
    monkeypatch.setattr(worker,'apply_transfer',crash)
    with pytest.raises(RuntimeError):worker.process(ticket)
    with session() as db:
        assert db.scalar(select(Account.ownership_revision))==1
        assert db.scalar(select(func.count()).select_from(Audit))==1
        assert db.get(Dispute,ticket[0]).state=='defending'
        assert db.scalar(select(func.count()).select_from(DisputeEvent))==1
    monkeypatch.setattr(worker,'apply_transfer',original)
    with session() as db,db.begin():db.get(Dispute,ticket[0]).lease_until=now(db)-timedelta(seconds=1)
    replacement=worker.claim();assert replacement[1]>ticket[1]
    worker.process(ticket)
    with session() as db:assert db.scalar(select(Account.ownership_revision))==1
    worker.process(replacement)
    with session() as db:assert db.scalar(select(Account.ownership_revision))==2


def test_deleted_source_registration_is_reviewed_not_resurrected(client,environment):
    users,state=environment;claim_owner(client,environment)
    reg=change(client,users[1],'post',BASE,dict(lookup_character_name='ExampleHero',label='sample',is_main=False)).json()
    payload=dict(source='registration',registration_id=reg['registration_id'],expected_registration_version=reg['version'],target_character=dict(server_name='sample-server',character_name='ExampleHero'))
    response=change(client,users[1],'post',VERIFY,payload);assert response.status_code==201,response.text
    p=response.json();state['removed']=p['required_slots'];result=confirm(client,users[1],p);state['removed']=()
    assert result.json()['ownership_outcome']=='dispute_opened'
    assert change(client,users[1],'delete',BASE+'/'+reg['registration_id']+'?expected_version='+str(reg['version'])).status_code==204
    expire_all();ticket=worker.claim();worker.process(ticket)
    with session() as db:
        assert db.scalar(select(Account.ownership_revision))==1
        d=db.get(Dispute,ticket[0]);assert d.state=='review_required' and d.reason=='REGISTRATION_REMOVED'
        assert db.get(Registration,uuid.UUID(reg['registration_id'])).deleted_at is not None


def test_transfer_preserves_old_private_data_and_group_membership_without_inheritance(client,environment):
    from app.game_accounts.models import CharacterRoleSummary,CharacterPersonalPreferences
    from app.groups.models import Group,GroupMembership
    from tests.test_game_accounts import page,save_data
    users,state=environment;claim_owner(client,environment)
    r=client.get(BASE,headers=users[0]).json()['items'][0]
    original=page(client,users[0],r['registration_id']);save=save_data(original)
    assert change(client,users[0],'put',BASE+'/'+r['registration_id']+'/character-settings',save).status_code==200
    original=page(client,users[0],r['registration_id']);old_save=save_data(original)
    gid=uuid.uuid4();mid=uuid.uuid4()
    with session() as db,db.begin():
        a=db.scalar(select(Account));c=db.scalar(select(Character));cid=c.id;old=a.owner_id;stamp=now(db)
        db.add(CharacterRoleSummary(user_id=old,character_id=cid,ownership_revision=1,role='dealer',version=1,summary={'private':'old'},saved_at=stamp))
        db.add(CharacterPersonalPreferences(user_id=old,character_id=cid,ownership_revision=1,preferred_role='dealer',visible=False,display_order=3,version=1,saved_at=stamp))
        db.add(Group(id=gid,name='sample',leader_membership_id=mid,representative_character_id=cid,representative_user_id=old,representative_display=c.summary,created_at=stamp))
        db.flush()
        db.add(GroupMembership(id=mid,group_id=gid,user_id=old,character_id=cid,display=c.summary,joined_at=stamp))
    p=open_dispute(client,environment);expire_all();worker.process(worker.claim())
    profile=client.get('/v2/me/characters/'+str(cid)+'/personal-profile',headers=users[1])
    assert profile.status_code==200,profile.text
    assert profile.json()['dealer']['summary'] is None and profile.json()['preferences']['visible'] is True
    assert client.get('/v2/me/characters/'+str(cid)+'/personal-profile',headers=users[0]).status_code==403
    assert change(client,users[0],'put',BASE+'/'+r['registration_id']+'/character-settings',old_save).status_code==403
    with session() as db:
        assert db.get(CharacterRoleSummary,(old,cid,1,'dealer')).summary=={'private':'old'}
        assert db.get(GroupMembership,mid).user_id==old and db.get(GroupMembership,mid).ended_at is None
        assert db.get(Group,gid).leader_membership_id==mid and db.get(Group,gid).revision==2
    assert client.get('/v1/groups/'+str(gid)).json()['representative']['status']=='needs_update'


def test_registration_limit_retries_without_partial_ownership_and_without_new_24h(client,environment):
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    with session() as db,db.begin():
        d=db.get(Dispute,uuid.UUID(p['dispute_id']));uid=d.challenger_id;stamp=now(db)
        for i in range(20):
            db.add(Registration(user_id=uid,lookup_name=f'Unused{i}',label='sample',is_main=False,preview=[],fetched_at=stamp,created_at=stamp,updated_at=stamp))
    expire_all();ticket=worker.claim();worker.process(ticket)
    with session() as db,db.begin():
        d=db.get(Dispute,ticket[0]);start=d.started_at
        assert d.state=='defending' and d.reason=='REGISTRATION_LIMIT'
        assert db.scalar(select(Account.ownership_revision))==1
        r=db.scalar(select(Registration).where(Registration.user_id==uid));r.deleted_at=now(db);d.next_retry_at=None
    worker.process(worker.claim())
    with session() as db:
        d=db.get(Dispute,ticket[0]);assert d.state=='transferred' and d.started_at==start
        assert db.scalar(select(Account.ownership_revision))==2


def test_active_party_relation_blocks_unsafe_transfer_without_room_adapter(client,environment):
    from app.raid_weekly.models import WeeklyState
    from app.raids.service import cycle
    from datetime import date
    users,state=environment;claim_owner(client,environment);p=open_dispute(client,environment)
    with session() as db,db.begin():
        a=db.scalar(select(Account));c=db.scalar(select(Character));stamp=now(db)
        db.add(WeeklyState(user_id=a.owner_id,character_id=c.id,raid_id='sample-raid',cycle_key=date.fromisoformat(cycle(stamp).cycle_key),
            active_party_id=uuid.uuid4(),active_difficulty_id='normal',joined_at=stamp,updated_at=stamp))
    expire_all();ticket=worker.claim();worker.process(ticket)
    with session() as db:
        d=db.get(Dispute,ticket[0]);assert d.state=='review_required' and d.reason=='PARTY_IMPACT_REVIEW_REQUIRED'
        assert db.scalar(select(Account.ownership_revision))==1


def test_younger_due_dispute_never_bypasses_earlier_retry(client,environment,monkeypatch):
    users,state=environment;claim_owner(client,environment)
    one=open_dispute(client,environment,1);two=open_dispute(client,environment,2);expire_all()
    ticket=worker.claim();assert ticket[0]==uuid.UUID(one['dispute_id'])
    monkeypatch.setattr(worker,'fetch',lambda _:(_ for _ in ()).throw(RuntimeError('temporary')))
    worker.process(ticket)
    assert worker.claim() is None
    with session() as db:
        second=db.get(Dispute,uuid.UUID(two['dispute_id']))
        assert second.reason=='WAITING_FOR_EARLIER_DISPUTE'
        assert db.scalar(select(Account.ownership_revision))==1


def test_database_slot_constraint_rejects_a_fourth_active_row(client,environment):
    from sqlalchemy.exc import IntegrityError
    users,state=environment;claim_owner(client,environment)
    extra=start(client,users[4])
    for i in (1,2,3):open_dispute(client,environment,i)
    with session() as db,db.begin():
        first=db.scalar(select(Dispute));p=db.get(Proof,uuid.UUID(extra['verification_id']));stamp=now(db)
        with pytest.raises(IntegrityError),db.begin_nested():
            db.add(Dispute(account_id=first.account_id,owner_id=first.owner_id,challenger_id=p.actor_id,
                ownership_revision=first.ownership_revision,generation=first.generation,sequence=4,slot=4,proof_id=p.id,
                started_at=stamp,deadline=stamp+timedelta(hours=24)))
            db.flush()
        assert db.scalar(select(func.count()).select_from(Dispute))==3


def test_client_boolean_or_untyped_receipt_cannot_issue_v2_proof(client,environment,monkeypatch):
    from dataclasses import replace
    users,state=environment;original=observations.fetch
    def untyped(*args,**kwargs):
        return replace(original(*args,**kwargs),equipment_evidence=None,proof_validated=True)
    monkeypatch.setattr(observations,'fetch',untyped)
    response=change(client,users[0],'post',VERIFY,{'source':'direct_input','character_name':'ExampleHero'})
    assert response.status_code==503
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Proof))==0
        assert db.scalar(select(func.count()).select_from(Account))==0
