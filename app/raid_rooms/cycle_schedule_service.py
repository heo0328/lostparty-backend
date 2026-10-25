from app.raid_rooms import beta_schedule
from app.raid_rooms import beta_profile
"""W4-A2 commands own exactly one actual target and the original ACK transaction."""
import uuid
from sqlalchemy import select
from app.game_accounts.support import fail
from app.raid_rooms import (cycle_planning as plan,cycle_proposals as proposals,cycle_schedule as graph,
    cycle_lifecycle as life,cycle_commands as commands,cycles,cycle_wire as wire)
from app.raid_rooms.cycle_creation import scope
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
from app.raid_rooms.cycle_planning_models import CycleProposal
from app.raid_rooms.source_models import ScheduleGroup,ScheduleProposal as Proposal,SessionBinding


def target(db,uid,rid,key,stamp,body=None,*,leader=False):
    plan.ready(db);room,row=commands.resolve(db,uid,rid,key,stamp,write=body is not None)
    cm=life.actual_member(db,row,uid,states=('participating',))
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    if body is not None:
        commands.cas(db,row,body,stamp,leader=leader)
        if any(body.get(name,getattr(row,attr))!=getattr(row,attr) for name,attr in
                (('expected_plan_revision','plan_revision'),('expected_members_revision','members_revision'))):fail('REVISION_CONFLICT')
    if leader:
        if commands.leadership(db,row)['leader_cycle_member_id']!=cm.id:fail('TARGET_LEADER_REQUIRED',403)
        life.qualify(db,room,row,cm)
    return room,row,cm


def load_group(db,uid,gid,key,stamp,body=None,*,leader=False):
    group=db.get(ScheduleGroup,gid)
    if group is None:fail('SCHEDULE_GROUP_NOT_FOUND',404)
    room,row,cm=target(db,uid,group.room_id,key,stamp,body,leader=leader)
    if gid not in {g.id for g in graph.groups(db,row)}:fail('TARGET_SCOPE_MISMATCH',400)
    return room,row,cm,group


def final_schedules(db,row,versions):
    def check(stamp):
        for sid,revision in versions:
            sess=db.get(graph.Session,sid)
            if sess.schedule_revision!=revision or sess.starts_at<stamp:fail('SCHEDULE_IN_PAST')
    return check


def edit(principal,rid,command,data):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        room,row,cm=target(db,uid,rid,body['target_cycle_key'],stamp,body,leader=True)
        before={s.id for s in graph.sessions(db,row) if s.state=='confirmed'}
        if beta_profile.enabled():beta_schedule.edit(db,room,row,body,stamp,command)
        else:plan.edit(db,room,row,uid,command,data.groups,stamp)
        versions=[(s.id,s.schedule_revision) for s in graph.sessions(db,row) if s.state=='confirmed' and s.id not in before]
        return 200,life.ack(db,row,command,stamp),final_schedules(db,row,versions)
    return cycles.execute(principal,'edit-schedule',command,dict(room_id=str(rid),body=body),run)


