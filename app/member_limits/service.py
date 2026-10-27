"""Member limit foundation; G1 exposes self reads, writes remain server-internal.

Production raid-room integration is a later stage.

Writes share the game-mutations lock. Limit changes require an explicit trusted
server authorization callback; this module does not grant an app user that power.
"""
from dataclasses import asdict, dataclass
from typing import Callable
from sqlalchemy import func, select
from app.auth.models import User
from app.core.database import session, now
from app.game_accounts.support import authorize, fail, lock
from app.groups.models import Group, GroupMembership
from app.member_limits.models import MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit


@dataclass(frozen=True)
class Limits:
    group_capacity: int = 15
    joined_groups: int = 5
    raid_rooms: int = 10

    def __post_init__(self):
        if any(type(value) is not int or not 0 <= value <= 2147483647
               for value in asdict(self).values()):
            raise ValueError('Limits must be non-negative PostgreSQL integers')


def values(row):
    return Limits(row.group_capacity, row.joined_groups, row.raid_rooms) if row else Limits()


def metric(used, limit):
    if used is None:
        return dict(used=None, remaining=None, state='unavailable', can_increase=None)
    return dict(used=used, remaining=max(0, limit-used),
                state='exceeded' if used > limit else 'at_limit' if used == limit else 'within',
                can_increase=used < limit)


def joined_group_count(db, uid):
    return db.scalar(select(func.count()).select_from(GroupMembership).join(
        Group, Group.id == GroupMembership.group_id).where(
        GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None), Group.ended_at.is_(None)))


def snapshot(db, uid, *, room_count=None):
    """Caller must authorize and provide a consistent read transaction. Never inserts."""
    row, head = db.get(MemberUsageLimits, uid), db.get(MemberUsageHead, uid)
    limits = values(row)
    used = joined_group_count(db, uid)
    if room_count is not None and not callable(room_count):
        raise TypeError('Explicit room usage source must be callable')
    rooms = room_count(db, uid) if room_count is not None else None
    if room_count is not None and (type(rooms) is not int or rooms < 0):
        fail('SERVICE_UNAVAILABLE', 503)
    issues = []
    if rooms is not None and rooms > limits.raid_rooms:
        issues.append(dict(code='MEMBER_RAID_LIMIT_EXCEEDED', dimension='raid_rooms',
                           used=rooms, limit=limits.raid_rooms))
    if used > limits.joined_groups:
        issues.append(dict(code='MEMBER_GROUP_LIMIT_EXCEEDED', dimension='joined_groups',
                           used=used, limit=limits.joined_groups))
    return dict(policy_version='member-room-limits-v1', evaluated_at=db.info.get('active_usage_stamp') or now(db),
                limits_revision=row.revision if row else 1, usage_revision=head.revision if head else 1,
                limit_source='account' if row else 'default', updated_at=row.updated_at if row else None,
                limits=asdict(limits), usage=dict(joined_groups=metric(used, limits.joined_groups),
                                                raid_rooms=metric(rooms, limits.raid_rooms)), issues=issues)


def get(principal):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        from app.raid_rooms.participation_core import room_count
        from app.raid_rooms.readiness import require_active,require_two_cycle_active
        from app.raid_rooms.active_usage import enabled
        (require_two_cycle_active if enabled(db) else require_active)(db)
        uid=authorize(db,principal);db.info['active_usage_stamp']=now(db)
        return snapshot(db,uid,room_count=room_count)


def record_group_membership_change(db, uid):
    """Called in the same transaction as a confirmed membership change, never on replay.

    The lock is also acquired here so all future callers use the same ordering.
    The caller still owns role/identity validation and the actual relation write.
    """
    lock(db, 'game-mutations-v1')
    row = db.get(MemberUsageLimits, uid)
    if row is None:
        db.add(MemberUsageLimits(user_id=uid, revision=1, **asdict(Limits()), updated_at=now(db)))
    head = db.get(MemberUsageHead, uid)
    if head is None:
        head = MemberUsageHead(user_id=uid, revision=1)
        db.add(head)
    head.revision += 1


def change_limits(db, uid, expected_revision: int, limits: Limits, *,
                  authority: str, reason: str, authorize_change: Callable):
    """Trusted server-only boundary; caller owns transaction commit/rollback.

    No default permissive authority, HTTP wrapper, CLI, billing, or admin role.
    Authorization callback must reject unauthorized invocations, without network I/O.
    """
    if not callable(authorize_change):
        raise TypeError('Explicit server authorization is required')
    if not isinstance(limits, Limits) or type(expected_revision) is not int or expected_revision < 1:
        raise ValueError('Invalid limit change')
    if (not isinstance(authority, str) or not 1 <= len(authority.strip()) <= 80 or
            not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 200):
        raise ValueError('Internal audit authority and reason required')
    lock(db, 'game-mutations-v1')
    authorize_change(db, uid)
    if db.scalar(select(User.id).where(User.id == uid).with_for_update()) is None:
        fail('MEMBER_NOT_FOUND', 404)
    row = db.get(MemberUsageLimits, uid, populate_existing=True)
    revision = row.revision if row else 1
    if revision != expected_revision:
        fail('REVISION_CONFLICT')
    previous = values(row)
    if previous == limits:
        return revision
    current = now(db)
    if row is None:
        row = MemberUsageLimits(user_id=uid)
        db.add(row)
    row.revision = revision + 1
    for key, value in asdict(limits).items():
        setattr(row, key, value)
    row.updated_at = current
    db.add(MemberUsageLimitAudit(user_id=uid, revision=row.revision,
                                before=asdict(previous), after=asdict(limits),
                                authority=authority.strip(), reason=reason.strip(), created_at=row.updated_at))
    return row.revision
