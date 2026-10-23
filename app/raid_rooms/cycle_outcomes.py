"""Current-target completion: exact item leases, immutable prior evidence, no N effects."""
import uuid
from datetime import datetime
from sqlalchemy import select,text
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycles,cycle_commands as commands,cycle_lifecycle as life,cycle_schedule as graph,cycle_planning as planning,cycle_wire as wire
from app.raid_rooms.cycle_models import RoomCycle,CycleRound,CycleGeneration,CycleMember,CycleAssignment
from app.raid_rooms.cycle_outcome_models import CycleOutcome
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.cycle_planning_models import CycleProposal
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round
from app.raid_rooms.source_models import TimeReservation as Reservation,SessionParticipation as Participation,ScheduleProposal as Proposal
from app.raid_weekly import service as weekly
from app.raid_weekly.models import WeeklyState


def enabled(db):return list(db.scalars(text('SELECT version_num FROM public.alembic_version')))in (['0029_cycle_outcomes'],['0030_completion_corrections'])
def ready(db):
    if not enabled(db):fail('RECRUITMENT_COMMAND_NOT_READY',503)


def playable(stamp,key):
    value=cycles.target(stamp,key)
    if value.key!=value.current:fail('TARGET_CYCLE_NOT_CURRENT')
    if stamp<value.playable_from:fail('PLAY_NOT_STARTED')
    return value


def target(db,uid,rid,key,stamp):
    ready(db);room,row,_=life.target_row(db,uid,rid,key,stamp)
    if row is None:fail('TARGET_NOT_OPEN')
    if row.state=='review_required':fail('ROOM_REVIEW_REQUIRED')
    cm=life.actual_member(db,row,uid)
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    return room,row,cm


def assignments(db,row):
    return list(db.scalars(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id)
        .join(CycleRound,CycleRound.round_id==Assignment.round_id).where(CycleAssignment.cycle_id==row.id,
        CycleAssignment.generation==row.generation,CycleRound.is_current.is_(True)).order_by(Assignment.id)))


