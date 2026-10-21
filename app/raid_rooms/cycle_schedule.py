"""Creation and admission graph for an explicit cycle/generation.

No current-week/global-leader inference. Coordinated resolution, edits and
worker transitions belong to W4. Copying an N graph never creates consent.
"""
import uuid
from datetime import date,datetime,time,timedelta,timezone
from sqlalchemy import select
from app.game_accounts.support import fail
from app.raid_rooms import scheduling as graph, cycle_admission as admission
from app.raid_rooms.cycle_application_models import CycleSession, CycleSessionSegment
from app.raid_rooms.integrated_models import RecruitmentSession as Session, RecruitmentSegment as Segment
from app.raid_rooms.source_models import (ScheduleGroup, ScheduleAlternative, SessionBinding,
    SegmentDurationEvidence)
from app.raid_rooms.schedule_heads import ScheduleHead


def local_start(key,weekday,clock):
    base=date.fromisoformat(key)
    day=base+timedelta(days=(weekday-3)%7)
    hour,minute=map(int,clock.split(':'))
    # Wed 00:00–05:55 belongs to the end of this actual cycle, not its
    # preceding calendar midnight. Never shift the requested cycle itself.
    if weekday==3 and hour<6:day+=timedelta(days=7)
    return datetime.combine(day,time(hour,minute),graph.raids.KST).astimezone(timezone.utc)


def sessions(db, target):
    return list(db.scalars(select(Session).join(CycleSession, CycleSession.session_id == Session.id).where(
        CycleSession.cycle_id == target.id, CycleSession.generation == target.generation).order_by(Session.id)))


def choices(db, target, stamp):
    result = []
    for session in sessions(db, target):
        binding = db.get(SessionBinding, session.id)
        deadline = session.starts_at - timedelta(minutes=30) if session.state == 'confirmed' else None
        closed = deadline is not None and stamp >= deadline
        result.append(dict(session_id=session.id, required=binding.required, join_deadline=deadline,
            permission=dict(allowed=not closed, reason='RECRUITMENT_CLOSED' if closed else None,
                next_change_at=deadline if not closed else None)))
    return result


def deadlines(db, target, selected, stamp):
    available = choices(db, target, stamp)
    ids = {r['session_id'] for r in available}
    if len(set(selected)) != len(selected) or set(selected) - ids:
        fail('INVALID_REQUEST', 400)
    for row in available:
        if (row['required'] or row['session_id'] in selected) and not row['permission']['allowed']:
            fail('RECRUITMENT_CLOSED')


def enrol(db, target, member, selected, stamp, *, creating=False, copied=False):
    deadlines(db, target, selected, stamp)
    for session in sessions(db, target):
        if creating or db.get(SessionBinding, session.id).required or session.id in selected:
            graph.participation(db, session, member,
                confirm=session.state == 'confirmed' and not copied, stamp=stamp)


