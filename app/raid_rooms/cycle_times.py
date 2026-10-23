"""Explicit target submissions and consent. GETs share one read-only snapshot."""
import uuid
from copy import deepcopy
from datetime import datetime,timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,text
from app.game_accounts.support import fail,GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import (cycles,cycle_commands as commands,cycle_lifecycle as life,
    cycle_schedule as schedule,cycle_wire as wire,availability)
from app.raid_rooms.cycle_creation import scope,permission
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleSubmission,CycleAssignment
from app.raid_rooms.cycle_application_models import CycleSession,CycleSessionSegment
from app.raid_rooms.cycle_consent_models import CycleConsent
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentRoom as Room
from app.raid_rooms.source_models import (PersonalAvailability,SessionParticipation as Participation,TimeReservation as Reservation)
from app.raid_rooms.member_reads import paginate


def ready(db):
    if list(db.scalars(text('SELECT version_num FROM public.alembic_version'))) not in (['0027_cycle_consents'],['0028_cycle_planning'],['0029_cycle_outcomes'],['0030_completion_corrections']):
        fail('RECRUITMENT_COMMAND_NOT_READY',503)


def own_target(db,uid,rid,key,stamp,*,write=False):
    ready(db)
    if write:room,row=commands.resolve(db,uid,rid,key,stamp)
    else:
        from app.raid_rooms.cycle_member_reads import read_target
        room,row=read_target(db,uid,rid,key,stamp)
    cm=life.actual_member(db,row,uid,states=('participating',) if write else life.VALID_STATES)
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    return room,row,cm


def submission_view(db,row,cm):
    current=db.get(CycleSubmission,cm.id)
    return dict(membership_id=cm.membership_id,cycle_member_id=cm.id,cycle_member_revision=cm.revision,
        target_cycle_key=row.cycle_key,state='ready' if current else 'missing',revision=current.revision if current else 1,
        source_personal_version=current.source_personal_revision if current else None,
        intervals=deepcopy(current.intervals) if current else [],
        normalized_intervals=deepcopy(current.normalized_intervals) if current else [],
        submitted_at=current.submitted_at if current else None)


