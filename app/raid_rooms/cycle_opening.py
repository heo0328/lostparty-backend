from app.raid_rooms import cycle_group_policy as group_policy
from app.raid_rooms import beta_schedule
from app.raid_rooms import beta_profile
"""Explicit future opening/reopening with the source C leader's own bundle."""
import uuid
from copy import deepcopy
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail,GameError
from app.raid_rooms import cycle_lifecycle as life,cycle_admission as admission,cycle_schedule as schedule
from app.raid_rooms import cycle_commands as commands,cycle_wire as wire,cycles,admission_context as selection_context
from app.raid_rooms.cycle_creation import permission
from app.raid_rooms.cycle_models import RoomCycle,CycleGeneration,CycleRound,CycleOpening
from app.raid_rooms.integrated_models import RecruitmentRound as Round
from app.raid_rooms.source_models import ScheduleAlternative
from app.raid_rooms.participation_commands import Target,Selection

from app.raid_rooms import session_display as display, session_display_schemas as display_schemas


def schedule_inputs(db,source):
    pairs={str(i.id):i.raid_id for i,r in admission.rounds(db,source)}
    result=[]
    for group in sorted(schedule.groups(db,source),key=lambda g:str(g.id)):
        alternatives=[]
        for alt in schedule.alternatives(db,group):
            clock=lambda v:f'{v//60:02}:{v%60:02}' if v is not None else None
            if len(set(alt.item_order))!=len(alt.item_order) or set(alt.item_order)-set(pairs):fail('ROOM_REVIEW_REQUIRED')
            # C may retain only unfinished item times after a party completion.
            # N still contains the full bundle; append completed C items in the
            # captured settings order without treating the copied intent as consent.
            order=list(alt.item_order)
            missing=set(pairs)-set(order)
            completed={str(i.id) for i,r in admission.rounds(db,source) if r.state=='completed'}
            if missing-completed:fail('ROOM_REVIEW_REQUIRED')
            order += [v['item_id'] for v in source.settings_snapshot['items'] if v['item_id'] in missing]
            alternatives.append(dict(client_alternative_key=schedule.alternative_key(db,alt),existing_session_id=None,expected_session_revision=None,
                weekday=alt.weekday,starts_local=clock(alt.start_minute),leader_latest_start_local=clock(alt.latest_start_minute),
                item_order=[pairs[i] for i in order]))
        result.append(wire.BScheduleGroup.model_validate(dict(client_group_key=db.get(schedule.ScheduleHead,group.id).client_key,
            existing_group_id=None,expected_group_revision=None,occurrence_mode=group.occurrence_mode,
            planning_mode=group.planning_mode,required=group.required,auto_confirm_additional_members=group.auto_additional_members,
            day_scope=group.day_scope,alternatives=alternatives)))
    return result


