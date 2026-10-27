"""Per-session quorum; immutable proposal content and exact schedule generations."""
import uuid
from datetime import datetime,timedelta
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raids import service as raids
from app.raid_rooms import scheduling as graph,time_policy as policy
from app.raid_rooms.integrated_models import RecruitmentSession as Session,RecruitmentMembership as Member,RecruitmentSegment as Segment
from app.raid_rooms.source_models import ScheduleProposal as Proposal,ProposalTarget,ProposalResponse,SessionParticipation as Participation,SegmentDurationEvidence


def eligible(db,session):
    return [p for p in db.scalars(select(Participation).join(Member,Member.id==Participation.membership_id).where(
        Participation.session_id==session.id,Participation.state=='active',Member.ended_at.is_(None)))
        if graph.assignments(db,db.get(Member,p.membership_id),session)]


def votes(db,proposal):
    result=[]
    for target in db.scalars(select(ProposalTarget).where(ProposalTarget.proposal_id==proposal.id).order_by(ProposalTarget.session_id)):
        session=db.get(Session,target.session_id);parts=eligible(db,session)
        accepted=0
        for part in parts:
            row=db.get(ProposalResponse,(proposal.id,part.membership_id,1,proposal.proposal_plan_revision))
            accepted+=bool(row and row.response=='accept')
        count=len(parts);required=policy.quorum(count) if count else 1
        result.append(dict(session_id=session.id,eligible_count=count,accepted_count=accepted,required_votes=required,
            satisfied=count>0 and accepted>=required))
    return result


def create(db,room,creator,data,stamp):
    if len({t.session_id for t in data.targets})!=len(data.targets):fail('INVALID_REQUEST',400)
    planned=[]
    for target in data.targets:
        session=db.get(Session,target.session_id)
        if session is None or session.room_id!=room.id:fail('SESSION_NOT_FOUND',404)
        if session.state!='confirmed':fail('SCHEDULE_NOT_CONFIRMED')
        if session.schedule_revision!=target.expected_schedule_revision:fail('REVISION_CONFLICT')
        existing=graph.active_segments(db,session.id);requested={i.item_id:i.duration_minutes for i in target.item_durations}
        if not existing:fail('ROUND_NOT_ACTIVE')
        if len(requested)!=len(target.item_durations) or set(requested)!={s.item_id for s in existing}:fail('ROOM_ITEMS_CHANGED')
        values=[];cursor=target.starts_at
        for segment in existing:
            value=requested[segment.item_id]
            if value is None:
                minutes,source,settings=graph.duration(db,db.get(graph.Item,segment.item_id))
            else:
                minutes,source=value,'explicit';settings=db.get(graph.ItemSettings,segment.item_id)
            end=cursor+timedelta(minutes=minutes)
            values.append(dict(segment_id=segment.id,item_id=segment.item_id,round_id=segment.round_id,
                starts_at=cursor,ends_at=end,duration_minutes=minutes,duration_source=source,
                policy_version=settings.duration_policy_version,item_settings_revision=settings.revision))
            cursor=end
        policy.interval(target.starts_at,cursor,data.expected_cycle_key,floor=graph.floor(db,room.id,data.expected_cycle_key),current=stamp)
        planned.append((session,values))
    value=Proposal(id=uuid.uuid4(),room_id=room.id,creator_membership_id=creator.id,revision=1,
        proposal_plan_revision=1,created_from_plan_revision=room.plan_revision,state='pending',created_at=stamp)
    db.add(value);db.flush()
    for session,segments in planned:
        db.add(ProposalTarget(proposal_id=value.id,session_id=session.id,room_id=room.id,
            base_schedule_revision=session.schedule_revision,proposed_segments=jsonable_encoder(segments)))
    db.flush()
    for member in graph.members(db,room.id):graph.ensure_response(db,value,member,stamp)
    db.flush()
    # N1 always requires the leader's explicit response, even on creation.
    if all(v['eligible_count']>=2 for v in votes(db,value)):
        own=db.get(ProposalResponse,(value.id,creator.id,1,1));own.response='accept';own.responded_at=stamp
    room.plan_revision+=1;room.revision+=1
    return value


