"""Actor-bound creation preflight and atomic C/N command; staged until cutover."""
from app.raid_rooms import beta_profile, beta_schedule, beta_output
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.support import fail, GameError
from app.game_accounts.lifecycle import digest
from app.groups.models import GroupMembership
from app.raid_weekly.models import WeeklyState
from app.raid_rooms import (cycles, cycle_admission as admission, cycle_schedule as schedule,
    admission_context as context, admission_service as base, command_context as opaque)
from app.raid_rooms import cycle_wire as wire
from app.raid_rooms.participation_commands import Selection, Target
from app.raid_rooms.integrated_models import (RecruitmentRoom as Room, RecruitmentMembership as Member,
    RecruitmentItem as Item, RecruitmentRound as Round)
from app.raid_rooms.source_models import RoomSettings, ItemSettings
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleRound, CycleOpening
from app.raids import service as raids


def permission(reason=None, next_change=None):
    return dict(allowed=reason is None, reason=reason, next_change_at=next_change)


def scope(stamp, key, target=None):
    value = cycles.target(stamp, key)
    return dict(server_now=stamp, current_cycle_key=value.current, target_cycle_key=value.key,
        playable_from=value.playable_from, phase=value.phase, target_revision=target.revision if target else None,
        policy_version=cycles.POLICY, room_cycle_id=target.id if target else None,
        target_generation=target.generation if target else None)


def creation_id(room_id, kind, name):
    return uuid.uuid5(room_id, kind + ':' + name)