def install(db, room, target, inputs, member, stamp, *, copied=False):
    if len({g.client_group_key for g in inputs}) != len(inputs):
        fail('INVALID_REQUEST', 400)
    if inputs and not any(g.required for g in inputs):
        fail('REQUIRED_SESSION_REQUIRED')
    pairs = {i.raid_id: (i, rd) for i, rd in admission.rounds(db, target)}
    for value in inputs:
        if value.existing_group_id is not None or value.expected_group_revision is not None:
            fail('INVALID_REQUEST', 400)
        if value.planning_mode == 'coordinated':
            if value.auto_confirm_additional_members is None or not 1 <= value.auto_confirm_additional_members < admission.capacity(target):
                fail('INVALID_REQUEST', 400)
        elif value.auto_confirm_additional_members is not None:
            fail('INVALID_REQUEST', 400)
        if value.day_scope == 'any_current_cycle':
            if value.planning_mode != 'coordinated' or value.occurrence_mode != 'one_of' or value.alternatives:
                fail('INVALID_REQUEST', 400)
        elif not value.alternatives:
            fail('INVALID_REQUEST', 400)
        if len({a.client_alternative_key for a in value.alternatives}) != len(value.alternatives):
            fail('INVALID_REQUEST', 400)
        group = ScheduleGroup(id=uuid.uuid4(), room_id=room.id, cycle_key=target.cycle_key,
            client_key=value.client_group_key, revision=1, occurrence_mode=value.occurrence_mode,
            planning_mode=value.planning_mode, day_scope=value.day_scope, required=value.required,
            auto_additional_members=value.auto_confirm_additional_members)
        db.add(group)
        db.flush()
        db.add(ScheduleHead(group_id=group.id, client_key=group.client_key, active=True))
        for choice in value.alternatives:
            if choice.existing_session_id is not None or choice.expected_session_revision is not None:
                fail('INVALID_REQUEST', 400)
            if (choice.starts_local is not None) != (value.planning_mode == 'manual'):
                fail('INVALID_REQUEST', 400)
            if len(choice.item_order) != len(pairs) or set(choice.item_order) != set(pairs):
                fail('ROOM_ITEMS_CHANGED')
            if choice.starts_local and choice.leader_latest_start_local and choice.starts_local > choice.leader_latest_start_local:
                fail('LEADER_START_LIMIT')
            minute = lambda v: int(v[:2])*60 + int(v[3:]) if v else None
            alternative = ScheduleAlternative(id=uuid.uuid4(), room_id=room.id, group_id=group.id,
                client_key=choice.client_alternative_key, weekday=choice.weekday, start_minute=minute(choice.starts_local),
                latest_start_minute=minute(choice.leader_latest_start_local),
                item_order=[str(pairs[r][0].id) for r in choice.item_order])
            db.add(alternative)
            db.flush()
            if value.planning_mode != 'manual' or (value.occurrence_mode != 'each' and len(value.alternatives) != 1):
                continue
            session = Session(id=uuid.uuid4(), room_id=room.id, revision=1, schedule_revision=1,
                state='unconfirmed', created_at=stamp)
            db.add(session)
            db.flush()
            db.add(CycleSession(session_id=session.id, room_id=room.id, cycle_id=target.id, generation=target.generation))
            db.add(SessionBinding(session_id=session.id, room_id=room.id, group_id=group.id, required=group.required))
            db.flush()
            for ordinal, raid in enumerate(choice.item_order, 1):
                item, rd = pairs[raid]
                evidence=next((v for v in target.settings_snapshot['items'] if v['item_id']==str(item.id)),None)
                if evidence is None:fail('ROOM_REVIEW_REQUIRED')
                minutes,source=evidence['duration_minutes'],evidence['duration_source']
                segment = Segment(id=uuid.uuid4(), room_id=room.id, session_id=session.id,
                    item_id=item.id, round_id=rd.id, ordinal=ordinal, duration_minutes=minutes, duration_source=source)
                db.add(segment)
                db.flush()
                db.add(SegmentDurationEvidence(segment_id=segment.id, room_id=room.id, session_id=session.id,
                    item_id=item.id, round_id=rd.id, item_settings_revision=evidence['item_settings_revision'],
                    duration_policy_version=evidence['duration_policy_version']))
                db.add(CycleSessionSegment(segment_id=segment.id, room_id=room.id, session_id=session.id,
                    cycle_id=target.id, generation=target.generation, item_id=item.id, round_id=rd.id))
            db.flush()
            start = local_start(target.cycle_key.isoformat(), choice.weekday, choice.starts_local)
            graph.set_times(db, session, start, target.cycle_key.isoformat(), stamp, validate_floor=False)
            graph.time.interval(start, session.ends_at, target.cycle_key.isoformat(),
                floor=stamp + timedelta(minutes=30), current=stamp)
            session.state = 'confirmed'
            alternative.session_id = session.id
            if group.occurrence_mode == 'one_of':
                group.selected_session_id = session.id
            db.flush()
    enrol(db, target, member, [], stamp, creating=True, copied=copied)
