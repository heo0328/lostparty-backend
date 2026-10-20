"""R2-B transaction primitives with restricted LOGIN and fabricated identities."""
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select, text, inspect, func
from sqlalchemy.exc import IntegrityError
from app.core.database import session, now
from app.game_accounts.support import authorize, GameError
from app.game_accounts.models import CharacterRoleSummary, Character, Account
from app.game_accounts.power_success import capture
from app.member_limits.models import MemberUsageHead, MemberUsageLimits
from app.raid_rooms import participation_core as core, readiness
from app.raid_rooms.participation_commands import Selection, Target
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member, RecruitmentItem as Item, RecruitmentRound as Round, RecruitmentAssignment as Assignment
from app.raid_rooms.source_models import RoomSettings, SessionParticipation, TimeReservation
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from tests.test_recruitment_sources import sources, imported, people, worlds
from tests.test_group_foundation import actor
from tests.test_raid_room_migrations import table_digests
from tests.test_role_summaries import summary


@pytest.fixture
def ready(sources,people):
    target,*_=sources
    old=set(inspect(target).get_table_names())-{'alembic_version'}
    before=table_digests(target,old)
    out=subprocess.run(['alembic','upgrade','0023_recruitment_resume'],env={**os.environ,
        'DATABASE_URL':target.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert out.returncode==0,'Isolated weekly link migration failed'
    assert table_digests(target,old)==before
    a,b=people('r2b-a'),people('r2b-b')
    return target,a,b,sources


def make_room(a, *, bundle=False, capacity=4):
    with session() as db,db.begin():
        stamp=now(db);rid,mid=uuid.uuid4(),uuid.uuid4()
        db.add(Room(id=rid,leader_membership_id=mid,title='synthetic',scope='public',group_id=None,
            app_capacity=capacity,revision=1,members_revision=1,plan_revision=1,migration_state='ready',created_at=stamp))
        db.flush()  # Leader FK is deferred; membership's room FK is immediate.
        db.add(Member(id=mid,room_id=rid,user_id=a['uid'],revision=1,joined_at=stamp))
        db.flush()
        db.add(RoomSettings(room_id=rid,revision=1,continuation_revision=1,admission_mode='direct_join',
            experience_level=None,combat_input_mode='shared',dealer_min=None,support_min=None,
            continuation_enabled=False,auto_open_enabled=False,auto_open_effective_cycle=None))
        chosen=[r for r in raids.catalog().raids if r.raid_id==('kazeros_act4' if capacity==8 else 'horizon_cathedral')]
        if bundle:chosen += [r for r in raids.catalog().raids if r.raid_id=='kazeros_act4']
        for raid in chosen:
            difficulty=raid.difficulties[0]
            item=Item(id=uuid.uuid4(),room_id=rid,raid_id=raid.raid_id,revision=1,created_at=stamp)
            db.add(item);db.flush()
            db.add(Round(id=uuid.uuid4(),room_id=rid,item_id=item.id,cycle_key=raids.cycle(stamp).cycle_key,
                difficulty_id=difficulty.difficulty_id,catalog_version=raids.catalog().catalog_version,
                game_party_size=raid.party_size,revision=1,state='active',created_at=stamp))
        return rid


def selection(db,w,**updates):
    cid=uuid.UUID(w['ids'][0]);head=db.get(MemberUsageHead,w['uid']);limits=db.get(MemberUsageLimits,w['uid'])
    role=updates.get('selected_role','dealer')
    summary=db.get(CharacterRoleSummary,(w['uid'],cid,1,role))
    values=dict(registration_id=w['rid'],character_id=cid,selected_role=role,
        expected_registration_version=1,expected_ownership_revision=1,expected_roster_revision=1,
        expected_lifecycle_revision=1,expected_role_summary_version=summary.version if summary else 1,
        expected_limits_revision=limits.revision if limits else 1,expected_usage_revision=head.revision if head else 1)
    return Selection(**(values|updates))


def targets(db,w,rid,party=1):
    result=[]
    for item,round in db.execute(select(Item,Round).join(Round,Round.item_id==Item.id).where(Item.room_id==rid,Round.state=='active')):
        state=db.get(WeeklyState,(w['uid'],uuid.UUID(w['ids'][0]),item.raid_id,round.cycle_key))
        result.append(Target(item_id=item.id,round_id=round.id,party_no=party,
            expected_round_revision=round.revision,expected_weekly_revision=state.revision if state else 1))
    return result


def admit(w,rid,**updates):
    party=updates.pop('party',1)
    with session() as db,db.begin():
        authorize(db,actor(w['uid']),write=True)
        room=db.get(Room,rid)
        member,rows,power=core.admit_bundle(db,w['uid'],room,selection(db,w,**updates),targets(db,w,rid,party),raids.cycle(now(db)).cycle_key)
        return member.id,[r.id for r in rows],power


def denied(code,fn,*args,**kwargs):
    with pytest.raises(GameError) as error:fn(*args,**kwargs)
    assert error.value.code==code


def test_additive_migration_readiness_and_legacy_dedup(ready):
    target,a,b,source=ready
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        readiness.require_ready(db,integrated=True)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy))==0
        assert core.room_count(db,source[4]['uid'])==2
    with session() as db,db.begin():
        stamp=now(db)
        for member in db.scalars(select(Member).where(Member.room_id==source[1],Member.user_id==source[4]['uid'])):
            member.ended_at=stamp
        db.flush()
        assert core.room_count(db,source[4]['uid'])==1


