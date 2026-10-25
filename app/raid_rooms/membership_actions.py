"""Ordinary membership commands. One snapshot planner, one locked transaction.

Legacy cancel/end/leave and #22/#23 keep their original transports and effects.
A failed successor qualification never vetoes a proven actor departure.
"""
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from sqlalchemy import select, text
from app.game_accounts.support import fail, GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import (cycles, cycle_lifecycle as life, cycle_commands as commands,
    cycle_leadership as leaders, cycle_planning as planning, cycle_schedule as graph,
    atomic_members as atomic, membership_action_schemas as wire)
from app.raid_rooms.cycle_creation import permission
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember, CycleSubmission
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.membership_action_models import LeadershipRecovery, MembershipActionAudit
from app.raid_rooms.command_context import seal, unseal

POLICY = 'membership-actions-1'
ACTIONS = ('leave_target','leave_all','dissolve_led_targets','recover_leadership')
LIVE = ('participating','review_required')


def bounded(model,value, *, snapshot=None):
    # Required new fields stay closed while legacy optional content keeps its exact presence.
    import json
    from app.raid_rooms import beta_output
    result=beta_output.render(*snapshot,model,value,exclude_unset=True) if snapshot is not None else model.model_validate(atomic.encoded(value)).model_dump(mode="json",exclude_unset=True)
    if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())>1048576:fail('RESPONSE_TOO_LARGE',413)
    return result


def ready(db):
    if list(db.scalars(text('SELECT version_num FROM alembic_version'))) not in (['0031_membership_actions'],['0032_beta_recruitment']):
        fail('RECRUITMENT_COMMAND_NOT_READY',503)


def scope(stamp,key):
    return dict(server_now=stamp,current_cycle_key=life.raids.cycle(stamp).cycle_key,
        view_cycle_key=key,policy_version=POLICY)


def inc(value):
    if value>=2147483647:fail('REVISION_CONFLICT')
    return value+1


def rule(before,change=False,*,flexible=False):
    if change and before>=2147483647:fail('REVISION_CONFLICT')
    return dict(before=before,comparison='increase' if change else 'equal',
        exact_after=None if change and flexible else inc(before) if change else before)


def leadership(db,row):
    gen=db.get(CycleGeneration,(row.id,row.generation)) if row and row.generation else None
    if gen is None:return None
    cm=db.get(CycleMember,gen.leader_cycle_member_id) if gen.leader_cycle_member_id else None
    if gen.leader_cycle_member_id and (cm is None or (cm.cycle_id,cm.generation)!=(row.id,row.generation)):
        fail('ROOM_REVIEW_REQUIRED')
    return dict(leader_cycle_member_id=cm.id if cm else None,leader_membership_id=cm.membership_id if cm else None,
        leadership_revision=gen.leadership_revision)


def roster(db,row):
    return list(db.scalars(select(CycleMember).join(life.Member,life.Member.id==CycleMember.membership_id).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
        CycleMember.state.in_(LIVE),life.Member.ended_at.is_(None)).order_by(CycleMember.joined_order,CycleMember.id)))


def qualified(db,room,row,cm):
    # Review is a stored state, not permission to invent eligibility. Revalidate
    # the actual identity/leases with a read-only projection of its candidate state.
    probe=SimpleNamespace(**{c.name:getattr(cm,c.name) for c in cm.__table__.columns})
    probe.state='participating'
    try:
        _,proof=life.qualify(db,room,row,probe)
        return None,proof
    except GameError as error:return error.code,None


def successor(db,room,row,members):
    proof=[];eligible=[];uncertain=False;reasons=[]
    for cm in members:
        reason,value=qualified(db,room,row,cm)
        proof.append([planning.snapshot(cm),value,reason])
        if cm.joined_order is None:uncertain=True;reasons.append('JOIN_ORDER_UNVERIFIED')
        if reason:reasons.append(reason)
        if reason is None and cm.joined_order is not None:eligible.append(cm)
    chosen=None if uncertain else next(iter(eligible),None)
    return chosen,proof,sorted(set(reasons))[:16]


def member_effect(db,row,cm,state):
    owned=life.assignments(db,row,cm);first=next(iter(owned),None)
    return dict(membership_id=cm.membership_id,cycle_member_id=cm.id,cycle_member_revision=cm.revision,
        character_id=first.character_id if first else None,character_name=first.display.get('character_name') if first else None,
        joined_order=str(cm.joined_order) if cm.joined_order else None,revision_rule=rule(cm.revision,state!=cm.state),
        planned_state=state,cancelled_assignment_ids=[a.id for a in owned if a.state=='active' and state in ('cancelled','removed')],
        preserved_completed_assignment_ids=[a.id for a in owned if a.state=='completed'],state=cm.state)


