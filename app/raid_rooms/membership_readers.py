"""Explicit opt-in readers; historical anchors never become current authority."""
from datetime import date
from contextlib import nullcontext
from sqlalchemy import select, or_, and_
from app.game_accounts.support import fail, GameError, cursor_encode, cursor_decode
from app.game_accounts.lifecycle import digest
from app.raid_rooms import (membership_actions as actions, membership_action_schemas as wire,
    cycle_member_reads as legacy, cycle_queries as directory, cycle_lists,
    completed_room_lifecycle as archive)
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember, CycleAssignment
from app.raid_rooms.cycle_application_models import CycleSession
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member, RecruitmentAssignment as Assignment, RecruitmentRound as Round, RecruitmentItem as Item, RecruitmentSegment as Segment, RecruitmentSession as Session
from app.raid_rooms.source_models import SessionParticipation as Participation,TimeReservation
from app.raid_rooms.models import MemberHead
from app.raid_rooms.membership_action_models import LeadershipRecovery
from app.raid_rooms.cycle_creation import permission
from app.raid_weekly.service import parse_cycle

PROFILE = actions.POLICY


def scope(stamp,key,kind):
    return dict(server_now=stamp,current_cycle_key=actions.life.raids.cycle(stamp).cycle_key,
        target_cycle_key=key,policy_version=PROFILE,reader_kind=kind)


def locator(row,cm):
    if cm is None or cm.generation is None:return None
    return dict(membership_id=cm.membership_id,cycle_member_id=cm.id,room_cycle_id=row.id,
        target_cycle_key=row.cycle_key,target_generation=cm.generation)


def record(db,row,cm):
    values=list(db.scalars(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).where(
        CycleAssignment.cycle_id==row.id,CycleAssignment.generation==cm.generation,CycleAssignment.cycle_member_id==cm.id,
        Assignment.membership_id==cm.membership_id,Assignment.user_id==cm.user_id).order_by(Assignment.joined_at,Assignment.id)))
    rounds={a.round_id:db.get(Round,a.round_id) for a in values}
    if not values:fail('ROOM_REVIEW_REQUIRED')
    rds=[dict(item_id=rd.item_id,round_id=rd.id,raid_id=db.get(Item,rd.item_id).raid_id,
        difficulty_id=rd.difficulty_id,catalog_version=rd.catalog_version,state=rd.state) for rd in rounds.values()]
    assignments=[]
    for a in values:
        rd=rounds[a.round_id];build=a.build or {}
        completed_at=build.get('completed_at')
        completion_source=build.get('completion_source') if a.state=='completed' else None
        if completion_source not in ('manual','party'):completion_source=None
        assignments.append(dict(assignment_id=a.id,item_id=a.item_id,round_id=a.round_id,character_id=a.character_id,
            character_name=a.display.get('character_name'),raid_id=db.get(Item,a.item_id).raid_id,difficulty_id=rd.difficulty_id,
            catalog_version=rd.catalog_version,state=a.state,completion_source=completion_source,
            completed_at=completed_at or (a.ended_at if a.state=='completed' else None),ended_at=a.ended_at))
    segments=[]
    for seg,part,sess in db.execute(select(Segment,Participation,Session).join(Session,Session.id==Segment.session_id).join(
        Participation,and_(Participation.session_id==Session.id,Participation.membership_id==cm.membership_id)).join(
        CycleSession,CycleSession.session_id==Session.id).where(CycleSession.cycle_id==row.id,
        CycleSession.generation==cm.generation,Segment.round_id.in_(rounds)).order_by(Segment.session_id,Segment.ordinal)):
        segments.append(dict(segment_id=seg.id,round_id=seg.round_id,session_id=seg.session_id,
            starts_at=seg.starts_at,ends_at=seg.ends_at,state='released' if part.state!='active' or sess.state=='cancelled' else 'planned'))
    from app.raid_rooms.cycle_models import ParticipationEvent
    ended=db.scalar(select(ParticipationEvent).where(ParticipationEvent.cycle_member_id==cm.id,ParticipationEvent.action.in_(('cancelled','removed'))).order_by(ParticipationEvent.member_revision.desc()).limit(1))
    if ended is not None and 'record_schedule_segments' in ended.evidence:
        segments=ended.evidence['record_schedule_segments']
    elif ended is not None and cm.state in ('cancelled','removed'):
        # Existing atomic-departure events predate segment snapshots. Read the
        # immutable reservations owned by these old assignments, not a reused part.
        historical={}
        for saved in db.scalars(select(TimeReservation).where(TimeReservation.assignment_id.in_([a.id for a in values]),
                TimeReservation.released_at.is_not(None),TimeReservation.released_at<=cm.ended_at)
                .order_by(TimeReservation.released_at.desc(),TimeReservation.schedule_revision.desc(),TimeReservation.id.desc())):
            historical.setdefault(saved.segment_id,saved)
        segments=[dict(segment_id=v.segment_id,round_id=v.round_id,session_id=v.session_id,
            starts_at=v.starts_at,ends_at=v.ends_at,state='released') for v in historical.values()]
        segments.sort(key=lambda v:(str(v['session_id']),str(v['segment_id'])))
    return dict(locator=locator(row,cm),rounds=rds,assignments=assignments,schedule_segments=segments)


