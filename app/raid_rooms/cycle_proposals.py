"""Per-target quorum and append-only votes bound to the current CM revision."""
from app.raid_rooms import beta_schedule
import uuid
from datetime import datetime,timedelta
from sqlalchemy import select,func
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycle_planning as plan,cycle_schedule as graph,cycle_lifecycle as life
from app.raid_rooms.cycle_planning_models import CycleProposal,CycleVote
from app.raid_rooms.source_models import ScheduleProposal as Proposal,ProposalTarget,SessionParticipation as Participation,SegmentDurationEvidence,SessionBinding


def latest(db,proposal,cm):
    return db.scalar(select(CycleVote).where(CycleVote.proposal_id==proposal.id,CycleVote.cycle_member_id==cm.id,
        CycleVote.member_revision==cm.revision).order_by(CycleVote.revision.desc()).limit(1))


def vote(db,row,proposal,cm,response,command,stamp):
    previous=latest(db,proposal,cm)
    if previous is not None and previous.response==response:return False
    revision=1+db.scalar(select(func.coalesce(func.max(CycleVote.revision),0)).where(CycleVote.proposal_id==proposal.id,CycleVote.cycle_member_id==cm.id))
    if revision>2147483647:fail('REVISION_CONFLICT')
    db.add(CycleVote(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
        proposal_id=proposal.id,cycle_member_id=cm.id,membership_id=cm.membership_id,user_id=cm.user_id,
        member_revision=cm.revision,revision=revision,command_id=command,response=response,effective_at=stamp));db.flush()
    return True


def votes(db,row,proposal,binding):
    result=[]
    for target in binding.content:
        sess=db.get(graph.Session,uuid.UUID(target['session_id']));actual=plan.members(db,row,sess)
        accepted=sum(bool(v and v.response=='accept') for cm in actual for v in [latest(db,proposal,cm)])
        count=len(actual);required=graph.graph.time.quorum(count) if count else 1
        result.append(dict(session_id=sess.id,eligible_count=count,accepted_count=accepted,required_votes=required,
            satisfied=count>0 and accepted>=required))
    return result


def create(db,room,row,cm,command,targets,stamp):
    if len({t.session_id for t in targets})!=len(targets):fail('INVALID_REQUEST',400)
    sessions={s.id:s for s in graph.sessions(db,row)};content=[]
    for target in targets:
        sess=sessions.get(target.session_id)
        if sess is None:fail('TARGET_SCOPE_MISMATCH',400)
        beta=beta_schedule.get(db,row)
        if sess.state!='confirmed' and beta is None:fail('SCHEDULE_NOT_CONFIRMED')
        if sess.schedule_revision!=target.expected_schedule_revision:fail('REVISION_CONFLICT')
        if stamp>=sess.ends_at and not (beta and beta.needs_review):fail('SCHEDULE_ENDED')
        segments=graph.graph.active_segments(db,sess.id);requested={v.item_id:v.duration_minutes for v in target.item_durations}
        if len(requested)!=len(target.item_durations) or not segments or set(requested)!={s.item_id for s in segments}:fail('ROOM_ITEMS_CHANGED')
        cursor=target.starts_at;planned=[]
        for segment in segments:
            setting=next(v for v in row.settings_snapshot['items'] if v['item_id']==str(segment.item_id))
            explicit=requested[segment.item_id];minutes=explicit if explicit is not None else setting['duration_minutes']
            end=cursor+timedelta(minutes=minutes)
            planned.append(dict(segment_id=segment.id,item_id=segment.item_id,round_id=segment.round_id,
                starts_at=cursor,ends_at=end,duration_minutes=minutes,
                duration_source='explicit' if explicit is not None else setting['duration_source'],
                policy_version=setting['duration_policy_version'],item_settings_revision=setting['item_settings_revision']))
            cursor=end
        graph.graph.time.interval(target.starts_at,cursor,row.cycle_key.isoformat(),floor=plan.floor(db,row),current=stamp,
            minute_precision=beta is not None and beta.session_id==sess.id)
        content.append(dict(session_id=sess.id,base_schedule_revision=sess.schedule_revision,segments=planned))
    proposal=Proposal(id=uuid.uuid4(),room_id=room.id,creator_membership_id=cm.membership_id,revision=1,
        proposal_plan_revision=1,created_from_plan_revision=row.plan_revision,state='pending',created_at=stamp)
    db.add(proposal);db.flush()
    binding=CycleProposal(proposal_id=proposal.id,room_id=room.id,cycle_id=row.id,generation=row.generation,content=jsonable_encoder(content))
    db.add(binding)
    for t in content:db.add(ProposalTarget(proposal_id=proposal.id,session_id=t['session_id'],room_id=room.id,
        base_schedule_revision=t['base_schedule_revision'],proposed_segments=jsonable_encoder(t['segments'])))
    db.flush()
    # N1 always needs a separate explicit response. With N2+, creation is the
    # creator's explicit proposal and can record their vote, never apply here.
    counts=votes(db,row,proposal,binding)
    if all(v['eligible_count']>=2 for v in counts) and any(cm.id==m.id for t in content for m in plan.members(db,row,db.get(graph.Session,t['session_id']))):
        vote(db,row,proposal,cm,'accept',command,stamp)
    plan.event(db,row,cm.user_id,command,'proposal_created',stamp,dict(proposal_id=proposal.id,content=content))
    plan.bump(db,row);db.flush()
    return proposal