def plan_target(db,room,row,actor,action,stamp):
    if row.provenance!='explicit' or not row.generation or not row.settings_snapshot:fail('ROOM_REVIEW_REQUIRED')
    gen=db.get(CycleGeneration,(row.id,row.generation))
    if gen is None or row.state not in ('open','review_required') or gen.state not in ('open','review_required'):
        fail('ROOM_REVIEW_REQUIRED')
    lead=leadership(db,row);members=roster(db,row)
    mine=next((m for m in members if m.membership_id==actor.id),None)
    recovery=db.get(LeadershipRecovery,(row.id,row.generation))
    if action=='recover_leadership':
        if mine is None or recovery is None or recovery.state not in ('pending_review','review_remaining'):
            fail('LEADERSHIP_RECOVERY_NOT_REQUIRED')
        chosen,candidate_proof,reasons=successor(db,room,row,members)
        if chosen is None:fail('LEADERSHIP_RECOVERY_NOT_READY')
        # An already established, still eligible leader remains the leader.
        previous=next((m for m in members if m.id==gen.leader_cycle_member_id),None)
        if previous is not None and qualified(db,room,row,previous)[0] is None:chosen=previous
        affected=[]
        for cm in members:
            if cm.state=='review_required' and qualified(db,room,row,cm)[0] is None:
                atomic.bundle(db,row,cm)
                affected.append(member_effect(db,row,cm,'participating'))
        after_state='review_required' if reasons else 'open'
        transition='recover';new_id=chosen.id;status='active';reason='OTHER_REVIEW_REMAINS' if reasons else None
    else:
        affected_cms=members if action=='dissolve_led_targets' else [mine] if mine else []
        if not affected_cms:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
        if action=='dissolve_led_targets' and (mine is None or gen.leader_cycle_member_id!=mine.id):fail('TARGET_LEADER_REQUIRED',403)
        affected=[]
        for cm in affected_cms:
            atomic.bundle(db,row,cm)
            affected.append(member_effect(db,row,cm,'removed' if action=='dissolve_led_targets' else 'cancelled'))
        remaining=[m for m in members if m not in affected_cms]
        chosen=None;candidate_proof=[];reasons=[]
        if not remaining:
            transition='dissolve' if action=='dissolve_led_targets' else 'close_empty'
            new_id=None;after_state='closed';status='closed';reason=None
        elif gen.leader_cycle_member_id in {m.id for m in affected_cms}:
            chosen,candidate_proof,reasons=successor(db,room,row,remaining)
            if chosen is not None and chosen.state=='review_required':affected.append(member_effect(db,row,chosen,'participating'))
            new_id=chosen.id if chosen else None
            transition='automatic_successor' if chosen else 'leadership_pending'
            after_state='review_required' if chosen is None or row.state=='review_required' or reasons else 'open'
            status='active' if chosen else 'pending_review';reason='OTHER_REVIEW_REMAINS' if chosen and after_state=='review_required' else None if chosen else 'SUCCESSOR_UNAVAILABLE'
        else:
            transition='leave';new_id=gen.leader_cycle_member_id;after_state=row.state
            status='pending_review' if new_id is None else 'active';reason=recovery.reason if recovery else None
    after_gen='cancelled' if after_state=='closed' else after_state
    leader_changed=(gen.leader_cycle_member_id!=new_id or
        (recovery.state if recovery else 'active')!=status and not (status=='active' and recovery and recovery.state=='review_remaining'))
    lr=inc(gen.leadership_revision) if leader_changed else gen.leadership_revision
    new_leader=db.get(CycleMember,new_id) if new_id else None
    after=dict(leader_cycle_member_id=new_id,leader_membership_id=new_leader.membership_id if new_leader else None,
        leadership_revision=lr,status=status,recovery_reason=reason)
    selected=None
    if chosen:
        own=life.assignments(db,row,chosen);first=next(iter(own),None)
        selected=dict(membership_id=chosen.membership_id,cycle_member_id=chosen.id,cycle_member_revision=chosen.revision,
            planned_cycle_member_revision=inc(chosen.revision) if any(e['cycle_member_id']==chosen.id for e in affected) else chosen.revision,
            character_id=first.character_id,character_name=first.display.get('character_name'),joined_order=str(chosen.joined_order))
    parts=[p for e in affected if e['planned_state'] in ('cancelled','removed') for p in leaders.own_parts(db,row,db.get(CycleMember,e['cycle_member_id']))] if action!='recover_leadership' else []
    reservations=set()
    hidden=[]
    for e in affected:
        cm=db.get(CycleMember,e['cycle_member_id']);owned,rs,proof=atomic.bundle(db,row,cm)
        if e['planned_state'] in ('cancelled','removed'):reservations.update(r.id for r in rs)
        hidden.append(proof)
    apps=list(db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,
        CycleApplication.generation==row.generation,CycleApplication.state=='pending')))
    cancel_apps=[a for a in apps if action=='dissolve_led_targets' or after_state=='closed' or (action!='recover_leadership' and a.user_id==actor.user_id)]
    sessions=graph.sessions(db,row) if after_state=='closed' else []
    result=dict(target_cycle_key=row.cycle_key,room_cycle_id=row.id,target_generation=row.generation,
        target_revision=row.revision,members_revision=row.members_revision,plan_revision=row.plan_revision,
        target_state=row.state,generation_state=gen.state,planned_target_state=after_state,planned_generation_state=after_gen,
        revision_rules=dict(target=rule(row.revision,True,flexible=True),members=rule(row.members_revision,bool(affected)),
            plan=rule(row.plan_revision,True,flexible=True),leadership=rule(gen.leadership_revision,leader_changed)),
        leadership_before=lead,transition=transition,affected_members=affected,successor=selected,leadership_after=after,
        cleanup=dict(released_reservation_count=len(reservations),ended_participation_count=sum(p.state=='active' for p in parts),
            cancelled_application_count=len(cancel_apps),cancelled_session_count=len(sessions)))
    return result,[hidden,candidate_proof,atomic.cycle_proof(db,row),
        [planning.snapshot(m) for m in members],planning.snapshot(recovery) if recovery else None],reasons


