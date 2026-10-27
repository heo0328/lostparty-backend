"""Atomic member actions. Snapshot builders are shared by reads and locked writes.

No public commands are composed: cycles.execute owns the sole transaction, ACK
and boundary checks; these helpers only mutate the selected cycle graphs.
"""
import uuid
from datetime import datetime, timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.support import fail, GameError
from app.game_accounts.lifecycle import digest
from app.game_accounts.models import Character, Account, Configuration, Activity, Registration
from app.raid_rooms import (cycles, cycle_lifecycle as life, cycle_commands as commands,
    cycle_leadership as leaders, cycle_outcomes as outcomes, cycle_planning as plan,
    cycle_schedule as graph, atomic_member_schemas as wire)
from app.raid_rooms.cycle_creation import scope, permission
from app.raid_rooms.cycle_models import CycleGeneration, CycleMember, CycleSubmission
from app.raid_rooms.source_models import TimeReservation
from app.raid_rooms.command_context import seal, unseal


def encoded(value): return jsonable_encoder(value)

def bounded(model, value):
    import json
    result=model.model_validate(encoded(value)).model_dump(mode='json')
    if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())>1048576:fail('RESPONSE_TOO_LARGE',413)
    return result


def target(db,uid,rid,key,stamp):
    outcomes.ready(db)
    room,row,_=life.target_row(db,uid,rid,key,stamp)
    if row is None:fail('TARGET_NOT_OPEN')
    if row.provenance!='explicit' or not row.generation or row.settings_snapshot is None:fail('ROOM_REVIEW_REQUIRED')
    if row.state=='closed':fail('TARGET_CYCLE_CLOSED')
    generation=db.get(CycleGeneration,(row.id,row.generation))
    if generation is None:fail('ROOM_REVIEW_REQUIRED')
    if generation.state not in ('open','review_required'):fail('TARGET_CYCLE_CLOSED')
    return room,row


def bundle(db,row,cm):
    """Prove cleanup provenance and exact live leases without admitting the target.

    Ownership may have changed: it is captured for CAS, never used to transfer
    the stored membership or mutate a new owner's unrelated weekly rows.
    """
    member=db.get(life.Member,cm.membership_id)
    if member is None or member.room_id!=row.room_id or member.user_id!=cm.user_id or member.ended_at is not None:fail('ROOM_REVIEW_REQUIRED')
    owned=life.assignments(db,row,cm)
    if not owned or len({a.item_id for a in owned})!=len(owned):fail('ROOM_REVIEW_REQUIRED')
    proof=[]
    for a in owned:
        rd=db.get(outcomes.Round,a.round_id);item=db.get(graph.graph.Item,a.item_id)
        if (a.membership_id,a.user_id,a.room_id)!=(cm.membership_id,cm.user_id,row.room_id) or rd is None or item is None:fail('ROOM_REVIEW_REQUIRED')
        ledger_key=(cm.user_id,a.character_id,item.raid_id,row.cycle_key)
        weekly,lease=db.get(life.WeeklyState,ledger_key),db.get(life.WeeklyOccupancy,ledger_key)
        if a.state=='active' and (lease is None or lease.assignment_id!=a.id or weekly is None or
            weekly.active_party_id!=row.room_id or weekly.active_difficulty_id!=rd.difficulty_id or weekly.joined_at!=lease.joined_at):fail('ROOM_REVIEW_REQUIRED')
        character=db.get(Character,a.character_id)
        account=db.get(Account,character.account_id) if character else None
        configs=list(db.scalars(select(Configuration).where(Configuration.user_id==cm.user_id,
            Configuration.account_id==character.account_id).order_by(Configuration.id))) if character else []
        registrations=list(db.scalars(select(Registration).where(Registration.user_id==cm.user_id,
            Registration.account_id==character.account_id).order_by(Registration.id))) if character else []
        activities=[plan.snapshot(v) for c in configs for v in db.scalars(select(Activity).where(Activity.settings_id==c.id).order_by(Activity.character_id))]
        proof.append([plan.snapshot(a),plan.snapshot(rd),plan.snapshot(weekly) if weekly else None,
            plan.snapshot(lease) if lease else None,plan.snapshot(character) if character else None,
            plan.snapshot(account) if account else None,[plan.snapshot(c) for c in configs],activities,[plan.snapshot(r) for r in registrations]])
    parts=leaders.own_parts(db,row,cm)
    reservations=list(db.scalars(select(TimeReservation).where(TimeReservation.released_at.is_(None),
        (TimeReservation.assignment_id.in_([a.id for a in owned])) | (TimeReservation.participation_id.in_([p.id for p in parts])))
        .order_by(TimeReservation.id)))
    submission=db.get(CycleSubmission,cm.id)
    user=db.get(life.User,cm.user_id)
    hidden=[plan.snapshot(member),plan.snapshot(cm),user.status if user else None,proof,[plan.snapshot(p) for p in parts],
        [plan.snapshot(r) for r in reservations],plan.snapshot(submission) if submission else None]
    return owned,reservations,hidden


