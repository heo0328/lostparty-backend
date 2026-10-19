"""Shared internal invariants. Callers own authorization, lock and transaction."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import select, func
from fastapi.encoders import jsonable_encoder
from app.auth.models import User
from app.core.database import now
from app.game_accounts import lifecycle
from app.game_accounts.models import CharacterRoleSummary
from app.game_accounts.support import fail
from app.groups import admission_core as groups
from app.groups.models import Group, GroupMembership
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageLimits, MemberUsageHead
from app.raid_weekly import service as weekly
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from app.raid_rooms.models import Room, Round, Membership, DirectoryHead, MemberHead


def room(db, rid, *, active=True):
    row = db.get(Room, rid)
    if row is None:
        fail('ROOM_NOT_FOUND', 404)
    if active and row.ended_at is not None:
        fail('ROOM_NOT_ACTIVE')
    return row


def member(db, room, uid):
    row = db.scalar(select(Membership).where(Membership.room_id == room.id,
        Membership.user_id == uid, Membership.ended_at.is_(None)))
    if row is None:
        fail('ROOM_MEMBERSHIP_REQUIRED', 403)
    return row


def leader(db, room, uid):
    row = member(db, room, uid)
    if row.id != room.leader_membership_id:
        fail('ROOM_LEADER_REQUIRED', 403)
    return row


def current(db, room, expected_cycle, catalog_version=None):
    round = db.get(Round, room.round_id)
    cycle = raids.cycle(now(db))
    if expected_cycle != cycle.cycle_key or round.cycle_key.isoformat() != cycle.cycle_key:
        fail('CYCLE_CHANGED')
    if round.catalog_version != raids.catalog().catalog_version or (
            catalog_version is not None and catalog_version != round.catalog_version):
        fail('CATALOG_VERSION_CONFLICT')
    return round, cycle


def supported(room):
    # Q3 has no enabled group-room adapter in F1.
    if room.scope != 'public' or room.group_id is not None:
        fail('ROOM_FEATURE_UNSUPPORTED')


def cas(room, round, command, membership=None):
    if (room.revision != command.expected_room_revision or
            round.revision != command.expected_round_revision or
            room.members_revision != command.expected_members_revision):
        fail('REVISION_CONFLICT')
    if membership is not None and (
            command.expected_round_id != round.id or
            command.expected_membership_id != membership.id or
            command.expected_membership_revision != membership.revision):
        fail('REVISION_CONFLICT')


def room_count(db, uid):
    return db.scalar(select(func.count()).select_from(Membership).join(Room, Room.id == Membership.room_id)
        .where(Membership.user_id == uid, Membership.ended_at.is_(None), Room.ended_at.is_(None)))


def issues(db, room):
    result = []
    for m in db.scalars(select(Membership).where(Membership.room_id == room.id, Membership.ended_at.is_(None))):
        effective = limits.values(db.get(MemberUsageLimits, m.user_id))
        used = room_count(db, m.user_id)
        if used > effective.raid_rooms:
            result.append(dict(code='MEMBER_RAID_LIMIT_EXCEEDED', membership_id=str(m.id),
                               used=used, limit=effective.raid_rooms))
        if room.scope == 'group':
            used = limits.joined_group_count(db, m.user_id)
            if used > effective.joined_groups:
                result.append(dict(code='MEMBER_GROUP_LIMIT_EXCEEDED', membership_id=str(m.id),
                                   used=used, limit=effective.joined_groups))
    if room.scope == 'group':
        group = db.get(Group, room.group_id)
        owner = db.get(GroupMembership, group.leader_membership_id) if group else None
        if group is None or group.ended_at is not None or owner is None:
            fail('SERVICE_UNAVAILABLE', 503)
        used = db.scalar(select(func.count()).select_from(GroupMembership).where(
            GroupMembership.group_id == group.id, GroupMembership.ended_at.is_(None)))
        capacity = limits.values(db.get(MemberUsageLimits, owner.user_id)).group_capacity
        if used > capacity:
            result.append(dict(code='GROUP_CAPACITY_EXCEEDED', membership_id=None, used=used, limit=capacity))
    return result


def policy_snapshot(db, room):
    stamps = []
    for m in db.scalars(select(Membership).where(Membership.room_id == room.id,
                       Membership.ended_at.is_(None)).order_by(Membership.id)):
        row, head = db.get(MemberUsageLimits, m.user_id), db.get(MemberUsageHead, m.user_id)
        stamps.append((str(m.id), m.revision, row.revision if row else 1,
            head.revision if head else 1, room_count(db, m.user_id),
            limits.joined_group_count(db, m.user_id) if room.scope == 'group' else None))
    return lifecycle.digest((str(room.id), room.revision, room.members_revision, stamps, issues(db, room)))


def require_policy_snapshot(db, room, expected):
    if policy_snapshot(db, room) != expected:
        fail('POLICY_CONTEXT_CHANGED')
    if issues(db, room):
        fail('ROOM_RESTRICTED')


def selection(db, uid, data, round, *, increasing, lock=True):
    query = select(User).where(User.id == uid)
    user = db.scalar(query.with_for_update() if lock else query)
    if user is None or user.status != 'active':
        fail('ROOM_TARGET_UNAVAILABLE')
    character = groups.selected_character(db, uid, jsonable_encoder(data))
    summary = db.get(CharacterRoleSummary, (uid, character.id, data.expected_ownership_revision, data.selected_role))
    if (summary.version if summary else 1) != data.expected_role_summary_version:
        fail('REVISION_CONFLICT')
    row, head = db.get(MemberUsageLimits, uid), db.get(MemberUsageHead, uid)
    if ((row.revision if row else 1) != data.expected_limits_revision or
            (head.revision if head else 1) != data.expected_usage_revision):
        fail('POLICY_CONTEXT_CHANGED')
    if increasing and room_count(db, uid) >= limits.values(row).raid_rooms:
        fail('MEMBER_RAID_LIMIT_REACHED')
    try:
        difficulty = raids.difficulty(round.raid_id, round.difficulty_id, round.catalog_version)
    except raids.CatalogSelectionError as error:
        fail(error.code)
    try:
        level = Decimal(str(character.summary.get('item_level')))
    except (InvalidOperation, ValueError):
        level = None
    if not raids.meets_item_level(level, difficulty):
        fail('RAID_ITEM_LEVEL_REQUIRED')
    if not character.summary.get('class_name'):
        fail('CHARACTER_DATA_UNAVAILABLE')
    state = db.get(WeeklyState, (uid, character.id, round.raid_id, round.cycle_key))
    if (state.revision if state else 1) != data.expected_weekly_revision:
        fail('REVISION_CONFLICT')
    weekly.require_available_for_participation(db, uid, character.id, round.raid_id, round.cycle_key)
    if data.party_no > round.party_count:
        fail('ROOM_COMPOSITION_CONFLICT')
    # P1 is a client analysis snapshot only. Never replace provider level or impose power thresholds.
    return character, jsonable_encoder(dict(version=summary.version if summary else 1,
        summary=summary.summary if summary else None, saved_at=summary.saved_at if summary else None))


def require_no_time_overlap(db, uid, round):
    conflict = db.scalar(select(Membership.id).join(Round, Round.id == Membership.round_id)
        .where(Membership.user_id == uid, Membership.ended_at.is_(None),
               Round.ended_at.is_(None), Round.starts_at < round.ends_at, Round.ends_at > round.starts_at).limit(1))
    if conflict is not None:
        fail('SCHEDULE_CONFLICT')


def slot(db, uid, room, round, data, character):
    if db.scalar(select(Membership.id).where(Membership.room_id == room.id,
            Membership.user_id == uid, Membership.ended_at.is_(None))) is not None:
        fail('ROOM_MEMBER_EXISTS')
    rows = list(db.scalars(select(Membership).where(Membership.room_id == room.id,
        Membership.ended_at.is_(None), Membership.party_no == data.party_no)))
    occupied = {m.slot_no for m in rows}
    if len(rows) >= 4:
        fail('ROOM_FULL')
    role_rows = [m for m in rows if m.selected_role == data.selected_role]
    if (data.selected_role == 'support' and role_rows) or (
            data.selected_role == 'dealer' and (len(role_rows) >= 3 or any(
                m.display.get('class_name') == character.summary['class_name'] for m in role_rows))):
        fail('ROOM_COMPOSITION_CONFLICT')
    return next(n for n in range(1, 5) if n not in occupied)


def touch_user(db, uid, *, application=False):
    head = db.get(MemberHead, uid)
    if head is None:
        head = MemberHead(user_id=uid, membership_revision=1, application_revision=1)
        db.add(head)
    if application:
        head.application_revision += 1
    else:
        head.membership_revision += 1
        usage = db.get(MemberUsageHead, uid)
        if usage is None:
            db.add(MemberUsageHead(user_id=uid, revision=2))
        else:
            usage.revision += 1


def directory(db):
    row = db.get(DirectoryHead, 1)
    if row is None:
        fail('SERVICE_UNAVAILABLE', 503)
    row.revision += 1


def occupy(db, uid, room, round, data, character, build, stamp):
    require_no_time_overlap(db, uid, round)
    number = slot(db, uid, room, round, data, character)
    row = Membership(room_id=room.id, round_id=round.id, user_id=uid, character_id=character.id,
        selected_role=data.selected_role, party_no=data.party_no, slot_no=number,
        display=groups.display(character), build=build, ownership_revision=data.expected_ownership_revision,
        lifecycle_revision=data.expected_lifecycle_revision, revision=1, joined_at=stamp)
    db.add(row)
    state = weekly.require_available_for_participation(db, uid, character.id, round.raid_id, round.cycle_key)
    if state is None:
        state = WeeklyState(user_id=uid, character_id=character.id, raid_id=round.raid_id,
            cycle_key=round.cycle_key, revision=1, updated_at=stamp)
        db.add(state)
    state.active_party_id, state.active_difficulty_id, state.joined_at = room.id, round.difficulty_id, stamp
    state.revision += 1
    state.updated_at = stamp
    touch_user(db, uid)
    directory(db)
    db.flush()
    return row


def end_membership(db, room, round, membership, stamp):
    state = db.get(WeeklyState, (membership.user_id, membership.character_id, round.raid_id, round.cycle_key))
    if state and state.active_party_id == room.id and state.joined_at == membership.joined_at:
        state.active_party_id = state.active_difficulty_id = state.joined_at = None
        state.revision += 1
        state.updated_at = stamp
    membership.ended_at = stamp
    membership.revision += 1
    touch_user(db, membership.user_id)
    directory(db)