def preflight(db, uid, cid, role, items, gid, key, continuation, next_cid, next_role, stamp, *, room_id=None, beta_targets=None):
    target = cycles.target(stamp, key)
    if not items or len(items) > len(raids.catalog().raids) or len({i.raid_id for i in items}) != len(items):
        fail('INVALID_REQUEST', 400)
    if (next_cid is None) != (next_role is None):
        fail('INVALID_REQUEST', 400)
    combined = continuation and target.phase == 'current'
    if next_cid is not None and not combined:
        fail('INVALID_REQUEST', 400)
    effect = 'target_is_next' if target.phase == 'future' and continuation else 'target_and_next' if combined else 'target_only'
    room_id = room_id or uuid.uuid4()
    choice = context.selection(db, uid, cid, role)
    group = context.group_stamp(db, gid)
    if gid is not None and db.scalar(select(GroupMembership.id).where(GroupMembership.group_id == gid,
            GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None))) is None:
        fail('GROUP_MEMBERSHIP_REQUIRED', 403)
    admission.core._group(db, SimpleNamespace(scope='group' if gid else 'public', group_id=gid), uid)
    initial_reason = None
    try:
        admission.core._limits(db, uid, choice, True)
    except GameError as error:
        initial_reason = error.code

    def prospective(key, selection):
        character = admission.core.identity.selected_character(db, uid, selection.model_dump(mode='json'))
        reason, targets, conflicts = initial_reason, [], []
        for item in items:
            try:
                difficulty = raids.difficulty(item.raid_id, item.difficulty_id, raids.catalog().catalog_version)
            except raids.CatalogSelectionError as error:
                fail(error.code)
            state = db.get(WeeklyState, (uid, selection.character_id, item.raid_id, key))
            try:
                admission.core.weekly.require_available_for_participation(db, uid, selection.character_id, item.raid_id, key)
                try:
                    level = Decimal(str(character.summary.get('item_level')))
                except (InvalidOperation, ValueError):
                    level = None
                if not raids.meets_item_level(level, difficulty):
                    fail('RAID_ITEM_LEVEL_REQUIRED')
            except GameError as error:
                reason = reason or error.code
            if state is not None and state.active_party_id is not None:
                # Detail visibility is stronger than a publicly visible card.
                other = db.get(Room, state.active_party_id)
                visible = other is not None and db.scalar(select(Member.id).where(Member.room_id == other.id,
                    Member.user_id == uid, Member.ended_at.is_(None))) is not None
                conflicts.append(dict(room_id=state.active_party_id, target_cycle_key=key, raid_id=item.raid_id,
                    character_id=selection.character_id, can_view_detail=visible,
                    room_title=other.title if visible else None))
            iid = creation_id(room_id, 'item', item.raid_id)
            targets.append(dict(item_id=iid, round_id=creation_id(room_id, 'round', key.isoformat()+':'+item.raid_id),
                raid_id=item.raid_id, difficulty_id=item.difficulty_id, party_no=1,
                expected_round_revision=1, expected_weekly_revision=state.revision if state else 1))
        return dict(target_cycle_key=key, room_cycle_id=creation_id(room_id, 'cycle', key.isoformat()),
            generation=1, initial_target_revision=1, selection=selection, targets=targets,
            permission=permission(reason), conflicts=conflicts)

    first = prospective(target.key, choice)
    second_choice = context.selection(db, uid, next_cid, next_role) if next_cid is not None else choice
    second = prospective(target.key+timedelta(days=7), second_choice) if combined else None
    power = admission.core.power_comparison(db, uid, choice, None)
    reason = first['permission']['reason'] or (second['permission']['reason'] if second else None)
    stable = jsonable_encoder(dict(actor=uid, prospective_room_id=room_id, current=target.current, target=target.key,
        continuation=continuation, first=first, second=second, group=group,
        catalog=raids.catalog().catalog_version, power_revision=power['power_revision'],
        room_count=admission.core.room_count(db, uid)))
    if beta_profile.enabled():
        from app.raid_rooms.beta_schemas import BetaScheduleTarget
        expected=[target.key]+([target.key+timedelta(days=7)] if combined else [])
        if beta_targets is None:
            if not combined and any(k.startswith('next_') and k in ('next_base_starts_at','next_early_coordination_enabled','next_early_additional_members') for k in beta_profile.query()):
                fail('INVALID_REQUEST',400)
            beta_targets=[dict(target_cycle_key=k.isoformat(),**beta_schedule.query_config('' if index==0 else 'next_').model_dump(mode='json')) for index,k in enumerate(expected)]
        if len(beta_targets)!=len(expected) or {v['target_cycle_key'] for v in beta_targets}!={k.isoformat() for k in expected}:fail('INVALID_REQUEST',400)
        size=next(r.party_size for r in raids.catalog().raids if r.raid_id==items[0].raid_id) if len(items)==1 else 4
        duration=sum(base.DEFAULT_DURATION.get(v.difficulty_id,0) for v in items)
        if not duration:fail('DURATION_POLICY_UNAVAILABLE')
        for value in beta_targets:
            beta_schedule.config({k:v for k,v in value.items() if k!='target_cycle_key'},key=value['target_cycle_key'],capacity=size,duration=duration,stamp=stamp)
        stable['beta']=[beta_targets,beta_schedule.context_basis(db,uid)]
    snapshot = digest(stable)
    expires = min(stamp+timedelta(seconds=opaque.LIFETIME_SECONDS), raids.cycle(stamp).ends_at)
    token = opaque.seal(dict(actor=str(uid), command='create-v2', room=str(room_id), target=key,
        continuation=continuation, next_cid=str(next_cid) if next_cid else None, next_role=next_role,
        expires=expires.isoformat(), digest=snapshot, **beta_profile.marker()))
    data = dict(expected_cycle_key=target.current.isoformat(), server_time=stamp,
        catalog_version=raids.catalog().catalog_version, policy_snapshot=snapshot, context_token=token,
        selection=choice, targets=[{k:t[k] for k in ('raid_id', 'difficulty_id', 'expected_weekly_revision')}
            for t in first['targets']], group_revision=group[1] if group else None,
        settings_defaults=dict(opening_mode='explicit', experience_unrestricted_value=None,
            experience_levels=[dict(value=k, label=v) for k,v in [('tryLevel','트라이'),('clearExp','클경'),
                ('multiClearExp','다클경'),('semiExperienced','반숙'),('experienced','숙련')]]),
        comparison=power, permissions=dict(create=permission(reason)), target_cycle_key=key,
        expected_target_revision=None, issued_at=stamp, expires_at=expires, prospective_room_id=room_id,
        target_creation=first, next_cycle_creation=second, continuation_effect=effect)
    if beta_profile.enabled():data['beta_schedule_targets']=beta_targets
    return dict(scope=scope(stamp,key), data=data)


def get(principal, cid, role, items, gid, key, continuation=False, next_cid=None, next_role=None):
    with base.snapshot(principal) as (db, uid, stamp):
        return beta_output.render(db,uid,stamp,wire.OutputContract3GetV2MeRaidRoomCreationContext,jsonable_encoder(preflight(db,uid,cid,role,items,gid,key,continuation,next_cid,next_role,stamp)))