def cycle_proof(db,row):
    from app.raid_rooms.cycle_planning_models import CycleProposal
    from app.raid_rooms.source_models import ScheduleProposal
    from app.raid_rooms.cycle_application_models import CycleApplication
    proposals=list(db.scalars(select(ScheduleProposal).join(CycleProposal,CycleProposal.proposal_id==ScheduleProposal.id).where(
        CycleProposal.cycle_id==row.id,CycleProposal.generation==row.generation).order_by(ScheduleProposal.id)))
    apps=list(db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,
        CycleApplication.generation==row.generation).order_by(CycleApplication.id)))
    return [plan.snapshot(row),plan.snapshot(db.get(CycleGeneration,(row.id,row.generation))),
        [plan.snapshot(s) for s in graph.sessions(db,row,history=True)],
        [plan.snapshot(p) for p in proposals],[plan.snapshot(a) for a in apps]]


def body_base(stamp,row):
    return dict(expected_cycle_key=life.raids.cycle(stamp).cycle_key,target_cycle_key=row.cycle_key.isoformat(),
        room_cycle_id=str(row.id),target_generation=row.generation,expected_target_revision=row.revision)


def confirmation(uid,rid,row,action,data,hidden,expected,stamp):
    binding=digest(encoded([uid,rid,action,{k:v for k,v in scope(stamp,row.cycle_key.isoformat(),row).items() if k!='server_now'},data,hidden,expected]))
    expires=min(stamp+timedelta(seconds=120),life.raids.cycle(stamp).ends_at)
    return dict(context_token=seal(dict(actor=str(uid),room=str(rid),command=action,body=expected,
        expires=expires.isoformat(),digest=binding)),issued_at=stamp,expires_at=expires),binding


def validate_token(uid,rid,action,body,stamp):
    if body['expected_cycle_key']!=life.raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
    token=unseal(body['context_token'])
    if (token.get('actor'),token.get('room'),token.get('command'))!=(str(uid),str(rid),action) or token.get('body')!={k:v for k,v in body.items() if k!='context_token'}:fail('CONTEXT_INVALID',400)
    if stamp>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
    return token


def explicit_cas(row,body,cm,*,departure=False):
    if (str(row.id),row.generation)!=(body['room_cycle_id'],body['target_generation']):fail('TARGET_SCOPE_MISMATCH',400)
    if row.revision!=body['expected_target_revision']:fail('REVISION_CONFLICT')
    field='actor_cycle_member_id' if departure else 'target_cycle_member_id'
    revision='expected_cycle_member_revision' if departure else 'expected_target_cycle_member_revision'
    if str(cm.id)!=body[field]:fail('TARGET_SCOPE_MISMATCH',400)
    if cm.revision!=body[revision]:fail('REVISION_CONFLICT')


def removal_effect(row,cm,owned,reservations):
    return dict(target_cycle_key=row.cycle_key,cycle_member_id=cm.id,
        cancel_assignment_ids=[a.id for a in owned if a.state=='active'],
        preserved_completed_assignment_ids=[a.id for a in owned if a.state=='completed'],released_reservation_count=len(reservations))


