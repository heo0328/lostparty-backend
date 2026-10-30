"""Staged v2 general admission commands. Each write owns one target only."""
from app.raid_rooms import beta_profile, beta_schedule, beta_output
import uuid
from datetime import datetime, time, timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.support import fail, GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import (cycles, admission_context as context, admission_service as base,
    command_context as opaque, cycle_admission as admission, cycle_schedule as schedule, cycle_wire as wire)
from app.raid_rooms.cycle_creation import scope, permission
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember
from app.raid_rooms.cycle_application_models import CycleApplication as Application
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member
from app.raid_rooms.participation_commands import Selection, Target
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids

from app.raid_rooms import session_display as display, session_display_schemas as display_schemas


def resolve(db, uid, rid, key, stamp, *, write=False):
    room=base.room(db,uid,rid)
    from app.raid_rooms.completed_room_lifecycle import require_active
    require_active(db,rid)
    value,row=cycles.resolve(db,rid,key,stamp,write=write)
    if row is None:fail('TARGET_NOT_OPEN')
    admission.capacity(row)
    if row.state!='open':fail('ROOM_REVIEW_REQUIRED' if row.state=='review_required' else 'ROUND_NOT_ACTIVE')
    if room.ended_at is not None:fail('ROOM_NOT_ACTIVE')
    return room,row


def leadership(db,row):
    generation=db.get(CycleGeneration,(row.id,row.generation))
    leader=db.get(CycleMember,generation.leader_cycle_member_id) if generation else None
    if generation is not None and (generation.state=='cancelled' or (generation.state=='completed' and row.state=='closed' and generation.closed_at is not None)) and leader is None:
        return dict(leader_cycle_member_id=None,leadership_revision=generation.leadership_revision,leader_membership_id=None)
    if generation is None or leader is None:fail('ROOM_REVIEW_REQUIRED')
    return dict(leader_cycle_member_id=leader.id,leadership_revision=generation.leadership_revision,
        leader_membership_id=leader.membership_id)


def target_state(db,row):
    generation=db.get(CycleGeneration,(row.id,row.generation))
    return {'cancelled':'cancelled','completed':'completed','stopped':'stopped_incomplete',
        'review_required':'review_required'}.get(generation.state,'open')


def require_leader(db,uid,row):
    leader=db.get(CycleMember,leadership(db,row)['leader_cycle_member_id'])
    member=db.get(Member,leader.membership_id)
    if leader.user_id!=uid or leader.state!='participating' or member.ended_at is not None:
        fail('ROOM_LEADER_REQUIRED',403)


def cas(db, row, body, stamp, *, leader=False):
    if body['expected_cycle_key']!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
    if body['target_cycle_key']!=row.cycle_key.isoformat() or body['expected_target_revision']!=row.revision:
        fail('TARGET_CONTEXT_STALE')
    for name,actual in (('expected_room_revision',db.get(Room,row.room_id).revision),
            ('expected_members_revision',row.members_revision),('expected_plan_revision',row.plan_revision)):
        if name in body and body[name]!=actual:fail('REVISION_CONFLICT')
    if leader and body['expected_leadership_revision']!=leadership(db,row)['leadership_revision']:
        fail('LEADERSHIP_CHANGED')


def target_items(db,uid,row,selection):
    result=[]
    for item,rd in admission.rounds(db,row):
        state=db.get(WeeklyState,(uid,selection.character_id,item.raid_id,row.cycle_key))
        result.append(Target(item_id=item.id,round_id=rd.id,party_no=1,
            expected_round_revision=rd.revision,expected_weekly_revision=state.revision if state else 1))
    return result