def evaluate(db,room,row,proposal,binding,uid,command,stamp):
    if not binding.content:return False
    if proposal.state!='pending':return False
    sessions={s.id:s for s in graph.sessions(db,row)}
    if any(uuid.UUID(t['session_id']) not in sessions or (sessions[uuid.UUID(t['session_id'])].state!='confirmed' and beta_schedule.get(db,row) is None) or
            sessions[uuid.UUID(t['session_id'])].schedule_revision!=t['base_schedule_revision'] for t in binding.content):
        proposal.state='obsolete';proposal.revision+=1
        plan.event(db,row,uid,command,'proposal_obsolete',stamp,dict(proposal_id=proposal.id));plan.bump(db,row);return False
    if not all(v['satisfied'] for v in votes(db,row,proposal,binding)):return False
    prepared=[]
    for target in binding.content:
        sess=sessions[uuid.UUID(target['session_id'])];values=target['segments'];start=datetime.fromisoformat(values[0]['starts_at']);end=datetime.fromisoformat(values[-1]['ends_at'])
        beta=beta_schedule.get(db,row)
        if stamp>=sess.ends_at and not (beta and beta.needs_review):fail('SCHEDULE_ENDED')
        graph.graph.time.interval(start,end,row.cycle_key.isoformat(),floor=plan.floor(db,row),current=stamp,
            minute_precision=beta is not None and beta.session_id==sess.id)
        existing={s.id:s for s in graph.graph.active_segments(db,sess.id)}
        if {uuid.UUID(v['segment_id']) for v in values}!=set(existing):fail('PROPOSAL_CONTEXT_CHANGED')
        for v in values:
            seg=existing[uuid.UUID(v['segment_id'])]
            if (str(seg.item_id),str(seg.round_id))!=(v['item_id'],v['round_id']):fail('PROPOSAL_CONTEXT_CHANGED')
        prepared.append((sess,values,existing,start,end,plan.members(db,row,sess)))
    before=[]
    for sess,values,existing,start,end,actual in prepared:
        before.append(dict(session=plan.snapshot(sess),segments=[plan.snapshot(s) for s in existing.values()]))
        for cm in actual:
            part=db.scalar(select(Participation).where(Participation.session_id==sess.id,Participation.membership_id==cm.membership_id))
            graph.graph.release(db,participation=part,reason='schedule_changed',stamp=stamp)
            part.confirmation_state='confirmation_pending';part.confirmed_at=part.confirmed_schedule_revision=None;part.revision+=1
        sess.starts_at=start;sess.ends_at=end;sess.schedule_revision+=1;sess.revision+=1;sess.state='confirmed'
        beta=beta_schedule.get(db,row)
        if beta is not None:
            beta.confirmation_kind='proposal_confirmed';beta.needs_review=False;beta.revision+=1
        for value in values:
            segment=existing[uuid.UUID(value['segment_id'])]
            for name in ('duration_minutes','duration_source'):setattr(segment,name,value[name])
            segment.starts_at=datetime.fromisoformat(value['starts_at']);segment.ends_at=datetime.fromisoformat(value['ends_at'])
            evidence=db.get(SegmentDurationEvidence,segment.id)
            evidence.item_settings_revision=value['item_settings_revision'];evidence.duration_policy_version=value['policy_version']
        db.flush()
        for cm in actual:
            response=latest(db,proposal,cm)
            if response and response.response=='accept':plan.consent(db,room,row,cm,sess,command,stamp,
                dict(kind='proposal_acceptance',proposal_id=str(proposal.id),vote_id=str(response.id),vote_command=str(response.command_id)))
    proposal.state='applied';proposal.revision+=1
    plan.event(db,row,uid,command,'proposal_applied',stamp,dict(proposal_id=proposal.id,previous=before));plan.bump(db,row);db.flush()
    return True


