"""T-only cancellation, deterministic succession and explicit leadership transfer."""
import uuid
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycle_lifecycle as life,cycle_schedule as schedule,cycle_commands as commands,cycles,cycle_wire as wire
from app.raid_rooms.cycle_creation import permission
from app.raid_rooms.cycle_models import CycleGeneration,CycleMember,CycleSubmission
from app.raid_rooms.cycle_application_models import CycleApplication,CycleSession
from app.raid_rooms.source_models import SessionParticipation,TimeReservation,ScheduleProposal,ProposalTarget


def own_parts(db,row,cm):
    return list(db.scalars(select(SessionParticipation).join(CycleSession,CycleSession.session_id==SessionParticipation.session_id).where(
        CycleSession.cycle_id==row.id,CycleSession.generation==row.generation,SessionParticipation.membership_id==cm.membership_id)))


def release_parts(db,row,cm,stamp,*,ending=True):
    proof=[]
    for part in own_parts(db,row,cm):
        proof.append([part.id,part.revision,part.state,part.confirmation_state,part.confirmed_at,part.confirmed_schedule_revision])
        schedule.graph.release(db,participation=part,reason='future_cancel' if ending else 'character_changed',stamp=stamp)
        if part.state=='active':
            part.revision+=1
            if ending:part.state='ended'
            else:
                part.confirmation_state='confirmation_pending' if db.get(schedule.Session,part.session_id).state=='confirmed' else 'not_required'
                part.confirmed_at=part.confirmed_schedule_revision=None
    return proof


def prepare_cancel(db,uid,rid,key,stamp):
    room,row,value=life.target_row(db,uid,rid,key,stamp,next_only=True)
    if row is None:fail('TARGET_NOT_OPEN')
    cm=life.actual_member(db,row,uid,states=(*life.VALID_STATES,'review_required'))
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    if row.state!='open':fail('TARGET_CYCLE_CLOSED')
    owned=life.assignments(db,row,cm);parts=own_parts(db,row,cm)
    reservations=list(db.scalars(select(TimeReservation).where(TimeReservation.participation_id.in_([p.id for p in parts]),
        TimeReservation.released_at.is_(None)).order_by(TimeReservation.id)))
    leadership=commands.leadership(db,row);leader=leadership['leader_cycle_member_id']==cm.id
    others=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
        CycleMember.id!=cm.id,CycleMember.state.in_((*life.VALID_STATES,'review_required'))).order_by(CycleMember.id)))
    candidates,proof=life.candidates(db,room,row,cm) if leader else ([],[])
    successor=next((c for c in candidates if c['permission']['allowed']),None)
    mode='leave' if not leader else 'auto_successor' if others else 'close_target'
    reason='SUCCESSOR_UNAVAILABLE' if mode=='auto_successor' and successor is None else None
    apps=list(db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,
        CycleApplication.generation==row.generation,CycleApplication.state=='pending').order_by(CycleApplication.id)))
    ledger=[]
    for item,rd in life.admission.rounds(db,row):
        for a in owned:
            if a.item_id!=item.id:continue
            key_tuple=(uid,a.character_id,item.raid_id,row.cycle_key)
            state,lease=db.get(life.WeeklyState,key_tuple),db.get(life.WeeklyOccupancy,key_tuple)
            ledger.append([a.id,a.revision,a.state,state.revision if state else 1,str(lease.assignment_id) if lease else None])
    data=dict(room_id=rid,impact=dict(effect_scope='target_bundle',assignment_count=sum(a.state=='active' for a in owned),
        reservation_count=len(reservations),preserves_other_cycles=True,preserves_global_membership=True),
        permission=permission(reason),leadership=leadership,members_revision=row.members_revision,mode=mode,successor=successor)
    hidden=[cm.id,cm.revision,cm.state,[[p.id,p.revision,p.state,p.confirmation_state,p.confirmed_schedule_revision] for p in parts],
        [[r.id,r.schedule_revision,r.starts_at,r.ends_at] for r in reservations],ledger,proof,
        [[a.id,a.revision] for a in apps],[[m.id,m.revision,m.state] for m in others]]
    submission=db.get(CycleSubmission,cm.id)
    hidden.append(submission.revision if submission else None)
    result,binding=life.sign(uid,rid,key,'cancel',jsonable_encoder(data),hidden,stamp,row=row,
        extra={'successor':str(successor['cycle_member_id']) if successor else None})
    return result,binding,room,row,cm,owned