def preflight(db,uid,room,row,cid,role,intent,stamp,*,include_session_display=False):
    if intent not in ('apply','join'):fail('INVALID_REQUEST',400)
    selection=context.selection(db,uid,cid,role)
    targets=target_items(db,uid,row,selection)
    minimum=row.settings_snapshot['combat_requirement']['dealer_min' if role=='dealer' else 'support_min']
    power=admission.core.power_comparison(db,uid,selection,minimum)
    reason=None
    evaluation=None
    if intent=='apply':
        from app.raid_rooms import admission_eligibility
        evaluation=admission_eligibility.single(db,uid,room,row,selection)
        reason=evaluation['reason']
        if evaluation['allowed']:
            for t in targets:t.party_no=evaluation['parties'][t.item_id]
    if row.settings_snapshot['admission_mode']!=('leader_only' if intent=='apply' else 'direct_join'):
        reason='ADMISSION_MODE_CHANGED'
    if reason is None:
        try:
            admission.admit_bundle(db,uid,room,row,selection,targets,None,stamp,validate_only=True,pending=intent=='apply',unified=intent=='apply')
        except GameError as error:
            reason=error.code
            if admission.capacity(row)==8 and reason in ('ROOM_FULL','ROOM_COMPOSITION_CONFLICT'):
                alternate=[t.model_copy(update={'party_no':2}) for t in targets]
                try:
                    admission.admit_bundle(db,uid,room,row,selection,alternate,None,stamp,validate_only=True,pending=intent=='apply',unified=intent=='apply')
                    targets=alternate;reason=None
                except GameError:pass
    choices=schedule.choices(db,row,stamp)
    if any(c['required'] and not c['permission']['allowed'] for c in choices):reason=reason or 'RECRUITMENT_CLOSED'
    if intent=='apply' and db.scalar(select(Application.id).where(Application.cycle_id==row.id,
            Application.generation==row.generation,Application.user_id==uid,Application.state=='pending',
            Application.expires_at>stamp)) is not None:reason=reason or 'ROOM_APPLICATION_EXISTS'
    # Public origin is captured on the application, never accepted from a client.
    stable=jsonable_encoder([str(uid),str(room.id),str(row.id),row.generation,row.revision,
        row.settings_revision,row.members_revision,row.plan_revision,leadership(db,row),
        context.group_stamp(db,room.group_id,retained=True),room.scope,room.revision,row.settings_snapshot,
        selection,targets,power['power_revision'],choices,context.policy(db,room)])
    metadata=display.existing(db,uid,row,stamp,intent,choices) if include_session_display else None
    if evaluation is not None:stable.append(evaluation['evidence'])
    if include_session_display:stable.append(metadata)
    if beta_profile.enabled():stable.append([beta_profile.PROFILE,beta_schedule.context_basis(db,uid)])
    policy=digest(stable)
    expires=min(stamp+timedelta(seconds=opaque.LIFETIME_SECONDS),raids.cycle(stamp).ends_at)
    token=opaque.seal(dict(actor=str(uid),room=str(room.id),cycle=str(row.id),intent=intent,
        command='admit-v2',expires=expires.isoformat(),digest=policy,**display.marker(include_session_display),**beta_profile.marker()))
    result=dict(scope=scope(stamp,row.cycle_key.isoformat(),row),data=dict(room_id=room.id,room_revision=room.revision,
        members_revision=row.members_revision,plan_revision=row.plan_revision,
        expected_cycle_key=raids.cycle(stamp).cycle_key,server_time=stamp,catalog_version=raids.catalog().catalog_version,
        policy_snapshot=policy,context_token=token,selection=selection,targets=targets,session_choices=choices,
        comparison=power,permissions={intent:permission(reason)},target_cycle_key=row.cycle_key,
        expected_target_revision=row.revision,issued_at=stamp,expires_at=expires,leadership=leadership(db,row)))
    if include_session_display:result["data"]["session_display"]=metadata
    return result


def get_context(principal,rid,key,cid,role,intent,include_session_display=False):
    if intent=='change_character':
        from app.raid_rooms import cycle_character
        return cycle_character.get(principal,rid,key,cid,role,include_session_display)
    with base.snapshot(principal) as (db,uid,stamp):
        room,row=resolve(db,uid,rid,key,stamp)
        return display.output(display_schemas.AdmissionDisplayContext, jsonable_encoder(
            preflight(db,uid,room,row,cid,role,intent,stamp,include_session_display=include_session_display)), include_session_display, snapshot=(db,uid,stamp))