def removal_target(db,room,row,uid,cm,stamp):
    actor=life.actual_member(db,row,uid,states=('participating',))
    owned=life.assignments(db,row,cm)
    if actor is None or not owned:fail('TARGET_LEADER_REQUIRED',403)
    leadership=commands.leadership(db,row)
    data=dict(target_cycle_key=row.cycle_key,room_cycle_id=row.id,target_generation=row.generation,target_revision=row.revision,
        actor_cycle_member_id=actor.id,actor_cycle_member_revision=actor.revision,target_cycle_member_id=cm.id,
        target_cycle_member_revision=cm.revision,character_id=owned[0].character_id,
        character_name=owned[0].display.get('character_name'),leadership=leadership)
    reason=None;proof=None;values=None
    try:
        if actor.id!=leadership['leader_cycle_member_id']:fail('TARGET_LEADER_REQUIRED',403)
        _,qualification=life.qualify(db,room,row,actor)
        if cm.id in (actor.id,leadership['leader_cycle_member_id']) or cm.state not in ('participating','review_required'):fail('ROOM_REMOVAL_TARGET_INVALID')
        values,reservations,proof=bundle(db,row,cm)
        _,_,actor_proof=bundle(db,row,actor)
        proof=[proof,actor_proof,qualification,plan.snapshot(room),cycle_proof(db,row)]
    except GameError as error:
        reason=error.code;reservations=[]
    effect=removal_effect(row,cm,values,reservations) if reason is None else None
    return data,reason,effect,proof,values


def prepare_removal(db,uid,rid,key,cmid,stamp):
    room,row=target(db,uid,rid,key,stamp)
    cm=db.get(CycleMember,cmid)
    if cm is not None and cm.cycle_id==row.id and cm.generation is None:fail('ROOM_REVIEW_REQUIRED')
    if cm is None or (cm.cycle_id,cm.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
    source,reason,effect,proof,owned=removal_target(db,room,row,uid,cm,stamp)
    value=cycles.target(stamp,key)
    opposite=(value.current+timedelta(days=7)).isoformat() if value.key==value.current else value.current.isoformat()
    _,other=cycles.resolve(db,rid,opposite,stamp)
    other_cm=life.actual_member(db,other,cm.user_id,states=('participating','review_required')) if other else None
    if other is not None and other_cm is None:
        other_cm=db.scalar(select(CycleMember).join(life.Member,life.Member.id==CycleMember.membership_id).where(
            CycleMember.cycle_id==other.id,CycleMember.user_id==cm.user_id,CycleMember.generation.is_(None),
            CycleMember.state=='review_required',life.Member.ended_at.is_(None)))
    relation=dict(target_cycle_key=opposite,status='none',target=None)
    both_reason='OTHER_TARGET_NOT_PARTICIPATING';other_effect=other_proof=other_owned=None
    if other_cm:
        review=other_cm.generation is None or other_cm.state=='review_required' or other.state!='open' or other.provenance!='explicit' or not other.generation
        relation['status']='review_required' if review else 'participating'
        both_reason='ROOM_REVIEW_REQUIRED' if review else 'TARGET_LEADER_REQUIRED'
        if not review:
            try:
                other_target,other_reason,other_effect,other_proof,other_owned=removal_target(db,room,other,uid,other_cm,stamp)
                relation['target']=other_target;both_reason=other_reason
            except GameError as error:both_reason=error.code
    if row.state=='review_required' or cm.state=='review_required' or db.get(CycleGeneration,(row.id,row.generation)).state!='open':both_reason='ROOM_REVIEW_REQUIRED'
    data=dict(action='member_removal',room_id=rid,target_membership_id=cm.membership_id,source=source,opposite_relation=relation,options={})
    base={**body_base(stamp,row),**dict(target_membership_id=str(cm.membership_id),target_cycle_member_id=str(cm.id),expected_target_cycle_member_revision=cm.revision)}
    bindings={}
    for mode in ('current_only','both'):
        denial=reason if mode=='current_only' else reason or both_reason
        impact=None;conf=None
        if denial is None:
            effects=[effect] if mode=='current_only' else [effect,other_effect]
            impact=dict(mode=mode,affected_cycle_keys=[e['target_cycle_key'] for e in effects],targets=effects,
                preserves_completed=True,preserves_global_membership=True)
            meaningful=dict(action='member_removal',room_id=rid,target_membership_id=cm.membership_id,source=source,impact=impact)
            conf,bindings[mode]=confirmation(uid,rid,row,'member_removal',meaningful,
                proof if mode=='current_only' else [proof,other_proof],{**base,'mode':mode},stamp)
        data['options'][mode]=dict(permission=permission(denial),impact=impact,confirmation=conf)
    return dict(scope=scope(stamp,key,row),data=data),bindings,room,row,cm,owned,other,other_cm,other_owned


def display(db,owned,selected):
    values=[]
    for a in owned:
        if a.state not in ('active','completed'):continue
        rd=db.get(outcomes.Round,a.round_id);item=db.get(graph.graph.Item,a.item_id)
        try:
            difficulty=life.raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version)
            raid=outcomes.weekly.raid_by_id(item.raid_id)
        except life.raids.CatalogSelectionError as error:fail(error.code)
        values.append(dict(assignment_id=a.id,round_id=a.round_id,item_id=a.item_id,character_id=a.character_id,
            character_name=a.display.get('character_name'),raid_id=item.raid_id,raid_name=raid.display_name,
            difficulty_id=rd.difficulty_id,difficulty_name=difficulty.name,catalog_version=rd.catalog_version,
            effect='complete' if a.id==selected.id else 'cancel' if a.state=='active' else 'preserve_completed'))
    result=dict(character_id=selected.character_id,character_name=selected.display.get('character_name'),assignments=values)
    return {**result,'display_revision':digest(encoded(result))}


