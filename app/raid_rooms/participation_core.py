"""R2 transaction primitives, not public admission authorization.

Caller authorizes actor, owns the game-mutations lock, room/context CAS and
transaction. Admission-mode/approver rights, deadlines, sessions/consent and
idempotent ACK belong to the integrating command, never inferred here.
"""
import uuid
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from sqlalchemy import select, func, union
from app.auth.models import User
from app.core.database import now
from app.game_accounts.models import CharacterRoleSummary
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.support import fail
from app.groups import admission_core as identity
from app.groups.models import Group, GroupMembership
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageLimits, MemberUsageHead
from app.raid_weekly import service as weekly
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from app.raid_rooms import core as legacy
from app.raid_rooms.models import Room as OldRoom, Membership as OldMember
from app.raid_rooms.integrated_models import (RecruitmentRoom as Room, RecruitmentItem as Item,
    RecruitmentRound as Round, RecruitmentMembership as Member, RecruitmentAssignment as Assignment)
from app.raid_rooms.source_models import RoomSettings
from app.raid_rooms.weekly_links import WeeklyOccupancy


def room_count(db, uid):
    # Integrated rooms are authoritative, including ended memberships. Never
    # resurrect usage from the preserved legacy copy after integrated cleanup.
    old = select(OldMember.room_id).join(OldRoom, OldRoom.id == OldMember.room_id).where(
        OldMember.user_id == uid, OldMember.ended_at.is_(None), OldRoom.ended_at.is_(None),
        ~select(Room.id).where(Room.id==OldRoom.id).exists())
    new = select(Member.room_id).join(Room, Room.id == Member.room_id).where(
        Member.user_id == uid, Member.ended_at.is_(None), Room.ended_at.is_(None))
    return db.scalar(select(func.count()).select_from(union(old,new).subquery()))


def power_comparison(db, uid, selection, minimum):
    key=(uid,selection.character_id,selection.expected_ownership_revision,selection.selected_role)
    head=db.get(CharacterRoleSummary,key)
    if (head.version if head else 1) != selection.expected_role_summary_version:
        fail('REVISION_CONFLICT')
    success=db.get(RolePowerSuccess,key)
    actual=success.combat_power if success else None
    state=('unrestricted' if minimum is None else 'missing' if actual is None else
           'meets' if Decimal(actual)>=Decimal(minimum) else 'below')
    return dict(selected_role=selection.selected_role,requirement=minimum,actual=actual,state=state,
        source='flutter_analysis',trust='client_submitted',current_summary_version=head.version if head else 1,
        success_summary_version=success.source_summary_version if success else None,
        power_revision=success.power_revision if success else 1,observed_at=success.observed_at if success else None,
        success_saved_at=success.source_saved_at if success else None,
        success_issues=deepcopy(success.source_summary.get('issues',[])) if success else [],
        current_issues=deepcopy(head.summary.get('issues',[])) if head else [])


def _limits(db, uid, selection, increasing):
    row,head=db.get(MemberUsageLimits,uid),db.get(MemberUsageHead,uid)
    if ((row.revision if row else 1)!=selection.expected_limits_revision or
            (head.revision if head else 1)!=selection.expected_usage_revision):
        fail('POLICY_CONTEXT_CHANGED')
    if increasing and room_count(db,uid)>=limits.values(row).raid_rooms:
        fail('MEMBER_RAID_LIMIT_REACHED')


def _group(db, room, uid, allow_external=False):
    if room.scope!='group':return  # Public admission independent of linked group.
    group=db.get(Group,room.group_id)
    if group is None or group.ended_at is not None:fail('GROUP_NOT_ACTIVE')
    member=db.scalar(select(GroupMembership).where(GroupMembership.group_id==group.id,
        GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None)))
    if member is None and not allow_external:fail('GROUP_MEMBERSHIP_REQUIRED',403)
    owner=db.get(GroupMembership,group.leader_membership_id)
    if owner is None or owner.ended_at is not None:fail('SERVICE_UNAVAILABLE',503)
    count=db.scalar(select(func.count()).select_from(GroupMembership).where(
        GroupMembership.group_id==group.id,GroupMembership.ended_at.is_(None)))
    if count>limits.values(db.get(MemberUsageLimits,owner.user_id)).group_capacity:
        fail('GROUP_CAPACITY_EXCEEDED')
    if member is not None and limits.joined_group_count(db,uid)>limits.values(db.get(MemberUsageLimits,uid)).joined_groups:
        fail('MEMBER_GROUP_LIMIT_EXCEEDED')


def _room_restrictions(db, room):
    for uid in db.scalars(select(Member.user_id).where(Member.room_id==room.id,Member.ended_at.is_(None))):
        effective=limits.values(db.get(MemberUsageLimits,uid))
        if room_count(db,uid)>effective.raid_rooms:
            fail('ROOM_RESTRICTED')
        if room.scope=='group' and limits.joined_group_count(db,uid)>effective.joined_groups:
            fail('ROOM_RESTRICTED')