def ack(db,command_id,room,row,member,assignments,stamp):
    revisions=[dict(resource='target',id=row.id,revision=row.revision),
        dict(resource='members',id=row.id,revision=row.members_revision),
        dict(resource='plan',id=row.id,revision=row.plan_revision),
        dict(resource='membership',id=member.id,revision=member.revision)]
    revisions += [dict(resource='assignment',id=a.id,revision=a.revision) for a in assignments]
    return wire.OutputContract3PostV2RaidRoomsRoomIdJoin.model_validate(dict(scope=scope(stamp,row.cycle_key.isoformat(),row),
        data=dict(command_id=command_id,outcome='applied',executed_at=stamp,room_id=room.id,
            target_cycle_key=row.cycle_key,revisions=revisions))).model_dump(mode='json')


def application_ack(command_id,app,row,stamp):
    return wire.OutputContract3PostV2RaidRoomsRoomIdApplications.model_validate(dict(
        scope=scope(stamp,row.cycle_key.isoformat(),row),data=dict(command_id=command_id,room_id=app.room_id,
            application_id=app.id,revision=app.revision,state=app.state,executed_at=stamp,
            target_cycle_key=row.cycle_key))).model_dump(mode='json')


def admit(principal,rid,command_id,data,*,applying=False):
    body=beta_profile.body(data);intent='apply' if applying else 'join'
    def run(db,uid,stamp):
        room,row=resolve(db,uid,rid,body['target_cycle_key'],stamp,write=True)
        cas(db,row,body,stamp)
        token=opaque.unseal(body['selection_context']['context_token'])
        beta_profile.check_marker(token)
        if (token.get('actor')!=str(uid) or token.get('command')!='admit-v2' or token.get('room')!=str(rid)
                or token.get('cycle')!=str(row.id) or token.get('intent')!=intent):fail('CONTEXT_INVALID',400)
        if stamp>=datetime.fromisoformat(token['expires']):fail('CONTEXT_EXPIRED')
        current=preflight(db,uid,room,row,data.selection.character_id,data.selection.selected_role,intent,stamp,include_session_display=display.enabled(token))['data']
        if token['digest']!=current['policy_snapshot']:fail('SELECTION_CONTEXT_CHANGED')
        if body['expected_policy_snapshot']!=current['policy_snapshot']:fail('POLICY_CONTEXT_CHANGED')
        if body['expected_catalog_version']!=current['catalog_version']:fail('CATALOG_VERSION_CONFLICT')
        if body['selection']!=jsonable_encoder(current['selection']):fail('REVISION_CONFLICT')
        if not current['permissions'][intent]['allowed']:fail(current['permissions'][intent]['reason'])
        if applying and body['target_items']!=jsonable_encoder(current['targets']):fail('TARGET_SCOPE_MISMATCH',400)
        selected=data.target_session_ids
        final_guard=schedule.final_deadlines(db,row,selected,stamp)
        selection=Selection.model_validate(body['selection'])
        targets=[Target.model_validate(t) for t in body['target_items']]
        member,assignments,power=admission.admit_bundle(db,uid,room,row,selection,targets,command_id,stamp,
            validate_only=applying,pending=applying,unified=applying)
        if applying:
            existing=db.scalar(select(Application).where(Application.cycle_id==row.id,Application.generation==row.generation,
                Application.user_id==uid,Application.state=='pending'))
            if existing is not None:
                if existing.expires_at>stamp:fail('ROOM_APPLICATION_EXISTS')
                existing.state='expired';existing.ended_at=stamp;existing.revision+=1;db.flush()
            from app.raid_rooms import application_display
            character=admission.core.identity.selected_character(db,uid,body['selection'])
            character_display=admission.core.identity.display(character) | application_display.snapshot_level(character)
            app=Application(id=uuid.uuid4(),room_id=rid,cycle_id=row.id,generation=row.generation,user_id=uid,revision=1,
                selection=body['selection'],targets=body['target_items'],session_ids=[str(i) for i in selected],
                display=character_display,
                build=jsonable_encoder(power),origin_scope=room.scope,origin_group_id=room.group_id,state='pending',
                created_at=stamp,expires_at=datetime.combine(row.cycle_key+timedelta(days=7),time(6),raids.KST))
            db.add(app);db.flush()
            if beta_profile.enabled():
                from app.raid_rooms.beta_models import BetaApplicationMemo
                from app.raid_rooms import beta_text
                saved=beta_schedule.get(db,row)
                db.add(BetaApplicationMemo(application_id=app.id,memo=beta_text.normalize(body.get('application_memo')),
                    promise_revision=db.get(schedule.Session,saved.session_id).schedule_revision if saved else None))
                db.flush()
            # A pending application changes neither target participants nor leases.
            result=(201,application_ack(command_id,app,row,stamp))
        else:
            schedule.enrol(db,row,member,selected,stamp)
            if schedule.planning_enabled(db):
                from app.raid_rooms import cycle_planning
                cycle_planning.refresh(db,room,row,uid,command_id,stamp)
            result=(200,ack(db,command_id,room,row,member,assignments,stamp))
        return *result,final_guard
    return cycles.execute(principal,intent,command_id,dict(room_id=str(rid),body=body),run)