def prepare_departure(db,uid,rid,key,round_id,stamp):
    room,row=target(db,uid,rid,key,stamp)
    if row.state!='open' or db.get(CycleGeneration,(row.id,row.generation)).state!='open':fail('ROOM_REVIEW_REQUIRED')
    cm=life.actual_member(db,row,uid,states=('participating',))
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    _,qualification=life.qualify(db,room,row,cm)
    owned,reservations,proof=bundle(db,row,cm)
    link=db.get(outcomes.CycleRound,round_id)
    if link is None or (link.cycle_id,link.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
    cycles.require_current_round(db,row,round_id)
    selected=next((a for a in owned if a.round_id==round_id and a.state=='active'),None)
    if selected is None or db.get(outcomes.Round,round_id).state!='active':fail('ROUND_NOT_ACTIVE')
    others=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
        CycleMember.id!=cm.id,CycleMember.state.in_(('participating','review_required'))).order_by(CycleMember.joined_order,CycleMember.id)))
    actual_memberships={cm.membership_id}|{m.membership_id for m in others}
    if any(a.state=='active' and a.membership_id not in actual_memberships for a in outcomes.assignments(db,row)):fail('ROOM_REVIEW_REQUIRED')
    leadership=commands.leadership(db,row);reason=None;successor=None;successor_proof=[]
    try:outcomes.playable(stamp,key)
    except GameError as error:reason=error.code
    active=[a for a in owned if a.state=='active'];previous=[a.id for a in owned if a.state=='completed']
    complete_all=True
    for item,rd in life.admission.rounds(db,row):
        assignments=[a for a in outcomes.assignments(db,row) if a.round_id==rd.id]
        remaining=[a for a in assignments if a.id!=selected.id and not(a.membership_id==cm.membership_id and a.state=='active')]
        proven=rd.state=='completed' or (rd.state=='active' and (selected.round_id==rd.id or any(a.state=='completed' for a in remaining))
            and not any(a.state in ('active','stopped_incomplete') for a in remaining))
        complete_all=complete_all and proven
    mode='close_completed' if complete_all else 'close_incomplete'
    if others:
        mode='leave'
        if leadership['leader_cycle_member_id']==cm.id:
            mode='automatic_successor'
            candidates,candidate_proof=life.candidates(db,room,row,cm)
            successor_proof=candidate_proof
            eligible={m.id for m in others if m.state=='participating' and any(a.state=='active' for a in life.assignments(db,row,m))}
            candidate=next((c for c in candidates if c['cycle_member_id'] in eligible and c['permission']['allowed']),None)
            if candidate:successor={k:v for k,v in candidate.items() if k!='permission'}
            else:reason=reason or 'SUCCESSOR_UNAVAILABLE'
    impact=dict(complete_assignment_ids=[selected.id],cancel_assignment_ids=[a.id for a in active if a.id!=selected.id],
        preserved_completed_assignment_ids=previous,released_reservation_count=len(reservations),departure_effect=mode,
        successor=successor,preserves_other_cycles=True,preserves_global_membership=True)
    data=dict(action='personal_completion_departure',room_id=rid,subject=dict(membership_id=cm.membership_id,
        cycle_member_id=cm.id,cycle_member_revision=cm.revision,character_id=selected.character_id,round_id=round_id,
        assignment_id=selected.id,assignment_revision=selected.revision),leadership=leadership,impact=impact,
        display=display(db,owned,selected),permission=permission(reason),confirmation=None)
    expected={**body_base(stamp,row),'actor_cycle_member_id':str(cm.id),'expected_cycle_member_revision':cm.revision,'round_id':str(round_id)}
    hidden=[proof,qualification,plan.snapshot(room),cycle_proof(db,row),[plan.snapshot(m) for m in others],successor_proof,
        [plan.snapshot(a) for a in outcomes.assignments(db,row)]]
    conf,binding=confirmation(uid,rid,row,'personal_completion_departure',data,hidden,expected,stamp)
    if reason is None:data['confirmation']=conf
    return dict(scope=scope(stamp,key,row),data=data),binding,room,row,cm,owned,selected


