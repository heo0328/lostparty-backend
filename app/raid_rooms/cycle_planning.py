"""Target-specific schedule graph, bounded automatic search and immutable evidence."""
import uuid
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycle_schedule as graph,cycle_lifecycle as life,cycle_times as times,cycles
from app.raid_rooms.cycle_models import CycleMember,CycleOpening,CycleSubmission
from app.raid_rooms.cycle_application_models import CycleSession,CycleSessionSegment
from app.raid_rooms.cycle_planning_models import CycleAlternative,CycleScheduleEvent
from app.raid_rooms.source_models import (ScheduleGroup,ScheduleAlternative,SessionBinding,SessionParticipation as Participation,
    TimeReservation as Reservation,SegmentDurationEvidence)
from app.raid_rooms.integrated_models import RecruitmentMembership as Member
from app.raid_rooms.schedule_heads import ScheduleHead


def ready(db):
    if not graph.planning_enabled(db):fail('RECRUITMENT_COMMAND_NOT_READY',503)


def bump(db,row):
    if max(row.revision,row.plan_revision)>=2147483647:fail('REVISION_CONFLICT')
    row.revision+=1;row.plan_revision+=1;cycles.touch_directory(db,row.cycle_key)


def event(db,row,uid,command,kind,stamp,evidence):
    db.add(CycleScheduleEvent(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
        actor_id=uid,command_id=command,kind=kind,effective_at=stamp,evidence=jsonable_encoder(evidence)))


def snapshot(obj):return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}


def floor(db,row):
    values=list(db.scalars(select(CycleOpening).where(CycleOpening.cycle_id==row.id,
        CycleOpening.generation==row.generation,CycleOpening.state=='applied')))
    if not values or any(not v.evidence.get('search_floor_at') for v in values):fail('ROOM_REVIEW_REQUIRED')
    return max(datetime.fromisoformat(v.evidence['search_floor_at']) for v in values)


def members(db,row,sess=None):
    query=select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(CycleMember.cycle_id==row.id,
        CycleMember.generation==row.generation,CycleMember.state=='participating',Member.ended_at.is_(None))
    if sess is not None:
        query=query.join(Participation,Participation.membership_id==CycleMember.membership_id).where(
            Participation.session_id==sess.id,Participation.state=='active')
    result=[]
    rounds={s.round_id for s in graph.graph.active_segments(db,sess.id)} if sess else {rd.id for _,rd in graph.admission.rounds(db,row) if rd.state=='active'}
    for cm in db.scalars(query.order_by(CycleMember.joined_order,CycleMember.id)):
        owned={a.round_id for a in life.assignments(db,row,cm) if a.state=='active'}
        if rounds and rounds<=owned:result.append(cm)
    return result


def candidate(db,room,row,group,stamp,*,sess=None,alternative=None):
    if group.planning_mode!='coordinated':fail('SCHEDULE_NOT_COORDINATED')
    actual=members(db,row,sess)
    if not group.required and sess is None:
        lid=life.commands.leadership(db,row)['leader_cycle_member_id'];actual=[m for m in actual if m.id==lid]
    tables=[db.get(CycleSubmission,m.id) for m in actual]
    empty=dict(state='no_candidate',earliest_start=None,latest_start=None)
    if not actual or any(t is None for t in tables):return empty
    for cm in actual:
        try:life.qualify(db,room,row,cm)
        except GameError:return empty
    duration=sum(v['duration_minutes'] for v in row.settings_snapshot['items']) if sess is None else sum(s.duration_minutes for s in graph.graph.active_segments(db,sess.id))
    if not 0<duration<=1440:fail('SESSION_DURATION_EXCEEDED')
    choices=[alternative] if alternative else graph.alternatives(db,group)
    if sess is not None:
        linked=next((a for a in choices if a.session_id==sess.id),None)
        if linked:choices=[linked]
    first,last=times.bounds(row)
    tick=graph.graph.time.ceil_tick(max(stamp,floor(db,row),first+timedelta(hours=4))).astimezone(timezone.utc)
    busy={m.user_id:list(db.execute(select(Reservation.starts_at,Reservation.ends_at).where(Reservation.user_id==m.user_id,
        Reservation.released_at.is_(None),Reservation.starts_at<last,Reservation.ends_at>first,
        Reservation.session_id!=sess.id if sess else True))) for m in actual}
    found=[]
    while tick+timedelta(minutes=duration)<=last:
        end=tick+timedelta(minutes=duration);local=tick.astimezone(graph.graph.raids.KST)
        permitted=group.day_scope=='any_current_cycle' or any(a.weekday==local.isoweekday() and
            (a.latest_start_minute is None or local.hour*60+local.minute<=a.latest_start_minute) for a in choices)
        if permitted and all(graph.graph.time.covered(tick,end,t.normalized_intervals) for t in tables) and all(
                not any(a<end and b>tick for a,b in busy[m.user_id]) for m in actual):found.append(tick)
        tick+=graph.graph.time.TICK
    return dict(state='ready' if found else 'no_candidate',earliest_start=found[0] if found else None,latest_start=found[-1] if found else None)