def reevaluate(db,room,row,uid,command,stamp):
    for proposal,binding in db.execute(select(Proposal,CycleProposal).join(CycleProposal,CycleProposal.proposal_id==Proposal.id).where(
            CycleProposal.cycle_id==row.id,CycleProposal.generation==row.generation,Proposal.state=='pending').order_by(Proposal.created_at,Proposal.id)):
        try:
            with db.begin_nested():evaluate(db,room,row,proposal,binding,uid,command,stamp)
        except GameError:
            proposal.state='obsolete';proposal.revision+=1
            plan.event(db,row,uid,command,'proposal_obsolete',stamp,dict(proposal_id=proposal.id,reason='revalidation_failed'));plan.bump(db,row)


def views(db,row,mine,stamp):
    actual=life.actual_member(db,row,mine.user_id)
    values=[]
    for proposal,binding in db.execute(select(Proposal,CycleProposal).join(CycleProposal,CycleProposal.proposal_id==Proposal.id).where(
            CycleProposal.cycle_id==row.id,CycleProposal.generation==row.generation).order_by(Proposal.created_at,Proposal.id)):
        if not binding.content:continue
        response=latest(db,proposal,actual) if actual else None
        eligible=actual is not None and any(actual.id==m.id for t in binding.content for m in plan.members(db,row,db.get(graph.Session,uuid.UUID(t['session_id']))))
        values.append(dict(proposal_id=proposal.id,revision=proposal.revision,proposal_plan_revision=proposal.proposal_plan_revision,
            created_from_plan_revision=proposal.created_from_plan_revision,state=proposal.state,
            target_session_ids=[t['session_id'] for t in binding.content],
            base_schedules=[dict(session_id=t['session_id'],schedule_revision=t['base_schedule_revision']) for t in binding.content],
            proposed_sessions=[dict(session_id=t['session_id'],segments=[{k:v for k,v in s.items() if k!='item_settings_revision'}|dict(state='planned',released_reason=None) for s in t['segments']]) for t in binding.content],
            votes=votes(db,row,proposal,binding),my_response=dict(proposal_id=proposal.id,proposal_plan_revision=proposal.proposal_plan_revision,
                membership_id=mine.id,membership_generation=row.generation,response=response.response if response else 'pending',
                response_revision=response.revision if response else 1,responded_at=response.effective_at if response else None,
                response_set='newcomer' if actual and actual.joined_at>proposal.created_at else 'existing'),
            permissions=dict(respond_proposal=life.commands.permission(None if proposal.state=='pending' and eligible and row.state=='open' else 'PROPOSAL_TARGET_REQUIRED'))))
    return values