def get_submission(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        room,row,cm=own_target(db,uid,rid,key,stamp)
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdAvailabilitySubmission.model_validate(
            dict(scope=scope(stamp,key,row),data=submission_view(db,row,cm))).model_dump(mode='json')


def put_submission(principal,rid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        room,row,cm=own_target(db,uid,rid,body['target_cycle_key'],stamp,write=True)
        commands.cas(db,row,body,stamp)
        availability.verified(db,uid)
        final_guard=schedule.final_deadlines(db,row,[],stamp,join=False)
        personal=db.get(PersonalAvailability,uid);current=db.get(CycleSubmission,cm.id)
        if (body['expected_cycle_member_revision']!=cm.revision or
                body['expected_personal_version']!=(personal.revision if personal else 1) or
                body['expected_submission_revision']!=(current.revision if current else 1)):fail('REVISION_CONFLICT')
        if personal is None:fail('PERSONAL_AVAILABILITY_REQUIRED')
        if current is None or current.source_personal_revision!=personal.revision:
            if current is None:
                current=CycleSubmission(cycle_member_id=cm.id,room_id=rid,cycle_id=row.id,generation=row.generation,
                    membership_id=cm.membership_id,user_id=uid,revision=1)
                db.add(current)
            if current.revision==2147483647:fail('REVISION_CONFLICT')
            current.revision+=1;current.source_personal_revision=personal.revision
            current.intervals=deepcopy(personal.intervals);current.normalized_intervals=deepcopy(personal.normalized_intervals)
            current.submitted_at=stamp
            row.revision+=1;row.plan_revision+=1;cycles.touch_directory(db,row.cycle_key)
        db.flush()
        if schedule.planning_enabled(db):
            from app.raid_rooms import cycle_planning
            cycle_planning.refresh(db,room,row,uid,command,stamp)
        result=wire.OutputContract3GetV2MeRaidRoomsRoomIdAvailabilitySubmission.model_validate(
            dict(scope=scope(stamp,body['target_cycle_key'],row),data=submission_view(db,row,cm))).model_dump(mode='json')
        return 200,result,final_guard
    return cycles.execute(principal,'submission',command,dict(room_id=str(rid),body=body),run)


def session_target(db,uid,sid,key,stamp):
    ready(db)
    link=db.get(CycleSession,sid)
    if link is None:fail('SESSION_NOT_FOUND',404)
    room,row,cm=own_target(db,uid,link.room_id,key,stamp,write=True)
    if link.cycle_id!=row.id or link.generation!=row.generation:fail('TARGET_SCOPE_MISMATCH',400)
    current=db.get(schedule.Session,sid)
    part=db.scalar(select(Participation).where(Participation.session_id==sid,Participation.membership_id==cm.membership_id))
    if part is None or part.state!='active':fail('PARTICIPATION_ENDED')
    if current.state!='confirmed':fail('SCHEDULE_NOT_CONFIRMED')
    if current.ends_at is None or stamp>=current.ends_at:fail('SCHEDULE_ENDED')
    # Validate the actual T bundle and current selection; a persistent relation
    # or membership in C cannot authorize a confirmation for N.
    life.qualify(db,room,row,cm)
    values=schedule.graph.active_segments(db,sid)
    owned={a.round_id:a for a in life.assignments(db,row,cm) if a.state=='active'}
    values=[s for s in values if s.round_id in owned]
    if not values:fail('ROUND_NOT_ACTIVE')
    for segment in values:
        binding=db.get(CycleSessionSegment,segment.id)
        if (binding is None or (binding.cycle_id,binding.generation,binding.session_id)!=(row.id,row.generation,sid)
                or segment.starts_at is None or segment.ends_at is None):fail('ROOM_REVIEW_REQUIRED')
    return room,row,cm,current,part,values,owned


def confirm_permission(db,uid,row,sid,stamp):
    try:_,_,_,current,*_=session_target(db,uid,sid,row.cycle_key.isoformat(),stamp)
    except GameError as error:return permission(error.code)
    return permission(next_change=current.ends_at)


def record_confirmation(db,row,cm,current,part,values,owned,command,stamp,*,authorization):
    uid=cm.user_id;sid=current.id
    active=list(db.scalars(select(Reservation).where(Reservation.participation_id==part.id,Reservation.released_at.is_(None))))
    correct=(len(active)==len(values) and {r.segment_id for r in active}=={s.id for s in values} and
        all(r.schedule_revision==current.schedule_revision and r.assignment_id==owned[s.round_id].id and
            (r.starts_at,r.ends_at)==(s.starts_at,s.ends_at)
            for s in values for r in active if r.segment_id==s.id))
    already=part.confirmation_state=='confirmed' and part.confirmed_schedule_revision==current.schedule_revision
    if active and not (correct and already):fail('ROOM_REVIEW_REQUIRED')
    if already and not correct:fail('ROOM_REVIEW_REQUIRED')
    if not already:
        reservations=[]
        for segment in values:
            a=owned[segment.round_id]
            reservation=Reservation(id=uuid.uuid4(),room_id=row.room_id,participation_id=part.id,session_id=sid,
                membership_id=cm.membership_id,user_id=uid,assignment_id=a.id,item_id=a.item_id,round_id=a.round_id,
                segment_id=segment.id,schedule_revision=current.schedule_revision,starts_at=segment.starts_at,ends_at=segment.ends_at)
            db.add(reservation);reservations.append(reservation)
        # The old rows stay released. New UUIDs identify this fresh interval,
        # even when the session and schedule revision are exactly the same.
        part.revision+=1;part.confirmation_state='confirmed'
        part.confirmed_at=stamp;part.confirmed_schedule_revision=current.schedule_revision
        db.add(CycleConsent(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
            cycle_member_id=cm.id,membership_id=cm.membership_id,user_id=uid,participation_id=part.id,session_id=sid,
            command_id=command,member_revision=cm.revision,participation_revision=part.revision,
            schedule_revision=current.schedule_revision,effective_at=stamp,
            evidence=jsonable_encoder(dict(authorization=authorization,submission=submission_view(db,row,cm),
                assignments=[life.assignment_snapshot(owned[s.round_id]) for s in values],
                reservations=[dict(id=r.id,segment_id=r.segment_id,assignment_id=r.assignment_id,
                    starts_at=r.starts_at,ends_at=r.ends_at) for r in reservations]))))
    db.flush()
    return not already


def confirm(principal,sid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        room,row,cm,current,part,values,owned=session_target(db,uid,sid,body['target_cycle_key'],stamp)
        commands.cas(db,row,body,stamp)
        if (body['expected_cycle_member_revision']!=cm.revision or
                body['expected_participation_revision']!=part.revision or
                body['expected_schedule_revision']!=current.schedule_revision):fail('REVISION_CONFLICT')
        changed=record_confirmation(db,row,cm,current,part,values,owned,command,stamp,
            authorization=dict(kind='explicit_confirmation',command_id=str(command)))
        already=not changed
        if changed:row.revision+=1;row.plan_revision+=1;cycles.touch_directory(db,row.cycle_key)
        db.flush()
        result=life.ack(db,row,command,stamp,outcome='noop' if already else 'applied',revisions=[
            dict(resource='target',id=row.id,revision=row.revision),
            dict(resource='participation',id=part.id,revision=part.revision)])
        def final(check):
            if check>=current.ends_at:fail('SCHEDULE_ENDED')
        return 200,result,final
    return cycles.execute(principal,'confirm',command,dict(session_id=str(sid),body=body),run)


def bounds(row):
    start=datetime.combine(row.cycle_key,datetime.min.time(),schedule.graph.raids.KST)+timedelta(hours=6)
    return start,start+timedelta(days=7)


def time_context(principal,rid,key,target_session_id=None):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        room,row,cm=own_target(db,uid,rid,key,stamp)
        ids={s.id for s in schedule.sessions(db,row)}
        if target_session_id is not None and target_session_id not in ids:fail('TARGET_SCOPE_MISMATCH',400)
        first,last=bounds(row);members=[]
        actual=db.scalars(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
            CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
            CycleMember.state.in_(life.VALID_STATES),Member.ended_at.is_(None)).order_by(CycleMember.joined_order,CycleMember.id))
        for m in actual:
            reservations=list(db.scalars(select(Reservation).where(Reservation.user_id==m.user_id,
                Reservation.starts_at<last,Reservation.ends_at>first,
                Reservation.session_id!=target_session_id if target_session_id else True).order_by(Reservation.starts_at,Reservation.ends_at,Reservation.id)))
            intervals=[]
            for reservation in reservations:
                if reservation.released_at is not None:continue
                start,end=max(reservation.starts_at,first),min(reservation.ends_at,last)
                if intervals and start<=intervals[-1]['ends_at']:intervals[-1]['ends_at']=max(end,intervals[-1]['ends_at'])
                else:intervals.append(dict(starts_at=start,ends_at=end))
            owned=life.assignments(db,row,m)
            members.append(dict(membership_id=m.membership_id,cycle_member_id=m.id,display=owned[0].display if owned else None,
                submission=submission_view(db,row,m),anonymous_busy=dict(state='ready',
                    revision=1+sum(r.schedule_revision+1+int(r.released_at is not None) for r in reservations),intervals=intervals)))
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdScheduleContext.model_validate(dict(scope=scope(stamp,key,row),
            data=dict(room_id=rid,target_cycle_key=key,members_revision=row.members_revision,plan_revision=row.plan_revision,
                evaluated_at=stamp,members=members,target_session_id=target_session_id,
                permissions=dict(view_schedule_context=permission())))).model_dump(mode='json')


def overlaps(principal,key,limit=20,cursor=None):
    if type(limit) is not int or not 1<=limit<=50:fail('INVALID_REQUEST',400)
    with commands.base.snapshot(principal) as (db,uid,stamp):
        ready(db);value=cycles.target(stamp,key)
        reservations=list(db.scalars(select(Reservation).join(CycleAssignment,CycleAssignment.assignment_id==Reservation.assignment_id)
            .join(CycleMember,CycleMember.id==CycleAssignment.cycle_member_id).join(RoomCycle,RoomCycle.id==CycleMember.cycle_id)
            .join(Member,Member.id==CycleMember.membership_id).join(Room,Room.id==RoomCycle.room_id).where(
                Reservation.user_id==uid,Reservation.released_at.is_(None),Reservation.ends_at>stamp,
                RoomCycle.cycle_key==value.key,CycleMember.generation==RoomCycle.generation,
                CycleMember.state=='participating',Member.ended_at.is_(None),Room.ended_at.is_(None))
            .order_by(Reservation.starts_at,Reservation.id)))
        def endpoint(r):
            a=db.get(schedule.graph.Assignment,r.assignment_id);rd=db.get(schedule.graph.Round,r.round_id)
            item=db.get(schedule.graph.Item,r.item_id);room=db.get(Room,r.room_id)
            raid=next((v for v in schedule.graph.raids.catalog().raids if v.raid_id==item.raid_id),None)
            return dict(reservation_id=r.id,room_id=r.room_id,item_ids=[r.item_id],session_id=r.session_id,
                character_id=a.character_id,character_display=a.display,raid_display=dict(raid_id=item.raid_id,
                    difficulty_id=rd.difficulty_id,display_name=raid.display_name if raid else item.raid_id),
                room_title=room.title,starts_at=r.starts_at,ends_at=r.ends_at)
        pairs=[]
        for i,left in enumerate(reservations):
            for right in reservations[i+1:]:
                if right.starts_at>=left.ends_at:break
                if right.session_id==left.session_id:continue
                pairs.append(dict(pair_id=digest(sorted([str(left.id),str(right.id)])),left=endpoint(left),right=endpoint(right),
                    starts_at=max(left.starts_at,right.starts_at),ends_at=min(left.ends_at,right.ends_at)))
        pairs.sort(key=lambda p:(p['starts_at'],p['pair_id']))
        ids={p[side]['reservation_id'] for p in pairs for side in ('left','right')}
        revision=digest(jsonable_encoder([key,value.current,limit,[[r.id,r.schedule_revision] for r in reservations]]))
        page,token=paginate(pairs,limit,cursor,['v2-overlaps',str(uid),str(principal[1].id)],revision)
        # This account-wide projection has no single RoomCycle head.
        return wire.OutputContract3GetV2MeRaidScheduleOverlaps.model_validate(dict(scope=scope(stamp,key),
            data=dict(items=page,pair_count=len(pairs),affected_room_count=len({r.room_id for r in reservations if r.id in ids}),
                reservation_count=len(ids),revision=revision,next_cursor=token,evaluated_at=stamp,target_cycle_key=key))).model_dump(mode='json')
