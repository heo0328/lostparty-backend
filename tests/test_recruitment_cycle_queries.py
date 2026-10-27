import uuid
from datetime import date
import pytest
from sqlalchemy import select, inspect
from app.core.database import session
from app.raid_rooms import cycle_queries as queries, cycle_wire as wire
from app.raid_rooms.cycle_models import RoomCycle
from tests.test_recruitment_cycle_creation import candidate, ready, sources, imported, people, worlds, preflight, request, denied
from tests.test_recruitment_cycle_commands import create_room, context, admission_request, commands
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor
from app.raid_rooms import cycle_member_reads as members
from tests.test_recruitment_cycle_lifecycle import lifecycle


def search_request(key,**updates):
    return wire.InputContract3PostV2RaidRoomsSearch.model_validate(dict(category='all',admission_scope=None,
        group_ids=[],filter_context_token=None,member_conditions=[],raid_ids=[],difficulty_ids=[],limit=20,
        cursor=None,target_cycle_key=key)|updates)


def test_directory_target_count_settings_and_readonly(candidate):
    engine,a,b=candidate
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    with session() as db,db.begin():
        target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        target.settings_snapshot=target.settings_snapshot|dict(experience_level='experienced')
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    for key,count,exp in ((c,1,None),(n,2,'experienced')):
        page=queries.search(None,search_request(key))
        card=page['data']['items'][0]
        assert card['app_member_count']==count and card['experience_level']==exp
        assert queries.get_card(actor(a['uid']),rid,key)['data']['leadership']['leader_cycle_member_id']==card['leadership']['leader_cycle_member_id']
        assert card['permissions']['view_detail']['allowed'] is False
        assert len(queries.search(None,search_request(key,remaining_slot_counts=[4-count]))['data']['items'])==1
        assert not queries.search(None,search_request(key,remaining_slot_counts=[4-count-1]))['data']['items']
    assert table_digests(engine,tables)==before


@pytest.mark.parametrize('invalid',[None,['experienced','experienced'],['unknown']])
def test_experience_filters_reject_null_duplicate_unknown(candidate,invalid):
    _,a,b=candidate;room=create_room(a);key=room['created_cycles'][0]['target_cycle_key']
    if invalid==['unknown']:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):search_request(key,experience_levels=invalid)
    else:denied('INVALID_REQUEST',queries.search,None,search_request(key,experience_levels=invalid))


def test_experience_or_matches_actual_null(candidate):
    _,a,b=candidate
    room=create_room(a);key=room['created_cycles'][0]['target_cycle_key']
    assert not queries.search(None,search_request(key,experience_levels=['experienced']))['data']['items']
    assert len(queries.search(None,search_request(key,experience_levels=['experienced','unrestricted']))['data']['items'])==1


def test_detail_and_plan_keep_target_assignments_and_formation(candidate):
    engine,a,b=candidate
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    assert members.detail(actor(b['uid']),rid,c)['data']['my_membership'] is None
    denied('ROOM_MEMBERSHIP_REQUIRED',members.plan,actor(b['uid']),rid,c)
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    detail=members.detail(actor(a['uid']),rid,c)
    assert len(detail['data']['members'])==1
    n_detail=members.detail(actor(a['uid']),rid,n)
    assert len(n_detail['data']['members'])==2
    assert sum(s['status']=='participating' for s in n_detail['data']['formation_slots'])==4
    assert sum(s['is_leader'] for s in n_detail['data']['formation_slots'])==2
    denied('WEEKLY_PARTICIPANT_REQUIRED',members.plan,actor(b['uid']),rid,c)
    for key,count in ((n,2),):
        plan=members.plan(actor(b['uid']),rid,key)['data']
        assert len(plan['my_assignments'])==count
        assert {v['target_cycle_key'] for v in plan['my_assignments']}==({key} if count else set())
        assert plan['my_target_role']==('member' if count else 'none')
    assert table_digests(engine,tables)==before


def test_cursor_normalization_and_target_directory_invalidation(candidate,people):
    _,a,b=candidate
    first=create_room(a);second=create_room(b,combined=False)
    third_room=create_room(people('w2-cursor-visible'),combined=False)
    rid=uuid.UUID(first['room_id']);c,n=[v['target_cycle_key'] for v in first['created_cycles']]
    conditions=dict(limit=1,experience_levels=['experienced','unrestricted'])
    page=queries.search(actor(a['uid']),search_request(c,**conditions))
    cursor=page['data']['next_cursor'];assert cursor
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    # N's mutation preserves C's directory and cursor. Valid OR order is immaterial.
    assert queries.search(actor(a['uid']),search_request(c,**(conditions|dict(experience_levels=['unrestricted','experienced'],cursor=cursor))))['data']['items']
    denied('INVALID_REQUEST',queries.search,actor(b['uid']),search_request(c,**(conditions|dict(cursor=cursor))))
    third=people('w2-cursor-third')
    commands.admit(actor(third['uid']),rid,uuid.uuid4(),admission_request(context(third,rid,c)))
    denied('CURSOR_STALE',queries.search,actor(a['uid']),search_request(c,**(conditions|dict(cursor=cursor))))