def create(principal, command_id, data):
    body = beta_profile.body(data)
    failure = dict(conflicts=[],available_at=None,failed_cycle_key=body['target_cycle_key'])
    def run(db, uid, stamp):
        key = body['target_cycle_key']
        value = cycles.target(stamp, key)
        if body['expected_cycle_key'] != value.current.isoformat():
            fail('CYCLE_CHANGED')
        if body['expected_target_revision'] is not None:
            fail('TARGET_CONTEXT_STALE')
        token = opaque.unseal(body['selection_context']['context_token'])
        beta_profile.check_marker(token)
        if token.get('actor') != str(uid) or token.get('command') != 'create-v2' or token.get('target') != key:
            fail('CONTEXT_INVALID', 400)
        if stamp >= datetime.fromisoformat(token['expires']):
            fail('CONTEXT_EXPIRED')
        if token['continuation'] != body['continuation']['enabled']:
            fail('SELECTION_CONTEXT_CHANGED')
        if db.get(Room,uuid.UUID(token['room'])) is not None:
            fail('CONTEXT_ALREADY_USED')
        current = preflight(db, uid, data.selection.character_id, data.selection.selected_role,
            data.items, data.group_id, key, token['continuation'],
            uuid.UUID(token['next_cid']) if token['next_cid'] else None, token['next_role'], stamp,
            room_id=uuid.UUID(token['room']),beta_targets=body.get('beta_schedule_targets'))['data']
        if current['permissions']['create']['reason']:
            denied=current['target_creation'] if not current['target_creation']['permission']['allowed'] else current['next_cycle_creation']
            failure.update(failed_cycle_key=denied['target_cycle_key'].isoformat(),conflicts=denied['conflicts'])
        if token['digest'] != current['policy_snapshot']:
            fail('SELECTION_CONTEXT_CHANGED')
        if body['selection'] != jsonable_encoder(current['selection']):
            fail('REVISION_CONFLICT')
        second = current['next_cycle_creation']
        expected_next = jsonable_encoder(second['selection']) if second else None
        if body['continuation']['next_selection'] != expected_next:
            fail('SELECTION_CONTEXT_CHANGED')
        if body['expected_catalog_version'] != current['catalog_version']:
            fail('CATALOG_VERSION_CONFLICT')
        if body['expected_group_revision'] != current['group_revision']:
            fail('REVISION_CONFLICT')
        if any(a.expected_weekly_revision != b['expected_weekly_revision'] for a,b in zip(data.items,current['targets'])):
            fail('REVISION_CONFLICT')
        if current['permissions']['create']['reason']:
            denied=current['target_creation'] if not current['target_creation']['permission']['allowed'] else second
            failure.update(failed_cycle_key=denied['target_cycle_key'].isoformat(),conflicts=denied['conflicts'])
            fail(current['permissions']['create']['reason'])
        if not body['title'].strip() or (body['scope']=='group' and data.group_id is None):
            fail('INVALID_REQUEST',400)
        if body['app_mode'] != ('single' if len(data.items)==1 else 'mixed_bundle'):
            fail('INVALID_REQUEST',400)
        combat=body['combat_requirement']
        if combat['input_mode']=='shared' and combat['dealer_min']!=combat['support_min']:
            fail('INVALID_REQUEST',400)
        rid, mid = current['prospective_room_id'], uuid.uuid4()
        if db.get(Room,rid) is not None:
            fail('CONTEXT_ALREADY_USED')
        size = next(r.party_size for r in raids.catalog().raids if r.raid_id==data.items[0].raid_id) if len(data.items)==1 else 4
        admission.core._limits(db, uid, current['selection'], True)
        room=Room(id=rid,leader_membership_id=mid,title=body['title'],scope=body['scope'],group_id=data.group_id,
            app_capacity=size,revision=1,members_revision=1,plan_revision=1,migration_state='ready',created_at=stamp)
        db.add(room)
        db.flush()
        db.add(Member(id=mid,room_id=rid,user_id=uid,revision=1,joined_at=stamp))
        db.add(RoomSettings(room_id=rid,revision=1,continuation_revision=1,admission_mode=body['admission_mode'],
            experience_level=body['experience_level'],combat_input_mode=combat['input_mode'],
            dealer_min=combat['dealer_min'],support_min=combat['support_min'],
            continuation_enabled=body['continuation']['enabled'],auto_open_enabled=False))
        for choice, prospective in zip(data.items,current['target_creation']['targets']):
            if choice.party_no>size//4:
                fail('ROOM_COMPOSITION_CONFLICT')
            if choice.duration_minutes is None and choice.difficulty_id not in base.DEFAULT_DURATION:
                fail('DURATION_POLICY_UNAVAILABLE')
            item=Item(id=prospective['item_id'],room_id=rid,raid_id=choice.raid_id,revision=1,created_at=stamp)
            db.add(item)
            db.flush()
            db.add(ItemSettings(item_id=item.id,room_id=rid,revision=1,difficulty_id=choice.difficulty_id,
                catalog_version=current['catalog_version'],duration_minutes=choice.duration_minutes,
                duration_policy_version=base.DURATION_POLICY))
        db.flush()
        admission.core.legacy.touch_user(db,uid)
        # The initial room unit was already checked before inserting its member.
        # Fresh selection stamps keep the internal target validator's usage CAS.
        admitted=[]
        for prospective in [current['target_creation']]+([second] if second else []):
            target_key=prospective['target_cycle_key']
            failure['failed_cycle_key']=target_key.isoformat()
            settings=dict(app_capacity=size, admission_mode=body['admission_mode'],
                experience_level=body['experience_level'],combat_requirement=combat,
                continuation_enabled=body['continuation']['enabled'],items=[dict(
                    item_id=str(source['item_id']),raid_id=choice.raid_id,difficulty_id=choice.difficulty_id,
                    catalog_version=current['catalog_version'],item_settings_revision=1,
                    duration_minutes=choice.duration_minutes or base.DEFAULT_DURATION[choice.difficulty_id],
                    duration_source='explicit' if choice.duration_minutes is not None else 'difficulty_default',
                    duration_policy_version=base.DURATION_POLICY)
                    for source,choice in zip(prospective['targets'],data.items)])
            row=RoomCycle(id=prospective['room_cycle_id'],room_id=rid,cycle_key=target_key,state='review_required',
                generation=1,revision=1,settings_revision=1,members_revision=1,plan_revision=1,
                settings_snapshot=settings,provenance='explicit',created_at=stamp)
            db.add(row)
            db.flush()
            generation=CycleGeneration(cycle_id=row.id,generation=1,state='review_required',
                leadership_revision=1,next_join_order=1,opened_at=stamp)
            db.add(generation)
            db.flush()
            targets=[]
            for source, choice in zip(prospective['targets'],data.items):
                rd=Round(id=source['round_id'],room_id=rid,item_id=source['item_id'],cycle_key=target_key,
                    difficulty_id=source['difficulty_id'],catalog_version=current['catalog_version'],
                    game_party_size=next(r.party_size for r in raids.catalog().raids if r.raid_id==source['raid_id']),
                    revision=1,state='active',created_at=stamp)
                db.add(rd)
                db.flush()
                db.add(CycleRound(round_id=rd.id,room_id=rid,item_id=rd.item_id,cycle_key=target_key,
                    cycle_id=row.id,generation=1,is_current=True))
                db.add(CycleOpening(id=uuid.uuid4(),room_id=rid,cycle_id=row.id,generation=1,item_id=rd.item_id,
                    command_id=command_id,mode='open',state='applied',effective_at=stamp,
                    evidence={'source':'creation','search_floor_at':(stamp+timedelta(minutes=30)).isoformat()}))
                targets.append(Target(item_id=rd.item_id,round_id=rd.id,party_no=choice.party_no,
                    expected_round_revision=1,expected_weekly_revision=source['expected_weekly_revision']))
            db.flush()
            saved_selection=prospective['selection']
            selection=context.selection(db,uid,saved_selection.character_id,saved_selection.selected_role)
            member, assignments,_=admission.admit_bundle(db,uid,room,row,selection,targets,command_id,stamp,opening=True)
            if beta_profile.enabled():
                cfg=next(v for v in body['beta_schedule_targets'] if v['target_cycle_key']==target_key.isoformat())
                beta_schedule.install(db,room,row,{k:v for k,v in cfg.items() if k!='target_cycle_key'},member,stamp)
            else:schedule.install(db,room,row,data.schedule_groups,member,stamp,copied=target_key!=value.current)
            row.revision=row.members_revision=row.plan_revision=1
            admitted.append(dict(target_cycle_key=target_key,room_cycle_id=row.id,generation=1,target_revision=1,
                leader_cycle_member_id=generation.leader_cycle_member_id))
        db.flush()
        result=dict(scope=scope(stamp,key,db.get(RoomCycle,current['target_creation']['room_cycle_id'])),data=dict(
            command_id=command_id,outcome='applied',executed_at=stamp,room_id=rid,target_cycle_key=key,
            revisions=[dict(resource='room',id=rid,revision=1),dict(resource='membership',id=mid,revision=1)],
            created_cycles=admitted,continuation_effect=current['continuation_effect']))
        result=wire.CreateAck.model_validate(result).model_dump(mode='json')
        def final(final_stamp):
            for item in admitted:
                row=db.get(RoomCycle,item['room_cycle_id'])
                failure['failed_cycle_key']=row.cycle_key.isoformat()
                try:schedule.deadlines(db,row,[],final_stamp)
                except GameError as error:
                    error.cycle_details=jsonable_encoder(failure)
                    raise
        return 201,result,final
    def checked(db,uid,stamp):
        try:return run(db,uid,stamp)
        except GameError as error:
            error.cycle_details=jsonable_encoder(failure)
            raise
    return cycles.execute(principal,'create',command_id,body,checked)
