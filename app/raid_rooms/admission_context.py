"""Read-only, actor-bound selection snapshots; opaque MAC, no client authority."""
import hashlib
import hmac
import json
import uuid
from decimal import Decimal,InvalidOperation
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.core.config import settings
from app.game_accounts.profiles import owned_character
from app.game_accounts.models import Registration, CharacterRoleSummary
from app.game_accounts.support import fail,GameError
from app.game_accounts.lifecycle import digest
from app.groups import admission_core as identity
from app.groups.models import Group, GroupMembership
from app.member_limits.models import MemberUsageLimits, MemberUsageHead
from app.raid_weekly.models import WeeklyState
from app.raid_rooms.participation_commands import Selection, Target
from app.raid_rooms import participation_core as core
from app.raid_rooms.integrated_models import RecruitmentItem as Item, RecruitmentRound as Round, RecruitmentMembership as Member
from app.raid_rooms.source_models import RoomSettings
from app.raids import service as raids


def token(value):
    raw=json.dumps(jsonable_encoder(value),sort_keys=True,separators=(',',':')).encode()
    return 's1.'+hmac.new(settings.recovery_key(),b'recruitment-selection-v1:'+raw,hashlib.sha256).hexdigest()


def verify(value, expected):
    if not hmac.compare_digest(value,expected):fail('SELECTION_CONTEXT_CHANGED')


def selection(db,uid,cid,role):
    account,character=owned_character(db,uid,cid)
    registration=db.scalar(select(Registration).where(Registration.user_id==uid,
        Registration.account_id==account.id,Registration.deleted_at.is_(None)))
    head=db.get(CharacterRoleSummary,(uid,cid,account.ownership_revision,role))
    limits,usage=db.get(MemberUsageLimits,uid),db.get(MemberUsageHead,uid)
    result=Selection(registration_id=registration.id,character_id=cid,selected_role=role,
        expected_registration_version=registration.version,expected_ownership_revision=account.ownership_revision,
        expected_roster_revision=account.roster_revision,expected_lifecycle_revision=character.lifecycle_revision,
        expected_role_summary_version=head.version if head else 1,
        expected_limits_revision=limits.revision if limits else 1,expected_usage_revision=usage.revision if usage else 1)
    identity.selected_character(db,uid,result.model_dump(mode='json'))
    return result


def group_stamp(db,gid,*,retained=False):
    if gid is None:return None
    group=db.get(Group,gid)
    if group is None or group.ended_at is not None:
        if retained:return [str(gid),group.revision if group else None,group.members_revision if group else None,'ended' if group else 'unavailable']
        fail('GROUP_NOT_FOUND',404)
    return [str(group.id),group.revision,group.members_revision]


def policy(db,room):
    rows=[]
    for uid in db.scalars(select(Member.user_id).where(Member.room_id==room.id,Member.ended_at.is_(None)).order_by(Member.user_id)):
        limit,usage=db.get(MemberUsageLimits,uid),db.get(MemberUsageHead,uid)
        rows.append([str(uid),limit.revision if limit else 1,usage.revision if usage else 1,
                     core.room_count(db,uid),core.limits.joined_group_count(db,uid)])
    settings=db.get(RoomSettings,room.id)
    return digest([str(room.id),room.revision,room.members_revision,room.plan_revision,
        settings.revision if settings else None,group_stamp(db,room.group_id,retained=True),rows])


def creation(db,uid,cid,role,items,gid,stamp):
    if not items or len(items)>len(raids.catalog().raids) or len({i.raid_id for i in items})!=len(items):
        fail('INVALID_REQUEST',400)
    cycle=raids.cycle(stamp)
    choice=selection(db,uid,cid,role)
    comparison=core.power_comparison(db,uid,choice,None)
    group=group_stamp(db,gid)
    if gid is not None and db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==gid,
            GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is None:
        fail('GROUP_MEMBERSHIP_REQUIRED',403)
    targets=[]
    reason=None
    character=identity.selected_character(db,uid,choice.model_dump(mode='json'))
    try:core._limits(db,uid,choice,True)
    except GameError as error:reason=error.code
    for item in items:
        try:difficulty=raids.difficulty(item.raid_id,item.difficulty_id,raids.catalog().catalog_version)
        except raids.CatalogSelectionError as error:fail(error.code)
        state=db.get(WeeklyState,(uid,cid,item.raid_id,core.weekly.parse_cycle(cycle.cycle_key)))
        try:
            core.weekly.require_available_for_participation(db,uid,cid,item.raid_id,core.weekly.parse_cycle(cycle.cycle_key))
            try:level=Decimal(str(character.summary.get('item_level')))
            except (InvalidOperation,ValueError):level=None
            if not raids.meets_item_level(level,difficulty):fail('RAID_ITEM_LEVEL_REQUIRED')
        except GameError as error:reason=reason or error.code
        targets.append(dict(raid_id=item.raid_id,difficulty_id=item.difficulty_id,
            expected_weekly_revision=state.revision if state else 1))
    binding=['create',str(uid),cycle.cycle_key,choice.model_dump(mode='json'),targets,group,
             comparison['power_revision'],core.room_count(db,uid),raids.catalog().catalog_version]
    return dict(expected_cycle_key=cycle.cycle_key,server_time=stamp,catalog_version=raids.catalog().catalog_version,
        policy_snapshot=digest(binding),context_token=token(binding),selection=choice,targets=targets,
        group_revision=group[1] if group else None,comparison=comparison,
        settings_defaults=dict(auto_open_default=False,experience_unrestricted_value=None,experience_levels=[dict(value=k,label=v) for k,v in
            [('tryLevel','트라이'),('clearExp','클경'),('multiClearExp','다클경'),('semiExperienced','반숙'),('experienced','숙련')]]),
        permissions=dict(create=dict(allowed=reason is None,reason=reason)))