def test_unscheduled_bundle_membership_assignments_and_ledger(ready):
    target,a,b,_=ready;rid=make_room(a,bundle=True)
    mid,ids,power=admit(a,rid)
    assert len(ids)==2 and power['state']=='unrestricted'
    with session() as db:
        assert core.room_count(db,a['uid'])==1
        for row in db.scalars(select(Assignment).where(Assignment.id.in_(ids))):
            assert row.membership_id==mid and row.party_no==row.slot_no==1
            item=db.get(Item,row.item_id);round=db.get(Round,row.round_id)
            key=(a['uid'],row.character_id,item.raid_id,round.cycle_key)
            assert db.get(WeeklyOccupancy,key).assignment_id==row.id
            assert db.get(WeeklyState,key).active_party_id==rid
        assert db.scalar(select(func.count()).select_from(SessionParticipation))==0
        assert db.scalar(select(func.count()).select_from(TimeReservation))==0
    _,peer,_=admit(b,rid)
    with session() as db:assert {r.slot_no for r in db.scalars(select(Assignment).where(Assignment.id.in_(peer)))}=={2}


def test_partial_bundle_stale_versions_and_rollback(ready):
    target,a,b,_=ready;rid=make_room(a,bundle=True)
    with session() as db,db.begin():
        authorize(db,actor(b['uid']),write=True)
        with pytest.raises(GameError) as error:
            core.admit_bundle(db,b['uid'],db.get(Room,rid),selection(db,b),targets(db,b,rid)[:1],raids.cycle(now(db)).cycle_key)
        assert error.value.code=='ROOM_ITEMS_CHANGED'
    before=table_digests(target,{'recruitment_memberships','recruitment_assignments','raid_weekly_states','recruitment_weekly_occupancies'})
    with pytest.raises(RuntimeError),session() as db,db.begin():
        authorize(db,actor(b['uid']),write=True)
        core.admit_bundle(db,b['uid'],db.get(Room,rid),selection(db,b),targets(db,b,rid),raids.cycle(now(db)).cycle_key)
        raise RuntimeError('synthetic post-write failure')
    assert table_digests(target,set(before))==before
    denied('REVISION_CONFLICT',admit,b,rid,expected_lifecycle_revision=2)
    assert table_digests(target,set(before))==before