def prepare(db,uid,rid,key,stamp,*,only=None):
    ready(db);cycles.target(stamp,key)
    room=commands.base.room(db,uid,rid);actor=commands.base.member(db,uid,room)
    from app.raid_rooms.completed_room_lifecycle import require_active
    require_active(db,rid)
    if room.ended_at:fail('ROOM_NOT_ACTIVE')
    current=cycles.target(stamp,key).current
    rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid,
        RoomCycle.cycle_key.in_((current,current+timedelta(days=7)))).order_by(RoomCycle.cycle_key)))
    active_members=list(db.scalars(select(life.Member).where(life.Member.room_id==rid,life.Member.ended_at.is_(None)).order_by(life.Member.id)))
    options={};bindings={};plans={}
    for action in (only,) if only else ACTIONS:
        targets=[];reason=None;visible=True;hidden=[];remaining={}
        try:
            for row in rows:
                mine=db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id,
                    CycleMember.membership_id==actor.id,CycleMember.generation==row.generation,CycleMember.state.in_(LIVE)))
                gen=db.get(CycleGeneration,(row.id,row.generation)) if row.generation else None
                relevant=(action=='leave_target' and row.cycle_key.isoformat()==key and mine is not None or
                    action=='leave_all' and mine is not None or
                    action=='dissolve_led_targets' and gen is not None and mine is not None and gen.leader_cycle_member_id==mine.id and row.state in ('open','review_required') or
                    action=='recover_leadership' and row.cycle_key.isoformat()==key and mine is not None)
                if relevant:
                    value,proof,reasons=plan_target(db,room,row,actor,action,stamp)
                    targets.append(value);hidden.append(proof);remaining[row.id]=reasons
            if not targets and action!='leave_all':
                visible=False
                fail('TARGET_LEADER_REQUIRED' if action=='dissolve_led_targets' else 'LEADERSHIP_RECOVERY_NOT_REQUIRED' if action=='recover_leadership' else 'WEEKLY_PARTICIPANT_REQUIRED')
            effects={t['room_cycle_id']:t for t in targets}
            # Missing/unknown live target is an explicit closure blocker.
            all_rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)))
            cancelled={aid for t in targets for m in t['affected_members'] for aid in m['cancelled_assignment_ids']}
            outstanding=list(db.scalars(select(life.Assignment).where(life.Assignment.room_id==rid,life.Assignment.state=='active').order_by(life.Assignment.id)))
            if action=='leave_all' and any(a.user_id==uid and a.id not in cancelled for a in outstanding):fail('ROOM_REVIEW_REQUIRED')
            end=bool(targets) and not any(a.id not in cancelled for a in outstanding) and all((effects[r.id]['planned_target_state'] if r.id in effects else r.state)=='closed' for r in all_rows)
            actor_end=end or action=='leave_all'
            room_effect=dict(kind='end' if end else 'preserve_review' if any((effects[r.id]['planned_target_state'] if r.id in effects else r.state)=='review_required' for r in rows) else 'preserve',
                actor_membership_will_end=actor_end,ended_persistent_membership_count=len(active_members) if end else int(actor_end),
                preserves_unaffected_cycles=True,room_revision_rule=rule(room.revision,end),actor_membership_revision_rule=rule(actor.revision,actor_end))
            impact=dict(action=action,affected_cycle_keys=[t['target_cycle_key'] for t in targets],targets=targets,
                room_effect=room_effect,existing_completion_preserved=True)
            impact['display_revision']=digest(atomic.encoded(impact))
            bound=digest(atomic.encoded([uid,rid,key,current,action,impact,hidden,planning.snapshot(room),planning.snapshot(actor),
                [planning.snapshot(m) for m in active_members],[[r.id,r.revision,r.state,r.generation] for r in all_rows],
                [planning.snapshot(a) for a in outstanding]]))
            expires=min(stamp+timedelta(seconds=120),life.raids.cycle(stamp).ends_at)
            expected=dict(expected_cycle_key=current.isoformat(),view_cycle_key=key,actor_membership_id=str(actor.id),
                expected_actor_membership_revision=actor.revision,action=action)
            confirmation=dict(context_token=seal(dict(actor=str(uid),room=str(rid),command='membership-action',body=expected,
                digest=bound,expires=expires.isoformat())),issued_at=stamp,expires_at=expires)
            options[action]=dict(visible=True,permission=permission(),impact=impact,confirmation=confirmation)
            bindings[action]=bound;plans[action]=remaining
        except GameError as error:
            if action=='recover_leadership' and error.code=='LEADERSHIP_RECOVERY_NOT_REQUIRED':visible=False
            options[action]=dict(visible=visible,permission=permission(error.code),impact=None,confirmation=None)
    return dict(scope=scope(stamp,key),data=dict(room_id=rid,room_revision=room.revision,
        actor=dict(membership_id=actor.id,membership_revision=actor.revision),options=options)),bindings,room,actor,plans