def prepare(db,uid,rid,key,intent,cid,role,stamp,*,seed=None,include_session_display=False,beta_config=None):
    if intent not in ('open','reopen') or (cid is None)!=(role is None):fail('INVALID_REQUEST',400)
    room,row,value=life.target_row(db,uid,rid,key,stamp,next_only=True,authorize_target=False)
    source,cm,owned,selected,public,source_proof,reason=life.source(db,uid,room,stamp)
    if commands.leadership(db,source)['leader_cycle_member_id']!=cm.id:reason=reason or 'TARGET_LEADER_REQUIRED'
    if cid is not None:
        try:selected=selection_context.selection(db,uid,cid,role)
        except GameError as error:reason=reason or error.code;selected=None
    if selected is None and cid is None:
        cid,role=owned[0].character_id,owned[0].selected_role
    else:cid,role=(selected.character_id,selected.selected_role) if selected else (cid,role)
    already=row is not None and row.state=='open'
    if already and group_policy.enabled(db):group_policy.authorize(db,room,row,uid)
    if row is not None and not already:
        generation=db.get(CycleGeneration,(row.id,row.generation))
        if generation.state!='cancelled':reason=reason or 'TARGET_CYCLE_CLOSED'
        elif intent!='reopen':reason=reason or 'TARGET_REOPEN_REQUIRED'
    elif intent=='reopen':reason=reason or 'TARGET_CONTEXT_STALE'
    rid_cycle=row.id if row else uuid.UUID(seed) if seed else uuid.uuid4()
    gen=row.generation if already else row.generation+1 if row else 1
    epoch=row.revision if already else row.revision+1 if row else 1
    if gen>2147483647 or epoch>2147483647:fail('REVISION_CONFLICT')
    settings=deepcopy(row.settings_snapshot if already else source.settings_snapshot)
    if not settings.get('items'):fail('ROOM_REVIEW_REQUIRED')
    # Prospective IDs are deterministic within this one opaque context seed.
    targets=[]
    proof=[]
    if not already:
        for item,rd in admission.rounds(db,source):
            state=db.get(life.WeeklyState,(uid,selected.character_id,item.raid_id,value.key)) if selected else None
            targets.append(Target(item_id=item.id,round_id=uuid.uuid5(rid_cycle,f'g{gen}:{item.id}'),party_no=1,
                expected_round_revision=1,expected_weekly_revision=state.revision if state else 1))
            proof.append([rd.id,rd.revision,rd.difficulty_id,rd.catalog_version])
    elif selected is not None:targets=commands.target_items(db,uid,row,selected)
    conflicts=[];comparison=None
    if selected is not None and not already:
        minimum=settings['combat_requirement']['dealer_min' if selected.selected_role=='dealer' else 'support_min']
        comparison=admission.core.power_comparison(db,uid,selected,minimum)
        if comparison['state'] in ('below','missing'):reason=reason or 'COMBAT_POWER_REQUIRED'
        for item,rd in admission.rounds(db,source):
            state=db.get(life.WeeklyState,(uid,selected.character_id,item.raid_id,value.key))
            try:
                admission.core.weekly.require_available_for_participation(db,uid,selected.character_id,item.raid_id,value.key)
                character=admission.core.identity.selected_character(db,uid,selected.model_dump(mode='json'))
                from decimal import Decimal,InvalidOperation
                try:level=Decimal(str(character.summary.get('item_level')))
                except (ValueError,InvalidOperation):level=None
                difficulty=admission.core.raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version)
                if not admission.core.raids.meets_item_level(level,difficulty):fail('RAID_ITEM_LEVEL_REQUIRED')
            except admission.core.raids.CatalogSelectionError as error:reason=reason or error.code
            except GameError as error:reason=reason or ('TARGET_CHARACTER_CONFLICT' if error.code=='WEEKLY_ALREADY_PARTICIPATING' else error.code)
            if state and state.active_party_id:
                other=db.get(commands.Room,state.active_party_id)
                visible=other is not None and db.scalar(select(life.Member.id).where(life.Member.room_id==other.id,
                    life.Member.user_id==uid,life.Member.ended_at.is_(None))) is not None
                conflicts.append(dict(room_id=state.active_party_id,target_cycle_key=value.key,raid_id=item.raid_id,
                    character_id=selected.character_id,can_view_detail=visible,room_title=other.title if visible else None))
    inputs=schedule_inputs(db,source) if not already else []
    data=dict(room_id=rid,source=public,selection=selected,targets=targets,target_session_ids=[],
        leadership=commands.leadership(db,row) if already else None,
        opening_effect='already_open' if already else 'reopen_and_join' if row else 'create_and_join',
        permission=permission(reason),conflicts=conflicts,prospective_room_cycle_id=rid_cycle,
        prospective_generation=gen,prospective_target_revision=epoch,
        item_settings=[dict(item_id=v['item_id'],difficulty_id=v['difficulty_id'],catalog_version=v['catalog_version'],
            duration_minutes=v['duration_minutes']) for v in settings['items']])
    if include_session_display:
        data["session_display"]=(display.none(uid,row,"opening") if already else
            display.preview(db,uid,source,key,rid_cycle,gen,settings,inputs))
    # A cancelled generation has deliberately no leader, but retains its epoch.
    if row and not already:
        old=db.get(CycleGeneration,(row.id,row.generation))
        data['leadership']=dict(leader_cycle_member_id=old.leader_cycle_member_id,leadership_revision=old.leadership_revision,
            leader_membership_id=None)
    if group_policy.enabled(db):
        inherited=group_policy.inherited(db,source,uid)
        data['group_policy_effect']=group_policy.effect(db,row) if already else group_policy.effect(db,source,inherited)
        data['group_policy_effect']['target_cycle_key']=value.key
        data['group_policy_effect']['room_cycle_id']=rid_cycle
        data['group_policy_effect']['generation']=gen
        source_proof.append(['group_policy',group_policy.state(group_policy.get(db,source)),inherited,
            group_policy.group_evidence(db,group_policy.get(db,source).group_id,uid)])
    hidden=[source_proof,room.revision,room.scope,selection_context.group_stamp(db,room.group_id,retained=True),settings,proof,
        comparison['power_revision'] if comparison else None,
        jsonable_encoder(inputs),[row.id,row.revision,row.generation,row.state] if row else None]
    if beta_profile.enabled():
        setting=beta_schedule.config(beta_config or beta_schedule.query_config(),key=key,
            capacity=settings['app_capacity'],duration=sum(v['duration_minutes'] for v in settings['items']),stamp=stamp)
        data['beta_schedule_config']=setting.model_dump(mode='json')
    value,binding=life.sign(uid,rid,key,'opening',jsonable_encoder(data),hidden,stamp,row=row,db=db,
        extra=dict(**display.marker(include_session_display),seed=str(rid_cycle),intent=intent,cid=str(cid),role=role))
    return value,binding,room,row,source,settings,inputs