def test_group_visibility_and_character_sql_filter_use_actual_target(candidate,people):
    from app.groups.models import Group,GroupMembership
    from tests.test_group_foundation import create as group_create
    from app.core.database import now
    from app.raid_rooms import cycle_creation
    _,a,b=candidate
    gid=uuid.UUID(group_create(a)[1]['group']['group_id'])
    bid=uuid.uuid4()
    with session() as db,db.begin():
        db.add(GroupMembership(id=bid,group_id=gid,user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),
            display=None,revision=1,joined_at=now(db)))
        db.get(Group,gid).members_revision+=1
    created=cycle_creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,continuation=True,gid=gid),
        scope='group',group_id=str(gid)))[1]['data']
    rid=uuid.UUID(created['room_id']);c,n=[v['target_cycle_key'] for v in created['created_cycles']]
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    source=queries.filters.get_context(actor(a['uid']),[gid])
    ref=next(m['member_ref'] for m in source['members'] if any(v['group_membership_id']==bid for v in m['aliases']))
    conditions=dict(group_ids=[gid],filter_context_token=source['filter_context_token'],member_conditions=[
        dict(member_ref=ref,character_ids=[b['ids'][0]])])
    assert not queries.search(actor(a['uid']),search_request(c,**conditions))['data']['items']
    assert not queries.search(actor(a['uid']),search_request(n,**conditions))['data']['items']
    from app.raid_rooms import cycle_lists
    from tests.test_recruitment_cycle_http import validate
    for key,count in ((c,1),(n,2)):
        projected=cycle_lists.projections(actor(a['uid']),gid,[rid],key,source['filter_context_token'])
        assert len(projected['data']['rooms'][0]['members'])==count
        assert all(v['target_cycle_key']==key for v in projected['data']['rooms'][0]['members'])
        validate('/v2/groups/{group_id}/raid-room-member-projections','get',200,projected)
    outsider=people('w2-private-outsider')
    denied('ROOM_NOT_FOUND',queries.get_card,actor(outsider['uid']),rid,n)
    with session() as db,db.begin():
        db.get(GroupMembership,bid).ended_at=now(db);db.get(Group,gid).members_revision+=1
    denied('FILTER_CONTEXT_STALE',queries.search,actor(a['uid']),search_request(n,**conditions))


def target_id(db,rid,key):
    return db.scalar(select(RoomCycle.id).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))


def test_own_target_exclusion_opposite_and_reappearance(lifecycle):
    from app.raid_rooms import cycle_leadership
    _,a,b=lifecycle
    created=create_room(a);rid=uuid.UUID(created['room_id']);c,n=[v['target_cycle_key'] for v in created['created_cycles']]
    for key in (c,n):
        assert not queries.search(actor(a['uid']),search_request(key))['data']['items']
        assert len(queries.search(actor(b['uid']),search_request(key))['data']['items'])==1
        assert len(queries.search(None,search_request(key))['data']['items'])==1
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    assert len(queries.search(actor(b['uid']),search_request(c))['data']['items'])==1
    assert not queries.search(actor(b['uid']),search_request(n))['data']['items']
    cancel=cycle_leadership.get_cancel(actor(b['uid']),rid,n)
    from tests.test_recruitment_cycle_lifecycle import cancel_body
    cycle_leadership.cancel(actor(b['uid']),rid,uuid.uuid4(),cancel_body(cancel))
    assert len(queries.search(actor(b['uid']),search_request(n))['data']['items'])==1
    assert queries.get_card(actor(a['uid']),rid,n)['data']['my_target_role']=='leader'


def test_exclusion_before_limit_and_old_cursor_stale(candidate,people,monkeypatch):
    _,a,b=candidate
    own=create_room(a);visible=create_room(b,combined=False)
    other=create_room(people('own-search-page2'),combined=False)
    key=own['created_cycles'][0]['target_cycle_key']
    first=queries.search(actor(a['uid']),search_request(key,limit=1))['data']
    second=queries.search(actor(a['uid']),search_request(key,limit=1,cursor=first['next_cursor']))['data']
    assert len(first['items'])==len(second['items'])==1
    assert {x['room_id'] for x in first['items']+second['items']}=={visible['room_id'],other['room_id']}
    assert second['next_cursor'] is None
    monkeypatch.setattr(queries,'SEARCH_SEMANTICS','old-semantics')
    old=queries.search(actor(a['uid']),search_request(key,limit=1))['data']['next_cursor']
    monkeypatch.setattr(queries,'SEARCH_SEMANTICS','own-target-participation-excluded-v1')
    denied('CURSOR_STALE',queries.search,actor(a['uid']),search_request(key,limit=1,cursor=old))


def test_exclusion_exact_cm_state_and_active_persistent_member(candidate):
    # Isolate SQL predicate boundaries with valid synthetic rows; no cleanup is
    # being claimed for these direct fixture state transitions.
    from app.core.database import now
    _,a,b=candidate;created=create_room(a);rid=uuid.UUID(created['room_id']);n=created['created_cycles'][1]['target_cycle_key']
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    for state in ('participating','review_required','completed','stopped','cancelled','removed'):
        with session() as db,db.begin():
            cm=db.scalar(select(queries.CycleMember).where(queries.CycleMember.cycle_id==target_id(db,rid,n),queries.CycleMember.user_id==b['uid']))
            stamp=now(db)
            cm.state=state;cm.ended_at=stamp if state in ('cancelled','removed') else None
        page=queries.search(actor(b['uid']),search_request(n))['data']['items']
        assert bool(page)==(state not in ('participating','review_required'))
        if page:assert page[0]['app_member_count']==2
    with session() as db,db.begin():
        cm=db.scalar(select(queries.CycleMember).where(queries.CycleMember.cycle_id==target_id(db,rid,n),queries.CycleMember.user_id==b['uid']))
        cm.state='review_required';cm.ended_at=None;db.get(queries.Member,cm.membership_id).ended_at=now(db)
    assert len(queries.search(actor(b['uid']),search_request(n))['data']['items'])==1
