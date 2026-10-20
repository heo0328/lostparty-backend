"""Integrated schedule graph and exact reservations. Caller owns write lock/tx."""
import uuid
from datetime import date,timedelta
from sqlalchemy import select,delete
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail
from app.core.database import now
from app.raids import service as raids
from app.raid_rooms import time_policy as time
from app.raid_rooms.integrated_models import (RecruitmentItem as Item,RecruitmentRound as Round,
    RecruitmentMembership as Member,RecruitmentAssignment as Assignment,RecruitmentSession as Session,RecruitmentSegment as Segment)
from app.raid_rooms.source_models import (ScheduleGroup,ScheduleAlternative,SessionBinding,SessionParticipation as Participation,
    TimeReservation as Reservation,AvailabilitySubmission,ItemSettings,SegmentDurationEvidence,OpeningEvent,
    ScheduleProposal as Proposal,ProposalTarget,ProposalResponse)
from app.raid_rooms.schedule_heads import ScheduleHead

DEFAULTS={'normal':10,'hard':20,'nightmare':30,'stage1':10,'stage2':20,'stage3':30}


def members(db,rid):
    return list(db.scalars(select(Member).where(Member.room_id==rid,Member.ended_at.is_(None)).order_by(Member.id)))


def active_items(db,rid,cycle_key):
    return list(db.scalars(select(Item).where(Item.room_id==rid,select(Round.id).where(
        Round.item_id==Item.id,Round.state=='active',Round.cycle_key==date.fromisoformat(cycle_key)).exists()).order_by(Item.id)))


def current_members(db,rid,cycle_key):
    return [m for m in members(db,rid) if db.scalar(select(Assignment.id).join(Round,Round.id==Assignment.round_id).where(
        Assignment.membership_id==m.id,Assignment.state=='active',Round.state=='active',Round.cycle_key==date.fromisoformat(cycle_key)).limit(1)) is not None]


def sessions(db,rid,stamp=None):
    return list(db.scalars(select(Session).join(SessionBinding,SessionBinding.session_id==Session.id).join(ScheduleGroup,ScheduleGroup.id==SessionBinding.group_id).join(ScheduleHead,ScheduleHead.group_id==ScheduleGroup.id).where(
        Session.room_id==rid,Session.state.in_(['unconfirmed','confirmed']),ScheduleHead.active.is_(True),ScheduleGroup.cycle_key==date.fromisoformat(raids.cycle(stamp or now(db)).cycle_key)).order_by(Session.id)))


def groups(db,rid,cycle_key):
    return list(db.scalars(select(ScheduleGroup).join(ScheduleHead,ScheduleHead.group_id==ScheduleGroup.id).where(
        ScheduleGroup.room_id==rid,ScheduleHead.active.is_(True),ScheduleGroup.cycle_key==date.fromisoformat(cycle_key)).order_by(ScheduleGroup.id)))


def segments(db,sid):
    return list(db.scalars(select(Segment).where(Segment.session_id==sid).order_by(Segment.ordinal)))


def active_segments(db,sid):
    return list(db.scalars(select(Segment).join(Round,Round.id==Segment.round_id).where(
        Segment.session_id==sid,Round.state=='active',Round.ended_at.is_(None)).order_by(Segment.ordinal)))


def assignments(db,member,session):
    segs=segments(db,session.id)
    return list(db.scalars(select(Assignment).join(Round,Round.id==Assignment.round_id).where(Assignment.membership_id==member.id,Assignment.state=='active',
        Round.state=='active',Round.ended_at.is_(None),Assignment.round_id.in_([s.round_id for s in segs]))))


def floor(db,rid,cycle_key):
    value=db.scalar(select(OpeningEvent.search_floor_at).where(OpeningEvent.room_id==rid,
        OpeningEvent.target_cycle==(date.fromisoformat(cycle_key) if isinstance(cycle_key,str) else cycle_key),OpeningEvent.state=='applied').order_by(OpeningEvent.search_floor_at.desc()).limit(1))
    if value is None:fail('OPENING_EVENT_REQUIRED')
    return value


def duration(db,item):
    settings=db.get(ItemSettings,item.id)
    if settings is None:fail('DURATION_POLICY_UNAVAILABLE')
    value=settings.duration_minutes if settings.duration_minutes is not None else DEFAULTS.get(settings.difficulty_id)
    if value is None:fail('DURATION_POLICY_UNAVAILABLE')
    return value,'explicit' if settings.duration_minutes is not None else 'difficulty_default',settings