def make_session(db,room,row,group,item_ids,start,stamp,alternative=None):
    pairs={i.id:(i,rd) for i,rd in graph.admission.rounds(db,row)}
    if len(set(item_ids))!=len(item_ids) or set(item_ids)!=set(pairs):fail('ROOM_ITEMS_CHANGED')
    if any(rd.state!='active' for _,rd in pairs.values()):fail('ROUND_NOT_ACTIVE')
    sess=graph.Session(id=uuid.uuid4(),room_id=room.id,revision=1,schedule_revision=1,state='unconfirmed',created_at=stamp)
    db.add(sess);db.flush()
    db.add(CycleSession(session_id=sess.id,room_id=room.id,cycle_id=row.id,generation=row.generation))
    db.add(SessionBinding(session_id=sess.id,room_id=room.id,group_id=group.id,required=group.required));db.flush()
    for ordinal,iid in enumerate(item_ids,1):
        item,rd=pairs[iid];setting=next(v for v in row.settings_snapshot['items'] if v['item_id']==str(iid))
        segment=graph.Segment(id=uuid.uuid4(),room_id=room.id,session_id=sess.id,item_id=iid,round_id=rd.id,
            ordinal=ordinal,duration_minutes=setting['duration_minutes'],duration_source=setting['duration_source'])
        db.add(segment);db.flush()
        db.add(CycleSessionSegment(segment_id=segment.id,room_id=room.id,cycle_id=row.id,generation=row.generation,
            session_id=sess.id,item_id=iid,round_id=rd.id))
        db.add(SegmentDurationEvidence(segment_id=segment.id,room_id=room.id,session_id=sess.id,item_id=iid,round_id=rd.id,
            item_settings_revision=setting['item_settings_revision'],duration_policy_version=setting['duration_policy_version']))
    db.flush()
    if start is not None:
        graph.graph.set_times(db,sess,start,row.cycle_key.isoformat(),stamp,validate_floor=False)
        graph.graph.time.interval(start,sess.ends_at,row.cycle_key.isoformat(),floor=floor(db,row),current=stamp)
        sess.state='confirmed'
    if alternative is not None:alternative.session_id=sess.id
    if group.occurrence_mode=='one_of':group.selected_session_id=sess.id
    lid=life.commands.leadership(db,row)['leader_cycle_member_id']
    for cm in members(db,row):
        if group.required or cm.id==lid:graph.graph.participation(db,sess,db.get(Member,cm.membership_id),stamp=stamp)
    db.flush()
    return sess


