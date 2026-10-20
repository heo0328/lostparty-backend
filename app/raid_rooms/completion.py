"""Completion, whole-membership cleanup and weekly closure are distinct effects."""
import uuid
from datetime import date,datetime,timedelta
from typing import Literal,Annotated
from pydantic import Field
from sqlalchemy import select
from app.core.database import now
from app.auth.models import User
from app.game_accounts.support import fail
from app.raid_rooms import admission_service as base,command_context as contexts,participation_core as core,scheduling as graph,proposals,continuation
from app.raid_rooms.availability_schemas import DTO,Version
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round,RecruitmentItem as Item,RecruitmentMembership as Member
from app.raid_rooms.source_models import RoomSettings,SessionParticipation as Participation,ContinuationChoice as Choice
from app.raid_weekly.models import WeeklyState


class ContextRequest(DTO):
    expected_cycle_key: str
    context_token: Annotated[str,Field(max_length=contexts.MAX_TOKEN_BYTES)]


class ContinuationResolution(DTO):
    action: Literal['keep','release']
    expected_choices_revision: Version


class LeadershipResolution(DTO):
    action: Literal['transfer','end']
    target_membership_id: uuid.UUID|None
    expected_target_revision: Version|None


class Personal(ContextRequest):
    continuation_resolution: ContinuationResolution|None
    leadership_resolution: LeadershipResolution|None