def release(db,*,participation=None,assignment=None,reason,stamp):
    query=select(Reservation).where(Reservation.released_at.is_(None))
    if participation is not None:query=query.where(Reservation.participation_id==participation.id)
    if assignment is not None:query=query.where(Reservation.assignment_id==assignment.id)
    if participation is None and assignment is None:raise ValueError('Exact reservation owner required')
    for row in db.scalars(query):row.released_at=stamp;row.released_reason=reason
    db.flush()


def reserve(db,part,session,stamp):
    if session.state!='confirmed':return
    if part.confirmation_state=='confirmed' and part.confirmed_schedule_revision==session.schedule_revision:return
    own={a.round_id:a for a in assignments(db,db.get(Member,part.membership_id),session)}
    from app.game_accounts.profiles import owned_character
    from app.game_accounts.lifecycle import require_usable
    for assignment in own.values():
        account,character=owned_character(db,part.user_id,assignment.character_id)
        require_usable(db,character)
        if account.ownership_revision!=assignment.ownership_revision or character.lifecycle_revision!=assignment.lifecycle_revision:fail('REVISION_CONFLICT')
    for segment in segments(db,session.id):
        assignment=own.get(segment.round_id)
        if assignment is None:continue
        existing=db.scalar(select(Reservation).where(Reservation.participation_id==part.id,
            Reservation.segment_id==segment.id,Reservation.schedule_revision==session.schedule_revision))
        if existing is not None:
            if existing.released_at is not None:fail('RESERVATION_GENERATION_ENDED')
            continue
        db.add(Reservation(id=uuid.uuid4(),room_id=session.room_id,participation_id=part.id,session_id=session.id,
            membership_id=part.membership_id,user_id=part.user_id,assignment_id=assignment.id,item_id=segment.item_id,
            round_id=segment.round_id,segment_id=segment.id,schedule_revision=session.schedule_revision,
            starts_at=segment.starts_at,ends_at=segment.ends_at))
    part.confirmation_state='confirmed';part.confirmed_schedule_revision=session.schedule_revision;part.confirmed_at=stamp
    db.flush()


def participation(db,session,member,*,confirm=False,stamp):
    row=db.scalar(select(Participation).where(Participation.session_id==session.id,Participation.membership_id==member.id))
    if row is None:
        row=Participation(id=uuid.uuid4(),room_id=session.room_id,session_id=session.id,membership_id=member.id,user_id=member.user_id,
            revision=1,state='active',confirmation_state='confirmation_pending' if session.state=='confirmed' else 'not_required')
        db.add(row);db.flush()
    elif row.state!='active':fail('PARTICIPATION_ENDED')
    if confirm:reserve(db,row,session,stamp)
    return row


def set_times(db,session,start,cycle_key,stamp,*,validate_floor=True):
    values=segments(db,session.id)
    total=sum(s.duration_minutes for s in values)
    if not values or total>1440:fail('SESSION_DURATION_EXCEEDED')
    end=start+timedelta(minutes=total)
    time.interval(start,end,cycle_key,floor=floor(db,session.room_id,cycle_key) if validate_floor else None,current=stamp)
    cursor=start
    for segment in values:
        segment.starts_at=cursor;segment.ends_at=cursor+timedelta(minutes=segment.duration_minutes);cursor=segment.ends_at
    session.starts_at=start;session.ends_at=end