def projection(db,uid,room,row,member,cm,stamp,*,anchored=False):
    known=row is not None and cm is not None and cm.generation is not None
    historical=bool(anchored or member.ended_at is not None or room.ended_at is not None or archive.is_archived(db,room.id) or
        cm is not None and (cm.state in ('cancelled','removed') or cm.generation!=row.generation))
    gen=db.get(CycleGeneration,(row.id,cm.generation)) if known else None
    lead=None
    if gen:
        leader=db.get(CycleMember,gen.leader_cycle_member_id) if gen.leader_cycle_member_id else None
        if leader and (leader.cycle_id,leader.generation)!=(row.id,cm.generation):fail('ROOM_REVIEW_REQUIRED')
        lead=dict(leader_cycle_member_id=leader.id if leader else None,leader_membership_id=leader.membership_id if leader else None,
            leadership_revision=gen.leadership_revision)
    is_leader=lead is not None and lead['leader_cycle_member_id']==(cm.id if cm else None) and cm is not None
    mode='record' if historical and known else 'relation_only' if cm is None else 'recovery' if not known else 'retained' if cm.state in ('completed','stopped') else 'participant'
    role='none' if mode in ('record','relation_only','recovery') else 'leader' if is_leader else 'member'
    state=db.get(LeadershipRecovery,(row.id,cm.generation)) if gen else None
    menu=not historical and member.ended_at is None and room.ended_at is None and not archive.is_archived(db,room.id)
    recovery_state='none';reason=None;revision=None;remaining=[];can=permission('LEADERSHIP_RECOVERY_NOT_REQUIRED')
    if not historical and state:
        revision=state.revision;reason=state.reason;remaining=state.remaining_review_reasons
        recovery_state={'pending_review':'leadership_pending','review_remaining':'review_remaining'}.get(state.state,'none')
        if mode in ('participant','retained') and menu and state.state in ('pending_review','review_remaining'):
            try:actions.plan_target(db,room,row,member,'recover_leadership',stamp);can=permission()
            except GameError as error:can=permission(error.code)
    elif not historical and (mode=='recovery' or row and row.state=='review_required'):
        recovery_state='unverified';reason='ROOM_REVIEW_REQUIRED'
    has_record=historical and gen is not None and bool(db.scalar(select(CycleAssignment.assignment_id).where(CycleAssignment.cycle_member_id==cm.id).limit(1)))
    own_source=known and bool(db.scalar(select(CycleAssignment.assignment_id).where(CycleAssignment.cycle_member_id==cm.id,CycleAssignment.generation==cm.generation).limit(1)))
    plan_allowed=bool(has_record or not historical and own_source)
    manages=bool(not historical and is_leader and row.state=='open' and gen.state=='open' and actions.qualified(db,room,row,cm)[0] is None)
    perms=dict(view_detail=permission(),view_plan=permission(None if plan_allowed else 'ROOM_REVIEW_REQUIRED' if cm else 'WEEKLY_PARTICIPANT_REQUIRED'),
        manage_target=permission(None if manages else 'ROOM_READ_ONLY' if historical else 'TARGET_LEADER_REQUIRED'),
        resume_weekly=permission('ROOM_READ_ONLY' if historical else 'ROUND_NOT_STOPPED'),
        read_action_menu=permission(None if menu else 'ROOM_READ_ONLY'))
    if not historical and mode=='retained' and cm.state=='stopped':
        # IF-001 disables app entry, not the retained server capability. Reuse
        # the legacy authority/source check; never issue or apply a resume here.
        from app.raid_rooms import cycle_resume
        expected=dict(expected_cycle_key=actions.life.raids.cycle(stamp).cycle_key,target_cycle_key=row.cycle_key.isoformat(),
            expected_target_revision=row.revision,expected_room_revision=room.revision,
            expected_members_revision=row.members_revision,expected_plan_revision=row.plan_revision,
            expected_cycle_member_revision=cm.revision,expected_leadership_revision=gen.leadership_revision,schedule_groups=None)
        try:cycle_resume.prepare_create(db,uid,room.id,expected,stamp);perms['resume_weekly']=permission()
        except GameError as error:perms['resume_weekly']=permission(error.code)
    target=dict(room_id=room.id,title=room.title,room_revision=room.revision,room_state='ended' if room.ended_at else 'active',
        target_cycle_key=row.cycle_key if row else None,room_cycle_id=row.id if row else None,
        target_generation=cm.generation if cm else row.generation if row else None,target_revision=row.revision if row else None,
        target_state='closed' if historical and known and cm.generation!=row.generation else row.state if row else None,
        generation_state=gen.state if gen else None,leadership=lead)
    if cm is None and row and row.generation:
        target['leadership']=actions.leadership(db,row);target['generation_state']=db.get(CycleGeneration,(row.id,row.generation)).state
    viewer=dict(membership_id=member.id,membership_revision=member.revision,membership_state='ended' if member.ended_at else 'active',
        cycle_member_id=cm.id if cm else None,cycle_member_revision=cm.revision if cm else None,cycle_member_state=cm.state if cm else 'not_selected',
        joined_order=str(cm.joined_order) if cm and cm.joined_order else None,role=role,mode=mode,record_locator=locator(row,cm) if cm else None)
    recovery=dict(state=recovery_state,reason=reason,revision=revision,remaining_review_reasons=remaining,
        menu_access=menu,can_request_recovery=can)
    return dict(target=target,viewer=viewer,recovery=recovery,permissions=perms),historical


