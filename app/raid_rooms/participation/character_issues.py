"""Read-only missing-character projections for own summaries and authorized targets."""
from datetime import date, timedelta
from sqlalchemy import and_, select
from app.game_accounts import roster_presence
from app.game_accounts.rosters.lifecycle import digest
from app.game_accounts.models import Account, Character, NameClaim, Registration
from app.game_accounts.support import fail
from app.raid_rooms.common import active_usage
from app.raid_rooms.admissions import admission_service as base
from app.raid_rooms.cycle_models import RoomCycle, CycleMember, CycleAssignment
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member, RecruitmentAssignment as Assignment
from app.raids.service import cycle

CODE = 'ROSTER_CHARACTER_MISSING'


def rows(db, stamp, *, owner_id=None, room_id=None, target_key=None):
    if not roster_presence.enabled(db):
        fail('RECRUITMENT_COMMAND_NOT_READY', 503)
    current = date.fromisoformat(cycle(stamp).cycle_key)
    transition = roster_presence.RosterTransition
    query = (select(Member, RoomCycle, CycleMember, Assignment, Character, transition).select_from(Member)
        .join(Room, Room.id == Member.room_id)
        .join(RoomCycle, RoomCycle.room_id == Room.id)
        .join(CycleMember, and_(CycleMember.cycle_id == RoomCycle.id,
            CycleMember.generation == RoomCycle.generation, CycleMember.membership_id == Member.id,
            CycleMember.user_id == Member.user_id))
        .join(CycleAssignment, and_(CycleAssignment.cycle_id == RoomCycle.id,
            CycleAssignment.generation == RoomCycle.generation, CycleAssignment.cycle_member_id == CycleMember.id,
            CycleAssignment.membership_id == Member.id, CycleAssignment.user_id == Member.user_id))
        .join(Assignment, and_(Assignment.id == CycleAssignment.assignment_id,
            Assignment.room_id == Room.id, Assignment.membership_id == Member.id,
            Assignment.user_id == Member.user_id, Assignment.round_id == CycleAssignment.round_id,
            Assignment.item_id == CycleAssignment.item_id))
        .join(Character, Character.id == Assignment.character_id)
        .join(Account, and_(Account.id == Character.account_id, Account.owner_id == Member.user_id,
            Account.ownership_revision == Assignment.ownership_revision))
        .join(NameClaim, and_(NameClaim.character_id == Character.id,
            NameClaim.server_name == Character.server_name, NameClaim.character_name == Character.character_name))
        .join(transition, and_(transition.character_id == Character.id,
            transition.account_id == Account.id, transition.owner_id == Member.user_id,
            transition.ownership_revision == Account.ownership_revision,
            transition.to_revision == Character.lifecycle_revision, transition.state == 'missing'))
        .where(active_usage.predicate(), RoomCycle.provenance == 'explicit',
            Account.verified_at.is_not(None),
            select(Registration.id).where(Registration.user_id == Member.user_id,
                Registration.account_id == Account.id, Registration.deleted_at.is_(None)).exists(),
            RoomCycle.cycle_key.in_((current, current + timedelta(days=7))),
            Assignment.state == 'active', Character.lifecycle_state == 'suspect', Character.status == 'suspect')
        .order_by(Room.id, RoomCycle.cycle_key, CycleMember.id, Assignment.id))
    if owner_id is not None:
        query = query.where(Member.user_id == owner_id)
    if room_id is not None:
        query = query.where(Room.id == room_id)
    if target_key is not None:
        query = query.where(RoomCycle.cycle_key == date.fromisoformat(target_key))
    return list(db.execute(query))


def summary(principal):
    with base.snapshot(principal) as (db, uid, stamp):
        values = rows(db, stamp, owner_id=uid)
        current = date.fromisoformat(cycle(stamp).cycle_key)
        return dict(profile='roster-character-issues-1',
            cycles=[dict(target_cycle_key=key.isoformat(),has_issues=any(t.cycle_key==key for _,t,*_ in values),
                affected_room_count=len({m.room_id for m,t,*_ in values if t.cycle_key==key}))
                for key in (current,current+timedelta(days=7))],has_issues=bool(values),
            affected_room_count=len({m.room_id for m, *_ in values}),
            affected_target_count=len({target.id for _, target, *_ in values}),
            current_cycle_key=current.isoformat(), next_cycle_key=(current + timedelta(days=7)).isoformat(),
            evaluated_at=stamp, issues_revision=digest([
                current, [[str(a.id), a.revision, str(t.id), str(cm.id), str(v.id)]
                          for _, t, cm, a, _, v in values]]))