class MembershipCommand(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_members_revision: Version
    expected_plan_revision: Version
    expected_membership_revision: Version


class Transfer(MembershipCommand):
    target_membership_id: uuid.UUID
    expected_target_revision: Version


def transfer(db,room,actor,target_id,expected):
    if actor.id!=room.leader_membership_id:fail('ROOM_LEADER_REQUIRED',403)
    target=db.get(Member,target_id)
    if target is None or target.room_id!=room.id or target.ended_at is not None or target.id==actor.id:fail('ROOM_TRANSFER_TARGET_INVALID')
    if target.revision!=expected:fail('REVISION_CONFLICT')
    if db.scalar(select(User).where(User.id==target.user_id).with_for_update()).status!='active':fail('ROOM_TARGET_UNAVAILABLE')
    room.leader_membership_id=target.id;actor.revision+=1;target.revision+=1;room.members_revision+=1;room.revision+=1


def end_participations(db,room,member,stamp):
    for part in db.scalars(select(Participation).where(Participation.room_id==room.id,Participation.membership_id==member.id,Participation.state=='active')):
        session=db.get(graph.Session,part.session_id)
        if not graph.assignments(db,member,session):
            graph.release(db,participation=part,reason='participation_ended',stamp=stamp);part.state='ended';part.revision+=1


def drop_membership(db,room,member,stamp,*,end=False):
    if end and member.id!=room.leader_membership_id:fail('ROOM_LEADER_REQUIRED',403)
    if member.id==room.leader_membership_id:
        if not end:fail('LEADERSHIP_RESOLUTION_REQUIRED')
        if len(graph.members(db,room.id))!=1:fail('ROOM_LAST_MEMBER_REQUIRED')
    for assignment in db.scalars(select(Assignment).where(Assignment.membership_id==member.id,Assignment.state=='active')):
        graph.release(db,assignment=assignment,reason='member_left',stamp=stamp)
        core.release_assignment(db,assignment,stamp)
    db.flush();end_participations(db,room,member,stamp)
    for choice in db.scalars(select(Choice).where(Choice.membership_id==member.id,Choice.ended_at.is_(None))):
        choice.state='released';choice.blocked_reason=None;choice.ended_at=stamp;choice.revision+=1
    member.ended_at=stamp;member.revision+=1
    if end:
        room.ended_at=stamp
        for round in db.scalars(select(Round).where(Round.room_id==room.id,Round.state=='active')):
            round.state='stopped_incomplete';round.ended_at=stamp;round.revision+=1
        for session in graph.sessions(db,room.id):session.state='cancelled';session.revision+=1
        for prop in db.scalars(select(graph.Proposal).where(graph.Proposal.room_id==room.id,graph.Proposal.state=='pending')):prop.state='cancelled';prop.revision+=1
    room.members_revision+=1;room.plan_revision+=1;room.revision+=1
    core.legacy.touch_user(db,member.user_id);core.legacy.directory(db);db.flush()
    if not end:proposals.reevaluate(db,room,stamp)


def complete_assignment(db,room,assignment,stamp,*,party):
    round=db.get(Round,assignment.round_id);item=db.get(Item,assignment.item_id)
    graph.release(db,assignment=assignment,reason='raid_completed',stamp=stamp)
    core.release_assignment(db,assignment,stamp)
    state=db.get(WeeklyState,(assignment.user_id,assignment.character_id,item.raid_id,round.cycle_key))
    if party:
        state.party_completed_at=stamp;state.completed_party_id=room.id;state.party_difficulty_id=round.difficulty_id
    else:
        state.manual_completed_at=stamp;state.manual_difficulty_id=round.difficulty_id
    assignment.state='completed'
    assignment.build={**(assignment.build or {}),'completion_source':'party' if party else 'manual','completed_at':stamp.isoformat()}
    db.flush();end_participations(db,room,db.get(Member,assignment.membership_id),stamp)


def command(principal,rid,key,data,command,round_id=None):
    def run(db,uid,stamp):
        payload=contexts.unseal(data.context_token)
        current_rid=rid
        if current_rid is None:
            try:current_rid=uuid.UUID(payload.get('room',''))
            except (ValueError,TypeError):fail('CONTEXT_TARGET_MISMATCH',400)
        if (payload.get('actor'),payload.get('room'),payload.get('command'),payload.get('round'))!=(str(uid),str(current_rid),command,str(round_id) if round_id else None):fail('CONTEXT_TARGET_MISMATCH',400)
        if data.expected_cycle_key!=graph.raids.cycle(stamp).cycle_key or payload.get('cycle')!=data.expected_cycle_key:fail('CYCLE_CHANGED')
        expiry=datetime.fromisoformat(payload['expires_at'])
        if stamp>=expiry:fail('COMMAND_CONTEXT_EXPIRED')
        room=base.room(db,uid,current_rid);actor=base.member(db,uid,room)
        view,binding,rounds,assignments,last,keep=contexts.source(db,room,actor,command,round_id,stamp)
        if not view['permission']['allowed']:fail(view['permission']['reason'],403 if view['permission']['reason'] in ('WEEKLY_PARTICIPANT_REQUIRED','ROOM_LEADER_REQUIRED','ROOM_MEMBERSHIP_REQUIRED') else 409)
        if binding!=payload.get('digest'):fail('COMMAND_CONTEXT_STALE')
        settings=db.get(RoomSettings,current_rid);leaving=False
        if command=='personal_completion' and last:
            if settings.continuation_enabled:
                decision=data.continuation_resolution
                if decision is None:fail('CONTINUATION_DECISION_REQUIRED')
                if decision.expected_choices_revision!=actor.revision:fail('REVISION_CONFLICT')
                if decision.action=='keep':
                    if not keep:
                        chosen=assignments[0]
                        active=list(db.scalars(select(Choice).where(Choice.membership_id==actor.id,Choice.target_cycle==date.fromisoformat(data.expected_cycle_key)+timedelta(days=7),Choice.ended_at.is_(None))))
                        values=[continuation.ChoiceInput(item_id=i,character_id=chosen.character_id,selected_role=chosen.selected_role,expected_ownership_revision=chosen.ownership_revision)
                            for i in db.scalars(select(Item.id).where(Item.room_id==current_rid))]
                        continuation.replace_choices(db,room,actor,date.fromisoformat(data.expected_cycle_key)+timedelta(days=7),values,
                            [continuation.Replace(choice_id=c.id,revision=c.revision) for c in active],stamp)
                else:leaving=True
            else:leaving=True
            if leaving and actor.id==room.leader_membership_id:
                resolution=data.leadership_resolution
                if resolution is None:fail('LEADERSHIP_RESOLUTION_REQUIRED')
                if resolution.action=='transfer':
                    if resolution.target_membership_id is None or resolution.expected_target_revision is None:fail('INVALID_REQUEST',400)
                    transfer(db,room,actor,resolution.target_membership_id,resolution.expected_target_revision)
                else:
                    if resolution.target_membership_id is not None or resolution.expected_target_revision is not None:fail('INVALID_REQUEST',400)
                    if len(graph.members(db,current_rid))!=1:fail('ROOM_LAST_MEMBER_REQUIRED')
        if command=='close_weekly':
            for assignment in assignments:
                graph.release(db,assignment=assignment,reason='weekly_closed',stamp=stamp);core.release_assignment(db,assignment,stamp);assignment.state='stopped_incomplete'
            for round in rounds:round.state='stopped_incomplete';round.ended_at=stamp;round.revision+=1
            db.flush()
            for member in graph.members(db,current_rid):end_participations(db,room,member,stamp)
            for session in graph.sessions(db,current_rid):session.state='cancelled';session.revision+=1
            for group in graph.groups(db,current_rid,data.expected_cycle_key):
                head=db.get(graph.ScheduleHead,group.id);head.active=False;head.ended_at=stamp;group.client_key='retired:'+str(group.id)
        else:
            for assignment in assignments:complete_assignment(db,room,assignment,stamp,party=command=='complete_item')
            if command=='complete_item':
                round=rounds[0];round.state='completed';round.ended_at=stamp;round.revision+=1
            if leaving:drop_membership(db,room,actor,stamp,end=actor.id==room.leader_membership_id)
        room.plan_revision+=1;room.revision+=1;db.flush()
        for prop in db.scalars(select(graph.Proposal).where(graph.Proposal.room_id==current_rid,graph.Proposal.state=='pending')):
            if command in ('close_weekly','complete_item'):prop.state='obsolete';prop.revision+=1
        if room.ended_at is None:proposals.reevaluate(db,room,stamp)
        result=dict(command_id=key,outcome='applied',executed_at=stamp,revisions=[base.revision('room',room),base.revision('plan',room,room.plan_revision),base.revision('membership',actor)]+[base.revision('assignment',a) for a in assignments])
        def final(current):
            if current>=expiry:fail('COMMAND_CONTEXT_EXPIRED')
        return 200,result,final
    return base.execute(principal,command,key,dict(room_id=str(rid),round_id=str(round_id) if round_id else None,body=data.model_dump(mode='json')),run)


def membership_command(principal,rid,key,data,operation):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room);base.unscheduled(db,room);base.cas(room,data)
        if data.expected_cycle_key!=graph.raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        if actor.revision!=data.expected_membership_revision:fail('REVISION_CONFLICT')
        if operation=='transfer':transfer(db,room,actor,data.target_membership_id,data.expected_target_revision)
        else:drop_membership(db,room,actor,stamp,end=operation=='end')
        room.plan_revision+=1;room.revision+=1;core.legacy.directory(db)
        return 200,dict(command_id=key,outcome='applied',executed_at=stamp,revisions=[base.revision('room',room),base.revision('membership',actor),base.revision('plan',room,room.plan_revision)])
    return base.execute(principal,operation,key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)
