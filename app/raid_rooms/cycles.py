"""Internal W1 primitives; no mounted v2 API or old-worker execution path.

Callers own one transaction, authority/context validation and the complete bundle
mutation. These helpers never commit or silently manufacture a missing target.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.core.database import session, now
from app.game_accounts.support import authorize, commit_result, fail, release, reserve
from app.raid_rooms.cycle_models import (RoomCycle, CycleGeneration, CycleMember,
    CycleRound, CycleAssignment, CycleDirectoryHead, ParticipationEvent)
from app.raid_rooms.integrated_models import (RecruitmentMembership as Membership,
    RecruitmentRoom as Room, RecruitmentItem as Item, RecruitmentRound as Round, RecruitmentAssignment as Assignment)
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids.service import cycle as actual_cycle, KST

MAX_JOIN_ORDER = 2**63 - 1
POLICY = 'two-cycle-contract-4'


@dataclass(frozen=True)
class Target:
    current: date
    key: date
    playable_from: datetime
    phase: str


def target(stamp, key):
    """C/N are explicit actual dates; 06:00 changes C, 10:00 permits play."""
    if not isinstance(key, str):
        fail('INVALID_REQUEST', 400)
    try:
        parsed = date.fromisoformat(key)
    except ValueError:
        fail('INVALID_REQUEST', 400)
    if parsed.isoformat() != key:
        fail('INVALID_REQUEST', 400)
    current = date.fromisoformat(actual_cycle(stamp).cycle_key)
    if parsed not in (current, current + timedelta(days=7)):
        fail('TARGET_CYCLE_UNAVAILABLE')
    playable = datetime.combine(parsed, time(10), KST).astimezone(timezone.utc)
    phase = 'future' if parsed != current else 'current'
    return Target(current, parsed, playable, phase)


def require_playable(stamp, key):
    value = target(stamp, key)
    if value.key != value.current or stamp < value.playable_from:
        fail('TARGET_NOT_PLAYABLE')
    return value


def resolve(db, room_id, key, stamp, *, write=False):
    """Resolve only. Reads and missing-target contexts do not insert rows."""
    value = target(stamp, key)
    query = select(RoomCycle).where(RoomCycle.room_id == room_id, RoomCycle.cycle_key == value.key)
    if write:
        query = query.with_for_update().execution_options(populate_existing=True)
    return value, db.scalar(query)


def require_current_round(db, cycle_row, round_id):
    link = db.get(CycleRound, round_id)
    if (link is None or link.cycle_id != cycle_row.id or link.room_id != cycle_row.room_id
            or cycle_row.generation is None or link.generation != cycle_row.generation or not link.is_current):
        fail('TARGET_CONTEXT_STALE')
    return link


def common_authority_cycle(db, room_id, stamp):
    """G1: a closed/review C still blocks fallback to N; never inserts C."""
    current = date.fromisoformat(actual_cycle(stamp).cycle_key)
    rows = {r.cycle_key: r for r in db.scalars(select(RoomCycle).where(
        RoomCycle.room_id == room_id, RoomCycle.cycle_key.in_((current, current + timedelta(days=7))))) }
    return rows.get(current) or rows.get(current + timedelta(days=7))


def directory_revision(db, key):
    # A prior UPSERT may have advanced a row already in the identity map.
    value = db.scalar(select(CycleDirectoryHead.revision).where(CycleDirectoryHead.cycle_key == key))
    return value if value is not None else 1


def touch_directory(db, key):
    # Absent head means revision 1. The FIRST mutation must therefore store 2.
    statement = insert(CycleDirectoryHead).values(cycle_key=key, revision=2)
    db.execute(statement.on_conflict_do_update(index_elements=['cycle_key'],
        set_={'revision': CycleDirectoryHead.revision + 1}))


def allocate_join_order(db, generation):
    """Generation row must be locked by the caller, in its bundle transaction."""
    value = generation.next_join_order
    if value is None:
        fail('JOIN_ORDER_EXHAUSTED')
    generation.next_join_order = value + 1 if value < MAX_JOIN_ORDER else None
    return value


def record_bundle_join(db, cycle_id, membership_id, command_id, stamp):
    """Record an already admitted COMPLETE bundle with exact weekly leases.

