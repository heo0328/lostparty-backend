"""Authenticated schedule commands; original ACK and transaction are shared with R2."""
from sqlalchemy import select
from app.core.database import now
from app.game_accounts.support import fail
from app.raids import service as raids
from app.raid_rooms import admission_service as base,scheduling as graph,proposals
from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentSession as Session
from app.raid_rooms.source_models import ScheduleGroup,ScheduleAlternative,SessionParticipation as Participation,ScheduleProposal as Proposal


def current(room,data,stamp):
    if data.expected_cycle_key!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
    if getattr(data,'expected_plan_revision',room.plan_revision)!=room.plan_revision or getattr(data,'expected_members_revision',room.members_revision)!=room.members_revision:fail('REVISION_CONFLICT')


def result(key,room,actor,stamp,*,outcome='applied',extra=()):
    return dict(command_id=key,outcome=outcome,executed_at=stamp,revisions=[base.revision('room',room),
        base.revision('plan',room,room.plan_revision),base.revision('membership',actor)]+list(extra))


def active_group(db,group,stamp):
    head=db.get(graph.ScheduleHead,group.id)
    if group.cycle_key!=graph.date.fromisoformat(raids.cycle(stamp).cycle_key):fail('CYCLE_CHANGED')
    if head is None or not head.active:fail('SCHEDULE_GROUP_ENDED')


