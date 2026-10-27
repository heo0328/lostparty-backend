"""Explicit current-week stopped-round resume. Fresh rounds/assignments, retained history."""
import uuid
from datetime import timedelta
from copy import deepcopy
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail
from app.raid_rooms import cycle_outcomes as outcomes,cycle_planning as plan,cycle_proposals as votes,cycle_schedule as graph,cycle_lifecycle as life,cycle_commands as commands,cycles,cycle_wire as wire
from app.raid_rooms.cycle_outcome_models import CycleResume
from app.raid_rooms.cycle_planning_models import CycleProposal
from app.raid_rooms.cycle_models import CycleMember,CycleRound,CycleGeneration,CycleSubmission
from app.raid_rooms.source_models import ScheduleProposal as Proposal
from app.raid_rooms.integrated_models import RecruitmentRound as Round
from app.raid_rooms.participation_commands import Target
from app.raid_rooms import resume_review as review


def source(db,row):
    rounds=[r for _,r in graph.admission.rounds(db,row) if r.state=='stopped_incomplete']
    members=list(db.scalars(select(CycleMember).join(life.Member,life.Member.id==CycleMember.membership_id).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.state=='stopped',life.Member.ended_at.is_(None)).order_by(CycleMember.joined_order)))
    ids={r.id for r in rounds}
    members=[cm for cm in members if {a.round_id for a in life.assignments(db,row,cm) if a.state=='stopped_incomplete'} & ids]
    return rounds,members


def actual(db,row,binding):
    _,members=source(db,row);old={v['id']:v['revision'] for v in binding.content['members']}
    return [cm for cm in members if old.get(str(cm.id))==cm.revision]


def counts(db,row,p,binding):
    members=actual(db,row,binding);accepted=sum(bool(v and v.response=='accept') for cm in members for v in [votes.latest(db,p,cm)])
    return members,accepted,graph.graph.time.quorum(len(members)) if members else 1


def retained(db,row,items):
    values=[]
    for group in graph.groups(db,row):
        alts=[]
        for a in graph.alternatives(db,group):
            clock=lambda v:f'{v//60:02}:{v%60:02}' if v is not None else None
            alts.append(dict(client_alternative_key=graph.alternative_key(db,a),existing_session_id=None,expected_session_revision=None,
                weekday=a.weekday,starts_local=clock(a.start_minute),leader_latest_start_local=clock(a.latest_start_minute),
                item_ids=[i for i in a.item_order if i in items]))
        values.append(dict(client_group_key=db.get(graph.ScheduleHead,group.id).client_key,existing_group_id=None,expected_group_revision=None,
            occurrence_mode=group.occurrence_mode,planning_mode=group.planning_mode,day_scope=group.day_scope,required=group.required,
            auto_confirm_additional_members=group.auto_additional_members,alternatives=alts))
    return values


def prepare_create(db,uid,rid,body,stamp):
    outcomes.playable(stamp,body['target_cycle_key'])
    room,row,cm=outcomes.target(db,uid,rid,body['target_cycle_key'],stamp)
    commands.cas(db,row,body,stamp,leader=True)
    if body['expected_room_revision']!=room.revision or body['expected_members_revision']!=row.members_revision or body['expected_plan_revision']!=row.plan_revision or body['expected_cycle_member_revision']!=cm.revision:fail('REVISION_CONFLICT')
    if commands.leadership(db,row)['leader_cycle_member_id']!=cm.id:fail('TARGET_LEADER_REQUIRED',403)
    life.qualify(db,room,row,cm)
    if not row.settings_snapshot['continuation_enabled']:fail('CONTINUATION_REQUIRED')
    rounds,members=source(db,row)
    if row.state!='closed' or not rounds or not members:fail('ROUND_NOT_STOPPED')
    pending=list(db.scalars(select(Proposal).join(CycleResume,CycleResume.proposal_id==Proposal.id).where(
        CycleResume.cycle_id==row.id,CycleResume.generation==row.generation,Proposal.state=='pending').order_by(Proposal.id)))
    groups=body['schedule_groups'] if body['schedule_groups'] is not None else retained(db,row,{str(r.item_id) for r in rounds})
    content=dict(rounds=[plan.snapshot(r) for r in rounds],members=[dict(id=str(m.id),revision=m.revision) for m in members],
        assignments=[life.assignment_snapshot(a) for m in members for a in life.assignments(db,row,m) if a.round_id in {r.id for r in rounds} and a.state=='stopped_incomplete'],schedule_groups=groups)
    return room,row,cm,jsonable_encoder(content),pending


