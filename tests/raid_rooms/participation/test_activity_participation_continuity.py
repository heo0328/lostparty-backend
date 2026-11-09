"""Synthetic existing-participation preservation, isolated PostgreSQL only."""
from datetime import date
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import select, inspect, delete

from app.core.database import session, now
from app.game_accounts.models import Activity, Character, Account, Registration, NameClaim
from app.game_accounts.support import lock
from app.raid_rooms.participation import cycle_lifecycle as life
from app.raid_rooms.common import cycle_worker
from app.raid_rooms.reads import cycle_member_reads as reads
from app.raid_rooms.participation import cycle_character, existing_participation, cycle_management, cycle_leadership
from app.raid_rooms.schedules import cycle_planning
from app.raid_rooms.cycle_models import RoomCycle, CycleMember, CycleGeneration
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from tests.raid_rooms.admissions.test_application_composition import current, candidate, ready, sources, imported, people, worlds
from tests.raid_rooms.admissions.test_recruitment_cycle_creation import preflight, request, creation, denied
from tests.raid_rooms.admissions.test_recruitment_cycle_commands import create_room, context, commands, admission_request, decision
from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import add_member, change_body, cancel_member
from tests.groups.test_group_foundation import actor
from tests.raid_rooms.common.test_raid_room_migrations import table_digests


def fingerprint(engine):
    return table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})


def off(w):
    with session() as db,db.begin():
        lock(db,'game-mutations-v1')
        db.execute(delete(Activity).where(Activity.character_id==uuid.UUID(w['ids'][0])))


@pytest.fixture
def joined(current):
    engine,a,b=current
    result=create_room(a,combined=True)
    rid=uuid.UUID(result['room_id'])
    c,n=[v['target_cycle_key'] for v in result['created_cycles']]
    add_member(b,rid,c);add_member(b,rid,n)
    return engine,a,b,rid,c,n


def qualify(rid,key,w):
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        cm=life.actual_member(db,row,w['uid'])
        return life.qualify(db,db.get(Room,rid),row,cm)


@pytest.mark.parametrize('who',['leader','member'])
def test_current_and_next_existing_reads_authority_and_worker_preserve(joined,who):
    engine,a,b,rid,c,n=joined
    before=[reads.detail(actor(a['uid']),rid,k)['data']['members'] for k in (c,n)]
    off(a if who=='leader' else b)
    before_db=fingerprint(engine)
    for i,key in enumerate((c,n)):
        assert reads.detail(actor(a['uid']),rid,key)['data']['members']==before[i]
        assert reads.plan(actor(b['uid']),rid,key)['data']['my_membership']
        qualify(rid,key,a);qualify(rid,key,b)
        assert cycle_management.get(actor(a['uid']),rid,key)
        if key == n:
            assert cycle_leadership.get_cancel(actor(b['uid']),rid,key)['data']['permission']['allowed']
    assert fingerprint(engine)==before_db
    cycle_worker.process_room(rid)
    assert fingerprint(engine)==before_db
    with session() as db:
        assert all(row.state=='open' for row in db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid)))


def test_eight_member_room_inactive_member_does_not_restrict_others(current,people):
    engine,a,b=current
    raid=next(r for r in commands.raids.catalog().raids if r.party_size==8)
    items=[commands.wire.BCreateTarget(raid_id=raid.raid_id,difficulty_id=raid.difficulties[0].difficulty_id,expected_weekly_revision=1)]
    ctx=creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',items,None,preflight(a)['data']['target_cycle_key'],False)
    result=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx))[1]['data']
    rid=uuid.UUID(result['room_id']);key=result['created_cycles'][0]['target_cycle_key']
    all_members=[a,b]+[people('continuity-eight-'+str(i)) for i in range(6)]
    for i,w in enumerate(all_members[1:],1):
        role='support' if i in (3,7) else 'dealer'
        if role=='support':
            with session() as db,db.begin():
                char=db.get(Character,uuid.UUID(w['ids'][0]));char.summary={**char.summary,'class_name':'바드'}
        commands.admit(actor(w['uid']),rid,uuid.uuid4(),admission_request(context(w,rid,key,role=role)))
    off(b)
    before=fingerprint(engine)
    cycle_worker.process_room(rid)
    assert fingerprint(engine)==before
    for w in all_members:
        detail=reads.detail(actor(w['uid']),rid,key)
        assert len(detail['data']['members'])==8
        assert all(m['status']=='valid' for m in detail['data']['members'])
        qualify(rid,key,w)


def test_a_to_active_b_change_preserves_original_key_and_opposite_cycle(joined):
    engine,a,b,rid,c,n=joined
    off(b)
    opposite=reads.plan(actor(b['uid']),rid,n)['data']['my_assignments']
    ctx=cycle_character.get(actor(b['uid']),rid,c,uuid.UUID(b['ids'][1]),'dealer')
    body=change_body(ctx,reads.plan(actor(b['uid']),rid,c));key=uuid.uuid4()
    result=cycle_character.execute(actor(b['uid']),rid,key,body)
    assert cycle_character.execute(actor(b['uid']),rid,key,body)==result
    assert reads.plan(actor(b['uid']),rid,n)['data']['my_assignments']==opposite
    denied('ACTIVITY_SELECTION_REQUIRED',cycle_character.get,actor(b['uid']),rid,c,uuid.UUID(b['ids'][0]),'dealer')