def get(principal,rid,key,kind,*,membership_id=None,cycle_member_id=None,include_resume_display=False,read_snapshot=None):
    if (membership_id is None)!=(cycle_member_id is None):fail('INVALID_REQUEST',400)
    with (nullcontext(read_snapshot) if read_snapshot is not None else actions.commands.base.snapshot(principal)) as (db,uid,stamp):
        actions.ready(db)
        if membership_id is not None:
            parse_cycle(key)
            member=db.get(Member,membership_id);cm=db.get(CycleMember,cycle_member_id);room=db.get(Room,rid)
            row=db.get(RoomCycle,cm.cycle_id) if cm else None
            if (member is None or member.user_id!=uid or member.room_id!=rid or cm is None or
                (cm.user_id,cm.membership_id,cm.room_id)!=(uid,member.id,rid) or row is None or row.cycle_key.isoformat()!=key or cm.generation is None):
                fail('ROOM_NOT_FOUND',404)
        else:
            room=actions.commands.base.room(db,uid,rid)
            member=actions.commands.base.member(db,uid,room)
            _,row=actions.cycles.resolve(db,rid,key,stamp)
            cm=db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.membership_id==member.id,
                CycleMember.generation==row.generation).order_by(CycleMember.joined_order.desc().nullslast(),CycleMember.id.desc())) if row else None
        value,historical=projection(db,uid,room,row,member,cm,stamp,anchored=membership_id is not None)
        value['target']['target_cycle_key']=key
        if historical and include_resume_display:fail('INVALID_REQUEST',400)
        if kind=='plan' and not value['permissions']['view_plan']['allowed']:fail(value['permissions']['view_plan']['reason'],403)
        value['content']=None;value['record']=record(db,row,cm) if historical and cm is not None and cm.generation is not None else None
        safe_leader=value['target']['leadership'] and (value['target']['leadership']['leader_cycle_member_id'] is not None or value['target']['generation_state'] in ('cancelled','completed'))
        if not historical and safe_leader and row and row.generation and row.state!='review_required' and (cm is None or cm.state!='review_required'):
            fn=legacy.detail if kind=='detail' else legacy.plan
            kwargs=dict(read_snapshot=(db,uid,stamp))
            if kind=='plan':kwargs['include_resume_display']=include_resume_display
            value['content']=fn(principal,rid,key,**kwargs)
        value['access']=dict(state='allowed',basis='historical_membership' if historical and member.ended_at else 'target_record' if historical else 'current_membership',
            read_only=historical,evaluated_at=stamp)
        model=wire.DetailProfile if kind=='detail' else wire.PlanProfile
        return actions.bounded(model,dict(scope=scope(stamp,key,kind),data=value),snapshot=(db,uid,stamp))