def get(principal,rid,key,*,round_id=None,cmid=None):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        if round_id is not None:
            return bounded(wire.DepartureContext,prepare_departure(db,uid,rid,key,round_id,stamp)[0])
        return bounded(wire.RemovalContext,prepare_removal(db,uid,rid,key,cmid,stamp)[0])


def cleanup(db,row,cm,owned,command,stamp,*,selected=None):
    from app.raid_rooms.integrated_models import RecruitmentSegment as Segment
    parts=leaders.own_parts(db,row,cm)
    segments=list(db.scalars(select(Segment).where(Segment.session_id.in_([p.session_id for p in parts]),
        Segment.round_id.in_([a.round_id for a in owned])).order_by(Segment.session_id,Segment.ordinal)))
    evidence=dict(record_schedule_segments=[dict(segment_id=s.id,round_id=s.round_id,session_id=s.session_id,
        starts_at=s.starts_at,ends_at=s.ends_at,state='released') for s in segments],
        assignments=[life.assignment_snapshot(a) for a in owned],participations=leaders.release_parts(db,row,cm,stamp))
    submission=db.get(CycleSubmission,cm.id)
    if submission is not None:evidence['submission']=plan.snapshot(submission);db.delete(submission)
    for a in owned:
        if a.state!='active':continue
        graph.graph.release(db,assignment=a,reason='raid_completed' if a==selected else 'future_cancel',stamp=stamp)
        life.admission.core.release_assignment(db,a,stamp)
        if a==selected:
            a.state='completed';rd=db.get(outcomes.Round,a.round_id);item=db.get(graph.graph.Item,a.item_id)
            weekly=db.get(life.WeeklyState,(a.user_id,a.character_id,item.raid_id,row.cycle_key))
            if weekly.manual_completed_at is None:weekly.manual_completed_at=stamp;weekly.manual_difficulty_id=rd.difficulty_id
            a.build={**(a.build or {}),'completion_source':'manual','completed_at':stamp.isoformat()}
    cm.state='cancelled' if selected else 'removed';cm.ended_at=stamp;cm.revision+=1
    life.event(db,row,cm,command,cm.state,stamp,evidence)
    row.members_revision+=1;plan.bump(db,row);db.flush()
    if selected:
        outcomes.event(db,row,cm.user_id,command,'personal_completion',stamp,evidence)
        life.decision(db,row,cm.user_id,command,'declined',stamp,dict(cancelled_cycle_member_id=cm.id,reason='personal_completion_departure'))
    return evidence