def test_exact_release_keeps_membership_and_old_release_preserves_new_room(ready):
    target,a,b,_=ready;first=make_room(a);mid,ids,_=admit(b,first)
    with session() as db,db.begin():
        authorize(db,actor(b['uid']),write=True)
        row=db.get(Assignment,ids[0]);stamp=now(db)
        assert core.release_assignment(db,row,stamp)
        db.flush()
        assert db.get(Member,mid).ended_at is None
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy))==0
    second=make_room(a);_,newids,_=admit(b,second)
    with session() as db,db.begin():
        authorize(db,actor(b['uid']),write=True)
        stamp=now(db);old=db.get(Assignment,ids[0])
        assert not core.release_assignment(db,old,stamp)
        current=db.get(Assignment,newids[0]);item=db.get(Item,current.item_id);round=db.get(Round,current.round_id)
        key=(b['uid'],current.character_id,item.raid_id,round.cycle_key)
        assert db.get(WeeklyOccupancy,key).assignment_id==current.id
        assert db.get(WeeklyState,key).active_party_id==second


def test_same_character_weekly_conflict_and_concurrent_winner(ready):
    target,a,b,_=ready;one,two=make_room(a),make_room(a)
    def attempt(rid):
        try:admit(b,rid);return 'ok'
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt,[one,two]))==['WEEKLY_ALREADY_PARTICIPATING','ok']


def write_power(w,role,value,observed,version=2):
    with session() as db,db.begin():
        payload=summary();payload.update(combat_power=value,combat_power_observed_at=observed if value else None,
            integrity_status='review',issues=[dict(code='SOURCE_UNAVAILABLE',severity='warning')])
        row=db.get(CharacterRoleSummary,(w['uid'],uuid.UUID(w['ids'][0]),1,role))
        stamp=now(db)
        if row is None:
            row=CharacterRoleSummary(user_id=w['uid'],character_id=uuid.UUID(w['ids'][0]),ownership_revision=1,role=role)
            db.add(row)
        row.version=version;row.summary=payload;row.saved_at=stamp
        db.flush();capture(db,row)


def test_precise_latest_success_not_max_or_other_role_and_null_retention(ready):
    target,a,b,_=ready;rid=make_room(a)
    with session() as db:
        assert core.power_comparison(db,b['uid'],selection(db,b),'100')['state']=='missing'
    write_power(b,'dealer','100.000000000000000000000000001','2026-10-15T10:00:00Z')
    write_power(b,'dealer','99.999999999999999999999999999','2026-10-16T10:00:00Z',3)
    write_power(b,'support','99999','2026-10-16T10:00:00Z')
    write_power(b,'dealer',None,None,4)
    with session() as db,db.begin():
        settings=db.get(RoomSettings,rid);settings.dealer_min=settings.support_min='100'
    denied('COMBAT_POWER_REQUIRED',admit,b,rid)
    denied('REVISION_CONFLICT',admit,b,rid,expected_role_summary_version=3)
    with session() as db,db.begin():
        result=core.power_comparison(db,b['uid'],selection(db,b),'99.999999999999999999999999999')
        assert result['state']=='meets' and result['current_summary_version']==4 and result['success_summary_version']==3
        assert result['power_revision']==3 and result['success_issues']
        db.get(RoomSettings,rid).dealer_min=db.get(RoomSettings,rid).support_min='99.999999999999999999999999999'
    _,ids,result=admit(b,rid)
    with session() as db:
        saved=db.get(Assignment,ids[0]).build
        assert saved['actual']=='99.999999999999999999999999999' and saved['success_summary']['issues']


def test_composition_and_verified_activity_guards(ready,people):
    target,a,b,_=ready;rid=make_room(a)
    admit(a,rid,selected_role='support')
    denied('ROOM_COMPOSITION_CONFLICT',admit,b,rid,selected_role='support')
    denied('ACTIVITY_SELECTION_REQUIRED',admit,b,rid,character_id=uuid.UUID(b['ids'][2]))
    with session() as db,db.begin():db.get(Account,b['aid']).owner_id=None
    denied('OWNERSHIP_REQUIRED',admit,b,rid)