def get(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        return bounded(wire.Context,prepare(db,uid,rid,key,stamp)[0])


def cleanup(db,row,cm,state,command,stamp):
    owned=life.assignments(db,row,cm)
    from app.raid_rooms.integrated_models import RecruitmentSegment as Segment
    parts=leaders.own_parts(db,row,cm)
    segments=list(db.scalars(select(Segment).where(Segment.session_id.in_([p.session_id for p in parts]),Segment.round_id.in_([a.round_id for a in owned])).order_by(Segment.session_id,Segment.ordinal)))
    evidence=dict(membership_action=True,record_schedule_segments=[dict(segment_id=s.id,round_id=s.round_id,session_id=s.session_id,starts_at=s.starts_at,ends_at=s.ends_at,state='released') for s in segments],
        assignments=[life.assignment_snapshot(a) for a in owned],participations=leaders.release_parts(db,row,cm,stamp))
    submission=db.get(CycleSubmission,cm.id)
    if submission is not None:evidence['submission']=planning.snapshot(submission);db.delete(submission)
    for a in owned:
        if a.state=='active':
            graph.graph.release(db,assignment=a,reason='future_cancel',stamp=stamp)
            life.admission.core.release_assignment(db,a,stamp)
    cm.state=state;cm.ended_at=stamp;cm.revision=inc(cm.revision)
    life.event(db,row,cm,command,state,stamp,evidence)
    return evidence


def execute(principal,rid,command,data):
    body=data.model_dump(mode='json');action=body['action']
    def run(db,uid,stamp):
        token=atomic.validate_token(uid,rid,'membership-action',body,stamp)
        value,bindings,room,actor,plans=prepare(db,uid,rid,body['view_cycle_key'],stamp,only=action)
        if (str(actor.id),actor.revision)!=(body['actor_membership_id'],body['expected_actor_membership_revision']):fail('REVISION_CONFLICT')
        option=value['data']['options'][action]
        if not option['permission']['allowed']:fail(option['permission']['reason'])
        life.require_match(token,bindings[action]);impact=option['impact'];guards=[];effects=[];evidence=[]
        for target in impact['targets']:
            row=db.get(RoomCycle,target['room_cycle_id']);gen=db.get(CycleGeneration,(row.id,row.generation))
            guards.append(graph.final_deadlines(db,row,[],stamp,join=False))
            for effect in target['affected_members']:
                cm=db.get(CycleMember,effect['cycle_member_id'])
                if effect['planned_state']=='participating':cm.state=effect['planned_state'];cm.revision=inc(cm.revision)
                else:evidence.append(cleanup(db,row,cm,effect['planned_state'],command,stamp))
            if target['planned_target_state']=='closed':leaders.close_target(db,row,stamp)
            else:
                for app in db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,
                    CycleApplication.generation==row.generation,CycleApplication.state=='pending',CycleApplication.user_id==uid)):
                    if action!='recover_leadership':app.state='cancelled';app.ended_at=stamp;app.revision=inc(app.revision)
            after=target['leadership_after']
            gen.leader_cycle_member_id=after['leader_cycle_member_id'];gen.leadership_revision=after['leadership_revision']
            gen.state=target['planned_generation_state'];row.state=target['planned_target_state']
            row.members_revision=target['revision_rules']['members']['exact_after']
            recovery=db.get(LeadershipRecovery,(row.id,row.generation))
            if recovery is None:
                recovery=LeadershipRecovery(cycle_id=row.id,generation=row.generation,revision=1);db.add(recovery)
            else:recovery.revision=inc(recovery.revision)
            recovery.state='review_remaining' if after['status']=='active' and after['recovery_reason'] else after['status']
            recovery.reason=after['recovery_reason'];recovery.remaining_review_reasons=plans[action][row.id]
            planning.bump(db,row);db.flush()
            if row.state=='open':planning.refresh(db,room,row,uid,command,stamp)
            effects.append(dict(target_cycle_key=row.cycle_key,room_cycle_id=row.id,target_generation=row.generation,
                target_revision=row.revision,members_revision=row.members_revision,plan_revision=row.plan_revision,
                target_state=row.state,generation_state=gen.state,leadership=leadership(db,row),
                leadership_status=after['status'],recovery_reason=after['recovery_reason'],
                members=[dict(membership_id=e['membership_id'],cycle_member_id=e['cycle_member_id'],
                    cycle_member_revision=db.get(CycleMember,e['cycle_member_id']).revision,state=e['planned_state'],
                    cancelled_assignment_ids=e['cancelled_assignment_ids'],preserved_completed_assignment_ids=e['preserved_completed_assignment_ids'])
                    for e in target['affected_members']]))
        ending=impact['room_effect']['kind']=='end';ended=0
        ending_members=list(db.scalars(select(life.Member).where(life.Member.room_id==rid,life.Member.ended_at.is_(None)))) if ending else [actor] if action=='leave_all' else []
        for member in ending_members:
            member.ended_at=stamp;member.revision=inc(member.revision);ended+=1
            life.admission.core.legacy.touch_user(db,member.user_id)
        if ending:room.ended_at=stamp;room.revision=inc(room.revision)
        if action=='leave_all' or ending:
            for app in db.scalars(select(CycleApplication).where(CycleApplication.room_id==rid,CycleApplication.state=='pending')):
                if ending or app.user_id==uid:app.state='cancelled';app.ended_at=stamp;app.revision=inc(app.revision)
        # Target-only changes also invalidate the owners' membership pages/quota.
        for mid in {m['membership_id'] for t in impact['targets'] for m in t['affected_members']}:
            if mid not in {m.id for m in ending_members}:life.admission.core.legacy.touch_user(db,db.get(life.Member,mid).user_id)
        db.add(MembershipActionAudit(id=uuid.uuid4(),room_id=rid,actor_membership_id=actor.id,user_id=uid,command_id=command,
            action=action,effective_at=stamp,evidence=atomic.encoded(dict(impact=impact,cleanup=evidence))))
        db.flush()
        result=bounded(wire.Result,dict(scope=scope(stamp,body['view_cycle_key']),data=dict(command_id=command,
            action=action,outcome='applied',executed_at=stamp,room_id=rid,room_revision=room.revision,
            actor_membership_id=actor.id,actor_membership_revision=actor.revision,actor_membership_ended=actor.ended_at is not None,
            affected_cycle_keys=[e['target_cycle_key'] for e in effects],effects=effects,room_ended=ending,ended_persistent_membership_count=ended)))
        def final(current):
            for guard in guards:guard(current)
            if current>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
        return 200,result,final
    return cycles.execute(principal,'membership-action',command,dict(room_id=str(rid),body=body),run)
