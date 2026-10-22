"""Replace an unfinished target bundle; old character usability is not a gate."""
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import cycle_lifecycle as life,cycle_leadership as leadership,cycle_commands as commands
from app.raid_rooms import cycle_admission as admission,cycle_schedule as schedule,cycle_wire as wire,cycles
from app.raid_rooms.cycle_creation import permission,scope
from app.raid_rooms.participation_commands import Selection,Target

from app.raid_rooms import session_display as display, session_display_schemas as display_schemas


def prepare(db,uid,rid,key,cid,role,stamp,*,include_session_display=False):
    room,row=commands.resolve(db,uid,rid,key,stamp)
    cm=life.actual_member(db,row,uid,states=('participating',))
    if cm is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
    owned=life.assignments(db,row,cm)
    if not owned or any(a.state!='active' for a in owned):fail('ROUND_NOT_ACTIVE')
    selection=life.selection_context.selection(db,uid,cid,role)
    targets=commands.target_items(db,uid,row,selection)
    by_item={a.item_id:a for a in owned}
    if set(by_item)!={t.item_id for t in targets}:fail('TARGET_BUNDLE_INCOMPLETE')
    for t in targets:t.party_no=by_item[t.item_id].party_no
    minimum=row.settings_snapshot['combat_requirement']['dealer_min' if role=='dealer' else 'support_min']
    power=admission.core.power_comparison(db,uid,selection,minimum);reason=None
    try:admission.admit_bundle(db,uid,room,row,selection,targets,None,stamp,validate_only=True,replacing=cm)
    except GameError as error:reason=error.code
    choices=schedule.choices(db,row,stamp)
    if any(c['required'] and not c['permission']['allowed'] for c in choices):reason=reason or 'RECRUITMENT_CLOSED'
    hidden=[room.revision,room.scope,life.selection_context.group_stamp(db,room.group_id),cm.id,cm.revision,
        [[a.id,a.revision,a.character_id,a.selected_role,a.party_no,a.slot_no] for a in owned],
        row.settings_snapshot,selection,targets,power['power_revision'],choices]
    metadata=display.existing(db,uid,row,stamp,"character",choices) if include_session_display else None
    if include_session_display:hidden.append(metadata)
    snapshot=digest(jsonable_encoder(hidden))
    data=dict(room_id=rid,room_revision=room.revision,members_revision=row.members_revision,plan_revision=row.plan_revision,
        expected_cycle_key=commands.raids.cycle(stamp).cycle_key,server_time=stamp,catalog_version=commands.raids.catalog().catalog_version,
        policy_snapshot=snapshot,selection=selection,targets=targets,session_choices=choices,comparison=power,
        permissions=dict(change_character=permission(reason)),target_cycle_key=key,expected_target_revision=row.revision,
        leadership=commands.leadership(db,row))
    if include_session_display:data["session_display"]=metadata
    # server_time is presentation, not an execution snapshot component.
    signed={k:v for k,v in jsonable_encoder(data).items() if k!='server_time'}
    value,binding=life.sign(uid,rid,key,'character',signed,jsonable_encoder(hidden),stamp,row=row,extra=display.marker(include_session_display))
    value['data']['server_time']=stamp
    return value,binding,room,row,cm,owned


def get(principal,rid,key,cid,role,include_session_display=False):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        value,*_=prepare(db,uid,rid,key,cid,role,stamp,include_session_display=include_session_display)
        return display.output(display_schemas.AdmissionDisplayContext,value,include_session_display)


def execute(principal,rid,command,data):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        token=life.verify_token(uid,rid,body|dict(context_token=body['selection_context']['context_token']),'character',stamp)
        value,binding,room,row,cm,owned=prepare(db,uid,rid,body['target_cycle_key'],data.selection.character_id,data.selection.selected_role,stamp,include_session_display=display.enabled(token))
        commands.cas(db,row,body,stamp);life.require_match(token,binding)
        current=value['data']
        if body['expected_cycle_member_revision']!=cm.revision:fail('REVISION_CONFLICT')
        expected={(str(a.id),a.revision) for a in owned}
        supplied={(v['assignment_id'],v['expected_revision']) for v in body['assignments']}
        if len(supplied)!=len(body['assignments']) or supplied!=expected:fail('REVISION_CONFLICT')
        if current['policy_snapshot']!=body['expected_policy_snapshot']:fail('POLICY_CONTEXT_CHANGED')
        if current['catalog_version']!=body['expected_catalog_version']:fail('CATALOG_VERSION_CONFLICT')
        if current['selection']!=body['selection'] or current['targets']!=body['target_items']:fail('TARGET_SCOPE_MISMATCH',400)
        if not current['permissions']['change_character']['allowed']:fail(current['permissions']['change_character']['reason'])
        final_guard=schedule.final_deadlines(db,row,data.target_session_ids,stamp)
        evidence=dict(assignments=[life.assignment_snapshot(a) for a in owned],
            participations=leadership.release_parts(db,row,cm,stamp,ending=False))
        member,_,_=admission.admit_bundle(db,uid,room,row,Selection.model_validate(body['selection']),
            [Target.model_validate(v) for v in body['target_items']],command,stamp,replacing=cm)
        schedule.enrol(db,row,member,data.target_session_ids,stamp)
        cm.revision+=1;life.event(db,row,cm,command,'character_changed',stamp,evidence)
        row.revision+=1;row.members_revision+=1;row.plan_revision+=1
        cycles.touch_directory(db,row.cycle_key);db.flush()
        if schedule.planning_enabled(db):
            from app.raid_rooms import cycle_planning
            cycle_planning.refresh(db,room,row,uid,command,stamp)
        return 200,life.ack(db,row,command,stamp),final_guard
    return cycles.execute(principal,'character',command,dict(room_id=str(rid),body=body),run)