def admission(db,uid,room,cid,role,intent,stamp):
    choice=selection(db,uid,cid,role)
    cycle=raids.cycle(stamp)
    targets=[]
    for item,round in db.execute(select(Item,Round).join(Round,Round.item_id==Item.id).where(
            Item.room_id==room.id,Round.state=='active',Round.ended_at.is_(None),Round.cycle_key==core.weekly.parse_cycle(cycle.cycle_key)).order_by(Item.id)):
        state=db.get(WeeklyState,(uid,cid,item.raid_id,round.cycle_key))
        targets.append(Target(item_id=item.id,round_id=round.id,party_no=1,
            expected_round_revision=round.revision,expected_weekly_revision=state.revision if state else 1))
    settings=db.get(RoomSettings,room.id)
    if settings is None:fail('SERVICE_UNAVAILABLE',503)
    minimum=settings.dealer_min if role=='dealer' else settings.support_min
    comparison=core.power_comparison(db,uid,choice,minimum)
    snapshot=policy(db,room)
    allowed=intent=='change_character' or settings.admission_mode==('leader_only' if intent=='apply' else 'direct_join')
    reason=None if allowed else 'ADMISSION_MODE_CHANGED'
    if allowed and intent!='change_character':
        try:core.admit_bundle(db,uid,room,choice,targets,cycle.cycle_key,validate_only=True,pending=intent=='apply')
        except GameError as error:
            reason=error.code
            if room.app_capacity==8 and reason in ('ROOM_FULL','ROOM_COMPOSITION_CONFLICT'):
                alternate=[t.model_copy(update={'party_no':2}) for t in targets]
                try:
                    core.admit_bundle(db,uid,room,choice,alternate,cycle.cycle_key,validate_only=True)
                    targets=alternate;reason=None
                except GameError:pass
    if intent=='change_character':
        own=db.scalar(select(Member).where(Member.room_id==room.id,Member.user_id==uid,Member.ended_at.is_(None)))
        if own is None:fail('ROOM_MEMBERSHIP_REQUIRED',403)
    from app.raid_rooms import scheduling
    session_choices=[]
    for session in scheduling.sessions(db,room.id,stamp):
        binding_row=db.get(scheduling.SessionBinding,session.id)
        deadline=session.starts_at-scheduling.timedelta(minutes=30) if session.state=='confirmed' else None
        closed=deadline is not None and stamp>=deadline
        session_choices.append(dict(session_id=session.id,required=binding_row.required,join_deadline=deadline,
            permission=dict(allowed=not closed,reason='RECRUITMENT_CLOSED' if closed else None)))
        if closed and binding_row.required and intent!='change_character':reason=reason or 'RECRUITMENT_CLOSED'
    binding=[intent,str(uid),str(room.id),cycle.cycle_key,room.revision,room.members_revision,room.plan_revision,
        snapshot,choice.model_dump(mode='json'),[t.model_dump(mode='json') for t in targets],comparison['power_revision'],jsonable_encoder(session_choices)]
    return dict(room_id=room.id,room_revision=room.revision,members_revision=room.members_revision,plan_revision=room.plan_revision,
        expected_cycle_key=cycle.cycle_key,server_time=stamp,catalog_version=raids.catalog().catalog_version,
        policy_snapshot=snapshot,context_token=token(binding),selection=choice,targets=targets,session_choices=session_choices,
        comparison=comparison,permissions={intent:dict(allowed=reason is None,reason=reason)})