def test_inactive_new_creation_application_join_next_week_and_approval_rejected(current):
    _,a,b=current
    result=create_room(a,mode='leader_only');rid=uuid.UUID(result['room_id'])
    c,n=[x['target_cycle_key'] for x in result['created_cycles']]
    ctx=context(b,rid,c,'apply');body=admission_request(ctx)
    application=commands.admit(actor(b['uid']),rid,uuid.uuid4(),body,applying=True)[1]['data']
    approval=decision(application,context(a,rid,c,'apply'))
    off(b)
    for key in (c,n):
        denied('ACTIVITY_SELECTION_REQUIRED',context,b,rid,key,'join')
        denied('ACTIVITY_SELECTION_REQUIRED',context,b,rid,key,'apply')
    denied('ACTIVITY_SELECTION_REQUIRED',preflight,b)
    denied('ACTIVITY_SELECTION_REQUIRED',commands.process,actor(a['uid']),uuid.UUID(application['application_id']),uuid.uuid4(),approval)
    denied('ACTIVITY_SELECTION_REQUIRED',commands.admit,actor(b['uid']),rid,uuid.uuid4(),body,applying=True)


@pytest.mark.parametrize('kind,code',[
    ('owner','OWNERSHIP_REQUIRED'),('registration','CHARACTER_NOT_FOUND'),
    ('retired','CHARACTER_UNUSABLE'),('claim','IDENTITY_CONFLICT'),
    ('disabled','ROOM_TARGET_UNAVAILABLE'),('lifecycle_revision','OWNERSHIP_REQUIRED'),
    ('ownership_revision','OWNERSHIP_REQUIRED')])
def test_other_existing_qualification_guards_preserved(joined,kind,code):
    _,a,b,rid,c,n=joined;off(b)
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));account=db.get(Account,char.account_id)
        if kind=='owner':account.owner_id=None
        if kind=='registration':db.get(Registration,b['rid']).deleted_at=now(db)
        if kind=='retired':char.lifecycle_state='retired'
        if kind=='claim':db.delete(db.get(NameClaim,(char.server_name,char.character_name)))
        if kind=='disabled':db.get(life.User,b['uid']).status='disabled'
        if kind=='lifecycle_revision':char.lifecycle_revision+=1
        if kind=='ownership_revision':account.ownership_revision+=1
    denied(code,qualify,rid,c,b)


@pytest.mark.parametrize('kind',['user','membership','room','cycle','generation','removed'])
def test_existing_identity_cannot_be_forged(joined,kind):
    _,a,b,rid,c,n=joined
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        cm=life.actual_member(db,row,b['uid']);probe=SimpleNamespace(**cycle_planning.snapshot(cm))
        room=db.get(Room,rid)
        if kind=='user':probe.user_id=a['uid']
        if kind=='membership':probe.membership_id=uuid.uuid4()
        if kind=='room':room=SimpleNamespace(id=uuid.uuid4())
        if kind=='cycle':row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        if kind=='generation':row=SimpleNamespace(**{**cycle_planning.snapshot(row),'generation':row.generation+1})
        if kind=='removed':
            ended=now(db);cm.state='removed';cm.ended_at=ended
        denied('SOURCE_PARTICIPATION_REQUIRED',existing_participation.selection,db,room,row,probe)


def test_last_participant_departure_does_not_revive_target(current):
    _,a,b=current;result=create_room(a);rid=uuid.UUID(result['room_id'])
    n=result['created_cycles'][1]['target_cycle_key'];off(a)
    cancel_member(a,rid,n)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        assert row.state=='closed'
        assert db.get(CycleGeneration,(row.id,row.generation)).state=='cancelled'


def test_inactive_leader_and_member_schedule_confirmation_and_completion(current):
    from tests.raid_rooms.schedules.test_recruitment_cycle_times import scheduled, confirm
    from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import complete
    _,a,b=current
    rid,c,n=scheduled(a,bundle=False)
    add_member(b,rid,c);add_member(b,rid,n)
    off(a);off(b)
    assert confirm(b,rid,c)[0]==200
    assert cycle_leadership.get_transfer(actor(a['uid']),rid,n)['data']['permission']['allowed']
    assert complete(b,rid,c)[0]==200




def test_existing_review_is_not_automatically_repaired(joined):
    engine,a,b,rid,c,n=joined
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        row.state='review_required'
        db.get(CycleGeneration,(row.id,row.generation)).state='review_required'
    before=fingerprint(engine)
    cycle_worker.process_room(rid)
    assert fingerprint(engine)==before
