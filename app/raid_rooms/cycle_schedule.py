"""Creation and admission graph for an explicit cycle/generation.

No current-week/global-leader inference. Coordinated resolution, edits and
worker transitions belong to W4. Copying an N graph never creates consent.
"""
import uuid
from datetime import date,datetime,time,timedelta,timezone
from sqlalchemy import select,func,text
from app.game_accounts.support import fail
from app.raid_rooms import scheduling as graph, cycle_admission as admission
from app.raid_rooms.cycle_application_models import CycleSession, CycleSessionSegment
from app.raid_rooms.integrated_models import RecruitmentSession as Session, RecruitmentSegment as Segment
from app.raid_rooms.source_models import (ScheduleGroup, ScheduleAlternative, SessionBinding,
    SegmentDurationEvidence,SessionParticipation)
from app.raid_rooms.schedule_heads import ScheduleHead


def planning_enabled(db):
    return list(db.scalars(text('SELECT version_num FROM public.alembic_version')))in (['0028_cycle_planning'],['0029_cycle_outcomes'],['0030_completion_corrections'],['0031_membership_actions'])


def groups(db,target):
    query=select(ScheduleGroup).join(ScheduleHead,ScheduleHead.group_id==ScheduleGroup.id).where(ScheduleHead.active.is_(True))
    if target.generation==1:
        return list(db.scalars(query.where(ScheduleGroup.room_id==target.room_id,ScheduleGroup.cycle_key==target.cycle_key)))
    from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
    return list(db.scalars(query.join(CycleScheduleGroup,CycleScheduleGroup.group_id==ScheduleGroup.id).where(
        CycleScheduleGroup.cycle_id==target.id,CycleScheduleGroup.generation==target.generation)))


def alternatives(db,group):
    if group.day_scope=='any_current_cycle':return []
    query=select(ScheduleAlternative).where(ScheduleAlternative.group_id==group.id)
    if planning_enabled(db):
        from app.raid_rooms.cycle_planning_models import CycleAlternative
        edition=db.scalar(select(func.max(CycleAlternative.edition)).where(CycleAlternative.group_id==group.id))
        if edition is not None:query=query.join(CycleAlternative,CycleAlternative.alternative_id==ScheduleAlternative.id).where(CycleAlternative.edition==edition)
    return list(db.scalars(query.order_by(ScheduleAlternative.id)))


def alternative_key(db,alternative):
    if planning_enabled(db):
        from app.raid_rooms.cycle_planning_models import CycleAlternative
        link=db.get(CycleAlternative,alternative.id)
        if link:return link.client_key
    return alternative.client_key


def local_start(key,weekday,clock):
    base=date.fromisoformat(key)
    day=base+timedelta(days=(weekday-3)%7)
    hour,minute=map(int,clock.split(':'))
    # Wed 00:00–05:55 belongs to the end of this actual cycle, not its
    # preceding calendar midnight. Never shift the requested cycle itself.
    if weekday==3 and hour<6:day+=timedelta(days=7)
    return datetime.combine(day,time(hour,minute),graph.raids.KST).astimezone(timezone.utc)


def sessions(db, target, *, history=False):
    return list(db.scalars(select(Session).join(CycleSession, CycleSession.session_id == Session.id)
        .join(SessionBinding,SessionBinding.session_id==Session.id).join(ScheduleHead,ScheduleHead.group_id==SessionBinding.group_id).where(
        CycleSession.cycle_id == target.id, CycleSession.generation == target.generation,ScheduleHead.active.is_(True),
        True if history else Session.state.in_(('unconfirmed','confirmed'))).order_by(Session.id)))


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


def final_deadlines(db,target,selected,stamp,*,join=True):
    if join:deadlines(db,target,selected,stamp)
    original={s.id:(s.state,s.schedule_revision) for s in sessions(db,target)}
    cutoffs=[v['join_deadline'] for v in choices(db,target,stamp) if join and (v['required'] or v['session_id'] in selected) and v['join_deadline'] is not None]
    def final(check):
        if any(check>=cutoff for cutoff in cutoffs):fail('RECRUITMENT_CLOSED')
        for sess in sessions(db,target):
            if sess.state=='confirmed' and original.get(sess.id)!=(sess.state,sess.schedule_revision) and sess.starts_at<check:fail('SCHEDULE_IN_PAST')
    return final


def enrol(db, target, member, selected, stamp, *, creating=False, copied=False):
    deadlines(db, target, selected, stamp)
    for session in sessions(db, target):
        if creating or db.get(SessionBinding, session.id).required or session.id in selected:
            old=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==session.id,
                SessionParticipation.membership_id==member.id))
            if old is not None and old.state=='ended':
                old.state='active';old.revision+=1
                old.confirmation_state='confirmation_pending' if session.state=='confirmed' else 'not_required'
                old.confirmed_at=old.confirmed_schedule_revision=None
            graph.participation(db, session, member,
                confirm=creating and session.state == 'confirmed' and not copied, stamp=stamp)


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
            client_key=value.client_group_key if target.generation==1 else f'g{target.generation}-{uuid.uuid4().hex}', revision=1, occurrence_mode=value.occurrence_mode,
            planning_mode=value.planning_mode, day_scope=value.day_scope, required=value.required,
            auto_additional_members=value.auto_confirm_additional_members)
        db.add(group)
        db.flush()
        db.add(ScheduleHead(group_id=group.id, client_key=value.client_group_key, active=True))
        if target.generation>1:
            from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
            db.add(CycleScheduleGroup(group_id=group.id,room_id=room.id,cycle_id=target.id,generation=target.generation))
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