def get_cancel(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        value,*_=prepare_cancel(db,uid,rid,key,stamp)
        return wire.CancellationContext.model_validate(value).model_dump(mode='json')


def close_target(db,row,stamp):
    ids={s.id for s in schedule.sessions(db,row)}
    for proposal in db.scalars(select(ScheduleProposal).where(ScheduleProposal.room_id==row.room_id,ScheduleProposal.state=='pending')):
        targets=set(db.scalars(select(ProposalTarget.session_id).where(ProposalTarget.proposal_id==proposal.id)))
        if targets & ids:
            if targets-ids:fail('ROOM_REVIEW_REQUIRED')
            proposal.state='cancelled';proposal.revision+=1
    for app in db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,
            CycleApplication.generation==row.generation,CycleApplication.state=='pending')):
        app.state='cancelled';app.ended_at=stamp;app.revision+=1
    for session in schedule.sessions(db,row):
        session.state='cancelled';session.revision+=1
    for item,rd in life.admission.rounds(db,row):
        if rd.state=='active':rd.state='stopped_incomplete';rd.ended_at=stamp;rd.revision+=1
    generation=db.get(CycleGeneration,(row.id,row.generation))
    generation.state='cancelled';generation.closed_at=stamp;generation.leader_cycle_member_id=None
    row.state='closed'