def legacy_membership(db,uid,room,row,member,cm,key,stamp):
    # Reuse the exact legacy envelope only where its strict state vocabulary fits.
    if row is None or row.provenance!='explicit' or row.generation is None or row.state=='review_required' or not row.settings_snapshot or cm is None or cm.generation!=row.generation or cm.state in ('cancelled','removed','review_required'):
        return None
    own=legacy.own_view(db,room,row,member);owned=legacy.assignments(db,row,member.id)
    return dict(membership_id=member.id,revision=member.revision,room_id=room.id,state='current' if member.ended_at is None else 'ended',
        joined_at=member.joined_at,ended_at=member.ended_at,assignments=[dict(assignment_id=a.id,revision=a.revision,item_id=a.item_id,
        round_id=a.round_id,character_id=a.character_id,selected_role=a.selected_role,state=a.state,target_cycle_key=key,cycle_member_id=link.cycle_member_id) for a,link in owned],
        room=directory.card(db,room,row,uid,stamp),recovery_only=False,history_only=member.ended_at is not None,
        permissions=dict(view_plan=permission(None if member.ended_at is None else 'WEEKLY_PARTICIPANT_REQUIRED')),
        target_role=own['target_role'],cycle_member_id=cm.id,cycle_member_revision=cm.revision,joined_order=str(cm.joined_order) if cm.joined_order else None,
        target_participation_state=cm.state,target_cycle_key=key,room_cycle_id=row.id,target_generation=row.generation,target_revision=row.revision)


def memberships(principal,key,state='current',limit=20,cursor=None):
    if state not in ('current','ended','all') or type(limit) is not int or not 1<=limit<=50:fail('INVALID_REQUEST',400)
    with actions.commands.base.snapshot(principal) as (db,uid,stamp):
        actions.ready(db);target=actions.cycles.target(stamp,key)
        query=select(Member,Room,RoomCycle,CycleMember).join(Room,Room.id==Member.room_id).outerjoin(RoomCycle,
            and_(RoomCycle.room_id==Room.id,RoomCycle.cycle_key==target.key)).outerjoin(CycleMember,
            and_(CycleMember.cycle_id==RoomCycle.id,CycleMember.membership_id==Member.id)).where(Member.user_id==uid)
        from app.raid_rooms.active_usage import predicate
        current=predicate()
        history=or_(Member.ended_at.is_not(None),Room.ended_at.is_not(None),archive.archived(Room.id),
            CycleMember.state.in_(('completed','stopped','cancelled','removed')),CycleMember.generation!=RoomCycle.generation)
        if state=='current':query=query.where(current)
        elif state=='ended':query=query.where(history)
        head=db.get(MemberHead,uid);revision=head.membership_revision if head else 1
        binding=['membership-actions-1',str(uid),str(principal[1].id),key,state,limit]
        epoch=digest([revision,actions.cycles.directory_revision(db,target.key),target.current.isoformat()])
        offset=cursor_decode(cursor,binding,epoch) if cursor else 0
        values=list(db.execute(query.order_by(Member.joined_at.desc(),Member.id.desc(),CycleMember.generation.desc().nullslast(),CycleMember.id.desc()).offset(offset).limit(limit+1)))
        token=cursor_encode(dict(scope=binding,revision=epoch,offset=offset+limit)) if len(values)>limit else None
        items=[]
        for member,room,row,cm in values[:limit]:
            value,historical=projection(db,uid,room,row,member,cm,stamp)
            value['target']['target_cycle_key']=key
            value['content']=None if historical else legacy_membership(db,uid,room,row,member,cm,key,stamp)
            items.append(value)
        return actions.bounded(wire.MembershipPage,dict(scope=scope(stamp,key,'memberships'),data=dict(
            items=items,membership_head=revision,next_cursor=token,evaluated_at=stamp)),snapshot=(db,uid,stamp))
