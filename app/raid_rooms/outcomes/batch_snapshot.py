"""Internal batch evidence; callers own authorization and snapshot/transaction.

Active effects are bounded independently of immutable completion history. This
module does not expose routes, issue tokens, mutate rows or open transactions.
"""
import hashlib
import json

from sqlalchemy import select

from app.game_accounts.common.support import GameError, fail
from app.raid_rooms.models.cycle_models import CycleAssignment, CycleRound
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.integrated_models import RecruitmentItem as Item
from app.raid_rooms.models.integrated_models import RecruitmentRound as Round
from app.raid_weekly.service import raid_by_id


class _ArrayDigest:
    """Byte-identical to lifecycle.digest(list(records)), with bounded memory."""
    def __init__(self):
        self._hash = hashlib.sha256(b'[')
        self.count = 0

    def add(self, record):
        if self.count:
            self._hash.update(b', ')
        self._hash.update(json.dumps(record, sort_keys=True, default=str).encode())
        self.count += 1

    def finish(self):
        result = self._hash.copy()
        result.update(b']')
        return result.hexdigest()


def _query(row, state, user_id):
    query = (select(Assignment, CycleAssignment, Round, CycleRound, Item)
             .join(CycleAssignment, CycleAssignment.assignment_id == Assignment.id)
             .outerjoin(Round, Round.id == Assignment.round_id)
             .outerjoin(CycleRound, CycleRound.round_id == Assignment.round_id)
             .outerjoin(Item, Item.id == Assignment.item_id)
             .where(CycleAssignment.room_id == row.room_id,
                    CycleAssignment.cycle_id == row.id,
                    CycleAssignment.generation == row.generation,
                    Assignment.state == state))
    if user_id is not None:
        query = query.where(CycleAssignment.user_id == user_id)
    return query.order_by(Assignment.id)


def _validate(row, assignment, link, rd, current, item):
    expected = (row.room_id, assignment.id, assignment.membership_id,
                assignment.user_id, assignment.item_id, assignment.round_id)
    if ((link.room_id, link.assignment_id, link.membership_id, link.user_id,
         link.item_id, link.round_id) != expected or assignment.room_id != row.room_id
            or rd is None or current is None or item is None
            or (rd.room_id, rd.item_id, rd.cycle_key) != (row.room_id, item.id, row.cycle_key)
            or (current.room_id, current.cycle_id, current.generation, current.item_id)
            != (row.room_id, row.id, row.generation, item.id)
            or item.room_id != row.room_id):
        fail('ROOM_REVIEW_REQUIRED')


def active_assignments(db, row, *, user_id=None):
    """Return only live effects, proving current-round identity and slot bounds.

    Weekly occupancy, authority and character qualification remain the command's
    responsibility. Historical identities never participate in these limits.
    """
    maximum = 5 if user_id is not None else 40
    rows = list(db.execute(_query(row, 'active', user_id).limit(maximum + 1)))
    if len(rows) > maximum:
        fail('ROOM_REVIEW_REQUIRED')
    result, member_items, slots, selections = [], set(), set(), {}
    for assignment, link, rd, current, item in rows:
        _validate(row, assignment, link, rd, current, item)
        member_item = (link.cycle_member_id, item.id)
        slot = (rd.id, assignment.party_no, assignment.slot_no)
        selection = (assignment.character_id, assignment.selected_role)
        if (not current.is_current or rd.state != 'active'
                or member_item in member_items or slot in slots
                or selections.get(link.cycle_member_id, selection) != selection):
            fail('ROOM_REVIEW_REQUIRED')
        member_items.add(member_item)
        slots.add(slot)
        selections[link.cycle_member_id] = selection
        result.append(assignment)
    return result


def _raid_name(raid_id):
    try:
        return raid_by_id(raid_id).display_name
    except GameError as error:
        if error.code != 'RAID_NOT_FOUND':
            raise
        return raid_id


def _record(assignment, link, rd, item):
    # Names and current character/provider state are deliberately not evidence.
    # Include every persisted assignment column, linkage and round provenance.
    return dict(assignment={c.name: getattr(assignment, c.name)
                            for c in Assignment.__table__.columns},
                binding={c.name: getattr(link, c.name)
                         for c in CycleAssignment.__table__.columns},
                raid_id=item.raid_id,
                round=dict(id=rd.id, item_id=rd.item_id, cycle_key=rd.cycle_key,
                           difficulty_id=rd.difficulty_id, catalog_version=rd.catalog_version))


def preserved_completed(db, row, *, user_id=None, exclude_assignment_ids=()):
    """Aggregate all completed records of this room/T/generation, including reentry.

    Do not filter by current round, ended membership or current character owner.
    Exclusion lets a command prove its preexisting history after new completions.
    The caller supplies only its bounded, newly completed assignment IDs.
    """
    excluded = frozenset(exclude_assignment_ids)
    if len(excluded) > 40:
        raise ValueError('Only bounded new completion IDs may be excluded')
    query = _query(row, 'completed', user_id)
    if excluded:
        query = query.where(Assignment.id.not_in(excluded))
    total, groups = _ArrayDigest(), {}
    result = db.execute(query.execution_options(yield_per=128))
    try:
        for assignment, link, rd, current, item in result:
            _validate(row, assignment, link, rd, current, item)
            record = _record(assignment, link, rd, item)
            total.add(record)
            if item.raid_id not in groups:
                groups[item.raid_id] = _ArrayDigest()
            groups[item.raid_id].add(record)
    finally:
        result.close()
    return dict(assignment_count=total.count, digest=total.finish(),
                raids=[dict(raid_id=raid_id, raid_name=_raid_name(raid_id),
                            assignment_count=value.count, digest=value.finish())
                       for raid_id, value in sorted(groups.items())])