def context(db,uid,rid,key,kind,round_id,stamp):
    if kind not in ('close_weekly','complete_item','personal_completion'):fail('INVALID_REQUEST',400)
    if (kind=='close_weekly')!=(round_id is None):fail('INVALID_REQUEST',400)
    room,row,cm=target(db,uid,rid,key,stamp)
    pairs=graph.admission.rounds(db,row)
    if round_id is not None:
        link=db.get(CycleRound,round_id)
        if link is None or (link.cycle_id,link.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
        cycles.require_current_round(db,row,round_id)
    rounds=[r for _,r in pairs if r.state=='active' and (round_id is None or r.id==round_id)]
    all_values=assignments(db,row)
    values=[a for a in all_values if a.round_id in {r.id for r in rounds} and a.state=='active' and (kind!='personal_completion' or a.membership_id==cm.membership_id)]
    reason=None
    try:playable(stamp,key)
    except GameError as error:reason=error.code
    if row.state!='open' or not rounds or not values:reason=reason or 'ROUND_NOT_ACTIVE'
    if kind=='complete_item' and commands.leadership(db,row)['leader_cycle_member_id']!=cm.id:reason=reason or 'TARGET_LEADER_REQUIRED'
    if kind=='close_weekly' and not row.settings_snapshot['continuation_enabled']:reason=reason or 'CONTINUATION_REQUIRED'
    reservations=list(db.scalars(select(Reservation).where(Reservation.assignment_id.in_([a.id for a in values])).order_by(Reservation.id)))
    proof=[]
    for a in values:
        item,rd=next((i,r) for i,r in pairs if r.id==a.round_id)
        state=db.get(WeeklyState,(a.user_id,a.character_id,item.raid_id,row.cycle_key))
        lease=db.get(life.WeeklyOccupancy,(a.user_id,a.character_id,item.raid_id,row.cycle_key))
        proof.append([planning.snapshot(a),planning.snapshot(state) if state else None,planning.snapshot(lease) if lease else None])
    data=dict(room_id=rid,command=kind,actor_membership_id=cm.membership_id,actor_membership_revision=db.get(life.Member,cm.membership_id).revision,
        room_revision=room.revision,members_revision=row.members_revision,plan_revision=row.plan_revision,target_round_id=round_id,
        effect_scope='target_cycle' if kind=='close_weekly' else 'personal_item' if kind=='personal_completion' else 'item_round',
        impact=dict(round_ids=[r.id for r in rounds],membership_count=len({a.membership_id for a in values}),assignment_count=len(values),
            reservation_segment_count=sum(r.released_at is None for r in reservations),completed_preserved_count=sum(a.state=='completed' for a in all_values)),
        permission=commands.permission(reason),target_cycle_key=key,leadership=commands.leadership(db,row),
        actor_cycle_member_id=cm.id,actor_cycle_member_revision=cm.revision)
    hidden=[cm.state,cm.revision,room.revision,row.settings_snapshot,proof,[planning.snapshot(r) for r in rounds],
        [planning.snapshot(r) for r in reservations],
        [planning.snapshot(s) for s in graph.sessions(db,row,history=True)],
        [planning.snapshot(s) for r in rounds for s in db.scalars(select(graph.Segment).where(graph.Segment.round_id==r.id))]]
    result,binding=life.sign(uid,rid,key,kind,jsonable_encoder(data),hidden,stamp,row=row,extra={'round':str(round_id) if round_id else None})
    return result,binding,room,row,cm,rounds,values


def get(principal,rid,key,kind,round_id=None):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        result,*_=context(db,uid,rid,key,kind,round_id,stamp)
        return wire.OutputContract3GetV2RaidRoomsRoomIdCommandContext.model_validate(result).model_dump(mode='json')


def event(db,row,uid,command,kind,stamp,evidence):
    db.add(CycleOutcome(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
        actor_id=uid,command_id=command,kind=kind,effective_at=stamp,evidence=jsonable_encoder(evidence)))


def settle_participations(db,row,stamp,*,stopping=False):
    for sess in graph.sessions(db,row,history=True):
        active=graph.graph.active_segments(db,sess.id)
        for part in db.scalars(select(Participation).where(Participation.session_id==sess.id,Participation.state=='active')):
            owned=set(db.scalars(select(Assignment.round_id).where(Assignment.membership_id==part.membership_id,Assignment.state=='active')))
            if not any(s.round_id in owned for s in active):
                part.state='ended';part.revision+=1
        if not active and sess.state in ('confirmed','unconfirmed'):sess.state='cancelled' if stopping else 'finished';sess.revision+=1


def obsolete(db,row):
    for p in db.scalars(select(Proposal).join(CycleProposal,CycleProposal.proposal_id==Proposal.id).where(
            CycleProposal.cycle_id==row.id,CycleProposal.generation==row.generation,Proposal.state=='pending')):
        p.state='obsolete';p.revision+=1


def execute(principal,rid,round_id,command,data,kind):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        ready(db);key=body['target_cycle_key'];playable(stamp,key)
        current_rid=rid
        if round_id is not None:
            link=db.get(CycleRound,round_id)
            if link is None:fail('ROUND_NOT_FOUND',404)
            current_rid=link.room_id
        token=life.verify_token(uid,current_rid,body,kind,stamp)
        if token.get('round')!=(str(round_id) if round_id else None):fail('TARGET_SCOPE_MISMATCH',400)
        result,binding,room,row,cm,rounds,values=context(db,uid,current_rid,key,kind,round_id,stamp)
        commands.cas(db,row,body,stamp);life.require_match(token,binding)
        permission=result['data']['permission']
        if not permission['allowed']:fail(permission['reason'],403 if permission['reason']=='TARGET_LEADER_REQUIRED' else 409)
        evidence=dict(assignments=[planning.snapshot(a) for a in values],rounds=[planning.snapshot(r) for r in rounds],
            reservations=[planning.snapshot(r) for r in db.scalars(select(Reservation).where(Reservation.assignment_id.in_([a.id for a in values])))])
        affected={a.membership_id for a in values}
        for a in values:
            graph.graph.release(db,assignment=a,reason='weekly_closed' if kind=='close_weekly' else 'raid_completed',stamp=stamp)
            graph.admission.core.release_assignment(db,a,stamp)
            a.state='stopped_incomplete' if kind=='close_weekly' else 'completed'
            if kind!='close_weekly':
                item,rd=next((i,r) for i,r in graph.admission.rounds(db,row) if r.id==a.round_id)
                state=db.get(WeeklyState,(a.user_id,a.character_id,item.raid_id,row.cycle_key))
                if kind=='complete_item':state.party_completed_at=stamp;state.completed_party_id=room.id;state.party_difficulty_id=rd.difficulty_id
                else:state.manual_completed_at=stamp;state.manual_difficulty_id=rd.difficulty_id
                a.build={**(a.build or {}),'completion_source':'party' if kind=='complete_item' else 'manual','completed_at':stamp.isoformat()}
        if kind in ('complete_item','close_weekly'):
            for rd in rounds:rd.state='stopped_incomplete' if kind=='close_weekly' else 'completed';rd.ended_at=stamp;rd.revision+=1
        db.flush()
        for member in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.membership_id.in_(affected))):
            active=any(a.state=='active' for a in life.assignments(db,row,member))
            if not active:member.state='stopped' if kind=='close_weekly' else 'completed';member.ended_at=stamp
            member.revision+=1;life.event(db,row,member,command,'stopped' if kind=='close_weekly' else 'completed',stamp,evidence)
        db.flush();settle_participations(db,row,stamp,stopping=kind=='close_weekly')
        if kind=='close_weekly':
            for sess in graph.sessions(db,row,history=True):
                if sess.state in ('confirmed','unconfirmed'):sess.state='cancelled';sess.revision+=1
        unfinished=any(r.state=='active' for _,r in graph.admission.rounds(db,row))
        actual_active=any(a.state=='active' for a in assignments(db,row))
        if not unfinished or not actual_active:
            row.state='closed';generation=db.get(CycleGeneration,(row.id,row.generation))
            generation.state='stopped' if kind=='close_weekly' else 'completed';generation.closed_at=stamp
            for app in db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,CycleApplication.generation==row.generation,CycleApplication.state=='pending')):
                app.state='cancelled';app.ended_at=stamp;app.revision+=1
        obsolete(db,row);row.members_revision+=1;planning.bump(db,row)
        event(db,row,uid,command,kind,stamp,evidence);db.flush()
        def final(current):
            playable(current,key)
            if current>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
        return 200,life.ack(db,row,command,stamp),final
    return cycles.execute(principal,{'close_weekly':'close','complete_item':'complete','personal_completion':'personal'}[kind],command,
        dict(room_id=str(rid) if rid else None,round_id=str(round_id) if round_id else None,body=body),run)