def cancel(principal,rid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        token=life.verify_token(uid,rid,body,'cancel',stamp)
        value,binding,room,row,cm,owned=prepare_cancel(db,uid,rid,body['target_cycle_key'],stamp)
        commands.cas(db,row,body,stamp,leader=True)
        final_guard=schedule.final_deadlines(db,row,[],stamp,join=False)
        current=value['data'];successor=current['successor']
        if token['successor']!=(str(successor['cycle_member_id']) if successor else None) or not current['permission']['allowed']:
            fail('SUCCESSOR_UNAVAILABLE')
        if token['digest']!=binding:
            fail('SUCCESSOR_UNAVAILABLE' if current['mode']=='auto_successor' else 'TARGET_CONTEXT_STALE')
        evidence=dict(assignments=[life.assignment_snapshot(a) for a in owned],
            participations=release_parts(db,row,cm,stamp),joined_order=str(cm.joined_order),joined_at=cm.joined_at)
        submission=db.get(CycleSubmission,cm.id)
        if submission is not None:
            evidence['submission']={name:getattr(submission,name) for name in ('revision','source_personal_revision',
                'intervals','normalized_intervals','submitted_at')}
            db.delete(submission)
        for a in owned:
            if a.state=='active':life.admission.core.release_assignment(db,a,stamp)
        cm.state='cancelled';cm.ended_at=stamp;cm.revision+=1
        life.event(db,row,cm,command,'cancelled',stamp,evidence)
        generation=db.get(CycleGeneration,(row.id,row.generation))
        if current['mode']!='leave':
            generation.leadership_revision+=1
            if current['mode']=='auto_successor':
                old=generation.leader_cycle_member_id;generation.leader_cycle_member_id=uuid.UUID(successor['cycle_member_id'])
                life.decision(db,row,uid,command,'automatic_successor',stamp,dict(previous=old,successor=successor))
            else:
                close_target(db,row,stamp)
                life.decision(db,row,uid,command,'future_empty_cancelled',stamp,dict(reason='future_empty_cancelled',actor=cm.id))
        life.decision(db,row,uid,command,'declined',stamp,dict(cancelled_cycle_member_id=cm.id,
            character_id=str(owned[0].character_id) if owned else None,
            raid_ids=[i.raid_id for i,r in life.admission.rounds(db,row)]))
        row.revision+=1;row.members_revision+=1;row.plan_revision+=1
        cycles.touch_directory(db,row.cycle_key);db.flush()
        if schedule.planning_enabled(db):
            from app.raid_rooms import cycle_planning
            cycle_planning.refresh(db,room,row,uid,command,stamp)
        return 200,life.ack(db,row,command,stamp),final_guard
    return cycles.execute(principal,'cancel',command,dict(room_id=str(rid),body=body),run)


def prepare_transfer(db,uid,rid,key,stamp):
    room,row,value=life.target_row(db,uid,rid,key,stamp)
    if row is None:fail('TARGET_NOT_OPEN')
    cm=life.actual_member(db,row,uid)
    if cm is None or commands.leadership(db,row)['leader_cycle_member_id']!=cm.id:fail('TARGET_LEADER_REQUIRED',403)
    candidates,proof=life.candidates(db,room,row,cm)
    reason=None;actor_proof=None
    try:_,actor_proof=life.qualify(db,room,row,cm)
    except GameError as error:reason=error.code
    if not any(c['permission']['allowed'] for c in candidates):reason=reason or 'SUCCESSOR_UNAVAILABLE'
    data=dict(room_id=rid,leadership=commands.leadership(db,row),members_revision=row.members_revision,
        candidates=candidates,permission=permission(reason),preserves_other_cycles=True,changes_formation=False)
    result,binding=life.sign(uid,rid,key,'transfer',jsonable_encoder(data),[cm.id,cm.revision,actor_proof,proof],stamp,row=row)
    return result,binding,row,cm


def get_transfer(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        value,*_=prepare_transfer(db,uid,rid,key,stamp)
        return wire.TransferContext.model_validate(value).model_dump(mode='json')


def transfer(principal,rid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        token=life.verify_token(uid,rid,body,'transfer',stamp)
        value,binding,row,cm=prepare_transfer(db,uid,rid,body['target_cycle_key'],stamp)
        commands.cas(db,row,body,stamp,leader=True)
        life.require_match(token,binding)
        current=value['data'];candidate=next((c for c in current['candidates'] if c['cycle_member_id']==body['candidate_cycle_member_id']),None)
        if not current['permission']['allowed']:fail(current['permission']['reason'])
        if candidate is None or not candidate['permission']['allowed']:fail('SUCCESSOR_UNAVAILABLE')
        if candidate['revision']!=body['expected_candidate_revision']:fail('REVISION_CONFLICT')
        generation=db.get(CycleGeneration,(row.id,row.generation))
        generation.leader_cycle_member_id=uuid.UUID(candidate['cycle_member_id']);generation.leadership_revision+=1
        row.revision+=1;row.plan_revision+=1;cycles.touch_directory(db,row.cycle_key)
        life.decision(db,row,uid,command,'leadership_transferred',stamp,dict(previous=cm.id,candidate=candidate))
        db.flush()
        return 200,life.ack(db,row,command,stamp)
    return cycles.execute(principal,'transfer',command,dict(room_id=str(rid),body=body),run)


def action_permissions(db,uid,room,row,stamp):
    result={}
    for name,prepare in (('cancel_target_participation',prepare_cancel),('transfer_leadership',prepare_transfer)):
        try:result[name]=prepare(db,uid,room.id,row.cycle_key.isoformat(),stamp)[0]['data']['permission']
        except GameError as error:result[name]=permission(error.code)
    from app.raid_rooms import cycle_opening
    key=(life.cycles.target(stamp,row.cycle_key.isoformat()).current+life.timedelta(days=7)).isoformat()
    for name,intent in (('open_next_cycle','open'),('reopen_next_cycle','reopen')):
        try:
            value=cycle_opening.prepare(db,uid,room.id,key,intent,None,None,stamp)[0]['data']
            result[name]=value['permission']
            if value['opening_effect']=='already_open':result[name]=permission('TARGET_ALREADY_OPEN')
        except GameError as error:result[name]=permission(error.code)
    return result