def make_session(db,room,group,item_ids,start,stamp,alternative=None,*,confirm_leader=True):
    cycle_key=raids.cycle(stamp).cycle_key
    all_items=active_items(db,room.id,cycle_key)
    if len(set(item_ids))!=len(item_ids) or set(item_ids)!={i.id for i in all_items}:fail('ROOM_ITEMS_CHANGED')
    session=Session(id=uuid.uuid4(),room_id=room.id,revision=1,schedule_revision=1,state='unconfirmed',created_at=stamp)
    db.add(session);db.flush()
    for n,iid in enumerate(item_ids,1):
        item=db.get(Item,iid)
        rd=db.scalar(select(Round).where(Round.item_id==iid,Round.state=='active',Round.cycle_key==date.fromisoformat(raids.cycle(stamp).cycle_key)))
        if rd is None:fail('ROUND_NOT_ACTIVE')
        minutes,source,settings=duration(db,item)
        segment=Segment(id=uuid.uuid4(),room_id=room.id,session_id=session.id,item_id=iid,round_id=rd.id,ordinal=n,
            duration_minutes=minutes,duration_source=source)
        db.add(segment);db.flush()
        db.add(SegmentDurationEvidence(segment_id=segment.id,room_id=room.id,session_id=session.id,item_id=iid,
            round_id=rd.id,item_settings_revision=settings.revision,duration_policy_version=settings.duration_policy_version))
    db.flush()
    if sum(s.duration_minutes for s in segments(db,session.id))>1440:fail('SESSION_DURATION_EXCEEDED')
    db.add(SessionBinding(room_id=room.id,session_id=session.id,group_id=group.id,required=group.required));db.flush()
    if alternative is not None:alternative.session_id=session.id
    if group.occurrence_mode=='one_of':group.selected_session_id=session.id
    if start is not None:
        set_times(db,session,start,cycle_key,stamp);session.state='confirmed'
    db.flush()
    for m in members(db,room.id):
        if (group.required or m.id==room.leader_membership_id) and assignments(db,m,session):
            participation(db,session,m,confirm=confirm_leader and session.state=='confirmed' and m.id==room.leader_membership_id,stamp=stamp)
    return session


def install(db,room,inputs,stamp,*,creating=False,confirm_leader=True):
    if len({g.client_group_key for g in inputs})!=len(inputs):fail('INVALID_REQUEST',400)
    current=groups(db,room.id,raids.cycle(stamp).cycle_key)
    if any(s.state=='confirmed' for s in sessions(db,room.id)):fail('SCHEDULE_PROPOSAL_REQUIRED')
    items={i.raid_id:i.id for i in active_items(db,room.id,raids.cycle(stamp).cycle_key)}
    def order(alt):return list(alt.item_ids) if hasattr(alt,'item_ids') else [items.get(r) for r in alt.item_order]
    if inputs and not any(g.required for g in inputs):fail('REQUIRED_SESSION_REQUIRED')
    for data in inputs:
        if creating and (data.existing_group_id is not None or data.expected_group_revision is not None):fail('INVALID_REQUEST',400)
        if (data.existing_group_id is None)!=(data.expected_group_revision is None):fail('INVALID_REQUEST',400)
        if data.existing_group_id is not None:
            old=db.get(ScheduleGroup,data.existing_group_id)
            if old is None or old.room_id!=room.id or old not in current or old.revision!=data.expected_group_revision:fail('REVISION_CONFLICT')
        if data.planning_mode=='coordinated':
            if data.auto_confirm_additional_members is None or not 1<=data.auto_confirm_additional_members<room.app_capacity:fail('INVALID_REQUEST',400)
        elif data.auto_confirm_additional_members is not None:fail('INVALID_REQUEST',400)
        if data.day_scope=='any_current_cycle':
            if data.planning_mode!='coordinated' or data.occurrence_mode!='one_of' or data.alternatives:fail('INVALID_REQUEST',400)
        elif not data.alternatives:fail('INVALID_REQUEST',400)
        if len({a.client_alternative_key for a in data.alternatives})!=len(data.alternatives):fail('INVALID_REQUEST',400)
        for alt in data.alternatives:
            if alt.existing_session_id is not None or alt.expected_session_revision is not None:fail('SCHEDULE_PROPOSAL_REQUIRED')
            if (alt.starts_local is not None)!=(data.planning_mode=='manual'):fail('INVALID_REQUEST',400)
            if len(order(alt))!=len(items) or set(order(alt))!=set(items.values()):fail('ROOM_ITEMS_CHANGED')
            if alt.starts_local and alt.leader_latest_start_local and alt.starts_local>alt.leader_latest_start_local:fail('LEADER_START_LIMIT')
    # Only unconfirmed draft graphs can be replaced directly; confirmed graphs require proposals.
    for old in current:
        old.selected_session_id=None
    db.flush()
    for session in sessions(db,room.id):
        if db.scalar(select(ProposalTarget.proposal_id).where(ProposalTarget.session_id==session.id)):fail('SCHEDULE_PROPOSAL_REQUIRED')
        if db.scalar(select(Reservation.id).where(Reservation.session_id==session.id)):fail('SCHEDULE_PROPOSAL_REQUIRED')
        for model in (Participation,SegmentDurationEvidence,Segment,ScheduleAlternative,SessionBinding):
            key=model.session_id
            db.execute(delete(model).where(key==session.id))
        db.delete(session)
    db.flush()
    for old in current:
        db.execute(delete(ScheduleAlternative).where(ScheduleAlternative.group_id==old.id))
        db.delete(db.get(ScheduleHead,old.id));db.flush();db.delete(old)
    db.flush()
    for data in inputs:
        group=ScheduleGroup(id=data.existing_group_id or uuid.uuid4(),room_id=room.id,cycle_key=date.fromisoformat(raids.cycle(stamp).cycle_key),
            client_key=data.client_group_key,revision=(data.expected_group_revision+1) if data.expected_group_revision else 1,
            occurrence_mode=data.occurrence_mode,planning_mode=data.planning_mode,day_scope=data.day_scope,required=data.required,
            auto_additional_members=data.auto_confirm_additional_members)
        db.add(group);db.flush()
        db.add(ScheduleHead(group_id=group.id,client_key=data.client_group_key,active=True));db.flush()
        for value in data.alternatives:
            minute=lambda v: int(v[:2])*60+int(v[3:]) if v else None
            alt=ScheduleAlternative(id=uuid.uuid4(),room_id=room.id,group_id=group.id,client_key=value.client_alternative_key,
                weekday=value.weekday,start_minute=minute(value.starts_local),latest_start_minute=minute(value.leader_latest_start_local),
                item_order=[str(i) for i in order(value)])
            db.add(alt);db.flush()
            if group.planning_mode=='manual' and (group.occurrence_mode=='each' or len(data.alternatives)==1):
                make_session(db,room,group,order(value),
                    time.local_start(raids.cycle(stamp).cycle_key,value.weekday,value.starts_local),stamp,alt,confirm_leader=confirm_leader)
    db.flush()