No selection, admission or ownership bypass is exposed: W2 validates those
before creating the assignments. This finalizer verifies the DB ownership chain
and allocates one target-specific order, in the SAME transaction as admission.
    """
    row = db.scalar(select(RoomCycle).where(RoomCycle.id == cycle_id).with_for_update()
                    .execution_options(populate_existing=True))
    if row is None or row.provenance != 'explicit' or row.generation is None:
        fail('ROOM_REVIEW_REQUIRED')
    if row.state not in ('open', 'review_required'):
        fail('ROUND_NOT_ACTIVE')
    target(stamp, row.cycle_key.isoformat())
    generation = db.scalar(select(CycleGeneration).where(CycleGeneration.cycle_id == row.id,
        CycleGeneration.generation == row.generation).with_for_update().execution_options(populate_existing=True))
    if generation is None or generation.state not in ('open', 'review_required'):
        fail('ROUND_NOT_ACTIVE')
    # An explicit, not-yet-finalized generation may be opened by its first bundle.
    opening = generation.state == 'review_required' and generation.leader_cycle_member_id is None
    if not opening and row.state != 'open':
        fail('ROUND_NOT_ACTIVE')
    persistent = db.get(Membership, membership_id)
    room = db.get(Room, row.room_id)
    if (persistent is None or persistent.room_id != row.room_id or persistent.ended_at is not None
            or room.ended_at is not None):
        fail('ROOM_MEMBERSHIP_REQUIRED', 403)
    items = set(db.scalars(select(Item.id).where(Item.room_id == row.room_id)))
    assignments = list(db.scalars(select(Assignment).join(CycleRound, CycleRound.round_id == Assignment.round_id)
        .where(Assignment.membership_id == membership_id, Assignment.room_id == row.room_id,
            Assignment.state == 'active', CycleRound.cycle_id == row.id,
            CycleRound.generation == row.generation, CycleRound.is_current.is_(True))))
    if not items or len(assignments) != len(items) or {a.item_id for a in assignments} != items:
        fail('TARGET_BUNDLE_INCOMPLETE')
    if len({(a.character_id, a.selected_role) for a in assignments}) != 1:
        fail('TARGET_BUNDLE_INCOMPLETE')
    for assignment in assignments:
        link = require_current_round(db, row, assignment.round_id)
        item = db.get(Item, link.item_id)
        rd = db.get(Round, assignment.round_id)
        if rd.state != 'active':
            fail('ROUND_NOT_ACTIVE')
        key = (persistent.user_id, assignment.character_id, item.raid_id, row.cycle_key)
        occupancy, weekly = db.get(WeeklyOccupancy, key), db.get(WeeklyState, key)
        if (occupancy is None or occupancy.assignment_id != assignment.id
                or weekly is None or weekly.active_party_id != row.room_id
                or weekly.active_difficulty_id != rd.difficulty_id or weekly.joined_at != occupancy.joined_at):
            fail('WEEKLY_OCCUPANCY_CHANGED')
    member = db.scalar(select(CycleMember).where(CycleMember.cycle_id == row.id,
        CycleMember.generation == row.generation, CycleMember.membership_id == membership_id))
    if member is not None and member.state == 'participating':
        return member
    if member is not None and member.state not in ('cancelled', 'removed'):
        fail('TARGET_CONTEXT_STALE')  # Completed/stopped history is not a new join.
    order = allocate_join_order(db, generation)
    if member is None:
        member = CycleMember(id=uuid.uuid4(), room_id=row.room_id, cycle_id=row.id, generation=row.generation,
            membership_id=membership_id, user_id=persistent.user_id, revision=1)
        db.add(member)
    else:
        member.revision += 1
    member.state, member.joined_order, member.joined_at, member.ended_at = 'participating', order, stamp, None
    if opening:
        generation.leader_cycle_member_id = member.id
        generation.state = 'open'
        row.state = 'open'
    row.revision += 1
    row.members_revision += 1
    row.plan_revision += 1
    db.flush()
    for assignment in assignments:
        binding = db.get(CycleAssignment, assignment.id)
        if binding is not None:
            if binding.cycle_member_id != member.id:
                fail('TARGET_CONTEXT_STALE')
        else:
            db.add(CycleAssignment(assignment_id=assignment.id, room_id=row.room_id, cycle_id=row.id,
                generation=row.generation, cycle_member_id=member.id, membership_id=member.membership_id,
                user_id=member.user_id, item_id=assignment.item_id, round_id=assignment.round_id))
    db.add(ParticipationEvent(id=uuid.uuid4(), room_id=row.room_id, cycle_id=row.id,
        generation=row.generation, cycle_member_id=member.id, membership_id=member.membership_id,
        user_id=member.user_id, command_id=command_id, action='joined', member_revision=member.revision,
        effective_at=stamp, evidence={'assignments': [{'id': str(a.id), 'revision': a.revision,
            'round_id': str(a.round_id), 'item_id': str(a.item_id),'character_id':str(a.character_id),
            'selected_role':a.selected_role,'party_no':a.party_no,'slot_no':a.slot_no,
            'display':a.display,'build':a.build,'ownership_revision':a.ownership_revision,
            'lifecycle_revision':a.lifecycle_revision,'joined_at':a.joined_at.isoformat()} for a in assignments]}))
    touch_directory(db, row.cycle_key)
    db.flush()
    return member


def execute(principal, operation, key, payload, run):
    """Persist the original ACK before week/context/authority revalidation.

W2 commands supply a validated mutation callback. Reuse the existing durable
lease store; do not introduce a second dedup namespace or in-memory cache.
    """
    name = 'recruitment-v2-' + operation
    if len(name) > 32:
        raise ValueError('Operation name exceeds durable store limit')
    ticket, replay = reserve(principal, name, key, payload)
    if replay:
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            stamp = now(db)
            outcome = run(db, uid, stamp)
            status, result = outcome[:2]
            saved = commit_result(db, ticket, status, result)
            db.flush()
            final = now(db)
            if actual_cycle(final).cycle_key != actual_cycle(stamp).cycle_key:
                fail('CYCLE_CHANGED')
            if len(outcome)==3:
                outcome[2](final)
            return saved
    except Exception:
        release(ticket)
        raise