def _slot(db, room, round, selection, character, party_no, *, exclude_membership_id=None):
    if party_no>min(room.app_capacity//4,round.game_party_size//4):
        fail('ROOM_COMPOSITION_CONFLICT')
    query=select(Assignment).where(Assignment.round_id==round.id,
        Assignment.state=='active',Assignment.party_no==party_no)
    if exclude_membership_id is not None:query=query.where(Assignment.membership_id!=exclude_membership_id)
    rows=list(db.scalars(query))
    if len(rows)>=4:fail('ROOM_FULL')
    same=[r for r in rows if r.selected_role==selection.selected_role]
    if ((selection.selected_role=='support' and same) or (selection.selected_role=='dealer' and
            (len(same)>=3 or any(r.display.get('class_name')==character.summary['class_name'] for r in same)))):
        fail('ROOM_COMPOSITION_CONFLICT')
    return next(n for n in range(1,5) if n not in {r.slot_no for r in rows})


def admit_bundle(db, uid, room, selection, targets, expected_cycle_key, *, validate_only=False, pending=False, public_origin_application=None, resume_item_ids=None):
    """Atomically attach every active item; caller must roll back on any rejection.

    Supports empty/unscheduled rooms without inventing sessions. Existing persistent
    members may acquire next-round assignments without consuming another room unit.
    This does not approve an application or grant a caller HTTP admission authority.
    """
    if pending and not validate_only:raise ValueError('Pending validation cannot write occupancy')
    stamp=now(db)
    cycle=raids.cycle(stamp)
    if expected_cycle_key!=cycle.cycle_key:fail('CYCLE_CHANGED')
    if room.ended_at is not None:fail('ROOM_NOT_ACTIVE')
    if room.migration_state!='ready':fail('ROOM_REVIEW_REQUIRED')
    query=select(User).where(User.id==uid)
    user=db.scalar(query if validate_only else query.with_for_update())
    if user is None or user.status!='active':fail('ROOM_TARGET_UNAVAILABLE')
    member=db.scalar(select(Member).where(Member.room_id==room.id,Member.user_id==uid,Member.ended_at.is_(None)))
    _limits(db,uid,selection,member is None and not pending)
    origin=public_origin_application
    allow_external=(origin is not None and origin.room_id==room.id and origin.user_id==uid and
                    origin.origin_state=='known' and origin.origin_scope=='public' and origin.state=='pending')
    _group(db,room,uid,allow_external=allow_external)
    _room_restrictions(db,room)
    character=identity.selected_character(db,uid,selection.model_dump(mode='json'))
    if not character.summary.get('class_name'):fail('CHARACTER_DATA_UNAVAILABLE')
    settings=db.get(RoomSettings,room.id)
    if settings is None:fail('SERVICE_UNAVAILABLE',503)
    minimum=settings.dealer_min if selection.selected_role=='dealer' else settings.support_min
    power=power_comparison(db,uid,selection,minimum)
    if power['state'] in ('missing','below'):fail('COMBAT_POWER_REQUIRED')
    pairs=list(db.execute(select(Item,Round).join(Round,
        (Round.room_id==Item.room_id)&(Round.item_id==Item.id)).where(Item.room_id==room.id,
        Round.state=='active',Round.ended_at.is_(None),Round.cycle_key==weekly.parse_cycle(expected_cycle_key))))
    by_id={t.item_id:t for t in targets}
    if resume_item_ids is not None:
        # Internal resume command derives this set from stopped assignments;
        # ordinary client admission can never request a partial bundle.
        pairs=[(i,r) for i,r in pairs if i.id in resume_item_ids]
    if not pairs or len(by_id)!=len(targets) or set(by_id)!={i.id for i,r in pairs}:
        fail('ROOM_ITEMS_CHANGED')
    all_items=set(db.scalars(select(Item.id).where(Item.room_id==room.id)))
    if set(by_id)!=(all_items if resume_item_ids is None else set(resume_item_ids)):fail('ROOM_ITEMS_CHANGED')
    if len({i.id for i,r in pairs})!=len(pairs):fail('ROOM_ITEMS_CHANGED')
    if room.app_capacity!=(pairs[0][1].game_party_size if len(all_items)==1 else 4):
        fail('ROOM_COMPOSITION_CONFLICT')
    plans=[]
    for item,round in pairs:
        target=by_id[item.id]
        if target.round_id!=round.id or target.expected_round_revision!=round.revision:fail('REVISION_CONFLICT')
        if round.catalog_version!=raids.catalog().catalog_version:fail('CATALOG_VERSION_CONFLICT')
        raid=next((r for r in raids.catalog().raids if r.raid_id==item.raid_id),None)
        if raid is None or raid.party_size!=round.game_party_size:fail('ROOM_REVIEW_REQUIRED')
        try:difficulty=raids.difficulty(item.raid_id,round.difficulty_id,round.catalog_version)
        except raids.CatalogSelectionError as error:fail(error.code)
        try:level=Decimal(str(character.summary.get('item_level')))
        except (InvalidOperation,ValueError):level=None
        if not raids.meets_item_level(level,difficulty):fail('RAID_ITEM_LEVEL_REQUIRED')
        state=weekly.require_available_for_participation(db,uid,character.id,item.raid_id,round.cycle_key)
        if (state.revision if state else 1)!=target.expected_weekly_revision:fail('REVISION_CONFLICT')
        if db.get(WeeklyOccupancy,(uid,character.id,item.raid_id,round.cycle_key)) is not None:
            fail('WEEKLY_ALREADY_PARTICIPATING')
        if member and db.scalar(select(Assignment.id).where(Assignment.round_id==round.id,
                Assignment.membership_id==member.id)) is not None:fail('ROOM_MEMBER_EXISTS')
        if target.party_no>min(room.app_capacity//4,round.game_party_size//4):fail('ROOM_COMPOSITION_CONFLICT')
        plans.append((item,round,state,None if pending else _slot(db,room,round,selection,character,target.party_no)))
    if member is None:
        if not pending and db.scalar(select(func.count()).select_from(Member).where(Member.room_id==room.id,
                Member.ended_at.is_(None)))>=room.app_capacity:fail('ROOM_FULL')
    if validate_only:
        return member,[],power
    if member is None:
        member=Member(id=uuid.uuid4(),room_id=room.id,user_id=uid,revision=1,joined_at=stamp)
        db.add(member);db.flush()
    build=deepcopy(power)
    # Use the original success provenance, including warnings, rather than current
    # null/older head or a maximum/other-role observation.
    success=db.get(RolePowerSuccess,(uid,character.id,selection.expected_ownership_revision,selection.selected_role))
    if success:build['success_summary']=deepcopy(success.source_summary)
    from fastapi.encoders import jsonable_encoder
    assignments=[]
    for item,round,state,slot in plans:
        row=Assignment(id=uuid.uuid4(),room_id=room.id,item_id=item.id,round_id=round.id,
            membership_id=member.id,user_id=uid,character_id=character.id,selected_role=selection.selected_role,
            party_no=by_id[item.id].party_no,slot_no=slot,display=identity.display(character),
            build=jsonable_encoder(build),ownership_revision=selection.expected_ownership_revision,
            lifecycle_revision=selection.expected_lifecycle_revision,revision=1,state='active',joined_at=stamp)
        db.add(row)
        if state is None:
            state=WeeklyState(user_id=uid,character_id=character.id,raid_id=item.raid_id,
                cycle_key=round.cycle_key,revision=1,updated_at=stamp)
            db.add(state)
        state.active_party_id,state.active_difficulty_id,state.joined_at=room.id,round.difficulty_id,stamp
        state.revision+=1;state.updated_at=stamp
        db.flush()
        db.add(WeeklyOccupancy(user_id=uid,character_id=character.id,raid_id=item.raid_id,cycle_key=round.cycle_key,
            room_id=room.id,item_id=item.id,round_id=round.id,assignment_id=row.id,joined_at=stamp))
        assignments.append(row)
    room.members_revision+=1;room.plan_revision+=1;room.revision+=1
    legacy.touch_user(db,uid);legacy.directory(db)
    db.flush()
    if raids.cycle(now(db)).cycle_key!=expected_cycle_key:fail('CYCLE_CHANGED')
    return member,assignments,power


def release_assignment(db, assignment, stamp):
    """Internal whole-command cleanup; never an item-only leave HTTP operation."""
    if assignment.state!='active':return False
    item=db.get(Item,assignment.item_id);round=db.get(Round,assignment.round_id)
    key=(assignment.user_id,assignment.character_id,item.raid_id,round.cycle_key)
    link=db.get(WeeklyOccupancy,key)
    if link is None or link.assignment_id!=assignment.id:
        # Preserved legacy rows are not proof of a current integrated lease.
        fail('WEEKLY_OCCUPANCY_CHANGED')
    state=db.get(WeeklyState,key)
    if (state is None or state.active_party_id!=assignment.room_id or
            state.active_difficulty_id!=round.difficulty_id or state.joined_at!=link.joined_at):
        fail('SERVICE_UNAVAILABLE',503)
    state.active_party_id=state.active_difficulty_id=state.joined_at=None
    state.revision+=1;state.updated_at=stamp
    db.delete(link)
    assignment.state='left';assignment.ended_at=stamp;assignment.revision+=1
    return True
