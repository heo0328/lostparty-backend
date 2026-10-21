"""Existing C participants explicitly join or decline an already open N."""
import uuid
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycle_lifecycle as life,cycle_admission as admission,cycle_schedule as schedule
from app.raid_rooms import cycle_commands as commands,cycle_wire as wire,cycles,admission_context as selection_context
from app.raid_rooms.cycle_creation import permission
from app.raid_rooms.participation_commands import Selection,Target


def prepare(db,uid,rid,key,action,cid,role,stamp):
    if action not in ('join','decline') or (cid is None)!=(role is None):fail('INVALID_REQUEST',400)
    if action=='decline' and cid is not None:fail('INVALID_REQUEST',400)
    room,row,value=life.target_row(db,uid,rid,key,stamp,next_only=True)
    if row is None:fail('TARGET_NOT_OPEN')
    source,cm,owned,selected,public,source_proof,reason=life.source(db,uid,room,stamp,validate=action=='join')
    if row.state!='open':reason=reason or ('TARGET_REOPEN_REQUIRED' if commands.target_state(db,row)=='cancelled' else 'TARGET_CYCLE_CLOSED')
    targets=[];selected_ids=[];choices=[];comparison=None
    own=life.actual_member(db,row,uid)
    if own is not None:reason=reason or ('ROOM_MEMBER_EXISTS' if action=='join' else 'PARTICIPATION_CANCELLATION_REQUIRED')
    if action=='decline':selected=None
    elif cid is not None:
        try:selected=selection_context.selection(db,uid,cid,role)
        except GameError as error:reason=reason or error.code;selected=None
    if action=='join' and selected is not None:
        minimum=row.settings_snapshot['combat_requirement']['dealer_min' if selected.selected_role=='dealer' else 'support_min']
        comparison=admission.core.power_comparison(db,uid,selected,minimum)
        targets=commands.target_items(db,uid,row,selected)
        choices=schedule.choices(db,row,stamp)
        if reason is None:
            try:admission.admit_bundle(db,uid,room,row,selected,targets,None,stamp,validate_only=True)
            except GameError as error:
                reason=error.code
                if admission.capacity(row)==8 and reason in ('ROOM_FULL','ROOM_COMPOSITION_CONFLICT'):
                    alternate=[t.model_copy(update={'party_no':2}) for t in targets]
                    try:
                        admission.admit_bundle(db,uid,room,row,selected,alternate,None,stamp,validate_only=True)
                        targets=alternate;reason=None
                    except GameError:pass
                if reason=='WEEKLY_ALREADY_PARTICIPATING':reason='TARGET_CHARACTER_CONFLICT'
        if any(v['required'] and not v['permission']['allowed'] for v in choices):reason=reason or 'RECRUITMENT_CLOSED'
    conflicts=life.conflict_details(db,uid,room,row,selected)
    data=dict(room_id=rid,action=action,source=public,selection=selected,targets=targets,
        target_session_ids=selected_ids,permission=permission(reason),conflicts=conflicts)
    extra=dict(cid=str(selected.character_id) if selected else None,role=selected.selected_role if selected else None,
        source_character=str(owned[0].character_id))
    hidden=[source_proof,room.revision,room.scope,selection_context.group_stamp(db,room.group_id),
        row.settings_snapshot,commands.leadership(db,row),choices,comparison['power_revision'] if comparison else None]
    result,binding=life.sign(uid,rid,key,'continue-'+action,jsonable_encoder(data),hidden,stamp,row=row,extra=extra)
    return result,binding,room,row


def get(principal,rid,key,action='join',cid=None,role=None):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        value,*_=prepare(db,uid,rid,key,action,cid,role,stamp)
        return wire.ContinuationContext.model_validate(value).model_dump(mode='json')


def execute(principal,rid,command,data,*,decline=False):
    body=data.model_dump(mode='json');action='decline' if decline else 'join'
    def run(db,uid,stamp):
        token=life.verify_token(uid,rid,body,'continue-'+action,stamp)
        value,binding,room,row=prepare(db,uid,rid,body['target_cycle_key'],action,
            uuid.UUID(token['cid']) if token['cid'] else None,token['role'],stamp)
        commands.cas(db,row,body,stamp)
        life.require_match(token,binding)
        current=value['data']
        if not current['permission']['allowed']:
            error=GameError(current['permission']['reason'])
            error.cycle_details=dict(conflicts=current['conflicts'],available_at=None,failed_cycle_key=body['target_cycle_key'])
            raise error
        if decline:
            life.decision(db,row,uid,command,'declined',stamp,dict(source=current['source'],character_id=token['source_character'],
                raid_ids=[i.raid_id for i,r in admission.rounds(db,row)]))
            row.revision+=1;cycles.touch_directory(db,row.cycle_key)
        else:
            if current['selection']!=body['selection'] or current['targets']!=body['target_items']:
                fail('TARGET_SCOPE_MISMATCH',400)
            selection=Selection.model_validate(body['selection']);targets=[Target.model_validate(t) for t in body['target_items']]
            selected=[uuid.UUID(i) for i in body['target_session_ids']]
            final_guard=schedule.final_deadlines(db,row,selected,stamp)
            member,_,_=admission.admit_bundle(db,uid,room,row,selection,targets,command,stamp)
            schedule.enrol(db,row,member,selected,stamp)
            if schedule.planning_enabled(db):
                from app.raid_rooms import cycle_planning
                cycle_planning.refresh(db,room,row,uid,command,stamp)
        db.flush()
        result=life.ack(db,row,command,stamp)
        if decline:return 200,result
        return 200,result,final_guard
    return cycles.execute(principal,'decline' if decline else 'continue',command,dict(room_id=str(rid),body=body),run)