def test_foreign_key_rejects_wrong_weekly_owner(ready):
    target,a,b,_=ready;rid=make_room(a);_,ids,_=admit(b,rid)
    with session() as db,db.begin():
        row=db.scalar(select(WeeklyOccupancy).where(WeeklyOccupancy.assignment_id==ids[0]))
        # Even a valid existing next-week ledger key cannot rebind this round.
        db.add(WeeklyState(user_id=row.user_id,character_id=row.character_id,raid_id=row.raid_id,
            cycle_key=row.cycle_key+timedelta(days=7),revision=1,updated_at=now(db)))
        db.flush()
        with pytest.raises(IntegrityError),db.begin_nested():
            db.execute(text('UPDATE recruitment_weekly_occupancies SET cycle_key=cycle_key+7 WHERE assignment_id=:id'),dict(id=row.assignment_id))


def test_group_scope_admission_independent_of_public_link(ready):
    target,a,b,source=ready;rid=make_room(a)
    with session() as db,db.begin():
        room=db.get(Room,rid);room.group_id=source[6];room.scope='group'
    denied('GROUP_MEMBERSHIP_REQUIRED',admit,b,rid)
    with session() as db,db.begin():db.get(Room,rid).scope='public'
    assert admit(b,rid)[1]


def test_limit_and_existing_member_restrictions_are_atomic(ready):
    target,a,b,_=ready;rid=make_room(a)
    with session() as db,db.begin():
        db.add(MemberUsageLimits(user_id=b['uid'],revision=1,group_capacity=15,joined_groups=5,raid_rooms=0,updated_at=now(db)))
    denied('MEMBER_RAID_LIMIT_REACHED',admit,b,rid)
    with session() as db,db.begin():
        db.get(MemberUsageLimits,b['uid']).raid_rooms=1
        db.add(MemberUsageLimits(user_id=a['uid'],revision=1,group_capacity=15,joined_groups=5,raid_rooms=0,updated_at=now(db)))
    denied('ROOM_RESTRICTED',admit,b,rid)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy))==0
        assert db.scalar(select(Member.id).where(Member.room_id==rid,Member.user_id==b['uid'])) is None


def test_completed_item_blocks_entire_bundle_without_partial_writes(ready):
    target,a,b,_=ready;rid=make_room(a,bundle=True)
    with session() as db,db.begin():
        stamp=now(db);rows=targets(db,b,rid);item=db.get(Item,rows[-1].item_id);round=db.get(Round,rows[-1].round_id)
        db.add(WeeklyState(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),raid_id=item.raid_id,
            cycle_key=round.cycle_key,revision=2,manual_completed_at=stamp,updated_at=stamp))
    before=table_digests(target,{'recruitment_memberships','recruitment_assignments','raid_weekly_states','recruitment_weekly_occupancies'})
    denied('WEEKLY_ALREADY_COMPLETED',admit,b,rid)
    assert table_digests(target,set(before))==before


def test_single_eight_preserves_second_party_but_mixed_four_rejects_it(ready):
    target,a,b,_=ready;single=make_room(a,capacity=8)
    _,ids,_=admit(b,single,party=2)
    with session() as db:assert db.get(Assignment,ids[0]).party_no==2
    mixed=make_room(a,bundle=True)
    denied('ROOM_COMPOSITION_CONFLICT',admit,a,mixed,party=2)


def test_imported_assignment_without_proven_link_is_not_released(ready):
    target,a,b,source=ready
    before=table_digests(target,{'recruitment_assignments','raid_weekly_states'})
    with pytest.raises(GameError) as error,session() as db,db.begin():
        authorize(db,actor(source[4]['uid']),write=True)
        row=db.scalar(select(Assignment).where(Assignment.room_id==source[1],Assignment.user_id==source[4]['uid']))
        core.release_assignment(db,row,now(db))
    assert error.value.code=='WEEKLY_OCCUPANCY_CHANGED'
    assert table_digests(target,set(before))==before
