"""W3 authority, evidence and bounded contexts. Callers own the transaction."""
from app.raid_rooms import beta_profile,beta_schedule
import uuid
from decimal import Decimal,InvalidOperation
from datetime import datetime,timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.auth.models import User
from app.game_accounts.support import fail,GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import cycles,cycle_commands as commands,cycle_admission as admission,admission_context as selection_context
from app.raid_rooms import command_context as opaque,cycle_wire as wire
from app.raid_rooms.cycle_creation import scope,permission
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleGeneration,CycleAssignment,CycleRound,ParticipationEvent
from app.raid_rooms.cycle_lifecycle_models import CycleDecision
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentAssignment as Assignment
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids

VALID_STATES=('participating','completed','stopped')


def target_row(db,uid,rid,key,stamp,*,next_only=False):
    room=commands.base.room(db,uid,rid)
    from app.raid_rooms.completed_room_lifecycle import require_active
    require_active(db,rid)
    value,row=cycles.resolve(db,rid,key,stamp)
    if next_only and value.phase!='future':fail('TARGET_CYCLE_NOT_FUTURE')
    if room.ended_at is not None:fail('ROOM_NOT_ACTIVE')
    if row is not None:admission.capacity(row)
    return room,row,value


def actual_member(db,row,uid,*,states=VALID_STATES):
    if row is None:return None
    return db.scalar(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.user_id==uid,
        CycleMember.state.in_(states),Member.ended_at.is_(None)))


def assignments(db,row,cm):
    return list(db.scalars(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).join(
        CycleRound,CycleRound.round_id==Assignment.round_id).where((CycleRound.is_current.is_(True)) | (Assignment.state=='completed'),
        CycleAssignment.cycle_id==row.id,CycleAssignment.generation==row.generation,
        CycleAssignment.cycle_member_id==cm.id).order_by(Assignment.item_id)))


def qualify(db,room,row,cm):
    member=db.get(Member,cm.membership_id)
    if member is None or member.ended_at is not None or cm.state not in VALID_STATES:fail('SOURCE_PARTICIPATION_REQUIRED',403)
    user=db.get(User,cm.user_id)
    if user is None or user.status!='active':fail('ROOM_TARGET_UNAVAILABLE')
    owned=assignments(db,row,cm)
    if {a.item_id for a in owned}!={i.id for i,r in admission.rounds(db,row)} or not owned:
        fail('ROOM_REVIEW_REQUIRED')
    if len({(a.character_id,a.selected_role) for a in owned})!=1:fail('ROOM_REVIEW_REQUIRED')
    selected=selection_context.selection(db,cm.user_id,owned[0].character_id,owned[0].selected_role)
    if any((a.ownership_revision,a.lifecycle_revision)!=(selected.expected_ownership_revision,selected.expected_lifecycle_revision)
            for a in owned):fail('OWNERSHIP_REQUIRED',403)
    admission.core._limits(db,cm.user_id,selected,False)
    admission.core._group(db,room,cm.user_id,existing=True)
    admission.core._room_restrictions(db,room)
    minimum=row.settings_snapshot['combat_requirement']['dealer_min' if selected.selected_role=='dealer' else 'support_min']
    power=admission.core.power_comparison(db,cm.user_id,selected,minimum)
    if power['state'] in ('below','missing'):fail('COMBAT_POWER_REQUIRED')
    ledgers=[]
    character=admission.core.identity.selected_character(db,cm.user_id,selected.model_dump(mode='json'))
    try:level=Decimal(str(character.summary.get('item_level')))
    except (ValueError,InvalidOperation):level=None
    for item,rd in admission.rounds(db,row):
        try:difficulty=raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version)
        except raids.CatalogSelectionError as error:fail(error.code)
        if not raids.meets_item_level(level,difficulty):fail('RAID_ITEM_LEVEL_REQUIRED')
        a=next(a for a in owned if a.item_id==item.id)
        if a.state not in ('active','completed','stopped_incomplete'):fail('SOURCE_PARTICIPATION_REQUIRED',403)
        key=(cm.user_id,a.character_id,item.raid_id,row.cycle_key)
        state,lease=db.get(WeeklyState,key),db.get(WeeklyOccupancy,key)
        if a.state=='active' and (lease is None or lease.assignment_id!=a.id or state is None or state.active_party_id!=room.id
                or state.joined_at!=lease.joined_at):fail('WEEKLY_OCCUPANCY_CHANGED')
        ledgers.append([str(a.id),a.revision,a.state,state.revision if state else 1,str(lease.assignment_id) if lease else None])
    return selected,[selected.model_dump(mode='json'),power['power_revision'],ledgers]


