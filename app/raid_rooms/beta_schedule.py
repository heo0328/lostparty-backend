"""One promise per actual T. Callers hold the game mutation lock/transaction."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import secrets
import uuid
from sqlalchemy import select, text, or_
from app.game_accounts.support import fail
from app.raid_rooms import beta_profile, beta_schemas, time_policy
from app.raid_rooms.beta_models import (BetaSchedule, BetaAvailabilityCopy, BetaPromiseReservation,
                                        BetaApplicationMemo)

HEAD='0032_beta_recruitment'


def available(db):
    if 'beta_schema_ready' not in db.info:
        db.info['beta_schema_ready']=list(db.scalars(text('SELECT version_num FROM public.alembic_version')))==[HEAD]
    return db.info['beta_schema_ready']


def get(db,row):
    if row is None or not available(db):return None
    saved=db.get(BetaSchedule,row.id)
    return saved if saved is not None and saved.generation==row.generation else None


def personal_revision(db,uid):
    from app.raid_rooms.source_models import PersonalAvailability
    current=db.get(PersonalAvailability,uid)
    return current.revision if current else None



def context_basis(db,uid):
    """Bind current own busy evidence as well as the personal table revision."""
    from app.raid_rooms.source_models import TimeReservation
    reservations=list(db.execute(select(TimeReservation.id,TimeReservation.schedule_revision,
        TimeReservation.starts_at,TimeReservation.ends_at).where(TimeReservation.user_id==uid,
        TimeReservation.released_at.is_(None)).order_by(TimeReservation.id)))
    return [personal_revision(db,uid),[[str(rid),revision,start.isoformat(),end.isoformat()]
        for rid,revision,start,end in reservations]]

def config(value, *, key, capacity, duration, stamp, require_future=True):
    value=beta_schemas.BetaScheduleConfig.model_validate(value)
    if value.early_additional_members is not None and value.early_additional_members>=capacity:
        fail('INVALID_REQUEST',400)
    start=value.base_starts_at
    if not time_policy.aligned(start):fail('INVALID_REQUEST',400)
    time_policy.interval(start,start+timedelta(minutes=duration),key,
        floor=stamp+timedelta(minutes=30) if require_future else None,current=stamp if require_future else None)
    if require_future and stamp>=start-timedelta(minutes=30):fail('RECRUITMENT_CLOSED')
    return value


def query_config(prefix=''):
    params=beta_profile.query()
    try:
        raw=params[prefix+'early_coordination_enabled']
        if raw not in ('true','false'):raise ValueError()
        enabled=raw=='true';additional=params.get(prefix+'early_additional_members')
        if not enabled and additional is not None:raise ValueError()
        if additional is not None and (not additional.isascii() or not additional.isdigit()):raise ValueError()
        return beta_schemas.BetaScheduleConfig.model_validate(dict(
            base_starts_at=params[prefix+'base_starts_at'],early_coordination_enabled=enabled,
            early_additional_members=int(additional) if additional is not None else None))
    except (ValueError,KeyError,TypeError):fail('INVALID_REQUEST',400)


def copy_personal(db,row,cm,stamp):
    from app.raid_rooms import availability
    from app.raid_rooms.source_models import PersonalAvailability
    from app.raid_rooms.cycle_models import CycleSubmission
    availability.verified(db,cm.user_id)
    personal=db.get(PersonalAvailability,cm.user_id)
    if personal is not None and (not isinstance(personal.intervals,list) or not isinstance(personal.normalized_intervals,list)):
        fail('ROOM_REVIEW_REQUIRED')
    intervals=deepcopy(personal.intervals) if personal else []
    normalized=deepcopy(personal.normalized_intervals) if personal else []
    # Use the same typed interval rules as explicit personal saves. A failed or
    # inconsistent persisted normalization must never become all-available.
    from app.raid_rooms.availability_schemas import PersonalIn
    from pydantic import ValidationError
    try:
        PersonalIn.model_validate(dict(expected_version=personal.revision if personal else 1,timezone='Asia/Seoul',intervals=intervals))
        if availability.normalize(intervals)!=normalized:fail('ROOM_REVIEW_REQUIRED')
    except (ValidationError,TypeError,KeyError,ValueError):fail('ROOM_REVIEW_REQUIRED')
    current=db.get(CycleSubmission,cm.id)
    if current is None:
        current=CycleSubmission(cycle_member_id=cm.id,room_id=row.room_id,cycle_id=row.id,generation=row.generation,
            membership_id=cm.membership_id,user_id=cm.user_id,revision=1)
        db.add(current)
    else:current.revision+=1
    current.source_personal_revision=personal.revision if personal else 1
    current.intervals=intervals;current.normalized_intervals=normalized;current.submitted_at=stamp
    copied=db.get(BetaAvailabilityCopy,cm.id)
    if copied is None:
        copied=BetaAvailabilityCopy(cycle_member_id=cm.id)
        db.add(copied)
    copied.state='configured' if normalized else 'unset'
    copied.source_personal_version=personal.revision if personal else 1
    copied.copied_at=stamp
    db.flush()


def install(db,room,row,config_value,member,stamp):
    from app.raid_rooms import cycle_planning as plan, cycle_schedule as graph, cycle_lifecycle as life
    from app.raid_rooms.source_models import ScheduleGroup
    from app.raid_rooms.schedule_heads import ScheduleHead
    from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
    duration=sum(v['duration_minutes'] for v in row.settings_snapshot['items'])
    setting=config(config_value,key=row.cycle_key.isoformat(),capacity=graph.admission.capacity(row),duration=duration,stamp=stamp)
    group=ScheduleGroup(id=uuid.uuid4(),room_id=room.id,cycle_key=row.cycle_key,client_key=uuid.uuid4().hex,
        revision=1,occurrence_mode='one_of',planning_mode='coordinated' if setting.early_coordination_enabled else 'unscheduled',
        day_scope='any_current_cycle' if setting.early_coordination_enabled else 'selected_weekdays',required=True,
        auto_additional_members=setting.early_additional_members)
    db.add(group);db.flush()
    db.add(ScheduleHead(group_id=group.id,client_key='beta-base-promise',active=True))
    db.add(CycleScheduleGroup(group_id=group.id,room_id=room.id,cycle_id=row.id,generation=row.generation));db.flush()
    order=[uuid.UUID(v['item_id']) for v in row.settings_snapshot['items']]
    sess=plan.make_session(db,room,row,group,order,None,stamp)
    graph.graph.set_times(db,sess,setting.base_starts_at,row.cycle_key.isoformat(),stamp,validate_floor=False)
    saved=db.get(BetaSchedule,row.id)
    if saved is None:
        saved=BetaSchedule(cycle_id=row.id,number=None,password=f'{secrets.randbelow(100000):05d}')
        db.add(saved)
    saved.generation=row.generation;saved.session_id=sess.id;saved.revision=1
    saved.base_starts_at=sess.starts_at;saved.base_ends_at=sess.ends_at
    saved.early_enabled=setting.early_coordination_enabled;saved.early_additional_members=setting.early_additional_members
    saved.confirmation_kind=None;saved.needs_review=False
    db.flush()
    cm=life.actual_member(db,row,member.user_id,states=('participating',))
    enrol(db,row,cm,stamp)
    return saved


def enrol(db,row,cm,stamp,*,consent=True,copy=True):
    from app.raid_rooms import cycle_schedule as graph, cycle_lifecycle as life, cycle_times as times
    from app.raid_rooms.source_models import SessionParticipation, TimeReservation
    from app.raid_rooms.integrated_models import RecruitmentMembership as Member
    saved=get(db,row)
    if saved is None:return
    if copy:copy_personal(db,row,cm,stamp)
    sess=db.get(graph.Session,saved.session_id)
    part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==sess.id,
        SessionParticipation.membership_id==cm.membership_id))
    if part is not None and part.state=='ended':
        part.state='active';part.revision+=1
        part.confirmation_state='confirmation_pending' if sess.state=='confirmed' else 'not_required'
        part.confirmed_at=part.confirmed_schedule_revision=None
    part=graph.graph.participation(db,sess,db.get(Member,cm.membership_id),stamp=stamp)
    if not consent:return
    owned={a.round_id:a for a in life.assignments(db,row,cm) if a.state=='active'}
    segments=[s for s in graph.graph.active_segments(db,sess.id) if s.round_id in owned]
    if sess.state=='confirmed':
        times.record_confirmation(db,row,cm,sess,part,segments,owned,uuid.uuid4(),stamp,
            authorization=dict(kind='beta_current_promise_join'))
    else:
        for segment in segments:
            existing=db.scalar(select(TimeReservation.id).where(TimeReservation.participation_id==part.id,
                TimeReservation.segment_id==segment.id,TimeReservation.released_at.is_(None)))
            if existing:continue
            assignment=owned[segment.round_id]
            reservation=TimeReservation(id=uuid.uuid4(),room_id=row.room_id,participation_id=part.id,session_id=sess.id,
                membership_id=cm.membership_id,user_id=cm.user_id,assignment_id=assignment.id,item_id=segment.item_id,
                round_id=segment.round_id,segment_id=segment.id,schedule_revision=sess.schedule_revision,
                starts_at=segment.starts_at,ends_at=segment.ends_at)
            db.add(reservation);db.flush()
            db.add(BetaPromiseReservation(reservation_id=reservation.id,cycle_id=row.id,generation=row.generation,cycle_member_id=cm.id))
    db.flush()


def candidate(db,room,row,stamp):
    from app.raid_rooms import cycle_planning as plan,cycle_schedule as graph,cycle_times as times
    from app.raid_rooms.cycle_models import CycleSubmission
    from app.raid_rooms.source_models import TimeReservation
    saved=get(db,row)
    empty=dict(state='no_candidate',earliest_start=None,latest_start=None)
    if saved is None or saved.confirmation_kind or saved.needs_review or not saved.early_enabled or stamp>=saved.base_starts_at-timedelta(minutes=30):return empty
    actual=plan.members(db,row,db.get(graph.Session,saved.session_id))
    if not actual:return empty
    duration=saved.base_ends_at-saved.base_starts_at
    first,last=times.bounds(row)
    tick=time_policy.ceil_tick(max(stamp,plan.floor(db,row),first+timedelta(hours=4))).astimezone(timezone.utc)
    tables={};busy={}
    for cm in actual:
        copy=db.get(BetaAvailabilityCopy,cm.id);table=db.get(CycleSubmission,cm.id)
        if copy is None or table is None:return empty
        try:plan.life.qualify(db,room,row,cm)
        except plan.GameError:return empty
        tables[cm.id]=(copy,table)
        own_promises=select(BetaPromiseReservation.reservation_id).where(BetaPromiseReservation.cycle_id==row.id,
            BetaPromiseReservation.generation==row.generation,BetaPromiseReservation.cycle_member_id==cm.id)
        busy[cm.id]=list(db.execute(select(TimeReservation.starts_at,TimeReservation.ends_at).where(
            TimeReservation.user_id==cm.user_id,TimeReservation.released_at.is_(None),
            TimeReservation.starts_at<last,TimeReservation.ends_at>first,or_(TimeReservation.id.not_in(own_promises),TimeReservation.session_id!=saved.session_id))))
    found=[]
    while tick<saved.base_starts_at and tick+duration<=last:
        end=tick+duration
        if all((copy.state=='unset' or time_policy.covered(tick,end,table.normalized_intervals)) and
               not any(a<end and b>tick for a,b in busy[cm.id])
               for cm in actual for copy,table in [tables[cm.id]]):found.append(tick)
        tick+=time_policy.TICK
    return dict(state='ready' if found else 'no_candidate',earliest_start=found[0] if found else None,latest_start=found[-1] if found else None)


def confirm(db,room,row,saved,start,kind,stamp,command=None):
    from app.raid_rooms import cycle_planning as plan,cycle_schedule as graph,cycle_times as times,cycle_lifecycle as life
    from app.raid_rooms.source_models import SessionParticipation
    sess=db.get(graph.Session,saved.session_id)
    if saved.confirmation_kind:return
    actual=plan.members(db,row,sess)
    for cm in actual:
        part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==sess.id,
            SessionParticipation.membership_id==cm.membership_id))
        graph.graph.release(db,participation=part,reason='schedule_changed',stamp=stamp)
    if start!=sess.starts_at:
        graph.graph.set_times(db,sess,start,row.cycle_key.isoformat(),stamp,validate_floor=False)
        sess.schedule_revision+=1
    sess.state='confirmed';sess.revision+=1
    saved.confirmation_kind=kind;saved.needs_review=False;saved.revision+=1
    db.flush()
    for cm in actual:
        part=db.scalar(select(SessionParticipation).where(SessionParticipation.session_id==sess.id,
            SessionParticipation.membership_id==cm.membership_id))
        owned={a.round_id:a for a in life.assignments(db,row,cm) if a.state=='active'}
        segments=[s for s in graph.graph.active_segments(db,sess.id) if s.round_id in owned]
        times.record_confirmation(db,row,cm,sess,part,segments,owned,command or uuid.uuid4(),stamp,
            authorization=dict(kind=kind,base_starts_at=saved.base_starts_at.isoformat()))
    plan.bump(db,row);db.flush()
    if kind=='base_confirmed':
        from app.core.database import now
        # A stalled clock transaction must retry as needs_review, not commit
        # an invented confirmation after the original departure passed.
        if now(db)>=saved.base_starts_at:fail('SERVICE_UNAVAILABLE',503)


def initial(db,room,row,stamp,command=None):
    from app.raid_rooms import cycle_planning as plan,cycle_schedule as graph
    saved=get(db,row)
    if saved is None or saved.confirmation_kind or saved.needs_review or not saved.early_enabled:return
    sess=db.get(graph.Session,saved.session_id)
    if len(plan.members(db,row,sess))<1+saved.early_additional_members:return
    value=candidate(db,room,row,stamp)
    if value['state']=='ready':confirm(db,room,row,saved,value['earliest_start'],'early_confirmed',stamp,command)


def reconcile(db,room,row,stamp):
    from app.raid_rooms import cycle_planning as plan
    saved=get(db,row)
    if saved is None or saved.confirmation_kind or saved.needs_review or row.state!='open' or room.ended_at is not None:return
    if stamp<saved.base_starts_at-timedelta(minutes=30):return
    if stamp>=saved.base_starts_at:
        saved.needs_review=True;saved.revision+=1;plan.bump(db,row)
    else:confirm(db,room,row,saved,saved.base_starts_at,'base_confirmed',stamp)
    db.flush()


def view(db,row,stamp):
    from app.raid_rooms import cycle_schedule as graph
    from app.raid_rooms.integrated_models import RecruitmentRoom
    saved=get(db,row)
    if saved is None or saved.generation!=row.generation:return None
    sess=db.get(graph.Session,saved.session_id)
    ended=row.state=='closed' or db.get(RecruitmentRoom,row.room_id).ended_at is not None or sess.state in ('finished','cancelled')
    kind=saved.confirmation_kind
    due=not ended and not kind and not saved.needs_review and stamp>=saved.base_starts_at-timedelta(minutes=30)
    state=('ended' if ended else kind or ('needs_review' if saved.needs_review else 'deadline_pending' if due else 'coordinating' if saved.early_enabled else 'base_committed'))
    actual_start=sess.starts_at if kind else None;actual_end=sess.ends_at if kind else None
    effective=actual_start or saved.base_starts_at;effective_end=actual_end or saved.base_ends_at
    deadline_status=('obsolete' if ended or kind in ('early_confirmed','proposal_confirmed') else 'processed' if kind or saved.needs_review else 'due_unprocessed' if due else 'not_due')
    return dict(policy_version='beta-schedule-1',revision=saved.revision,session_id=sess.id,
        base_starts_at=saved.base_starts_at,base_ends_at=saved.base_ends_at,base_deadline_at=saved.base_starts_at-timedelta(minutes=30),
        early_coordination_enabled=saved.early_enabled,early_additional_members=saved.early_additional_members,
        coordination_state=state,coordination_active=state=='coordinating',confirmed_starts_at=actual_start,confirmed_ends_at=actual_end,
        effective_starts_at=effective,effective_ends_at=effective_end,admission_deadline=effective-timedelta(minutes=30),
        deadline_status=deadline_status,pending_transition=('departure_review_due' if stamp>=saved.base_starts_at else 'base_confirmation_due') if due else None,
        review_reason='departure_passed_unconfirmed' if state=='needs_review' else None,evaluated_at=stamp)


def reconcile_before(principal,payload):
    """Clock effects commit independently even when the user command then fails."""
    from app.core.database import session,now
    from app.game_accounts.support import authorize
    from app.raid_rooms import completed_room_lifecycle as archive,admission_service
    from app.raid_rooms.cycle_models import RoomCycle
    from app.raid_rooms.integrated_models import RecruitmentRoom
    with session() as db,db.begin():
        if not available(db):
            if beta_profile.enabled():fail('RECRUITMENT_COMMAND_NOT_READY',503)
            return
        uid=authorize(db,principal,write=True)
        rid=archive.mutation_room(db,payload)
        if rid is None:return
        room=admission_service.room(db,uid,rid)
        stamp=now(db)
        for row in db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)):
            reconcile(db,room,row,stamp)


BLOCKED_OPERATIONS=frozenset({'apply','join','approve','continue','open','character','submission','confirm',
    'edit-schedule','select-schedule','propose-schedule','schedule-response','target-settings'})


def require_client(db,rid,operation,payload):
    if beta_profile.enabled() or rid is None or operation not in BLOCKED_OPERATIONS or not available(db):return
    from app.raid_rooms.cycle_models import RoomCycle
    from datetime import date
    key=payload.get('body',payload).get('target_cycle_key')
    query=select(BetaSchedule.cycle_id).join(RoomCycle,RoomCycle.id==BetaSchedule.cycle_id).where(RoomCycle.room_id==rid)
    if key:query=query.where(RoomCycle.cycle_key==date.fromisoformat(key))
    if db.scalar(query.limit(1)) is not None:fail('CLIENT_UPGRADE_REQUIRED')


def edit(db,room,row,body,stamp,command):
    from app.raid_rooms import cycle_planning as plan,cycle_schedule as graph
    from app.raid_rooms.source_models import SessionBinding,ScheduleGroup
    saved=get(db,row)
    if saved is None:fail('BETA_SCHEDULE_REQUIRED')
    if saved.needs_review:fail('SCHEDULE_REVIEW_REQUIRED')
    if saved.confirmation_kind:fail('SCHEDULE_PROPOSAL_REQUIRED')
    if stamp>=saved.base_starts_at-timedelta(minutes=30):fail('RECRUITMENT_CLOSED')
    enabled=body['early_coordination_enabled'];additional=body['early_additional_members']
    if enabled != body['accept_immediate_confirmation'] or enabled != (additional is not None):fail('INVALID_REQUEST',400)
    if additional is not None and not 1<=additional<graph.admission.capacity(row):fail('INVALID_REQUEST',400)
    if (saved.early_enabled,saved.early_additional_members)==(enabled,additional):return
    saved.early_enabled=enabled;saved.early_additional_members=additional;saved.revision+=1
    group=db.get(ScheduleGroup,db.get(SessionBinding,saved.session_id).group_id)
    group.planning_mode='coordinated' if enabled else 'unscheduled'
    group.day_scope='any_current_cycle' if enabled else 'selected_weekdays'
    group.auto_additional_members=additional;group.revision+=1
    plan.bump(db,row);db.flush()
    if enabled:initial(db,room,row,stamp,command)