def for_target(db, uid, room_id, target_key, stamp):
    # Persistent membership alone is not permission to see another actual week.
    viewer = db.scalar(select(CycleMember).join(RoomCycle, RoomCycle.id == CycleMember.cycle_id)
        .join(Member, Member.id == CycleMember.membership_id).where(
            RoomCycle.room_id == room_id, RoomCycle.cycle_key == date.fromisoformat(target_key),
            CycleMember.generation == RoomCycle.generation, CycleMember.user_id == uid,
            CycleMember.state.in_(('participating', 'completed', 'review_required')),
            Member.ended_at.is_(None)))
    if viewer is None:
        return []
    values = rows(db, stamp, room_id=room_id, target_key=target_key)
    mine = {c.account_id for m, _, _, _, c, _ in values if m.user_id == uid}
    registrations = dict(db.execute(select(Registration.account_id, Registration.id).where(
        Registration.user_id == uid, Registration.account_id.in_(mine), Registration.deleted_at.is_(None))).all()) if mine else {}
    return [dict(code=CODE, character_id=c.id, character_name=a.display.get('character_name'),
        target_cycle_key=target.cycle_key.isoformat(), assignment_id=a.id, cycle_member_id=cm.id,
        observed_at=observation.observed_at,
        registration_id=registrations.get(c.account_id) if member.user_id == uid else None)
        for member, target, cm, a, c, observation in values]


def issue_values(db, uid, stamp, *, room_id=None, target_key=None, owner_id=None):
    grouped = {}
    for member, target, cm, a, c, observation in rows(db,stamp,owner_id=owner_id,room_id=room_id,target_key=target_key):
        key = (target.id,cm.id,c.id)
        if key not in grouped:
            registration = db.scalar(select(Registration.id).where(Registration.user_id==uid,
                Registration.account_id==c.account_id,Registration.deleted_at.is_(None))) if member.user_id==uid else None
            grouped[key] = dict(code=CODE,room_id=member.room_id,target_cycle_key=target.cycle_key.isoformat(),
                room_cycle_id=target.id,target_generation=target.generation,cycle_member_id=cm.id,
                character_id=c.id,character_name=a.display.get('character_name'),assignment_ids=[],
                observed_at=observation.observed_at,registration_id=registration)
        grouped[key]['assignment_ids'].append(a.id)
    return list(grouped.values())


def own_page(db,uid,stamp,room_ids=None,target_key=None):
    from fastapi.encoders import jsonable_encoder
    items=issue_values(db,uid,stamp,owner_id=uid,target_key=target_key)
    if room_ids is not None:items=[i for i in items if i['room_id'] in room_ids]
    return dict(profile='roster-character-issues-1',evaluated_at=stamp,
        issues_revision=digest(jsonable_encoder([uid,items])),items=items)


def room_context(db,uid,rid,key,stamp):
    from fastapi.encoders import jsonable_encoder
    current=date.fromisoformat(cycle(stamp).cycle_key)
    summaries=[];selected=None
    for actual in (current,current+timedelta(days=7)):
        viewer=db.scalar(select(CycleMember.id).join(RoomCycle,RoomCycle.id==CycleMember.cycle_id)
            .join(Member,Member.id==CycleMember.membership_id).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==actual,
                CycleMember.generation==RoomCycle.generation,CycleMember.user_id==uid,
                CycleMember.state.in_(('participating','completed','review_required')),Member.ended_at.is_(None)))
        items=issue_values(db,uid,stamp,room_id=rid,target_key=actual.isoformat()) if viewer else None
        summaries.append(dict(target_cycle_key=actual.isoformat(),state='ready' if viewer else 'not_authorized',
            has_issues=bool(items) if viewer else None,
            affected_participant_count=len({i['cycle_member_id'] for i in items}) if viewer else None))
        if actual.isoformat()==key:selected=items
    return dict(profile='roster-character-issues-1',evaluated_at=stamp,
        issues_revision=digest(jsonable_encoder([uid,rid,summaries,selected])),
        target_summaries=summaries,selected_target_issues=selected)
