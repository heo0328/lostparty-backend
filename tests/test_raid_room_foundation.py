"""F1 internal transactions with real isolated PostgreSQL and fabricated identities."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from pydantic import ValidationError
from sqlalchemy import select, func, text, event
from sqlalchemy.exc import IntegrityError
from app.auth.models import User
from app.core.database import session, now, engine
from app.core.errors import AuthError
from app.game_accounts.models import Character, Account, RequestResult, CharacterRoleSummary
from app.game_accounts.support import fail
from app.groups import admission_core
from app.raid_rooms import core, service
from app.raid_rooms.models import Room, Round, Membership, Application, DirectoryHead, MemberHead
from app.raid_rooms.commands import Create, Schedule, Selection, Admission, Decision, Withdraw, MembershipCAS, Transfer
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from app.member_limits.models import MemberUsageLimits, MemberUsageHead
from app.member_limits.service import Limits
from tests.test_group_admissions import worlds
from tests.test_group_foundation import actor
from tests.test_member_limits import change

RAID = 'horizon_cathedral'


@pytest.fixture
def people(worlds):
    def make(subject):
        w = worlds(subject)
        with session() as db, db.begin():
            for i, cid in enumerate(w['ids']):
                c = db.get(Character, uuid.UUID(cid))
                c.summary = {**c.summary, 'class_name': subject+'-'+str(i)}
        return w
    return make


def selection(w, *, index=0, role='dealer', party=1, raid=RAID):
    cid = uuid.UUID(w['ids'][index])
    with session() as db:
        row = db.get(MemberUsageLimits, w['uid'])
        head = db.get(MemberUsageHead, w['uid'])
        weekly = db.get(WeeklyState, (w['uid'], cid, raid, core.weekly.parse_cycle(raids.cycle(now(db)).cycle_key)))
        return Selection(registration_id=w['rid'], character_id=cid, selected_role=role, party_no=party,
            expected_registration_version=1, expected_ownership_revision=1, expected_roster_revision=1,
            expected_lifecycle_revision=1, expected_role_summary_version=1,
            expected_weekly_revision=weekly.revision if weekly else 1,
            expected_limits_revision=row.revision if row else 1, expected_usage_revision=head.revision if head else 1)


def create_command(w, *, mode='direct_join', offset=0, **updates):
    with session() as db:
        stamp=now(db);cycle=raids.cycle(stamp)
    data=dict(title='test-room', raid_id=RAID, difficulty_id='stage1',
        expected_catalog_version=raids.catalog().catalog_version, expected_cycle_key=cycle.cycle_key,
        scope='public', group_id=None, admission_mode=mode,
        schedule=Schedule(starts_at=stamp+timedelta(hours=1+offset), ends_at=stamp+timedelta(hours=2+offset)),
        selection=selection(w))
    data.update(updates)
    return Create(**data)


def explicit_test_policy(db, uid, room, round, data, character):
    # Explicit test policy, never selected by the server on an app caller's behalf.
    assert room.scope=='public' and data.character_id==character.id


def create(w, command=None, key=None):
    return service.create(actor(w['uid']), key or uuid.uuid4(), command or create_command(w), policy=explicit_test_policy)


def admission(w, rid, *, role='dealer', index=0, party=1):
    with session() as db:
        room=db.get(Room,rid);round=db.get(Round,room.round_id)
        return Admission(selection=selection(w,role=role,index=index,party=party,raid=round.raid_id),
            expected_room_revision=room.revision, expected_round_revision=round.revision,
            expected_members_revision=room.members_revision, expected_policy_snapshot=core.policy_snapshot(db,room),
            expected_cycle_key=round.cycle_key.isoformat(), expected_catalog_version=round.catalog_version)


def join(w, rid, data=None, key=None, applying=False):
    return service.admit(actor(w['uid']),rid,key or uuid.uuid4(),data or admission(w,rid),
                         applying=applying,policy=explicit_test_policy)


def membership_command(w,rid,target=None):
    with session() as db:
        room=db.get(Room,rid);round=db.get(Round,room.round_id);member=core.member(db,room,w['uid'])
        data=dict(expected_room_revision=room.revision,expected_round_id=round.id,expected_round_revision=round.revision,
            expected_members_revision=room.members_revision,expected_membership_id=member.id,
            expected_membership_revision=member.revision)
        if target:
            other=core.member(db,room,target['uid'])
            return Transfer(**data,target_membership_id=other.id,expected_target_membership_revision=other.revision)
        return MembershipCAS(**data)


def recover(w,rid,operation='leave',command=None,key=None):
    return service.recover(actor(w['uid']),rid,key or uuid.uuid4(),command or membership_command(w,rid),operation)


def decision(aid):
    with session() as db:
        row=db.get(Application,aid);room=db.get(Room,row.room_id);round=db.get(Round,room.round_id)
        return Decision(expected_application_revision=row.revision,expected_room_revision=room.revision,
            expected_round_revision=round.revision,expected_members_revision=room.members_revision,
            expected_policy_snapshot=core.policy_snapshot(db,room),expected_cycle_key=round.cycle_key.isoformat())


def denied(code, fn, *args, **kwargs):
    with pytest.raises(AuthError) as exc:fn(*args,**kwargs)
    assert exc.value.code==code


def snapshot(rid,uid):
    with session() as db:
        r=db.get(Room,rid);round=db.get(Round,r.round_id);head=db.get(MemberUsageHead,uid)
        return (r.revision,r.members_revision,round.revision,r.leader_membership_id,
                db.get(DirectoryHead,1).revision,head.revision if head else 1,
                db.scalar(select(func.count()).select_from(Membership).where(Membership.room_id==rid,Membership.ended_at.is_(None))))


def test_creation_links_room_slot_weekly_usage_and_idempotent_ack(people):
    a=people('a');data=create_command(a);key=uuid.uuid4()
    status,ack=create(a,data,key);rid=uuid.UUID(ack['room_id'])
    assert status==201 and create(a,data,key)==(status,ack)
    with session() as db:
        r=db.get(Room,rid);m=core.member(db,r,a['uid']);round=db.get(Round,r.round_id)
        state=db.get(WeeklyState,(a['uid'],m.character_id,RAID,round.cycle_key))
        assert state.active_party_id==rid and state.joined_at==m.joined_at
        assert state.revision==2 and core.room_count(db,a['uid'])==1
        assert db.get(MemberUsageHead,a['uid']).revision==2
        assert db.get(MemberHead,a['uid']).membership_revision==2
        assert r.creation_scope=='public' and r.creation_group_id is None


def test_missing_policy_cannot_create_or_admit(people):
    a=people('a');data=create_command(a)
    with pytest.raises(TypeError):service.create(actor(a['uid']),uuid.uuid4(),data,policy=None)
    with pytest.raises(TypeError):service.create(actor(a['uid']),uuid.uuid4(),data)
    with session() as db:assert db.scalar(select(func.count()).select_from(Room))==0


def test_last_slot_competition_has_one_winner(people):
    a,b,c,d,e=[people(s) for s in 'abcde'];rid=uuid.UUID(create(a)[1]['room_id'])
    join(b,rid);join(c,rid)
    commands=[admission(d,rid,role='support'),admission(e,rid,role='support')]
    def attempt(pair):
        w,data=pair
        try:return join(w,rid,data)[0]
        except AuthError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,zip((d,e),commands)))
    assert results.count(200)==1 and len(results)==2
    with session() as db:assert db.scalar(select(func.count()).select_from(Membership).where(Membership.room_id==rid))==4


def test_composition_duplicate_class_and_support_caps(people):
    a,b,c=[people(s) for s in 'abc'];rid=uuid.UUID(create(a)[1]['room_id'])
    with session() as db,db.begin():
        first=db.get(Character,uuid.UUID(a['ids'][0]));other=db.get(Character,uuid.UUID(b['ids'][0]));other.summary={**other.summary,'class_name':first.summary['class_name']}
    denied('ROOM_COMPOSITION_CONFLICT',join,b,rid)
    join(b,rid,admission(b,rid,role='support'))
    denied('ROOM_COMPOSITION_CONFLICT',join,c,rid,admission(c,rid,role='support'))


def test_time_overlap_across_characters_and_adjacent_schedule(people):
    a=people('a');rid=uuid.UUID(create(a)[1]['room_id'])
    data=create_command(a,selection=selection(a,index=1))
    denied('SCHEDULE_CONFLICT',create,a,data)
    with session() as db:
        r=db.get(Round,db.get(Room,rid).round_id);start=r.ends_at
    second=data.model_copy(update={'schedule':Schedule(starts_at=start,ends_at=start+timedelta(hours=1))})
    assert create(a,second)[0]==201


def test_weekly_occupancy_and_completion_guard(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id'])
    denied('WEEKLY_ALREADY_PARTICIPATING',create,a,create_command(a,offset=3))
    with session() as db,db.begin():
        cycle=core.weekly.parse_cycle(raids.cycle(now(db)).cycle_key)
        db.add(WeeklyState(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),raid_id=RAID,
            cycle_key=cycle,revision=1,manual_completed_at=now(db),manual_difficulty_id='stage1',updated_at=now(db)))
    denied('WEEKLY_ALREADY_COMPLETED',join,b,rid)


def test_pending_not_reservation_and_approve_rechecks_activity(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id'])
    with session() as db:
        assert core.room_count(db,b['uid'])==0 and db.get(MemberUsageHead,b['uid']) is None
    with session() as db,db.begin():db.execute(text('DELETE FROM activity_characters WHERE settings_id=:id'),{'id':b['cid']})
    denied('ACTIVITY_SELECTION_REQUIRED',service.decide,actor(a['uid']),aid,uuid.uuid4(),decision(aid),approve=True,policy=explicit_test_policy)
    assert service.application(actor(b['uid']),aid)['state']=='pending'


def test_approval_ack_is_not_targets_private_state(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);data=decision(aid);key=uuid.uuid4()
    result=service.decide(actor(a['uid']),aid,key,data,approve=True,policy=explicit_test_policy)
    assert result[0]==200 and result[1]['actor_membership_id']!=result[1]['affected_membership_id']
    assert service.decide(actor(a['uid']),aid,key,data,approve=True,policy=explicit_test_policy)==result
    assert str(b['uid']) not in str(result)


def test_ack_failure_rolls_back_slot_weekly_usage_and_relation(people,monkeypatch):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);before=snapshot(rid,b['uid']);data=decision(aid);key=uuid.uuid4()
    original=service.commit_result
    def crash(*args):raise RuntimeError('injected ACK failure')
    monkeypatch.setattr(service,'commit_result',crash)
    with pytest.raises(RuntimeError):service.decide(actor(a['uid']),aid,key,data,approve=True,policy=explicit_test_policy)
    assert snapshot(rid,b['uid'])==before and service.application(actor(b['uid']),aid)['state']=='pending'
    monkeypatch.setattr(service,'commit_result',original)
    assert service.decide(actor(a['uid']),aid,key,data,approve=True,policy=explicit_test_policy)[0]==200


def test_rejoin_old_leave_ack_does_not_end_new_membership(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id']);join(b,rid)
    data=membership_command(b,rid);key=uuid.uuid4();left=recover(b,rid,command=data,key=key)
    new=join(b,rid)[1]['actor_membership_id'];before=snapshot(rid,b['uid'])
    assert new!=str(data.expected_membership_id) and recover(b,rid,command=data,key=key)==left
    assert snapshot(rid,b['uid'])==before
    fresh=membership_command(b,rid).model_copy(update={'expected_membership_id':data.expected_membership_id})
    denied('REVISION_CONFLICT',recover,b,rid,command=fresh)


def test_transfer_leave_and_last_end_survive_character_loss_and_limits(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id']);join(b,rid)
    change(a['uid'],Limits(15,5,0))
    with session() as db,db.begin():db.get(Account,a['aid']).owner_id=None
    recover(a,rid,'transfer',membership_command(a,rid,b))
    denied('ROOM_LAST_MEMBER_REQUIRED',recover,b,rid,'end')
    recover(a,rid)
    data=membership_command(b,rid);key=uuid.uuid4();ended=recover(b,rid,'end',data,key)
    assert recover(b,rid,'end',data,key)==ended
    with session() as db:
        assert core.room_count(db,b['uid'])==0 and db.get(Room,rid).ended_at is not None
        round=db.get(Round,db.get(Room,rid).round_id)
        state=db.get(WeeklyState,(b['uid'],uuid.UUID(b['ids'][0]),RAID,round.cycle_key))
        assert state.active_party_id is None and state.manual_completed_at is None


def test_limits_exact_then_restricted_room_blocks_other_members_admission(people):
    a,b,c=[people(s) for s in 'abc'];change(a['uid'],Limits(15,5,1))
    rid=uuid.UUID(create(a)[1]['room_id']);join(b,rid)
    with session() as db:assert not core.issues(db,db.get(Room,rid))
    change(a['uid'],Limits(15,5,0),expected=2)
    denied('ROOM_RESTRICTED',join,c,rid)
    change(a['uid'],Limits(15,5,1),expected=3)
    assert join(c,rid)[0]==200


def test_get_and_expiration_have_zero_sql_writes(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id'])
    with session() as db,db.begin():
        row=db.get(Application,aid);row.created_at=now(db)-timedelta(hours=25);row.expires_at=now(db)-timedelta(hours=1)
    verbs=[]
    def track(conn,cursor,statement,*args):verbs.append(statement.lstrip().split()[0].upper())
    event.listen(engine(),'before_cursor_execute',track)
    try:
        assert service.get(actor(a['uid']),rid)['phase']=='current'
        assert service.application(actor(b['uid']),aid)['state']=='expired'
    finally:event.remove(engine(),'before_cursor_execute',track)
    assert set(verbs)=={'SELECT'}
    with session() as db:assert db.get(Application,aid).state=='pending'
    denied('APPLICATION_NOT_PENDING',service.decide,actor(a['uid']),aid,uuid.uuid4(),decision(aid),approve=True,policy=explicit_test_policy)


def test_unresolved_group_and_unknown_time_are_not_enabled(people):
    a=people('a')
    denied('ROOM_FEATURE_UNSUPPORTED',create,a,create_command(a,scope='group',group_id=uuid.uuid4()))
    denied('SCHEDULE_REVIEW_REQUIRED',create,a,create_command(a,schedule=Schedule(starts_at=None,ends_at=None)))


def test_db_current_user_slot_and_leader_fk_constraints(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id']);join(b,rid)
    with pytest.raises(IntegrityError):
        with session() as db,db.begin():
            old=core.member(db,db.get(Room,rid),b['uid']);first=core.member(db,db.get(Room,rid),a['uid'])
            old.slot_no=first.slot_no
    with pytest.raises(IntegrityError):
        with session() as db,db.begin():db.get(Room,rid).leader_membership_id=uuid.uuid4()


@pytest.mark.parametrize('value',[True,0,'1',1.5,None])
def test_strict_internal_versions(value,people):
    a=people('a');data=selection(a).model_dump();data['expected_usage_revision']=value
    with pytest.raises(ValidationError):Selection(**data)


def test_eight_person_party_limits_are_per_party(people):
    users=[people('u'+str(i)) for i in range(9)]
    rid=uuid.UUID(create(users[0],create_command(users[0],raid_id='kazeros_act4',difficulty_id='normal'))[1]['room_id'])
    for i in (1,2):join(users[i],rid,admission(users[i],rid))
    join(users[3],rid,admission(users[3],rid,role='support'))
    # Same dealer class may appear in the other four-person party.
    with session() as db,db.begin():
        a=db.get(Character,uuid.UUID(users[0]['ids'][0]));b=db.get(Character,uuid.UUID(users[4]['ids'][0]))
        b.summary={**b.summary,'class_name':a.summary['class_name']}
    for i in (4,5,6):join(users[i],rid,admission(users[i],rid,party=2))
    join(users[7],rid,admission(users[7],rid,role='support',party=2))
    denied('ROOM_FULL',join,users[8],rid,admission(users[8],rid,role='support',party=2))
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Membership).where(Membership.room_id==rid))==8


def test_two_rooms_concurrent_approve_same_character_never_double_occupy(people):
    a,b,c=[people(s) for s in 'abc']
    rooms=[uuid.UUID(create(w,create_command(w,mode='leader_only'))[1]['room_id']) for w in (a,b)]
    aids=[uuid.UUID(join(c,r,applying=True)[1]['application_id']) for r in rooms]
    commands=[decision(x) for x in aids]
    def approve(pair):
        w,aid,data=pair
        try:return service.decide(actor(w['uid']),aid,uuid.uuid4(),data,approve=True,policy=explicit_test_policy)[0]
        except AuthError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        out=list(pool.map(approve,zip((a,b),aids,commands)))
    assert out.count(200)==1
    with session() as db:
        assert core.room_count(db,c['uid'])==1
        assert db.scalar(select(func.count()).select_from(Application).where(Application.state=='pending'))==1


def test_final_cycle_change_rolls_back_creation_and_ack(people,monkeypatch):
    a=people('a');data=create_command(a);original=service.commit_result;original_now=service.now
    crossed=[]
    def commit(*args):
        result=original(*args);crossed.append(True);return result
    def clock(db):
        stamp=original_now(db)
        return raids.cycle(stamp).ends_at if crossed else stamp
    monkeypatch.setattr(service,'commit_result',commit)
    monkeypatch.setattr(service,'now',clock)
    denied('CYCLE_CHANGED',create,a,data)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room))==0
        assert db.scalar(select(func.count()).select_from(WeeklyState))==0
        assert db.get(MemberUsageHead,a['uid']) is None
        assert db.scalar(select(RequestResult.completed_at).where(RequestResult.operation=='room-core-create')) is None


def test_withdraw_final_expiry_rolls_back_state_and_heads(people,monkeypatch):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);data=Withdraw(expected_application_revision=1)
    with session() as db:expiry=db.get(Application,aid).expires_at
    original=service.commit_result;original_now=service.now;crossed=[]
    def commit(*args):
        result=original(*args);crossed.append(True);return result
    monkeypatch.setattr(service,'commit_result',commit)
    monkeypatch.setattr(service,'now',lambda db:expiry if crossed else original_now(db))
    denied('APPLICATION_NOT_PENDING',service.withdraw,actor(b['uid']),aid,uuid.uuid4(),data)
    with session() as db:
        assert db.get(Application,aid).state=='pending'
        assert db.get(MemberHead,b['uid']).application_revision==2


def test_reject_withdraw_authorization_and_historical_replay(people):
    a,b,c=[people(s) for s in 'abc'];rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);data=Withdraw(expected_application_revision=1);key=uuid.uuid4()
    denied('ROOM_APPLICATION_NOT_FOUND',service.withdraw,actor(c['uid']),aid,key,data)
    denied('ROOM_MEMBERSHIP_REQUIRED',service.decide,actor(c['uid']),aid,uuid.uuid4(),decision(aid))
    first=service.withdraw(actor(b['uid']),aid,key,data)
    assert service.withdraw(actor(b['uid']),aid,key,data)==first
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);cmd=decision(aid);key=uuid.uuid4()
    rejected=service.decide(actor(a['uid']),aid,key,cmd)
    assert rejected[1]['state']=='rejected'
    assert service.decide(actor(a['uid']),aid,key,cmd)==rejected


def test_wrong_actor_private_read_and_forged_application_sources(people):
    a,b,c=[people(s) for s in 'abc'];rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    denied('ROOM_MEMBERSHIP_REQUIRED',service.get,actor(c['uid']),rid)
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id'])
    denied('ROOM_MEMBERSHIP_REQUIRED',service.application,actor(c['uid']),aid)
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.lifecycle_revision+=1
    denied('APPLICATION_CONTEXT_CHANGED',service.decide,actor(a['uid']),aid,uuid.uuid4(),decision(aid),approve=True,policy=explicit_test_policy)
    # Lifecycle/ownership stale is never repaired by a fabricated display or a P1 number.
    with pytest.raises(ValidationError):
        Selection(**{**selection(c).model_dump(),'combat_power':'999999999'})


def test_ended_room_logically_cancels_pending_without_writing_it(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    aid=uuid.UUID(join(b,rid,applying=True)[1]['application_id']);recover(a,rid,'end')
    out=service.application(actor(b['uid']),aid)
    assert out['state']=='cancelled' and out['ended_at'] is not None
    with session() as db:assert db.get(Application,aid).state=='pending'


def test_stale_policy_snapshot_and_distinct_key_body_conflict(people):
    a,b=people('a'),people('b');data=create_command(a);key=uuid.uuid4();rid=uuid.UUID(create(a,data,key)[1]['room_id'])
    denied('IDEMPOTENCY_CONFLICT',create,a,data.model_copy(update={'title':'changed'}),key)
    cmd=admission(b,rid);change(a['uid'],Limits(15,5,20))
    denied('POLICY_CONTEXT_CHANGED',join,b,rid,cmd)


def test_end_membership_never_clears_unrelated_occupancy(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id']);join(b,rid)
    other=uuid.uuid4()
    with session() as db,db.begin():
        round=db.get(Round,db.get(Room,rid).round_id)
        row=db.get(WeeklyState,(b['uid'],uuid.UUID(b['ids'][0]),RAID,round.cycle_key));row.active_party_id=other
    recover(b,rid)
    with session() as db:
        row=db.get(WeeklyState,(b['uid'],uuid.UUID(b['ids'][0]),RAID,round.cycle_key))
        assert row.active_party_id==other


def test_p1_analysis_cannot_override_provider_entry_level(people):
    a,b=people('a'),people('b');rid=uuid.UUID(create(a)[1]['room_id'])
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(b['ids'][0]));c.summary={**c.summary,'item_level':'100'}
        db.add(CharacterRoleSummary(user_id=b['uid'],character_id=c.id,ownership_revision=1,
            role='dealer',version=1,summary={'source':'flutter_analysis','item_level':'9999'},saved_at=now(db)))
    denied('RAID_ITEM_LEVEL_REQUIRED',join,b,rid)


def test_api_contract_not_extended_by_internal_models():
    import json
    from pathlib import Path
    from app.main import app
    assert app.openapi()==json.loads(Path('openapi/openapi.yaml').read_text())
    assert all(getattr(route.endpoint,'__module__','')!='app.raid_rooms.router' for route in app.routes)


def test_limit_causes_do_not_spread_to_unrelated_rooms(people,client):
    from tests.test_group_admissions import group as make_group, apply as group_apply, action as group_action
    a,b=people('a'),people('b')
    gid=uuid.UUID(make_group(client,a))
    pending=group_apply(client,b,str(gid)).json()['relation_id']
    assert group_action(client,a,pending,'approve').status_code==200
    rooms=[uuid.UUID(create(w)[1]['room_id']) for w in (a,b)]
    with session() as db,db.begin():
        for rid in rooms:
            row=db.get(Room,rid);row.scope='group';row.group_id=gid
    # Fixture-only group rooms; no enabled group create/join adapter is claimed.
    change(b['uid'],Limits(15,0,10))
    with session() as db:
        assert not core.issues(db,db.get(Room,rooms[0]))
        assert {x['code'] for x in core.issues(db,db.get(Room,rooms[1]))}=={'MEMBER_GROUP_LIMIT_EXCEEDED'}
    change(a['uid'],Limits(1,5,10))
    with session() as db:
        assert {x['code'] for x in core.issues(db,db.get(Room,rooms[0]))}=={'GROUP_CAPACITY_EXCEEDED'}
        assert {x['code'] for x in core.issues(db,db.get(Room,rooms[1]))}=={'GROUP_CAPACITY_EXCEEDED','MEMBER_GROUP_LIMIT_EXCEEDED'}
    change(a['uid'],Limits(2,5,10),expected=2)
    change(b['uid'],Limits(15,5,0),expected=2)
    with session() as db:
        # Exact group capacity is normal; B's personal raid excess only follows B.
        assert not core.issues(db,db.get(Room,rooms[0]))
        assert {x['code'] for x in core.issues(db,db.get(Room,rooms[1]))}=={'MEMBER_RAID_LIMIT_EXCEEDED'}