def create(principal,rid,command,data):
    body=review.command_body(data)
    def run(db,uid,stamp):
        protected='resume_context_token' in body
        checked=None
        if protected:
            original={k:v for k,v in body.items() if k!='resume_context_token'}
            _,row,_=outcomes.target(db,uid,rid,body['target_cycle_key'],stamp)
            checked=review.verify(body['resume_context_token'],uid,row,'create',stamp)
            shown,binding,basis,prepared=review.prepare(db,uid,rid,original,stamp)
            if checked['digest']!=binding:fail('TARGET_CONTEXT_STALE')
            room,row,cm,content,pending=prepared
            content.update(review_version=1,review_basis=basis)
        else:room,row,cm,content,pending=prepare_create(db,uid,rid,body,stamp)
        for previous in pending:previous.state='obsolete';previous.revision+=1
        p=Proposal(id=uuid.uuid4(),room_id=rid,creator_membership_id=cm.membership_id,revision=1,proposal_plan_revision=1,
            created_from_plan_revision=row.plan_revision,state='pending',created_at=stamp)
        db.add(p);db.flush();db.add(CycleProposal(proposal_id=p.id,room_id=rid,cycle_id=row.id,generation=row.generation,content=[]));db.flush()
        db.add(CycleResume(proposal_id=p.id,room_id=rid,cycle_id=row.id,generation=row.generation,content=jsonable_encoder(content)));db.flush()
        if len(content['members'])>=2 and str(cm.id) in {m['id'] for m in content['members']}:votes.vote(db,row,p,cm,'accept',command,stamp)
        plan.bump(db,row)
        def final(current):
            outcomes.playable(current,body['target_cycle_key'])
            if checked:
                if current>=review.datetime.fromisoformat(checked['expires']):fail('COMMAND_CONTEXT_EXPIRED')
                review.project_groups(row,basis,validate_at=current)
        return 200,life.ack(db,row,command,stamp,outcome='recorded',revisions=[dict(resource='proposal',id=p.id,revision=p.revision),dict(resource='target',id=row.id,revision=row.revision)]),final
    return cycles.execute(principal,'resume',command,dict(room_id=str(rid),body=body),run)