def candidates(principal,gid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        room,row,cm,group=load_group(db,uid,gid,key,stamp)
        value=plan.candidate(db,room,row,group,stamp)
        return wire.OutputContract3GetV2RaidScheduleGroupsGroupIdCandidates.model_validate(dict(scope=scope(stamp,key,row),
            data=dict(group_id=gid,revision=group.revision,plan_revision=row.plan_revision,evaluated_at=stamp,**value))).model_dump(mode='json')


def select_group(principal,gid,command,data):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        room,row,cm,group=load_group(db,uid,gid,body['target_cycle_key'],stamp,body,leader=True)
        final_guard=graph.final_deadlines(db,row,[],stamp,join=False)
        if beta_profile.enabled():
            if beta_schedule.get(db,row) is None:fail('BETA_SCHEDULE_REQUIRED')
            fail('SCHEDULE_PROPOSAL_REQUIRED')
        if group.revision!=body['expected_group_revision']:fail('REVISION_CONFLICT')
        if group.selected_session_id is not None:fail('SCHEDULE_PROPOSAL_REQUIRED')
        alt=next((a for a in graph.alternatives(db,group) if a.id==data.alternative_id),None)
        if data.alternative_id is not None and alt is None:fail('TARGET_SCOPE_MISMATCH',400)
        if group.planning_mode=='unscheduled':fail('SCHEDULE_TIME_REQUIRED')
        if group.occurrence_mode=='each' and alt is None:fail('INVALID_REQUEST',400)
        if alt is not None and alt.session_id is not None:fail('SCHEDULE_PROPOSAL_REQUIRED')
        if group.planning_mode=='manual':
            if alt is None:fail('INVALID_REQUEST',400)
            start=graph.local_start(row.cycle_key.isoformat(),alt.weekday,f'{alt.start_minute//60:02}:{alt.start_minute%60:02}')
        else:
            value=plan.candidate(db,room,row,group,stamp,alternative=alt)
            if value['state']!='ready':fail('NO_SCHEDULE_CANDIDATE')
            start=None
        order=[uuid.UUID(i) for i in alt.item_order] if alt else [i.id for i,_ in graph.admission.rounds(db,row)]
        sess=plan.make_session(db,room,row,group,order,start,stamp,alt)
        group.revision+=1;plan.bump(db,row)
        if start is not None:plan.consent(db,room,row,cm,sess,command,stamp,dict(kind='manual_schedule_selection'))
        plan.initial(db,room,row,uid,command,stamp)
        plan.event(db,row,uid,command,'groups_edited',stamp,dict(selected_group_id=gid,session_id=sess.id))
        return 200,life.ack(db,row,command,stamp),final_guard
    return cycles.execute(principal,'select-schedule',command,dict(group_id=str(gid),body=body),run)


def propose(principal,rid,command,data):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        room,row,cm=target(db,uid,rid,body['target_cycle_key'],stamp,body,leader=True)
        if beta_profile.enabled() and beta_schedule.get(db,row) is None:fail('BETA_SCHEDULE_REQUIRED')
        proposal=proposals.create(db,room,row,cm,command,data.targets,stamp)
        return 200,life.ack(db,row,command,stamp,outcome='recorded',revisions=[dict(resource='target',id=row.id,revision=row.revision),
            dict(resource='proposal',id=proposal.id,revision=proposal.revision)])
    return cycles.execute(principal,'propose-schedule',command,dict(room_id=str(rid),body=body),run)


def respond(principal,pid,command,data):
    from app.raid_rooms import resume_review
    body=resume_review.command_body(data)
    def run(db,uid,stamp):
        plan.ready(db)
        from app.raid_rooms import cycle_outcomes,cycle_resume
        from app.raid_rooms.cycle_outcome_models import CycleResume
        if cycle_outcomes.enabled(db) and db.get(CycleResume,pid) is not None:
            return cycle_resume.respond(db,uid,pid,command,body,stamp)
        if 'resume_context_token' in body:fail('CONTEXT_INVALID',400)
        binding=db.get(CycleProposal,pid)
        if binding is None:fail('PROPOSAL_NOT_FOUND',404)
        room,row,cm=target(db,uid,binding.room_id,body['target_cycle_key'],stamp,body)
        if (binding.cycle_id,binding.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
        proposal=db.get(Proposal,pid)
        if proposal.state!='pending':fail('PROPOSAL_NOT_PENDING')
        if (proposal.revision!=body['expected_proposal_revision'] or proposal.proposal_plan_revision!=body['expected_proposal_plan_revision']
                or cm.revision!=body['expected_cycle_member_revision']):fail('REVISION_CONFLICT')
        if not any(cm.id==m.id for t in binding.content for m in plan.members(db,row,db.get(graph.Session,uuid.UUID(t['session_id'])))):fail('PROPOSAL_TARGET_REQUIRED',403)
        if body['response']=='accept':life.qualify(db,room,row,cm)
        changed=proposals.vote(db,row,proposal,cm,body['response'],command,stamp)
        if changed:plan.bump(db,row)
        applied=proposals.evaluate(db,room,row,proposal,binding,uid,command,stamp)
        versions=[(uuid.UUID(t['session_id']),t['base_schedule_revision']+1) for t in binding.content] if applied else []
        return 200,life.ack(db,row,command,stamp,outcome='applied' if applied else 'recorded',revisions=[
            dict(resource='target',id=row.id,revision=row.revision),dict(resource='proposal',id=proposal.id,revision=proposal.revision)]),final_schedules(db,row,versions)
    return cycles.execute(principal,'schedule-response',command,dict(proposal_id=str(pid),body=body),run)
