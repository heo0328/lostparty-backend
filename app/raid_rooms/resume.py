"""Weekly resume creates new generations; completed history is immutable."""
import uuid
from datetime import date
from sqlalchemy import select
from app.game_accounts.support import fail
from app.raid_rooms import admission_service as base,scheduling as graph,participation_core as core,admission_context as context,time_policy
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round
from app.raid_rooms.resume_models import ResumeProposal
from app.raid_rooms.source_models import RoomSettings
from app.raid_rooms.completion import MembershipCommand
from app.raid_rooms.schedule_schemas import EditGroup
from app.raid_rooms.source_models import ScheduleGroup,ScheduleAlternative


class ResumeRequest(MembershipCommand):
    # null retains the stopped intent; [] explicitly resumes without sessions.
    schedule_groups: list[EditGroup]|None


def retained_groups(db,room,cycle,item_ids):
    values=[]
    for old in db.scalars(select(ScheduleGroup).where(ScheduleGroup.room_id==room.id,ScheduleGroup.cycle_key==date.fromisoformat(cycle)).order_by(ScheduleGroup.record_created_at,ScheduleGroup.id)):
        head=db.get(graph.ScheduleHead,old.id)
        if head is None or head.active:continue
        alternatives=[]
        for alt in db.scalars(select(ScheduleAlternative).where(ScheduleAlternative.group_id==old.id).order_by(ScheduleAlternative.id)):
            clock=lambda n:f'{n//60:02}:{n%60:02}' if n is not None else None
            alternatives.append(dict(client_alternative_key=alt.client_key,existing_session_id=None,expected_session_revision=None,
                weekday=alt.weekday,starts_local=clock(alt.start_minute),leader_latest_start_local=clock(alt.latest_start_minute),item_ids=[i for i in alt.item_order if i in item_ids]))
        values.append(dict(client_group_key=head.client_key,existing_group_id=None,expected_group_revision=None,occurrence_mode=old.occurrence_mode,
            planning_mode=old.planning_mode,day_scope=old.day_scope,required=old.required,auto_confirm_additional_members=old.auto_additional_members,alternatives=alternatives))
    # Multiple resume generations retain the latest graph for each client key.
    return list({g['client_group_key']:g for g in values}.values())


def stopped(db,room,cycle):
    result=[]
    for r in db.scalars(select(Round).where(Round.room_id==room.id,Round.cycle_key==date.fromisoformat(cycle),Round.state=='stopped_incomplete').order_by(Round.id)):
        # Only the latest stopped generation of each still-unfinished item.
        newer=db.scalar(select(Round.id).where(Round.item_id==r.item_id,Round.cycle_key==r.cycle_key,Round.created_at>r.created_at))
        if newer is None:result.append(r)
    return result


def target_members(db,proposal):
    ids={a['membership_id'] for a in proposal.content['assignments']}
    return [m for m in graph.members(db,proposal.room_id) if str(m.id) in ids]