def consent(db,room,row,cm,sess,command,stamp,authorization):
    life.qualify(db,room,row,cm)
    part=db.scalar(select(Participation).where(Participation.session_id==sess.id,Participation.membership_id==cm.membership_id,
        Participation.state=='active'))
    if part is None:fail('PARTICIPATION_ENDED')
    segments=graph.graph.active_segments(db,sess.id)
    owned={a.round_id:a for a in life.assignments(db,row,cm) if a.state=='active'}
    if not segments or any(s.round_id not in owned for s in segments):fail('ROUND_NOT_ACTIVE')
    return times.record_confirmation(db,row,cm,sess,part,segments,owned,command,stamp,authorization=authorization)


def initial(db,room,row,uid,command,stamp):
    if row.state!='open':return
    changed=[]
    for group in graph.groups(db,row):
        if group.planning_mode!='coordinated':continue
        alts=graph.alternatives(db,group)
        linked=[s for s in graph.sessions(db,row) if db.get(SessionBinding,s.id).group_id==group.id and s.state=='unconfirmed']
        if not linked and group.selected_session_id is None and group.required and len(members(db,row))>=1+group.auto_additional_members:
            targets=[None] if group.occurrence_mode=='one_of' else alts
            for alt in targets:
                if alt and alt.session_id is not None:continue
                value=candidate(db,room,row,group,stamp,alternative=alt)
                if value['state']!='ready':continue
                if alt is None and alts:
                    local=value['earliest_start'].astimezone(graph.graph.raids.KST)
                    alt=next(a for a in alts if a.weekday==local.isoweekday() and
                        (a.latest_start_minute is None or local.hour*60+local.minute<=a.latest_start_minute))
                order=[uuid.UUID(v) for v in alt.item_order] if alt else [i.id for i,_ in graph.admission.rounds(db,row)]
                linked.append(make_session(db,room,row,group,order,None,stamp,alt))
        for sess in linked:
            actual=members(db,row,sess)
            if len(actual)<1+group.auto_additional_members:continue
            value=candidate(db,room,row,group,stamp,sess=sess)
            if value['state']!='ready':continue
            start=value['earliest_start'];graph.graph.set_times(db,sess,start,row.cycle_key.isoformat(),stamp,validate_floor=False)
            graph.graph.time.interval(start,sess.ends_at,row.cycle_key.isoformat(),floor=floor(db,row),current=stamp)
            sess.state='confirmed';sess.revision+=1;db.flush()
            for cm in actual:consent(db,room,row,cm,sess,command,stamp,dict(kind='initial_coordination',submission=times.submission_view(db,row,cm)))
            changed.append(snapshot(sess))
    if changed:event(db,row,uid,command,'initial_confirmed',stamp,dict(sessions=changed));bump(db,row)
    db.flush()


def refresh(db,room,row,uid,command,stamp):
    if not graph.planning_enabled(db):return
    initial(db,room,row,uid,command,stamp)
    from app.raid_rooms import cycle_proposals
    cycle_proposals.reevaluate(db,room,row,uid,command,stamp)