def manual(principal,cid,raid_id,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        ready(db);value=playable(stamp,body['target_cycle_key'])
        if body['expected_cycle_key']!=value.current.isoformat():fail('CYCLE_CHANGED')
        account,character=weekly.scope(db,uid,cid,body)
        if body['expected_catalog_version']!=weekly.raids.catalog().catalog_version:fail('CATALOG_VERSION_CONFLICT')
        raid=weekly.raid_by_id(raid_id);state=db.get(WeeklyState,(uid,cid,raid_id,value.key))
        if (state.revision if state else 1)!=body['expected_revision']:fail('REVISION_CONFLICT')
        if body['completed']:
            weekly.lifecycle.require_usable(db,character)
            if not raid.is_active:fail('RAID_INACTIVE')
            if body['difficulty_id']:
                try:weekly.raids.difficulty(raid_id,body['difficulty_id'],body['expected_catalog_version'])
                except weekly.raids.CatalogSelectionError as error:fail(error.code)
            if state and state.active_party_id:fail('PARTICIPATION_CONFIRMATION_REQUIRED')
        had=bool(state and state.manual_completed_at)
        if had!=body['completed'] or had and state.manual_difficulty_id!=body['difficulty_id']:
            if state is None:state=WeeklyState(user_id=uid,character_id=cid,raid_id=raid_id,cycle_key=value.key,revision=1,updated_at=stamp)
            if state not in db:db.add(state)
            state.manual_completed_at=(state.manual_completed_at or stamp) if body['completed'] else None
            state.manual_difficulty_id=body['difficulty_id'] if body['completed'] else None
            state.revision+=1;state.updated_at=stamp
        db.flush()
        from app.raid_rooms.cycle_creation import scope
        result=wire.ManualCompletionResult.model_validate(dict(scope=scope(stamp,body['target_cycle_key']),data=weekly.entry(db,account,character,raid,value.key,weekly.raids.cycle(stamp),state))).model_dump(mode='json')
        return 200,result,lambda current:playable(current,body['target_cycle_key'])
    return cycles.execute(principal,'manual',command,dict(character_id=str(cid),raid_id=raid_id,body=body),run)
