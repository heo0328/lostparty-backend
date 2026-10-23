"""Bounded, read-only RR summary of authoritative ledgers and exact leases.

Works on the current 0023 storage. W1's 0024 shadow graph is not required for
these reads, and is never created or promoted as a side effect. No provider,
bootstrap, key access, session reservation or command/dedup writes occur here.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from sqlalchemy import select, and_, or_,text
import uuid
from app.game_accounts.models import Account, Character, Registration, NameClaim
from app.game_accounts.support import fail
from app.groups.models import Group, GroupMembership
from app.raid_rooms import cycles
from app.raid_rooms.queries import snapshot
from app.raid_rooms.integrated_models import (RecruitmentRoom as Room, RecruitmentMembership as Member,
    RecruitmentItem as Item, RecruitmentRound as Round, RecruitmentAssignment as Assignment)
from app.raid_rooms.source_models import ContinuationChoice
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids


def permission(reason=None, next_change_at=None):
    return dict(allowed=reason is None, reason=reason, next_change_at=next_change_at)


def metadata(principal):
    with snapshot(principal) as (db, uid, stamp):
        current = raids.cycle(stamp)
        def meta(key):
            bounds = raids.cycle(datetime.combine(key, time(6), raids.KST))
            target = cycles.target(stamp, key.isoformat())
            reason = 'CURRENT_CYCLE_REQUIRED' if target.key != target.current else 'PLAY_NOT_STARTED' if stamp < target.playable_from else None
            return dict(cycle_key=key.isoformat(), starts_at=bounds.starts_at, ends_at=bounds.ends_at,
                playable_from=target.playable_from, permissions=dict(read=permission(), create=permission(),
                    admit=permission(), complete=permission(reason, target.playable_from if reason else bounds.ends_at)))
        from datetime import date
        key = date.fromisoformat(current.cycle_key)
        return dict(server_now=stamp, current=meta(key), next=meta(key+timedelta(days=7)), policy_version=cycles.POLICY)


def owned_batch(db, uid, ids):
    """One bounded query reproduces owned_character's registration/identity checks.