def enrol(db,room,member,selected,stamp,*,creating=False):
    actual=sessions(db,room.id);ids={s.id for s in actual}
    if len(set(selected))!=len(selected) or set(selected)-ids:fail('INVALID_REQUEST',400)
    for session in actual:
        binding=db.get(SessionBinding,session.id)
        if binding.required or session.id in selected or creating:
            participation(db,session,member,confirm=session.state=='confirmed',stamp=stamp)
    # Every newcomer is a fresh pending responder, not an implicit proposal vote.
    for prop in db.scalars(select(Proposal).where(Proposal.room_id==room.id,Proposal.state=='pending')):
        ensure_response(db,prop,member,stamp)


def deadlines(db,room,selected,stamp,*,final=False):
    for session in sessions(db,room.id):
        binding=db.get(SessionBinding,session.id)
        if session.state=='confirmed' and (binding.required or session.id in selected):
            if stamp>=session.starts_at-timedelta(minutes=30):fail('RECRUITMENT_CLOSED')


def busy(db,uid,start,end,*,excluding=None):
    query=select(Reservation.id).where(Reservation.user_id==uid,Reservation.released_at.is_(None),
        Reservation.starts_at<end,Reservation.ends_at>start)
    if excluding is not None:query=query.where(Reservation.session_id!=excluding)
    return db.scalar(query.limit(1)) is not None