def edit(db,room,row,uid,command,groups,stamp):
    ready(db)
    current=graph.groups(db,row);live=graph.sessions(db,row)
    if any(s.state=='confirmed' or db.scalar(select(Reservation.id).where(Reservation.session_id==s.id).limit(1)) for s in live):fail('SCHEDULE_PROPOSAL_REQUIRED')
    if groups and not any(g.required for g in groups):fail('REQUIRED_SESSION_REQUIRED')
    if len({g.client_group_key for g in groups})!=len(groups):fail('INVALID_REQUEST',400)
    ids=[g.existing_group_id for g in groups if g.existing_group_id]
    if len(set(ids))!=len(ids):fail('INVALID_REQUEST',400)
    existing={g.id:g for g in current};pairs={i.id:rd for i,rd in graph.admission.rounds(db,row)}
    for g in groups:
        if (g.existing_group_id is None)!=(g.expected_group_revision is None):fail('INVALID_REQUEST',400)
        if g.existing_group_id and (g.existing_group_id not in existing or existing[g.existing_group_id].revision!=g.expected_group_revision):fail('REVISION_CONFLICT')
        if (g.planning_mode=='coordinated' and (g.auto_confirm_additional_members is None or not 1<=g.auto_confirm_additional_members<graph.admission.capacity(row))) or (g.planning_mode!='coordinated' and g.auto_confirm_additional_members is not None):fail('INVALID_REQUEST',400)
        if g.day_scope=='any_current_cycle':
            if g.planning_mode!='coordinated' or g.occurrence_mode!='one_of' or g.alternatives:fail('INVALID_REQUEST',400)
        elif not g.alternatives:fail('INVALID_REQUEST',400)
        if len({a.client_alternative_key for a in g.alternatives})!=len(g.alternatives):fail('INVALID_REQUEST',400)
        for a in g.alternatives:
            if a.existing_session_id is not None or a.expected_session_revision is not None:fail('SCHEDULE_PROPOSAL_REQUIRED')
            if (a.starts_local is not None)!=(g.planning_mode=='manual'):fail('INVALID_REQUEST',400)
            if len(a.item_ids)!=len(pairs) or set(a.item_ids)!=set(pairs):fail('ROOM_ITEMS_CHANGED')
            if a.starts_local and a.leader_latest_start_local and a.starts_local>a.leader_latest_start_local:fail('LEADER_START_LIMIT')
    before=dict(groups=[snapshot(g) for g in current],alternatives=[snapshot(a) for g in current for a in graph.alternatives(db,g)],
        sessions=[snapshot(s) for s in live])
    for old in current:db.get(ScheduleHead,old.id).active=False
    for sess in live:
        sess.state='cancelled';sess.revision+=1
        for part in db.scalars(select(Participation).where(Participation.session_id==sess.id,Participation.state=='active')):
            part.state='ended';part.revision+=1
    for g in groups:
        group=existing.get(g.existing_group_id)
        if group is None:
            group=ScheduleGroup(id=uuid.uuid4(),room_id=room.id,cycle_key=row.cycle_key,client_key=uuid.uuid4().hex,revision=1)
            db.add(group)
        else:group.revision+=1
        for name in ('occurrence_mode','planning_mode','day_scope','required'):setattr(group,name,getattr(g,name))
        group.auto_additional_members=g.auto_confirm_additional_members;group.selected_session_id=None
        db.flush()
        head=db.get(ScheduleHead,group.id)
        if head is None:db.add(ScheduleHead(group_id=group.id,client_key=g.client_group_key,active=True))
        else:head.client_key=g.client_group_key;head.active=True
        from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
        if db.get(CycleScheduleGroup,group.id) is None:db.add(CycleScheduleGroup(group_id=group.id,room_id=room.id,cycle_id=row.id,generation=row.generation))
        db.flush()
        for a in g.alternatives:
            minute=lambda v:int(v[:2])*60+int(v[3:]) if v else None
            alt=ScheduleAlternative(id=uuid.uuid4(),room_id=room.id,group_id=group.id,client_key=uuid.uuid4().hex,
                weekday=a.weekday,start_minute=minute(a.starts_local),latest_start_minute=minute(a.leader_latest_start_local),
                item_order=[str(i) for i in a.item_ids])
            db.add(alt);db.flush()
            db.add(CycleAlternative(alternative_id=alt.id,group_id=group.id,edition=group.revision,client_key=a.client_alternative_key))
            if g.planning_mode=='manual' and (g.occurrence_mode=='each' or len(g.alternatives)==1):
                sess=make_session(db,room,row,group,list(a.item_ids),graph.local_start(row.cycle_key.isoformat(),a.weekday,a.starts_local),stamp,alt)
                # Manual editing explicitly confirms only the leader's own time.
                cm=life.actual_member(db,row,uid,states=('participating',));consent(db,room,row,cm,sess,command,stamp,dict(kind='manual_schedule_edit'))
    event(db,row,uid,command,'groups_edited',stamp,dict(previous=before,requested=groups));bump(db,row)
    db.flush();initial(db,room,row,uid,command,stamp)