def create(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room,leader=True);base.unscheduled(db,room);base.cas(room,data)
        cycle=graph.raids.cycle(stamp).cycle_key
        if data.expected_cycle_key!=cycle:fail('CYCLE_CHANGED')
        if actor.revision!=data.expected_membership_revision:fail('REVISION_CONFLICT')
        if not db.get(RoomSettings,rid).continuation_enabled:fail('CONTINUATION_REQUIRED')
        rounds=stopped(db,room,cycle)
        members={m.id for m in graph.members(db,rid)}
        values=list(db.scalars(select(Assignment).where(Assignment.round_id.in_([r.id for r in rounds]),Assignment.state=='stopped_incomplete',Assignment.membership_id.in_(members)).order_by(Assignment.id)))
        if not rounds or not values:fail('ROUND_NOT_STOPPED')
        # A new explicit proposal supersedes the old immutable content rather
        # than inheriting votes or leaving a failed/outdated proposal stuck.
        for previous in db.scalars(select(ResumeProposal).where(ResumeProposal.room_id==rid,ResumeProposal.state=='pending')):
            previous.state='obsolete';previous.revision+=1
        groups=[g.model_dump(mode='json') for g in data.schedule_groups] if data.schedule_groups is not None else retained_groups(db,room,cycle,{str(r.item_id) for r in rounds})
        content=dict(cycle=cycle,schedule_groups=groups,rounds=[dict(id=str(r.id),revision=r.revision,item_id=str(r.item_id)) for r in rounds],
            assignments=[dict(id=str(a.id),revision=a.revision,membership_id=str(a.membership_id)) for a in values])
        p=ResumeProposal(id=uuid.uuid4(),room_id=rid,creator_membership_id=actor.id,revision=1,created_from_plan_revision=room.plan_revision,
            state='pending',content=content,responses={},created_at=stamp)
        if len({a.membership_id for a in values})>=2 and actor.id in {a.membership_id for a in values}:p.responses={str(actor.id):'accept'}
        db.add(p);room.plan_revision+=1;room.revision+=1;db.flush()
        return 200,dict(command_id=key,outcome='recorded',executed_at=stamp,revisions=[base.revision('proposal',p),base.revision('plan',room,room.plan_revision)])
    return base.execute(principal,'resume-proposal',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def respond(db,room,actor,p,data,stamp):
    if p.state!='pending':fail('PROPOSAL_NOT_PENDING')
    if data.expected_proposal_revision!=p.revision or data.expected_proposal_plan_revision!=1 or data.expected_membership_revision!=actor.revision:fail('REVISION_CONFLICT')
    if data.expected_cycle_key!=p.content['cycle'] or graph.raids.cycle(stamp).cycle_key!=p.content['cycle']:fail('CYCLE_CHANGED')
    members=target_members(db,p)
    if actor.id not in {m.id for m in members}:fail('PROPOSAL_TARGET_REQUIRED',403)
    p.responses={**p.responses,str(actor.id):data.response};db.flush()
    return evaluate(db,room,p,stamp)


def evaluate(db,room,p,stamp):
    if p.state!='pending':return False
    members=target_members(db,p)
    if not members or p.content['cycle']!=graph.raids.cycle(stamp).cycle_key:
        p.state='obsolete';p.revision+=1;return False
    if sum(p.responses.get(str(m.id))=='accept' for m in members)<time_policy.quorum(len(members)):return False
    originals=[]
    for source in p.content['rounds']:
        old=db.get(Round,uuid.UUID(source['id']))
        if old.state!='stopped_incomplete' or old.revision!=source['revision']:fail('PROPOSAL_CONTEXT_CHANGED')
        if db.scalar(select(Round.id).where(Round.item_id==old.item_id,Round.cycle_key==old.cycle_key,Round.state.in_(['active','completed']))):fail('PROPOSAL_CONTEXT_CHANGED')
        originals.append(old)
    new={}
    for old in originals:
        r=Round(id=uuid.uuid4(),room_id=room.id,item_id=old.item_id,cycle_key=old.cycle_key,difficulty_id=old.difficulty_id,
            catalog_version=old.catalog_version,game_party_size=old.game_party_size,revision=1,state='active',created_at=stamp)
        db.add(r);new[old.id]=r
    db.flush()
    for member in members:
        sources=[s for s in p.content['assignments'] if s['membership_id']==str(member.id)]
        values=[]
        for s in sources:
            a=db.get(Assignment,uuid.UUID(s['id']))
            if a.state!='stopped_incomplete' or a.revision!=s['revision']:fail('PROPOSAL_CONTEXT_CHANGED')
            values.append(a)
        if len({(a.character_id,a.selected_role) for a in values})!=1:fail('BUNDLE_CHARACTER_REQUIRED')
        chosen=context.selection(db,member.user_id,values[0].character_id,values[0].selected_role)
        if any(a.ownership_revision!=chosen.expected_ownership_revision or a.lifecycle_revision!=chosen.expected_lifecycle_revision for a in values):fail('REVISION_CONFLICT')
        targets=[]
        for a in values:
            r=new[a.round_id];item=db.get(graph.Item,a.item_id)
            state=db.get(core.WeeklyState,(member.user_id,a.character_id,item.raid_id,r.cycle_key))
            targets.append(base.Target(item_id=a.item_id,round_id=r.id,party_no=a.party_no,expected_round_revision=r.revision,expected_weekly_revision=state.revision if state else 1))
        core.admit_bundle(db,member.user_id,room,chosen,targets,p.content['cycle'],resume_item_ids={a.item_id for a in values})
    groups=[EditGroup.model_validate(g) for g in p.content['schedule_groups']]
    graph.install(db,room,groups,stamp,creating=True,confirm_leader=False)
    accepted={m.id for m in members if p.responses.get(str(m.id))=='accept'}
    for s in graph.sessions(db,room.id,stamp):
        for m in members:
            if graph.assignments(db,m,s):
                part=graph.participation(db,s,m,stamp=stamp)
                if m.id in accepted and s.state=='confirmed':graph.reserve(db,part,s,stamp)
    graph.evaluate_initial(db,room,stamp,confirm_members=accepted)
    p.state='applied';p.revision+=1;room.plan_revision+=1;room.revision+=1
    db.flush();return True