def get(principal,rid,key,intent,cid=None,role=None,include_session_display=False):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        value,*_=prepare(db,uid,rid,key,intent,cid,role,stamp,include_session_display=include_session_display)
        return display.output(display_schemas.OpeningDisplayContext,value,include_session_display,snapshot=(db,uid,stamp))


def execute(principal,rid,command,data):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        token=life.verify_token(uid,rid,body,'opening',stamp)
        if body['intent']!=token['intent']:fail('TARGET_SCOPE_MISMATCH',400)
        result,binding,room,row,source,settings,inputs=prepare(db,uid,rid,body['target_cycle_key'],token['intent'],
            uuid.UUID(token['cid']),token['role'],stamp,seed=token['seed'],include_session_display=display.enabled(token),beta_config=body.get('beta_schedule'))
        expected=row.revision if row else None
        if body['expected_target_revision']!=expected:fail('TARGET_CONTEXT_STALE')
        life.require_match(token,binding)
        current=result['data']
        if not current['permission']['allowed']:
            error=GameError(current['permission']['reason'],403 if current['permission']['reason']=='TARGET_LEADER_REQUIRED' else 409)
            error.cycle_details=dict(conflicts=current['conflicts'],available_at=None,failed_cycle_key=body['target_cycle_key'])
            raise error
        if current['selection']!=body['selection'] or current['targets']!=body['target_items'] or body['target_session_ids']:
            fail('TARGET_SCOPE_MISMATCH',400)
        if current['opening_effect']=='already_open':return 200,life.ack(db,row,command,stamp,outcome='noop')
        policy_effect=current.get('group_policy_effect')
        gen=current['prospective_generation'];epoch=current['prospective_target_revision']
        if row is None:
            row=RoomCycle(id=uuid.UUID(current['prospective_room_cycle_id']),room_id=rid,
                cycle_key=life.cycles.target(stamp,body['target_cycle_key']).key,state='review_required',generation=gen,
                revision=1,settings_revision=1,members_revision=1,plan_revision=1,settings_snapshot=settings,
                provenance='explicit',created_at=stamp)
            db.add(row);db.flush()
        else:
            for link in db.scalars(select(CycleRound).where(CycleRound.cycle_id==row.id,CycleRound.is_current.is_(True))):link.is_current=False
            db.flush()
            row.generation=gen;row.state='review_required';row.settings_snapshot=settings
            row.settings_revision+=1
        generation=CycleGeneration(cycle_id=row.id,generation=gen,state='review_required',leadership_revision=1,next_join_order=1,opened_at=stamp)
        db.add(generation);db.flush()
        if group_policy.enabled(db):group_policy.install(db,row,policy_effect['after']['scope'],policy_effect['after']['group_id'])
        by_item={i.id:(i,r) for i,r in admission.rounds(db,source)}
        targets=[Target.model_validate(t) for t in body['target_items']]
        for target in targets:
            item,old=by_item[target.item_id]
            rd=Round(id=target.round_id,room_id=rid,item_id=item.id,cycle_key=row.cycle_key,
                difficulty_id=old.difficulty_id,catalog_version=old.catalog_version,game_party_size=old.game_party_size,
                revision=1,state='active',created_at=stamp)
            db.add(rd);db.flush()
            db.add(CycleRound(round_id=rd.id,room_id=rid,item_id=item.id,cycle_key=row.cycle_key,
                cycle_id=row.id,generation=gen,is_current=True))
            db.add(CycleOpening(id=uuid.uuid4(),room_id=rid,cycle_id=row.id,generation=gen,item_id=item.id,
                command_id=command,mode=body['intent'],state='applied',effective_at=stamp,
                evidence={'source_cycle':str(source.id),'search_floor_at':(stamp+life.timedelta(minutes=30)).isoformat()}))
        db.flush()
        member,_,_=admission.admit_bundle(db,uid,room,row,Selection.model_validate(body['selection']),targets,command,stamp,opening=True)
        if beta_profile.enabled():beta_schedule.install(db,room,row,body['beta_schedule'],member,stamp)
        else:schedule.install(db,room,row,inputs,member,stamp,copied=True)
        # Exactly one epoch for the entire opening, including its first bundle.
        row.revision=epoch
        if gen==1:row.members_revision=row.plan_revision=1
        db.flush()
        result=life.ack(db,row,command,stamp)
        if policy_effect:
            policy_effect['after']=group_policy.state(group_policy.get(db,row))
            result['group_policy_effects']=jsonable_encoder([policy_effect])
        return 200,result,lambda final:schedule.deadlines(db,row,[],final)
    return cycles.execute(principal,'open',command,dict(room_id=str(rid),body=body),run)