def effect(db,row,cm,impact,completed):
    return dict(target_cycle_key=row.cycle_key,room_cycle_id=row.id,target_generation=row.generation,
        target_revision=row.revision,cycle_member_id=cm.id,cycle_member_revision=cm.revision,state=cm.state,
        leadership=commands.leadership(db,row),completed_assignment_ids=completed,
        cancelled_assignment_ids=impact['cancel_assignment_ids'],preserved_completed_assignment_ids=impact['preserved_completed_assignment_ids'])


def execute(principal,rid,command,data,*,departure=False):
    body=data.model_dump(mode='json');action='personal_completion_departure' if departure else 'member_removal'
    def run(db,uid,stamp):
        guards=[]
        token=validate_token(uid,rid,action,body,stamp)
        if departure:
            value,binding,room,row,cm,owned,selected=prepare_departure(db,uid,rid,body['target_cycle_key'],uuid.UUID(body['round_id']),stamp)
            explicit_cas(row,body,cm,departure=True)
            current=value['data'];denial=current['permission']['reason']
            if denial:fail(denial)
            life.require_match(token,binding)
            guards.append(graph.final_deadlines(db,row,[],stamp,join=False))
            impact=current['impact'];cleanup(db,row,cm,owned,command,stamp,selected=selected)
            generation=db.get(CycleGeneration,(row.id,row.generation))
            mode=impact['departure_effect']
            if mode=='automatic_successor':
                old=generation.leader_cycle_member_id
                generation.leader_cycle_member_id=impact['successor']['cycle_member_id'];generation.leadership_revision+=1
                life.decision(db,row,uid,command,'automatic_successor',stamp,dict(previous=old,successor=impact['successor']))
            elif mode.startswith('close_'):
                leaders.close_target(db,row,stamp)
                if mode=='close_completed':
                    generation.state='completed'
                    # close_target stops only active rounds; proven completed items
                    # keep their completion evidence and become completed rounds.
                    for _,rd in life.admission.rounds(db,row):
                        if rd.state=='stopped_incomplete':rd.state='completed'
                generation.leadership_revision+=1
            db.flush();outcomes.settle_participations(db,row,stamp,stopping=mode=='close_incomplete')
            if row.state=='open':plan.refresh(db,room,row,uid,command,stamp)
            effects=[effect(db,row,cm,impact,[selected.id])]
        else:
            value,bindings,room,row,cm,owned,other,other_cm,other_owned=prepare_removal(db,uid,rid,body['target_cycle_key'],uuid.UUID(body['target_cycle_member_id']),stamp)
            explicit_cas(row,body,cm)
            if str(cm.membership_id)!=body['target_membership_id']:fail('TARGET_SCOPE_MISMATCH',400)
            option=value['data']['options'][body['mode']]
            denial=option['permission']['reason']
            if denial:fail(denial,403 if denial=='TARGET_LEADER_REQUIRED' else 409)
            life.require_match(token,bindings[body['mode']])
            selected_targets=[(row,cm,owned)] if body['mode']=='current_only' else [(row,cm,owned),(other,other_cm,other_owned)]
            guards.extend(graph.final_deadlines(db,r,[],stamp,join=False) for r,_,_ in selected_targets)
            # All target proof/authority checks above precede the first mutation.
            for target_row,target_cm,values in selected_targets:
                cleanup(db,target_row,target_cm,values,command,stamp)
                plan.refresh(db,room,target_row,uid,command,stamp)
            effects=[effect(db,r,m,i,[]) for (r,m,_),i in zip(selected_targets,option['impact']['targets'])]
        db.flush()
        result=bounded(wire.ActionResult,dict(scope=scope(stamp,body['target_cycle_key'],row),data=dict(command_id=command,
            action=action,outcome='applied',executed_at=stamp,room_id=rid,subject_membership_id=cm.membership_id,
            affected_cycle_keys=[e['target_cycle_key'] for e in effects],effects=effects)))
        def final(current):
            for guard in guards:guard(current)
            if departure:outcomes.playable(current,body['target_cycle_key'])
            if current>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
        return 200,result,final
    return cycles.execute(principal,'personal-depart' if departure else 'member-remove',command,dict(room_id=str(rid),body=body),run)
