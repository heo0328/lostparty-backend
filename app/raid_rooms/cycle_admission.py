"""Target-specific admission primitives. Caller owns authorization and transaction.

The legacy Room remains the persistent membership anchor. Capacity, settings,
rounds, assignments and weekly leases are resolved only from the requested target.
No current-week aliases or global room revisions are mutated here.
"""
import uuid
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from sqlalchemy import select, func
from fastapi.encoders import jsonable_encoder
from app.auth.models import User
from app.game_accounts.support import fail
from app.game_accounts.power_success import RolePowerSuccess
from app.raid_rooms import cycles, participation_core as core
from app.raid_rooms.cycle_models import CycleMember, CycleRound, RoomCycle
from app.raid_rooms.integrated_models import (RecruitmentItem as Item, RecruitmentRound as Round,
    RecruitmentMembership as Member, RecruitmentAssignment as Assignment)
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState


def rounds(db, target):
    return list(db.execute(select(Item, Round).join(CycleRound,
        (CycleRound.item_id == Item.id) & (CycleRound.room_id == Item.room_id)).join(Round,
        Round.id == CycleRound.round_id).where(CycleRound.cycle_id == target.id,
        CycleRound.generation == target.generation, CycleRound.is_current.is_(True)).order_by(Item.id)))


def capacity(target):
    settings = target.settings_snapshot
    if target.provenance != 'explicit' or target.generation is None or not settings:
        fail('ROOM_REVIEW_REQUIRED')
    return settings['app_capacity']


def member_count(db, target):
    # A lease is a proof of actual participation even if its imported member is
    # under review. Persistent membership alone never occupies a target slot.
    query = select(Assignment.membership_id).join(CycleRound, CycleRound.round_id == Assignment.round_id).join(
        WeeklyOccupancy, WeeklyOccupancy.assignment_id == Assignment.id).where(
        CycleRound.cycle_id == target.id, CycleRound.is_current.is_(True),
        Assignment.state == 'active')
    if target.generation is not None:
        query = query.where(CycleRound.generation == target.generation)
    return db.scalar(select(func.count()).select_from(query.distinct().subquery()))