def evaluate(db,room,proposal,stamp):
    if proposal.state!='pending':return False
    targets=list(db.scalars(select(ProposalTarget).where(ProposalTarget.proposal_id==proposal.id)))
    for target in targets:
        session=db.get(Session,target.session_id)
        if session.state!='confirmed' or session.schedule_revision!=target.base_schedule_revision:
            proposal.state='obsolete';proposal.revision+=1;return False
    if not all(v['satisfied'] for v in votes(db,proposal)):return False
    prepared=[]
    for target in targets:
        session=db.get(Session,target.session_id);values=target.proposed_segments
        existing={s.id:s for s in graph.active_segments(db,session.id)}
        if {uuid.UUID(v['segment_id']) for v in values}!=set(existing):fail('PROPOSAL_CONTEXT_CHANGED')
        start=datetime.fromisoformat(values[0]['starts_at']);end=datetime.fromisoformat(values[-1]['ends_at'])
        policy.interval(start,end,raids.cycle(stamp).cycle_key,floor=graph.floor(db,room.id,raids.cycle(stamp).cycle_key),current=stamp)
        for v in values:
            segment=existing[uuid.UUID(v['segment_id'])]
            rd=db.get(graph.Round,segment.round_id)
            if rd.state!='active' or (str(segment.item_id),str(segment.round_id))!=(v['item_id'],v['round_id']):fail('PROPOSAL_CONTEXT_CHANGED')
        prepared.append((session,values,existing,start,end))
    for session,values,existing,start,end in prepared:
        parts=eligible(db,session)
        for part in parts:graph.release(db,participation=part,reason='schedule_changed',stamp=stamp)
        session.starts_at=start;session.ends_at=end;session.schedule_revision+=1;session.revision+=1
        for v in values:
            segment=existing[uuid.UUID(v['segment_id'])]
            segment.duration_minutes=v['duration_minutes'];segment.duration_source=v['duration_source']
            segment.starts_at=datetime.fromisoformat(v['starts_at']);segment.ends_at=datetime.fromisoformat(v['ends_at'])
            evidence=db.get(SegmentDurationEvidence,segment.id)
            evidence.item_settings_revision=v['item_settings_revision'];evidence.duration_policy_version=v['policy_version']
        db.flush()
        for part in parts:
            response=db.get(ProposalResponse,(proposal.id,part.membership_id,1,proposal.proposal_plan_revision))
            part.confirmation_state='confirmation_pending';part.confirmed_schedule_revision=part.confirmed_at=None;part.revision+=1
            if response and response.response=='accept':graph.reserve(db,part,session,stamp)
    proposal.state='applied';proposal.revision+=1;room.plan_revision+=1;room.revision+=1
    db.flush()
    return True


def reevaluate(db,room,stamp):
    for proposal in db.scalars(select(Proposal).where(Proposal.room_id==room.id,Proposal.state=='pending').order_by(Proposal.created_at,Proposal.id)):
        try:
            with db.begin_nested():evaluate(db,room,proposal,stamp)
        except GameError:
            # An obsolete proposal must not veto an independent membership
            # change. The nested attempt leaves every schedule unchanged.
            proposal.state='obsolete';proposal.revision+=1
    from app.raid_rooms.resume_models import ResumeProposal
    from app.raid_rooms.resume import evaluate as evaluate_resume
    for proposal in db.scalars(select(ResumeProposal).where(ResumeProposal.room_id==room.id,ResumeProposal.state=='pending').order_by(ResumeProposal.created_at,ResumeProposal.id)):
        try:
            with db.begin_nested():evaluate_resume(db,room,proposal,stamp)
        except GameError:
            proposal.state='obsolete';proposal.revision+=1