def apply(db,room,row,p,binding,uid,command,stamp):
    members,accepted,required=counts(db,row,p,binding)
    if not members or accepted<required:return False
    old={r.id:r for _,r in graph.admission.rounds(db,row) if r.state=='stopped_incomplete'}
    if set(old)!={uuid.UUID(r['id']) for r in binding.content['rounds']} or any(old[uuid.UUID(r['id'])].revision!=r['revision'] for r in binding.content['rounds']):fail('PROPOSAL_CONTEXT_CHANGED')
    originals={}
    for cm in members:
        life.qualify(db,room,row,cm)
        values=[a for a in life.assignments(db,row,cm) if a.round_id in old and a.state=='stopped_incomplete']
        snapshots={v['id']:v for v in binding.content['assignments'] if v['membership_id']==str(cm.membership_id)}
        if any(str(a.id) not in snapshots or a.revision!=snapshots[str(a.id)]['revision'] for a in values):fail('PROPOSAL_CONTEXT_CHANGED')
        originals[cm.id]=values
    protected=binding.content.get('review_version')==1
    if protected:
        review.valid_basis(db,row,binding.content,binding.content['review_basis'],members)
        review.project_groups(row,binding.content['review_basis'],validate_at=stamp)
        saved_effect=review.effect(db,row,life.actual_member(db,row,uid),binding.content,binding.content['review_basis'],members,accepted,required)
    # Each stopped Round is replaced, never revived. Completed item rounds stay current.
    new={}
    for previous in old.values():
        db.get(CycleRound,previous.id).is_current=False
        rd=Round(id=uuid.uuid4(),room_id=room.id,item_id=previous.item_id,cycle_key=row.cycle_key,difficulty_id=previous.difficulty_id,
            catalog_version=previous.catalog_version,game_party_size=previous.game_party_size,revision=1,state='active',created_at=stamp)
        db.add(rd);new[previous.id]=rd
    db.flush()
    for rd in new.values():db.add(CycleRound(round_id=rd.id,room_id=room.id,item_id=rd.item_id,cycle_key=row.cycle_key,cycle_id=row.id,generation=row.generation,is_current=True))
    gen=db.get(CycleGeneration,(row.id,row.generation));previous_generation=plan.snapshot(gen)
    row.state='open';gen.state='open';gen.closed_at=None;db.flush()
    vote_set=[dict(id=str(cm.id),member_revision=cm.revision,response=v.response if (v:=votes.latest(db,p,cm)) else 'pending') for cm in members]
    accepted_ids={uuid.UUID(v['id']) for v in vote_set if v['response']=='accept'}
    for cm in members:
        previous=originals[cm.id];chosen=life.selection_context.selection(db,cm.user_id,previous[0].character_id,previous[0].selected_role)
        targets=[]
        for a in previous:
            rd=new[a.round_id];item=db.get(graph.graph.Item,a.item_id);state=db.get(life.WeeklyState,(cm.user_id,a.character_id,item.raid_id,row.cycle_key))
            targets.append(Target(item_id=a.item_id,round_id=rd.id,party_no=a.party_no,expected_round_revision=1,expected_weekly_revision=state.revision if state else 1))
        graph.admission.admit_bundle(db,cm.user_id,room,row,chosen,targets,command,stamp,resuming=cm,resume_items={a.item_id for a in previous})
        cm.state='participating';cm.ended_at=None;cm.revision+=1
        life.event(db,row,cm,command,'joined',stamp,dict(resume_proposal_id=str(p.id),previous=[life.assignment_snapshot(a) for a in previous]))
    submissions=[]
    for cm in members:
        submission=db.get(CycleSubmission,cm.id)
        if submission is not None:submissions.append(plan.snapshot(submission));db.delete(submission)
    outcomes.event(db,row,uid,command,'resume_applied',stamp,dict(proposal_id=str(p.id),search_floor_at=(stamp+timedelta(minutes=30)).isoformat(),previous=binding.content,previous_generation=previous_generation,submissions=submissions,vote_set=vote_set,**(dict(review_effect=saved_effect) if protected else {})))
    db.flush()
    groups=[wire.BEditGroup.model_validate(g) for g in binding.content['schedule_groups']]
    plan.edit(db,room,row,uid,command,groups,stamp,confirm_manual=False,evaluate_initial=False)
    for sess in graph.sessions(db,row):
        if sess.state=='confirmed':
            for cm in plan.members(db,row,sess):
                if cm.id in accepted_ids:plan.consent(db,room,row,cm,sess,command,stamp,dict(kind='weekly_resume',proposal_id=str(p.id)))
    p.state='applied';p.revision+=1;row.members_revision+=1;plan.bump(db,row);db.flush();return True