def admit_bundle(db, uid, room, target, selection, targets, command_id, stamp, *,
                 validate_only=False, pending=False, public_origin_application=None, opening=False, replacing=None, resuming=None, resume_items=None, unified=False):
    from app.raid_rooms import cycle_group_policy as group_policy
    room=group_policy.project(db,room,target)
    if pending and not validate_only:
        raise ValueError('Pending validation cannot acquire a lease')
    cycles.target(stamp, target.cycle_key.isoformat())
    if room.ended_at is not None:
        fail('ROOM_NOT_ACTIVE')
    size = capacity(target)
    if target.state != 'open' and not (opening and target.state == 'review_required'):
        fail('ROUND_NOT_ACTIVE' if target.state == 'closed' else 'ROOM_REVIEW_REQUIRED')
    user = db.scalar(select(User).where(User.id == uid).with_for_update()) if not validate_only else db.get(User, uid)
    if user is None or user.status != 'active':
        fail('ROOM_TARGET_UNAVAILABLE')
    member = db.scalar(select(Member).where(Member.room_id == room.id, Member.user_id == uid,
        Member.ended_at.is_(None)))
    core._limits(db, uid, selection, not pending and replacing is None, room_id=room.id)
    origin = public_origin_application
    allow_external = (origin is not None and origin.room_id == room.id and origin.user_id == uid
        and origin.origin_scope == 'public' and origin.state == 'pending')
    core._group(db, room, uid, allow_external=allow_external and not group_policy.enabled(db),
        existing=replacing is not None or resuming is not None)
    core._room_restrictions(db, room)
    character = core.identity.selected_character(db, uid, selection.model_dump(mode='json'))
    if not character.summary.get('class_name'):
        fail('CHARACTER_DATA_UNAVAILABLE')
    evaluation = None
    if unified:
        from app.raid_rooms import admission_eligibility
        evaluation = admission_eligibility.single(db, uid, room, target, selection, replacing=replacing,
            pinned={t.item_id: t.party_no for t in targets})
        if not evaluation['allowed']:
            fail(evaluation['reason'])
    minimum = target.settings_snapshot['combat_requirement'][
        'dealer_min' if selection.selected_role == 'dealer' else 'support_min']
    power = core.power_comparison(db, uid, selection, minimum)
    if power['state'] in ('missing', 'below'):
        fail('COMBAT_POWER_REQUIRED')
    pairs = rounds(db, target)
    choices = {t.item_id: t for t in targets}
    all_items = set(db.scalars(select(Item.id).where(Item.room_id == room.id)))
    if resuming is not None:
        if (member is None or resuming.membership_id!=member.id or resuming.cycle_id!=target.id
                or resuming.generation!=target.generation or resuming.state!='stopped'):fail('TARGET_CONTEXT_STALE')
        if not resume_items:fail('TARGET_BUNDLE_INCOMPLETE')
        pairs=[(i,r) for i,r in pairs if r.state=='active' and i.id in resume_items]
        all_items={i.id for i,r in pairs}
    if not pairs or len(choices) != len(targets) or set(choices) != all_items or {i.id for i, r in pairs} != all_items:
        fail('ROOM_ITEMS_CHANGED')
    if size != (pairs[0][1].game_party_size if len(all_items) == 1 and len(target.settings_snapshot['items'])==1 else 4):
        fail('ROOM_COMPOSITION_CONFLICT')
    if replacing is not None and (member is None or replacing.membership_id!=member.id or replacing.user_id!=uid
            or replacing.cycle_id!=target.id or replacing.generation!=target.generation or replacing.state!='participating'):
        fail('TARGET_CONTEXT_STALE')
    if replacing is None and resuming is None and member is not None and db.scalar(select(CycleMember.id).where(CycleMember.cycle_id == target.id,
            CycleMember.generation == target.generation, CycleMember.membership_id == member.id,
            CycleMember.state.in_(('participating', 'completed', 'stopped')))) is not None:
        fail('ROOM_MEMBER_EXISTS')
    if replacing is None and member_count(db, target) >= size:
        fail('ROOM_FULL')
    from app.raid_rooms import admission_history
    history=admission_history.resolve(db,target,member) if replacing is None and resuming is None else None
    plans = []
    # Only the target capacity is visible to the pure composition helper.
    from types import SimpleNamespace
    formation = SimpleNamespace(app_capacity=size)
    for item, rd in pairs:
        choice = choices[item.id]
        if rd.state != 'active' or rd.ended_at is not None:
            fail('ROUND_NOT_ACTIVE')
        if choice.round_id != rd.id or choice.expected_round_revision != rd.revision:
            fail('REVISION_CONFLICT')
        if rd.catalog_version != core.raids.catalog().catalog_version:
            fail('CATALOG_VERSION_CONFLICT')
        try:
            difficulty = core.raids.difficulty(item.raid_id, rd.difficulty_id, rd.catalog_version)
        except core.raids.CatalogSelectionError as error:
            fail(error.code)
        try:
            level = Decimal(str(character.summary.get('item_level')))
        except (InvalidOperation, ValueError):
            level = None
        if not core.raids.meets_item_level(level, difficulty):
            fail('RAID_ITEM_LEVEL_REQUIRED')
        old=evaluation['owned'].get(item.id) if evaluation is not None and replacing is not None else (db.scalar(select(Assignment).where(Assignment.round_id==rd.id,Assignment.membership_id==member.id).order_by(Assignment.joined_at.desc(),Assignment.id.desc())) if member else None)
        if history is not None and old is not None:
            if old.id not in {a.id for a in history.assignments}:fail('TARGET_CONTEXT_STALE')
            old=None  # fresh assignment; never recycle the ended locator
        if old is not None and (old.state!='active' if replacing else old.state!='left'):
            fail('TARGET_CONTEXT_STALE')
        if replacing is None and old is not None and old.state=='left':
            from app.raid_rooms.cycle_models import CycleAssignment,ParticipationEvent
            binding=db.get(CycleAssignment,old.id)
            cm=db.get(CycleMember,binding.cycle_member_id) if binding else None
            event=db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==cm.id,ParticipationEvent.member_revision==cm.revision)) if cm else None
            if event is not None and event.evidence.get('membership_action') is True:old=None
        if replacing is not None and old is None:fail('TARGET_BUNDLE_INCOMPLETE')
        lease=db.get(WeeklyOccupancy,(uid,character.id,item.raid_id,target.cycle_key))
        own_lease=replacing is not None and lease is not None and lease.assignment_id==old.id
        state = db.get(WeeklyState,(uid,character.id,item.raid_id,target.cycle_key)) if own_lease else core.weekly.require_available_for_participation(db, uid, character.id, item.raid_id, target.cycle_key)
        if own_lease and (state is None or state.active_party_id!=room.id or state.manual_completed_at is not None or state.party_completed_at is not None):
            fail('WEEKLY_OCCUPANCY_CHANGED')
        if (state.revision if state else 1) != choice.expected_weekly_revision:
            fail('REVISION_CONFLICT')
        if lease is not None and not own_lease:
            fail('WEEKLY_ALREADY_PARTICIPATING')
        if choice.party_no > min(size // 4, rd.game_party_size // 4):
            fail('ROOM_COMPOSITION_CONFLICT')
        # Checking a free slot never reserves it. Pending returns above the
        # write phase, but must obey the same confirmed-party composition.
        slot = evaluation['slots'][item.id] if evaluation is not None else core._slot(db, formation, rd, selection, character, choice.party_no,
            exclude_membership_id=member.id if replacing else None)
        if replacing is not None and old.party_no==choice.party_no:slot=old.slot_no
        plans.append((item, rd, state, slot, old))
    if validate_only:
        return member, [], power
    if replacing is not None:
        for item,rd,state,slot,old in plans:core.release_assignment(db,old,stamp)
        db.flush()
    if member is None:
        member = Member(id=uuid.uuid4(), room_id=room.id, user_id=uid, revision=1, joined_at=stamp)
        db.add(member)
        db.flush()
        core.legacy.touch_user(db, uid)
    build = deepcopy(power)
    success = db.get(RolePowerSuccess, (uid, character.id, selection.expected_ownership_revision, selection.selected_role))
    if success:
        build['success_summary'] = deepcopy(success.source_summary)
    assignments = []
    for item, rd, state, slot, old in plans:
        values=dict(room_id=room.id, item_id=item.id, round_id=rd.id,
            membership_id=member.id, user_id=uid, character_id=character.id, selected_role=selection.selected_role,
            party_no=choices[item.id].party_no, slot_no=slot, display=core.identity.display(character),
            build=jsonable_encoder(build), ownership_revision=selection.expected_ownership_revision,
            lifecycle_revision=selection.expected_lifecycle_revision, state='active', joined_at=stamp,ended_at=None)
        if old is None:
            assignment=Assignment(id=uuid.uuid4(),revision=1,**values)
            db.add(assignment)
        else:
            assignment=old
            for name,value in values.items():setattr(assignment,name,value)
            assignment.revision+=1
        if state is None:
            state = WeeklyState(user_id=uid, character_id=character.id, raid_id=item.raid_id,
                cycle_key=target.cycle_key, revision=1, updated_at=stamp)
            db.add(state)
        state.active_party_id, state.active_difficulty_id, state.joined_at = room.id, rd.difficulty_id, stamp
        state.revision += 1
        state.updated_at = stamp
        db.flush()
        db.add(WeeklyOccupancy(user_id=uid, character_id=character.id, raid_id=item.raid_id,
            cycle_key=target.cycle_key, room_id=room.id, item_id=item.id, round_id=rd.id,
            assignment_id=assignment.id, joined_at=stamp))
        assignments.append(assignment)
    db.flush()
    if resuming is None:cycles.record_bundle_join(db, target.id, member.id, command_id, stamp)
    else:
        from app.raid_rooms.cycle_models import CycleAssignment
        for a in assignments:db.add(CycleAssignment(assignment_id=a.id,room_id=room.id,cycle_id=target.id,generation=target.generation,
            cycle_member_id=resuming.id,membership_id=member.id,user_id=uid,item_id=a.item_id,round_id=a.round_id))
        db.flush()
    return member, assignments, power