def edit(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room,leader=True);base.unscheduled(db,room);current(room,data,stamp)
        graph.install(db,room,data.groups,stamp)
        room.plan_revision+=1;room.revision+=1;graph.evaluate_initial(db,room,stamp)
        return 200,result(key,room,actor,stamp)
    return base.execute(principal,'schedule-groups',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def candidates(principal,gid):
    with base.snapshot(principal) as (db,uid,stamp):
        group=db.get(ScheduleGroup,gid)
        if group is None:fail('SCHEDULE_GROUP_NOT_FOUND',404)
        room=base.room(db,uid,group.room_id);base.member(db,uid,room)
        active_group(db,group,stamp)
        if group.planning_mode!='coordinated':fail('SCHEDULE_NOT_COORDINATED')
        value=graph.candidate(db,room,group,stamp)
        return dict(group_id=gid,revision=group.revision,plan_revision=room.plan_revision,evaluated_at=stamp,**value)


def select_group(principal,gid,key,data):
    def run(db,uid,stamp):
        group=db.get(ScheduleGroup,gid)
        if group is None:fail('SCHEDULE_GROUP_NOT_FOUND',404)
        room=base.room(db,uid,group.room_id);actor=base.member(db,uid,room,leader=True);base.unscheduled(db,room);current(room,data,stamp)
        active_group(db,group,stamp)
        if group.revision!=data.expected_group_revision:fail('REVISION_CONFLICT')
        if group.selected_session_id is not None:fail('SCHEDULE_PROPOSAL_REQUIRED')
        alt=db.get(ScheduleAlternative,data.alternative_id) if data.alternative_id else None
        if alt is not None and alt.group_id!=gid:fail('INVALID_REQUEST',400)
        if data.alternative_id and alt is None:fail('INVALID_REQUEST',400)
        if group.planning_mode=='unscheduled':fail('SCHEDULE_TIME_REQUIRED')
        if group.planning_mode=='manual':
            if alt is None:fail('INVALID_REQUEST',400)
            clock=f'{alt.start_minute//60:02}:{alt.start_minute%60:02}'
            start=graph.time.local_start(data.expected_cycle_key,alt.weekday,clock)
        else:
            value=graph.candidate(db,room,group,stamp,weekday=alt.weekday if alt else None)
            if value['state']!='ready':fail('NO_SCHEDULE_CANDIDATE')
            start=None  # Chosen intent can exist before the additional-participant threshold.
        item_ids=[graph.uuid.UUID(i) for i in alt.item_order] if alt else [i.id for i in graph.active_items(db,room.id,data.expected_cycle_key)]
        graph.make_session(db,room,group,item_ids,start,stamp,alt)
        group.revision+=1;room.plan_revision+=1;room.revision+=1;graph.evaluate_initial(db,room,stamp)
        return 200,result(key,room,actor,stamp)
    return base.execute(principal,'select-schedule',key,dict(group_id=str(gid),body=data.model_dump(mode='json')),run)


def propose(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room,leader=True);base.unscheduled(db,room);current(room,data,stamp)
        value=proposals.create(db,room,actor,data,stamp)
        return 200,result(key,room,actor,stamp,outcome='recorded',extra=[dict(resource='proposal',id=value.id,revision=value.revision)])
    return base.execute(principal,'propose',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def respond(principal,pid,key,data):
    def run(db,uid,stamp):
        value=db.get(Proposal,pid)
        if value is None:
            from app.raid_rooms.resume_models import ResumeProposal
            from app.raid_rooms import resume
            value=db.get(ResumeProposal,pid)
            if value is None:fail('PROPOSAL_NOT_FOUND',404)
            room=base.room(db,uid,value.room_id);actor=base.member(db,uid,room);base.unscheduled(db,room);current(room,data,stamp)
            applied=resume.respond(db,room,actor,value,data,stamp)
            return 200,result(key,room,actor,stamp,outcome='applied' if applied else 'recorded',extra=[base.revision('proposal',value)])
        room=base.room(db,uid,value.room_id);actor=base.member(db,uid,room);base.unscheduled(db,room);current(room,data,stamp)
        if value.state!='pending':fail('PROPOSAL_NOT_PENDING')
        if value.revision!=data.expected_proposal_revision or value.proposal_plan_revision!=data.expected_proposal_plan_revision or actor.revision!=data.expected_membership_revision:fail('REVISION_CONFLICT')
        target_ids=list(db.scalars(select(graph.ProposalTarget.session_id).where(graph.ProposalTarget.proposal_id==pid)))
        if not any(p.membership_id==actor.id for sid in target_ids for p in proposals.eligible(db,db.get(Session,sid))):fail('PROPOSAL_TARGET_REQUIRED',403)
        response=graph.ensure_response(db,value,actor,stamp)
        if response.response!=data.response:
            response.response=data.response;response.responded_at=stamp;response.revision+=1;room.plan_revision+=1
        db.flush();applied=proposals.evaluate(db,room,value,stamp)
        return 200,result(key,room,actor,stamp,outcome='applied' if applied else 'recorded',extra=[dict(resource='proposal',id=value.id,revision=value.revision)])
    return base.execute(principal,'proposal-response',key,dict(proposal_id=str(pid),body=data.model_dump(mode='json')),run)


def confirm(principal,sid,key,data):
    def run(db,uid,stamp):
        session=db.get(Session,sid)
        if session is None:fail('SESSION_NOT_FOUND',404)
        room=base.room(db,uid,session.room_id);actor=base.member(db,uid,room);base.unscheduled(db,room);current(room,data,stamp)
        part=db.scalar(select(Participation).where(Participation.session_id==sid,Participation.membership_id==actor.id))
        if part is None or part.state!='active':fail('PARTICIPATION_ENDED')
        if (session.schedule_revision!=data.expected_schedule_revision or actor.revision!=data.expected_membership_revision or part.revision!=data.expected_participation_revision):fail('REVISION_CONFLICT')
        if session.state!='confirmed' or not graph.assignments(db,actor,session):fail('ROUND_NOT_ACTIVE')
        if stamp>=session.ends_at:fail('SCHEDULE_ENDED')
        was=part.confirmed_schedule_revision
        graph.reserve(db,part,session,stamp)
        if was!=part.confirmed_schedule_revision:part.revision+=1;room.plan_revision+=1
        def final(current):
            if current>=session.ends_at:fail('SCHEDULE_ENDED')
        return 200,result(key,room,actor,stamp),final
    return base.execute(principal,'confirm',key,dict(session_id=str(sid),body=data.model_dump(mode='json')),run)


# Two-cycle storage never falls back to the legacy global room graph.
from app.raid_rooms.v1_compat import read as _current_read
candidates=_current_read('candidates')(candidates)