def respond(db,uid,pid,command,body,stamp):
    binding=db.get(CycleResume,pid)
    if binding is None:fail('PROPOSAL_NOT_FOUND',404)
    key=body['target_cycle_key'];outcomes.playable(stamp,key)
    room,row,cm=outcomes.target(db,uid,binding.room_id,key,stamp)
    if (binding.cycle_id,binding.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
    commands.cas(db,row,body,stamp)
    p=db.get(Proposal,pid)
    if p.state!='pending':fail('PROPOSAL_NOT_PENDING')
    if body['expected_proposal_revision']!=p.revision or body['expected_proposal_plan_revision']!=p.proposal_plan_revision or body['expected_cycle_member_revision']!=cm.revision:fail('REVISION_CONFLICT')
    if cm.id not in {m.id for m in actual(db,row,binding)}:fail('PROPOSAL_TARGET_REQUIRED',403)
    protected=binding.content.get('review_version')==1
    checked=None
    if protected:
        if 'resume_context_token' not in body:fail('CONTEXT_INVALID',400)
        checked=review.verify(body['resume_context_token'],uid,row,'respond',stamp,proposal=p)
        shown,binding_hash=review.for_proposal(db,room,row,cm,p,binding.content,stamp)
        if shown['display']['status']=='stale':fail('PROPOSAL_CONTEXT_CHANGED')
        if shown['confirmation'] is None:fail(shown['display']['permission']['reason'])
        if checked['digest']!=binding_hash:fail('TARGET_CONTEXT_STALE')
    elif 'resume_context_token' in body:fail('CONTEXT_INVALID',400)
    if body['response']=='accept':life.qualify(db,room,row,cm)
    schedule_final=graph.final_deadlines(db,row,[],stamp,join=False)
    def final(current):
        outcomes.playable(current,key);schedule_final(current)
        if checked:
            if current>=review.datetime.fromisoformat(checked['expires']):fail('COMMAND_CONTEXT_EXPIRED')
            review.project_groups(row,binding.content['review_basis'],validate_at=current)
    if votes.vote(db,row,p,cm,body['response'],command,stamp):plan.bump(db,row)
    applied=apply(db,room,row,p,binding,uid,command,stamp)
    return 200,life.ack(db,row,command,stamp,outcome='applied' if applied else 'recorded'),final


def views(db,row,mine,stamp,include_resume_display=False):
    cm=life.actual_member(db,row,mine.user_id);result=[]
    for p,binding in db.execute(select(Proposal,CycleResume).join(CycleResume,CycleResume.proposal_id==Proposal.id).where(CycleResume.cycle_id==row.id,CycleResume.generation==row.generation).order_by(Proposal.created_at,Proposal.id)):
        members,accepted,required=counts(db,row,p,binding);v=votes.latest(db,p,cm) if cm else None
        own_response=v.response if v else 'pending'
        if p.state=='applied':
            from app.raid_rooms.cycle_outcome_models import CycleOutcome
            receipt=db.scalar(select(CycleOutcome).where(CycleOutcome.cycle_id==row.id,CycleOutcome.kind=='resume_applied',
                CycleOutcome.evidence['proposal_id'].astext==str(p.id)))
            if receipt is not None:
                recorded=receipt.evidence['vote_set'];members=recorded;accepted=sum(v['response']=='accept' for v in recorded)
                required=graph.graph.time.quorum(len(recorded))
                own_response=next((v['response'] for v in recorded if cm and v['id']==str(cm.id)),'pending')
        reason=None if p.state=='pending' and cm and cm.id in {m.id for m in members} else 'PROPOSAL_TARGET_REQUIRED'
        result.append(dict(proposal_id=p.id,kind='weekly_resume',revision=p.revision,proposal_plan_revision=p.proposal_plan_revision,
            created_from_plan_revision=p.created_from_plan_revision,state=p.state,target_round_ids=[r['id'] for r in binding.content['rounds']],
            eligible_count=len(members),accepted_count=accepted,required_votes=required,my_response=own_response,permissions=dict(respond_proposal=commands.permission(reason))))
    if include_resume_display:
        room=db.get(commands.Room,row.room_id)
        for value in result:
            p=db.get(Proposal,value['proposal_id']);binding=db.get(CycleResume,p.id)
            value['resume_review']=review.for_proposal(db,room,row,cm,p,binding.content,stamp,uid=mine.user_id)[0]
    return result