def load_application(db,uid,aid,stamp):
    app=db.get(Application,aid)
    if app is None:fail('ROOM_APPLICATION_NOT_FOUND',404)
    row=db.get(RoomCycle,app.cycle_id)
    if app.user_id!=uid:
        # Never reveal application existence to another room's member/leader.
        try:require_leader(db,uid,row)
        except GameError:fail('ROOM_APPLICATION_NOT_FOUND',404)
    return app,row


def application(principal,aid):
    with base.snapshot(principal) as (db,uid,stamp):
        app,row=load_application(db,uid,aid,stamp)
        cycles.target(stamp,row.cycle_key.isoformat())
        result=dict(scope=scope(stamp,row.cycle_key.isoformat(),row),data=dict(application_id=app.id,
            room_id=app.room_id,revision=app.revision,state='expired' if app.state=='pending' and stamp>=app.expires_at else app.state,created_at=app.created_at,expires_at=app.expires_at,
            ended_at=app.ended_at,display=app.display,character_id=app.selection['character_id'],
            selected_role=app.selection['selected_role'],admission_origin=dict(scope=app.origin_scope,
                group_id=str(app.origin_group_id) if app.origin_group_id else None),
            target_cycle_key=row.cycle_key,target_generation=app.generation))
        if uid!=app.user_id:
            room=db.get(Room,app.room_id);reason=None;power=None
            if app.state!='pending' or stamp>=app.expires_at:reason='APPLICATION_NOT_PENDING'
            elif app.generation!=row.generation:reason='TARGET_CONTEXT_STALE'
            elif row.state!='open' or room.ended_at is not None:reason='ROUND_NOT_ACTIVE'
            if reason is None:
                try:
                    saved=Selection.model_validate(app.selection)
                    choice=context.selection(db,app.user_id,saved.character_id,saved.selected_role)
                    if (choice.expected_ownership_revision,choice.expected_lifecycle_revision)!=(saved.expected_ownership_revision,saved.expected_lifecycle_revision):
                        fail('APPLICATION_CONTEXT_CHANGED')
                    targets=target_items(db,app.user_id,row,choice)
                    old={t['item_id']:t for t in app.targets}
                    if set(old)!={str(t.item_id) for t in targets}:fail('APPLICATION_CONTEXT_CHANGED')
                    for t in targets:
                        if old[str(t.item_id)]['round_id']!=str(t.round_id):fail('APPLICATION_CONTEXT_CHANGED')
                        t.party_no=old[str(t.item_id)]['party_no']
                    _,_,power=admission.admit_bundle(db,app.user_id,room,row,choice,targets,None,stamp,
                        validate_only=True,public_origin_application=app,unified=True)
                    schedule.deadlines(db,row,[uuid.UUID(i) for i in app.session_ids],stamp)
                except GameError as error:reason=error.code
            result['data']=dict(application=result['data'],room_revision=room.revision,members_revision=row.members_revision,
                plan_revision=row.plan_revision,server_time=stamp,
                eligibility=dict(evaluated_at=stamp,state='blocked' if reason else 'eligible',
                    reasons=[reason] if reason else [],comparison=power),permissions=dict(approve=permission(reason),
                    reject=permission(None if app.state=='pending' and stamp<app.expires_at and app.generation==row.generation else 'APPLICATION_NOT_PENDING')))
        return beta_output.render(db,uid,stamp,wire.OutputContract3GetV2RaidRoomApplicationsApplicationId,result)


