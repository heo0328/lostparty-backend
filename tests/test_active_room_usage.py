"""Accepted Issue13/171 quota boundaries against disposable PostgreSQL only."""
import uuid
from datetime import date,datetime,time,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.member_limits.models import MemberUsageHead
from app.raid_rooms import active_usage,participation_core,beta_profile,cycle_lists,membership_readers,cycle_creation
from app.raid_rooms.integrated_models import RecruitmentRoom,RecruitmentMembership
from app.raid_rooms.cycle_models import RoomCycle,CycleMember
from tests.test_beta_recruitment import (beta,current,candidate,ready,sources,imported,people,worlds,
    create_beta,beta_join,actor,cycle_commands,context,admission_request,beta_schemas)
from tests.test_membership_actions import run
from tests.test_recruitment_cycle_commands import decision


def seeds(uid,count,key=None):
    result=[]
    with session() as db,db.begin():
        stamp=now(db)
        if key is None:
            from app.raids.service import cycle
            key=date.fromisoformat(cycle(stamp).cycle_key)
        for _ in range(count):
            rid,mid,cid=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
            db.add(RecruitmentRoom(id=rid,leader_membership_id=mid,title='synthetic active review',scope='public',
                group_id=None,app_capacity=4,revision=1,members_revision=1,plan_revision=1,migration_state='ready',created_at=stamp))
            db.flush()  # leader FK is deferred; membership->room FK is immediate.
            db.add(RecruitmentMembership(id=mid,room_id=rid,user_id=uid,revision=1,joined_at=stamp))
            db.flush()
            db.add(RoomCycle(id=cid,room_id=rid,cycle_key=key,state='review_required',generation=None,revision=1,
                settings_revision=1,members_revision=1,plan_revision=1,settings_snapshot=None,provenance='legacy_unknown',created_at=stamp))
            db.flush()
            db.add(CycleMember(id=uuid.uuid4(),room_id=rid,cycle_id=cid,generation=None,membership_id=mid,
                user_id=uid,state='review_required',revision=1))
            result.append((rid,mid,cid))
    return result


def count(uid):
    with session() as db:return participation_core.room_count(db,uid)


def revision(uid):
    with session() as db:
        head=db.get(MemberUsageHead,uid);return head.revision if head else 1


def test_current_review_and_old_relations_match_both_lists_without_data_cleanup(beta):
    _,a,b=beta;uid=a['uid'];seed=seeds(uid,2)
    with session() as db:
        key=db.get(RoomCycle,seed[0][2]).cycle_key
    old=seeds(uid,7,key-timedelta(days=7))
    assert count(uid)==2
    from app.member_limits.service import get
    assert get(actor(uid))['usage']['raid_rooms']['used']==2
    for reader in [cycle_lists,membership_readers]:
        with beta_profile.using():value=reader.memberships(actor(uid),key.isoformat(),'current',50)
        assert len(value['data']['items'])==2
    with session() as db,db.begin():
        db.get(RecruitmentMembership,seed[0][1]).ended_at=now(db)
    assert count(uid)==1
    with session() as db:
        assert all(db.get(RecruitmentMembership,mid).ended_at is None for _,mid,_ in old)
        db.info['active_usage_stamp']=datetime.combine(key+timedelta(days=7),time(12),timezone.utc)
        assert active_usage.count(db,uid)==0


def test_nine_to_ten_combined_create_and_original_ack_do_not_double_charge(beta):
    _,a,b=beta;seeds(a['uid'],9);assert count(a['uid'])==9
    rid,key,_,body,command=create_beta(a,combined=True)
    assert count(a['uid'])==10
    before=revision(a['uid'])
    with beta_profile.using():
        data=beta_schemas.BetaCreateRequest.model_validate(body)
        assert cycle_creation.create(actor(a['uid']),command,data)[0]==201
    assert count(a['uid'])==10 and revision(a['uid'])==before
    with pytest.raises(GameError,match='MEMBER_RAID_LIMIT_REACHED'):create_beta(a)