def candidate(db,room,group,stamp,*,session=None,weekday=None):
    current=current_members(db,room.id,raids.cycle(stamp).cycle_key)
    target=current if group.required and session is None else (
        [db.get(Member,p.membership_id) for p in db.scalars(select(Participation).where(Participation.session_id==session.id,Participation.state=='active'))]
        if session else [db.get(Member,room.leader_membership_id)])
    target=[m for m in target if m.id in {c.id for c in current}]
    tables=[db.get(AvailabilitySubmission,m.id) for m in target]
    if not target or any(t is None for t in tables):return dict(state='no_candidate',earliest_start=None,latest_start=None)
    cycle=raids.cycle(stamp)
    item_ids=[i.id for i in active_items(db,room.id,cycle.cycle_key)]
    minutes=sum(duration(db,db.get(Item,i))[0] for i in item_ids)
    if minutes>1440:fail('SESSION_DURATION_EXCEEDED')
    alternatives=list(db.scalars(select(ScheduleAlternative).where(ScheduleAlternative.group_id==group.id)))
    selected_alt=next((a for a in alternatives if session and a.session_id==session.id),None)
    if selected_alt is not None:weekday=selected_alt.weekday
    lower=time.ceil_tick(max(stamp,floor(db,room.id,cycle.cycle_key),cycle.starts_at+timedelta(hours=4)))
    found=[];tick=lower
    # At most 2016 five-minute positions in one authoritative current cycle.
    reservations={m.user_id:list(db.execute(select(Reservation.starts_at,Reservation.ends_at).where(Reservation.user_id==m.user_id,
        Reservation.released_at.is_(None),Reservation.session_id!=session.id if session else True))) for m in target}
    while tick+timedelta(minutes=minutes)<=cycle.ends_at:
        end=tick+timedelta(minutes=minutes);local=tick.astimezone(raids.KST)
        allowed=(weekday is None or local.isoweekday()==weekday) and (group.day_scope=='any_current_cycle' or any(a.weekday==local.isoweekday() and
            (a.latest_start_minute is None or local.hour*60+local.minute<=a.latest_start_minute) for a in alternatives))
        if allowed and all(time.covered(tick,end,t.normalized_intervals) for t in tables) and all(
            not any(a<end and b>tick for a,b in reservations[m.user_id]) for m in target):found.append(tick)
        tick+=time.TICK
    return dict(state='ready' if found else 'no_candidate',earliest_start=found[0] if found else None,latest_start=found[-1] if found else None)


def evaluate_initial(db,room,stamp,*,confirm_members=None):
    changed=False
    for group in groups(db,room.id,raids.cycle(stamp).cycle_key):
        if group.planning_mode!='coordinated':continue
        linked=list(db.scalars(select(Session).join(SessionBinding,SessionBinding.session_id==Session.id).where(SessionBinding.group_id==group.id,Session.state=='unconfirmed')))
        if not linked and group.selected_session_id is None and group.required:
            if len(current_members(db,room.id,raids.cycle(stamp).cycle_key))<1+group.auto_additional_members:continue
            result=candidate(db,room,group,stamp)
            if result['state']!='ready':continue
            alternatives=list(db.scalars(select(ScheduleAlternative).where(ScheduleAlternative.group_id==group.id)))
            if group.occurrence_mode=='each':
                # Evaluate each weekday independently without turning one_of into many sessions.
                for alt in alternatives:
                    if alt.session_id is not None:continue
                    starts=candidate(db,room,group,stamp,weekday=alt.weekday)['earliest_start']
                    if starts:linked.append(make_session(db,room,group,[uuid.UUID(i) for i in alt.item_order],None,stamp,alt))
            else:
                ids=[i.id for i in active_items(db,room.id,raids.cycle(stamp).cycle_key)]
                linked=[make_session(db,room,group,ids,None,stamp)]
        for session in linked:
            parts=list(db.scalars(select(Participation).where(Participation.session_id==session.id,Participation.state=='active')))
            parts=[p for p in parts if assignments(db,db.get(Member,p.membership_id),session)]
            if len(parts)<1+group.auto_additional_members:continue
            result=candidate(db,room,group,stamp,session=session)
            if result['state']!='ready':continue
            set_times(db,session,result['earliest_start'],raids.cycle(stamp).cycle_key,stamp)
            session.state='confirmed';db.flush()
            changed=True
            for part in parts:
                if confirm_members is None or part.membership_id in confirm_members:reserve(db,part,session,stamp)
                else:part.confirmation_state='confirmation_pending'
    if changed:
        from app.raid_rooms.core import directory
        room.plan_revision+=1;room.revision+=1;directory(db)
    db.flush()
    return changed


def ensure_response(db,proposal,member,stamp):
    key=(proposal.id,member.id,1,proposal.proposal_plan_revision)
    value=db.get(ProposalResponse,key)
    if value is None:
        value=ProposalResponse(proposal_id=proposal.id,membership_id=member.id,membership_generation=1,
            proposal_plan_revision=proposal.proposal_plan_revision,room_id=member.room_id,revision=1,response='pending')
        db.add(value)
    return value
