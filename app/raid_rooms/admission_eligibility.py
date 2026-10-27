"""Read-only eligibility shared by application/change commands and batch reads."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from sqlalchemy import select
from app.game_accounts.models import CharacterRoleSummary
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.support import fail, GameError
from app.raid_rooms import participation_core as core
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment, RecruitmentRound as Round, RecruitmentItem as Item
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState

POLICY = 'admission-eligibility-2'
DUAL_CLASSES = frozenset(('바드', '발키리', '도화가', '홀리나이트'))
REASONS = ('RAID_ITEM_LEVEL_REQUIRED', 'COMBAT_POWER_REQUIRED', 'WEEKLY_ALREADY_COMPLETED',
           'WEEKLY_ALREADY_PARTICIPATING', 'ROOM_FULL', 'ROOM_COMPOSITION_CONFLICT')


def decimal(value):
    raw = str(value)
    if len(raw)>64 or not re.fullmatch(r'^[0-9]+(?:\.[0-9]+)?$',raw):
        fail('CHARACTER_DATA_UNAVAILABLE')
    try:
        result = Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        fail('CHARACTER_DATA_UNAVAILABLE')
    if not result.is_finite() or result < 0:
        fail('CHARACTER_DATA_UNAVAILABLE')
    return result


@dataclass
class Bundle:
    uid: object
    target: object
    pairs: list
    assignments: list
    states: dict
    leases: dict
    heads: dict
    successes: dict
    owned: tuple
    lease_sources: dict

    def comparison(self, cid, ownership, role):
        key = (cid, ownership, role)
        result = core.power_value(role, self.target.settings_snapshot['combat_requirement'][role + '_min'],
                                  self.heads.get(key), self.successes.get(key))
        for name in ('actual', 'requirement'):
            if result[name] is not None:
                decimal(result[name])
        return result


def load(db, uid, target, character_ids, *, owned=()):
    from app.raid_rooms import cycle_admission
    pairs = cycle_admission.rounds(db, target)
    item_ids = set(db.scalars(select(Item.id).where(Item.room_id==target.room_id)))
    if not pairs or len(pairs)!=len(item_ids) or {i.id for i,_ in pairs}!=item_ids:
        fail('ROOM_ITEMS_CHANGED')
    for item, rd in pairs:
        if rd.state != 'active' or rd.ended_at is not None:
            fail('ROUND_NOT_ACTIVE')
        if rd.catalog_version != core.raids.catalog().catalog_version:
            fail('CATALOG_VERSION_CONFLICT')
    ids = set(character_ids) | {a.character_id for a in owned}
    round_ids = [rd.id for _, rd in pairs]
    raids = [item.raid_id for item, _ in pairs]
    assignments = list(db.scalars(select(Assignment).where(Assignment.round_id.in_(round_ids), Assignment.state == 'active').order_by(Assignment.id)))
    states = {(s.character_id, s.raid_id): s for s in db.scalars(select(WeeklyState).where(
        WeeklyState.user_id == uid, WeeklyState.character_id.in_(ids), WeeklyState.raid_id.in_(raids), WeeklyState.cycle_key == target.cycle_key))} if ids else {}
    lease_rows = list(db.execute(select(WeeklyOccupancy, Assignment, Round)
        .join(Assignment,Assignment.id == WeeklyOccupancy.assignment_id).join(Round,Round.id == Assignment.round_id)
        .where(WeeklyOccupancy.user_id == uid, WeeklyOccupancy.character_id.in_(ids),
            WeeklyOccupancy.raid_id.in_(raids), WeeklyOccupancy.cycle_key == target.cycle_key))) if ids else []
    leases = {(s.character_id,s.raid_id):s for s,_,_ in lease_rows}
    lease_sources = {s.assignment_id:(a,r) for s,a,r in lease_rows}
    for key, state in states.items():
        if (state.active_party_id is not None) != (key in leases):
            fail('WEEKLY_OCCUPANCY_CHANGED')
    for key, lease in leases.items():
        state = states.get(key)
        assignment, source_round = lease_sources[lease.assignment_id]
        if (state is None or state.active_party_id != lease.room_id
                or state.active_difficulty_id != source_round.difficulty_id or state.joined_at != lease.joined_at
                or assignment.state != 'active' or source_round.state != 'active' or source_round.ended_at is not None):
            fail('WEEKLY_OCCUPANCY_CHANGED')
    heads = {(s.character_id, s.ownership_revision, s.role): s for s in db.scalars(select(CharacterRoleSummary).where(
        CharacterRoleSummary.user_id == uid, CharacterRoleSummary.character_id.in_(ids)))} if ids else {}
    successes = {(s.character_id, s.ownership_revision, s.role): s for s in db.scalars(select(RolePowerSuccess).where(
        RolePowerSuccess.user_id == uid, RolePowerSuccess.character_id.in_(ids)))} if ids else {}
    if owned and ({a.item_id for a in owned} != {i.id for i, _ in pairs} or len(owned) != len(pairs)
                  or any(a.state != 'active' or a.user_id != uid or a.room_id != target.room_id for a in owned)
                  or {a.id for a in owned} - {a.id for a in assignments}):
        fail('TARGET_BUNDLE_INCOMPLETE')
    for assignment in owned:
        raid = next(i.raid_id for i,r in pairs if i.id == assignment.item_id)
        lease = leases.get((assignment.character_id,raid))
        if lease is None or lease.assignment_id != assignment.id:
            fail('WEEKLY_OCCUPANCY_CHANGED')
    return Bundle(uid, target, pairs, assignments, states, leases, heads, successes, tuple(owned), lease_sources)


def evaluate(bundle, character, ownership, role, *, pinned=None):
    """Return a preview only. pinned is the saved application party at approval."""
    if pinned is not None and set(pinned) != {i.id for i, _ in bundle.pairs}:
        fail('ROOM_ITEMS_CHANGED')
    class_name = character.summary.get('class_name')
    if not isinstance(class_name, str) or not class_name.strip() or len(class_name)>64:
        fail('CHARACTER_DATA_UNAVAILABLE')
    if role == 'support' and class_name not in DUAL_CLASSES:
        return dict(supported=False, allowed=False, reason='ROLE_NOT_SUPPORTED', comparison=None, parties={}, slots={})
    power = bundle.comparison(character.id, ownership, role)
    result = dict(supported=True, allowed=False, reason=None, comparison=power, parties={}, slots={})
    def reject(reason):
        result['reason'] = reason
        return result
    level = decimal(character.summary.get('item_level'))
    for item, rd in bundle.pairs:
        try:
            difficulty = core.raids.difficulty(item.raid_id, rd.difficulty_id, rd.catalog_version)
        except core.raids.CatalogSelectionError as error:
            fail(error.code)
        if not core.raids.meets_item_level(level, difficulty):
            return reject('RAID_ITEM_LEVEL_REQUIRED')
    if power['state'] in ('missing', 'below'):
        return reject('COMBAT_POWER_REQUIRED')
    owned = {a.item_id: a for a in bundle.owned}
    # Validate ledger/lease coherence before interpreting occupancy as permission.
    for item, rd in bundle.pairs:
        state, lease = bundle.states.get((character.id, item.raid_id)), bundle.leases.get((character.id, item.raid_id))
        if (state is not None and state.active_party_id is not None) != (lease is not None):
            fail('WEEKLY_OCCUPANCY_CHANGED')
        if lease is not None:
            assignment, rd_source = bundle.lease_sources[lease.assignment_id]
            if (state.active_party_id != lease.room_id or state.active_difficulty_id != rd_source.difficulty_id
                    or assignment.state != 'active' or rd_source.state != 'active' or rd_source.ended_at is not None):
                fail('WEEKLY_OCCUPANCY_CHANGED')
    for item, rd in bundle.pairs:
        state = bundle.states.get((character.id, item.raid_id))
        if state and (state.manual_completed_at is not None or state.party_completed_at is not None):
            return reject('WEEKLY_ALREADY_COMPLETED')
    for item, rd in bundle.pairs:
        state, lease = bundle.states.get((character.id, item.raid_id)), bundle.leases.get((character.id, item.raid_id))
        old = owned.get(item.id)
        own = old is not None and lease is not None and lease.assignment_id == old.id
        if own and (lease.room_id != bundle.target.room_id or lease.item_id != item.id or lease.round_id != rd.id
                    or old.round_id != rd.id or old.character_id != character.id or old.user_id != bundle.uid
                    or state.active_difficulty_id != rd.difficulty_id):
            fail('WEEKLY_OCCUPANCY_CHANGED')
        if lease is not None and not own:
            return reject('WEEKLY_ALREADY_PARTICIPATING')
    size = bundle.target.settings_snapshot['app_capacity']
    if size != (bundle.pairs[0][1].game_party_size if len(bundle.pairs) == 1 else 4):
        return reject('ROOM_COMPOSITION_CONFLICT')
    if not owned and len({a.membership_id for a in bundle.assignments}) >= size:
        return reject('ROOM_FULL')
    excluded = {a.id for a in bundle.owned}
    for item, rd in bundle.pairs:
        old = owned.get(item.id)
        preferred = old.party_no if old else 1
        parties = [pinned[item.id]] if pinned is not None else [preferred] + [p for p in range(1, min(size // 4, rd.game_party_size // 4) + 1) if p != preferred]
        reasons = []
        for party in parties:
            if not 1 <= party <= min(size // 4, rd.game_party_size // 4):
                reasons.append('ROOM_COMPOSITION_CONFLICT')
                continue
            rows = [a for a in bundle.assignments if a.round_id == rd.id and a.party_no == party and a.id not in excluded]
            try:
                slot = core.composition_slot(rows, role, class_name)
            except GameError as error:
                reasons.append(error.code)
                continue
            result['parties'][item.id] = party
            result['slots'][item.id] = old.slot_no if old is not None and old.party_no == party else slot
            break
        else:
            return reject('ROOM_FULL' if all(r == 'ROOM_FULL' for r in reasons) else 'ROOM_COMPOSITION_CONFLICT')
    result['allowed'] = True
    return result


def single(db, uid, room, target, selection, *, replacing=None, pinned=None):
    from app.raid_rooms import cycle_lifecycle
    character = core.identity.selected_character(db, uid, selection.model_dump(mode='json'))
    owned = cycle_lifecycle.assignments(db, target, replacing) if replacing is not None else ()
    bundle = load(db, uid, target, [character.id], owned=owned)
    result = evaluate(bundle, character, selection.expected_ownership_revision, selection.selected_role, pinned=pinned)
    from app.game_accounts.lifecycle import digest
    from fastapi.encoders import jsonable_encoder
    result['evidence'] = digest(jsonable_encoder([evidence(bundle), facts(character), selection.selected_role, selection.expected_ownership_revision]))
    result['owned'] = {a.item_id:a for a in bundle.owned}
    return result


def facts(value):
    return {c.name: getattr(value, c.name) for c in value.__table__.columns}


def evidence(bundle):
    from app.game_accounts.lifecycle import digest
    from fastapi.encoders import jsonable_encoder
    return digest(jsonable_encoder([POLICY, facts(bundle.target),
        [[facts(i), facts(r)] for i, r in bundle.pairs], [facts(a) for a in bundle.assignments],
        [facts(s) for _, s in sorted(bundle.states.items(), key=lambda v: str(v[0]))], [facts(s) for _, s in sorted(bundle.leases.items(), key=lambda v: str(v[0]))],
        [facts(s) for _, s in sorted(bundle.heads.items(), key=lambda v: str(v[0]))], [facts(s) for _, s in sorted(bundle.successes.items(), key=lambda v: str(v[0]))],
        [facts(a) for a in bundle.owned],
        [[facts(a),facts(r)] for _,(a,r) in sorted(bundle.lease_sources.items(),key=lambda v:str(v[0]))]]))