def process(principal,aid,command_id,data,*,action='approve'):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        app,row=load_application(db,uid,aid,stamp)
        cycles.target(stamp,body['target_cycle_key'])
        cas(db,row,body,stamp,leader=action!='withdraw')
        if action=='withdraw':
            if uid!=app.user_id:fail('ROOM_APPLICATION_NOT_FOUND',404)
        else:require_leader(db,uid,row)
        if row.generation!=app.generation:fail('TARGET_CONTEXT_STALE')
        if app.revision!=body['expected_application_revision']:fail('REVISION_CONFLICT')
        if app.state!='pending' or stamp>=app.expires_at:fail('APPLICATION_NOT_PENDING')
        room=db.get(Room,app.room_id)
        selected=[uuid.UUID(i) for i in app.session_ids]
        if action=='approve':
            if room.ended_at is not None or row.state!='open':fail('ROUND_NOT_ACTIVE')
            original=Selection.model_validate(app.selection)
            selection=context.selection(db,app.user_id,original.character_id,original.selected_role)
            if (selection.expected_ownership_revision!=original.expected_ownership_revision or
                    selection.expected_lifecycle_revision!=original.expected_lifecycle_revision):fail('APPLICATION_CONTEXT_CHANGED')
            targets=target_items(db,app.user_id,row,selection)
            saved={str(t['item_id']):t for t in app.targets}
            if set(saved)!={str(t.item_id) for t in targets}:fail('APPLICATION_CONTEXT_CHANGED')
            for t in targets:
                old=saved[str(t.item_id)]
                if old['round_id']!=str(t.round_id):fail('APPLICATION_CONTEXT_CHANGED')
                t.party_no=old['party_no']
            final_guard=schedule.final_deadlines(db,row,selected,stamp)
            member,assignments,_=admission.admit_bundle(db,app.user_id,room,row,selection,targets,command_id,stamp,
                public_origin_application=app,unified=True)
            agreed=True
            if beta_schedule.get(db,row) is not None:
                from app.raid_rooms.beta_models import BetaApplicationMemo
                promise=db.get(BetaApplicationMemo,app.id)
                saved=beta_schedule.get(db,row)
                agreed=promise is not None and promise.promise_revision==db.get(schedule.Session,saved.session_id).schedule_revision
            schedule.enrol(db,row,member,selected,stamp,consent=agreed)
            if schedule.planning_enabled(db):
                from app.raid_rooms import cycle_planning
                cycle_planning.refresh(db,room,row,uid,command_id,stamp)
            app.state='accepted'
        else:app.state='withdrawn' if action=='withdraw' else 'rejected'
        app.revision+=1;app.ended_at=stamp;db.flush()
        if action=='approve':
            result=ack(db,command_id,room,row,member,assignments,stamp)
            result['data']['revisions'].append(dict(resource='application',id=app.id,revision=app.revision))
            return 200,result,final_guard
        return 200,application_ack(command_id,app,row,stamp)
    return cycles.execute(principal,action,command_id,dict(application_id=str(aid),body=body),run)