def source(db,uid,room,stamp,*,validate=True):
    current=raids.cycle(stamp).cycle_key
    _,row=cycles.resolve(db,room.id,current,stamp)
    if row is None:fail('SOURCE_PARTICIPATION_REQUIRED',403)
    admission.capacity(row)
    cm=actual_member(db,row,uid)
    if cm is None:fail('SOURCE_PARTICIPATION_REQUIRED',403)
    owned=assignments(db,row,cm)
    if not owned or {a.item_id for a in owned}!={i.id for i,r in admission.rounds(db,row)}:fail('ROOM_REVIEW_REQUIRED')
    member=db.get(Member,cm.membership_id)
    selected=None;evidence=[];reason=None
    if validate:
        try:selected,evidence=qualify(db,room,row,cm)
        except GameError as error:reason=error.code
    public=dict(source_cycle_key=row.cycle_key,membership_id=member.id,membership_revision=member.revision,
        assignment_ids=[a.id for a in owned],source_cycle_member_id=cm.id,source_cycle_member_revision=cm.revision)
    hidden=[row.id,row.generation,row.revision,cm.id,cm.revision,cm.state,member.revision,
        [[a.id,a.revision,a.state] for a in owned],evidence,reason]
    return row,cm,owned,selected,public,hidden,reason


def candidates(db,room,row,actor):
    result=[];proof=[]
    for cm in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,
            CycleMember.generation==row.generation,CycleMember.id!=actor.id,CycleMember.state.in_(VALID_STATES))
            .order_by(CycleMember.joined_order,CycleMember.id)):
        owned=assignments(db,row,cm)
        if not owned or cm.joined_order is None:continue
        reason=None;qualification=None
        try:_,qualification=qualify(db,room,row,cm)
        except GameError as error:reason=error.code
        first=owned[0]
        result.append(dict(cycle_member_id=cm.id,revision=cm.revision,joined_order=str(cm.joined_order),
            character_id=first.character_id,character_name=first.display.get('character_name'),permission=permission(reason)))
        proof.append([cm.id,cm.revision,cm.state,qualification,reason])
    return result,proof


def sign(uid,rid,key,command,data,hidden,stamp,*,row=None,extra=None,db=None):
    envelope=dict(scope=scope(stamp,key,row),data=data)
    stable_scope={k:v for k,v in envelope['scope'].items() if k!='server_now'}
    profile_basis=[beta_profile.PROFILE,beta_schedule.context_basis(db,uid)] if beta_profile.enabled() and command in ('opening','continue-join') else beta_profile.marker()
    basis=[uid,rid,command,stable_scope,data,hidden]
    if beta_profile.enabled():basis.append(profile_basis)
    binding=digest(jsonable_encoder(basis))
    expires=min(stamp+timedelta(seconds=120),raids.cycle(stamp).ends_at)
    token=dict(actor=str(uid),room=str(rid),target=key,command=command,expires=expires.isoformat(),digest=binding)
    token.update(extra or {})
    token.update(beta_profile.marker())
    data.update(context_token=opaque.seal(token),issued_at=stamp,expires_at=expires)
    return envelope,binding


def verify_token(uid,rid,body,command,stamp):
    if body['expected_cycle_key']!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
    token=opaque.unseal(body['context_token'])
    beta_profile.check_marker(token)
    if (token.get('actor')!=str(uid) or token.get('room')!=str(rid) or token.get('target')!=body['target_cycle_key']
            or token.get('command')!=command):fail('TARGET_SCOPE_MISMATCH',400)
    if stamp>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
    return token


def require_match(token,binding):
    if token['digest']!=binding:fail('TARGET_CONTEXT_STALE')


def decision(db,row,uid,command,kind,stamp,evidence):
    db.add(CycleDecision(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
        user_id=uid,command_id=command,kind=kind,effective_at=stamp,evidence=jsonable_encoder(evidence)))


def event(db,row,cm,command,action,stamp,evidence):
    db.add(ParticipationEvent(id=uuid.uuid4(),room_id=row.room_id,cycle_id=row.id,generation=row.generation,
        cycle_member_id=cm.id,membership_id=cm.membership_id,user_id=cm.user_id,command_id=command,
        action=action,member_revision=cm.revision,effective_at=stamp,evidence=jsonable_encoder(evidence)))


def assignment_snapshot(a):
    return {name:getattr(a,name) for name in ('id','revision','item_id','round_id','membership_id','user_id',
        'character_id','selected_role','party_no','slot_no','display','build','ownership_revision','lifecycle_revision',
        'state','joined_at','ended_at')}


def ack(db,row,command,stamp,*,outcome='applied',revisions=None):
    result=dict(scope=scope(stamp,row.cycle_key.isoformat(),row),data=dict(command_id=command,outcome=outcome,
        executed_at=stamp,room_id=row.room_id,target_cycle_key=row.cycle_key,
        revisions=revisions or [dict(resource='target',id=row.id,revision=row.revision)]))
    return wire.OutputContract3PostV2RaidRoomsRoomIdJoin.model_validate(result).model_dump(mode='json')


def conflict_details(db,uid,room,row,selected):
    result=[]
    if selected is None:return result
    for item,rd in admission.rounds(db,row):
        state=db.get(WeeklyState,(uid,selected.character_id,item.raid_id,row.cycle_key))
        if state is None or state.active_party_id in (None,room.id):continue
        other=db.get(commands.Room,state.active_party_id)
        visible=other is not None and db.scalar(select(Member.id).where(Member.room_id==other.id,
            Member.user_id==uid,Member.ended_at.is_(None))) is not None
        result.append(dict(room_id=state.active_party_id,raid_id=item.raid_id,character_id=selected.character_id,
            target_cycle_key=row.cycle_key,can_view_detail=visible,room_title=other.title if visible else None))
    return result