All inaccessible IDs fail the entire batch with 403, without existence hints.
Suspect but still-owned characters may be read; their action permission is false.
    """
    rows = list(db.execute(select(Character, Account, NameClaim).join(Account, Account.id == Character.account_id)
        .join(Registration, and_(Registration.account_id == Account.id, Registration.user_id == uid,
                                Registration.deleted_at.is_(None)))
        .outerjoin(NameClaim, and_(NameClaim.server_name == Character.server_name,
                                  NameClaim.character_name == Character.character_name))
        .where(Character.id.in_(ids))))
    if len(rows) != len(ids) or {r[0].id for r in rows} != set(ids):
        fail('OWNERSHIP_REQUIRED', 403)
    result = {}
    for character, account, claim in rows:
        if account.owner_id != uid or account.verified_at is None:
            fail('OWNERSHIP_REQUIRED', 403)
        if character.lifecycle_state == 'retired':
            fail('CHARACTER_UNUSABLE')
        if claim is None or claim.character_id != character.id:
            fail('IDENTITY_CONFLICT')
        result[character.id] = (account, character)
    return result


def graphs(db, uid, ids, keys, lease_ids):
    """Assignments are own sources only; no arbitrary room IDs from the client."""
    rows = db.execute(select(Assignment, Round, Item, Member, Room)
        .join(Round, Round.id == Assignment.round_id).join(Item, Item.id == Assignment.item_id)
        .join(Member, Member.id == Assignment.membership_id).join(Room, Room.id == Assignment.room_id)
        .join(WeeklyState, and_(WeeklyState.user_id == Assignment.user_id,
            WeeklyState.character_id == Assignment.character_id, WeeklyState.raid_id == Item.raid_id,
            WeeklyState.cycle_key == Round.cycle_key, WeeklyState.active_party_id == Assignment.room_id))
        .where(Assignment.user_id == uid, Assignment.character_id.in_(ids), Round.cycle_key.in_(keys),
            or_(Assignment.state == 'active', Assignment.id.in_(lease_ids)))).all()
    by_id, by_key = {}, defaultdict(list)
    for row in rows:
        assignment, rd, item, member, room = row
        by_id[assignment.id] = row
        by_key[(assignment.character_id, item.raid_id, rd.cycle_key)].append(row)
    return by_id, by_key


def participation(state, lease, candidates, by_id, account, character, visible_groups):
    if state is None or state.active_party_id is None:
        if lease is not None:
            fail('SERVICE_UNAVAILABLE', 503)
        return None
    if lease is not None:
        row = by_id.get(lease.assignment_id)
        if row is None:
            fail('SERVICE_UNAVAILABLE', 503)
    else:
        # A preserved legacy lease has no integrated occupancy row. A unique
        # exact Round/Assignment is enough for a REVIEW indication, never consent.
        matches = [r for r in candidates if r[0].state == 'active' and r[0].room_id == state.active_party_id
                   and r[1].difficulty_id == state.active_difficulty_id and r[0].joined_at == state.joined_at]
        if len(matches) != 1:
            fail('SERVICE_UNAVAILABLE', 503)
        row = matches[0]
    assignment, rd, item, member, room = row
    if (assignment.room_id != state.active_party_id or rd.difficulty_id != state.active_difficulty_id
            or (lease is not None and lease.joined_at != state.joined_at)):
        fail('SERVICE_UNAVAILABLE', 503)
    member_current = member.ended_at is None
    visible = room.scope == 'public' or member_current or room.group_id in visible_groups
    valid = (lease is not None and assignment.state == rd.state == 'active' and assignment.ended_at is None
        and rd.ended_at is None and member_current and room.ended_at is None and room.migration_state == 'ready'
        and assignment.ownership_revision == account.ownership_revision
        and assignment.lifecycle_revision == character.lifecycle_revision
        and character.lifecycle_state == 'active' and character.status == 'confirmed')
    return dict(room_id=room.id, round_id=rd.id, assignment_id=assignment.id, difficulty_id=rd.difficulty_id,
        status='confirmed' if valid else 'review_required', room_title=room.title if visible else None,
        can_view_detail=bool(member_current and visible))


def cycle_evidence(db,uid,ids,keys):
    revision=list(db.scalars(text('SELECT version_num FROM public.alembic_version')))
    if revision not in (['0029_cycle_outcomes'],['0030_completion_corrections'],['0031_membership_actions']):return None,set()
    from app.raid_rooms.cycle_models import CycleAssignment,CycleMember,RoomCycle,CycleRound
    from app.raid_rooms.cycle_lifecycle_models import CycleDecision
    query=select(Assignment,Item,RoomCycle,CycleMember,CycleRound).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).join(
        RoomCycle,RoomCycle.id==CycleAssignment.cycle_id).join(CycleMember,CycleMember.id==CycleAssignment.cycle_member_id).join(
        CycleRound,CycleRound.round_id==Assignment.round_id).join(Item,Item.id==Assignment.item_id).join(Member,Member.id==Assignment.membership_id).where(
        Assignment.user_id==uid,Assignment.character_id.in_(ids),RoomCycle.cycle_key.in_(keys),
        CycleAssignment.generation==RoomCycle.generation,Member.ended_at.is_(None))
    confirmed=set();actual=set()
    for a,item,row,cm,rd in db.execute(query):
        identity=(a.character_id,item.raid_id,row.cycle_key)
        if row.provenance=='explicit' and rd.is_current and cm.state in ('participating','completed','stopped'):
            actual.add(identity)
            if row.state=='open' and cm.state=='participating':confirmed.add(a.id)
    declines=set()
    for decision,row in db.execute(select(CycleDecision,RoomCycle).join(RoomCycle,RoomCycle.id==CycleDecision.cycle_id).where(
            CycleDecision.user_id==uid,CycleDecision.kind=='declined',RoomCycle.cycle_key.in_(keys),CycleDecision.generation==RoomCycle.generation)):
        evidence=decision.evidence
        try:cid=uuid.UUID(evidence['character_id'])
        except (KeyError,ValueError,TypeError):continue
        if cid in ids:
            declines.update((cid,raid,row.cycle_key) for raid in evidence.get('raid_ids',[]) if (cid,raid,row.cycle_key) not in actual)
    return confirmed,declines


def summary(principal, data):
    with snapshot(principal) as (db, uid, stamp):
        catalog = raids.catalog()
        targets = [cycles.target(stamp, key) for key in data.target_cycle_keys]
        if len(data.character_ids)*len(targets)*len(catalog.raids) > 500:
            fail('SERVICE_UNAVAILABLE', 503)
        owned = owned_batch(db, uid, data.character_ids)
        keys = [t.key for t in targets]
        states = {(r.character_id, r.raid_id, r.cycle_key): r for r in db.scalars(select(WeeklyState).where(
            WeeklyState.user_id == uid, WeeklyState.character_id.in_(data.character_ids), WeeklyState.cycle_key.in_(keys)))}
        leases = {(r.character_id, r.raid_id, r.cycle_key): r for r in db.scalars(select(WeeklyOccupancy).where(
            WeeklyOccupancy.user_id == uid, WeeklyOccupancy.character_id.in_(data.character_ids), WeeklyOccupancy.cycle_key.in_(keys)))}
        by_id, by_key = graphs(db, uid, data.character_ids, keys, [r.assignment_id for r in leases.values()])
        choices = {(r.character_id, r.raid_id, r.target_cycle): r for r in db.scalars(select(ContinuationChoice).where(
            ContinuationChoice.user_id == uid, ContinuationChoice.character_id.in_(data.character_ids),
            ContinuationChoice.target_cycle.in_(keys), ContinuationChoice.ended_at.is_(None)))}
        confirmed,declines=cycle_evidence(db,uid,data.character_ids,keys)
        visible_groups = set(db.scalars(select(GroupMembership.group_id).join(Group, Group.id == GroupMembership.group_id)
            .where(GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None), Group.ended_at.is_(None))))
        entries = []
        for cid in data.character_ids:
            account, character = owned[cid]
            usable = character.lifecycle_state == 'active' and character.status == 'confirmed'
            for target in targets:
                for raid in catalog.raids:
                    key = (cid, raid.raid_id, target.key)
                    state, lease, choice = states.get(key), leases.get(key), choices.get(key)
                    part = participation(state, lease, by_key[key], by_id, account, character, visible_groups)
                    if part and confirmed is not None and part['assignment_id'] not in confirmed:part['status']='review_required'
                    sources = []
                    if state is not None:
                        if state.manual_completed_at is not None:
                            sources.append(dict(source='manual', completed_at=state.manual_completed_at,
                                difficulty_id=state.manual_difficulty_id, party_id=None))
                        if state.party_completed_at is not None:
                            sources.append(dict(source='party', completed_at=state.party_completed_at,
                                difficulty_id=state.party_difficulty_id, party_id=state.completed_party_id))
                    playable_reason = ('CURRENT_CYCLE_REQUIRED' if target.key != target.current else
                                       'PLAY_NOT_STARTED' if stamp < target.playable_from else None)
                    mark_reason = (playable_reason or ('RAID_INACTIVE' if not raid.is_active else None)
                        or ('CHARACTER_UNUSABLE' if not usable else None)
                        or ('PARTICIPATION_CONFIRMATION_REQUIRED' if part else None))
                    clear_reason = playable_reason or (None if state and state.manual_completed_at else 'MANUAL_COMPLETION_NOT_FOUND')
                    continuation = ('confirmed' if part and part['status'] == 'confirmed' else
                                    'blocked' if part or (choice and choice.state == 'blocked') else
                                    'declined' if key in declines else 'legacy_intent' if choice else 'not_selected')
                    view_reason = None if part and part['can_view_detail'] else 'ROOM_MEMBERSHIP_REQUIRED' if part else 'NOT_PARTICIPATING'
                    time_change = target.playable_from if playable_reason else raids.cycle(stamp).ends_at
                    entries.append(dict(character_id=cid, raid_id=raid.raid_id, target_cycle_key=target.key.isoformat(),
                        weekly_revision=state.revision if state else 1, ownership_revision=account.ownership_revision,
                        lifecycle_revision=character.lifecycle_revision, completion_sources=sources, participation=part,
                        continuation_state=continuation, permissions=dict(mark_completed=permission(mark_reason, time_change if playable_reason or mark_reason is None else None),
                            clear_manual_completion=permission(clear_reason, time_change if playable_reason or clear_reason is None else None),
                            view_participation=permission(view_reason))))
        return dict(server_now=stamp, current_cycle_key=targets[0].current.isoformat(),
            target_cycle_keys=data.target_cycle_keys, catalog_version=catalog.catalog_version, entries=entries)