def test_existing_relationship_outside_usage_cannot_bypass_limit_and_leaving_releases(beta):
    _,a,b=beta;rid,key,_,_,_=create_beta(a);rows=seeds(b['uid'],10)
    with session() as db,db.begin():
        db.add(RecruitmentMembership(id=uuid.uuid4(),room_id=rid,user_id=b['uid'],revision=1,joined_at=now(db)))
    with pytest.raises(GameError,match='MEMBER_RAID_LIMIT_REACHED'):beta_join(b,rid,key)
    with session() as db,db.begin():db.get(RecruitmentMembership,rows[0][1]).ended_at=now(db)
    oldrev=revision(b['uid']);assert beta_join(b,rid,key)[0]==200
    assert count(b['uid'])==10 and revision(b['uid'])==oldrev+1
    with beta_profile.using():run(b,rid,key,'leave_all')
    assert count(b['uid'])==9


def test_same_room_opposite_cycle_does_not_use_another_slot(beta):
    _,a,b=beta;rid,c,_,_,_=create_beta(a,combined=True);n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    seeds(b['uid'],9);assert beta_join(b,rid,c)[0]==200
    assert count(b['uid'])==10
    assert beta_join(b,rid,n)[0]==200 and count(b['uid'])==10
    with beta_profile.using():run(b,rid,n,'leave_target')
    assert count(b['uid'])==10
    with beta_profile.using():run(b,rid,c,'leave_all')
    assert count(b['uid'])==9


def test_concurrent_approvals_only_fill_one_last_room_slot(beta,people):
    _,a,b=beta;d=people('quota-other-leader')
    r1,c,_,_,_=create_beta(a,mode='leader_only');r2,c2,_,_,_=create_beta(d,mode='leader_only')
    seeds(b['uid'],9);pending=[]
    for owner,rid,key in [(a,r1,c),(d,r2,c2)]:
        with beta_profile.using():
            req=admission_request(context(b,rid,key,'apply'))
            ack=cycle_commands.admit(actor(b['uid']),rid,uuid.uuid4(),req,applying=True)[1]['data']
            request=decision(ack,context(owner,rid,key,'apply'))
            pending.append((owner,uuid.UUID(ack['application_id']),request))
    assert count(b['uid'])==9
    def approve(args):
        owner,aid,request=args
        try:
            with beta_profile.using():return cycle_commands.process(actor(owner['uid']),aid,uuid.uuid4(),request)[0]
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(approve,pending))
    assert sum(type(v) is int and 200<=v<300 for v in results)==1,results
    assert count(b['uid'])==10


def test_concurrent_creations_cannot_both_take_the_last_slot(beta):
    _,a,b=beta;seeds(a['uid'],9)
    choices=[{**a,'ids':[cid,*[v for v in a['ids'] if v!=cid]]} for cid in a['ids'][:2]]
    def create(w):
        try:return create_beta(w)[0]
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,choices))
    assert sum(isinstance(v,uuid.UUID) for v in results)==1,results
    assert count(a['uid'])==10


def test_usage_failure_rolls_back_and_dissolve_updates_other_users_once(beta,monkeypatch):
    from app.raid_rooms import membership_actions
    from tests.test_membership_actions import menu,body
    from tests.test_recruitment_cycle_times import fingerprints
    engine,a,b=beta;rid,key,_,_,_=create_beta(a);beta_join(b,rid,key)
    with beta_profile.using():m=menu(a,rid,key)
    req=body(m,'dissolve_led_targets');command=uuid.uuid4();before=fingerprints(engine)
    original=active_usage.finish
    def fail_after_usage(db,snapshot):original(db,snapshot);raise RuntimeError('synthetic usage failure')
    monkeypatch.setattr(active_usage,'finish',fail_after_usage)
    with beta_profile.using(),pytest.raises(RuntimeError):membership_actions.execute(actor(a['uid']),rid,command,req)
    assert fingerprints(engine)==before and count(a['uid'])==count(b['uid'])==1
    monkeypatch.setattr(active_usage,'finish',original)
    with beta_profile.using():result=membership_actions.execute(actor(a['uid']),rid,command,req)
    assert count(a['uid'])==count(b['uid'])==0
    heads=(revision(a['uid']),revision(b['uid']))
    with beta_profile.using():assert membership_actions.execute(actor(a['uid']),rid,command,req)==result
    assert (revision(a['uid']),revision(b['uid']))==heads
