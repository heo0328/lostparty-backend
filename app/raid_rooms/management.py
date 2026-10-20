"""Room management mutates current resources without rewriting completed history."""
import uuid
from typing import Literal,Annotated
from pydantic import Field
from sqlalchemy import select
from app.game_accounts.support import fail
from app.groups.models import Group,GroupMembership
from app.raid_rooms import admission_service as base,scheduling as graph,completion
from app.raid_rooms.admission_schemas import DTO,Version,Experience,Combat
from app.raid_rooms.source_models import RoomSettings
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment


class RoomSettingsIn(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_settings_revision: Version
    experience_level: Experience|None
    combat_requirement: Combat
    admission_mode: Literal['direct_join','leader_only']


class Visibility(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_members_revision: Version
    expected_settings_revision: Version
    expected_group_revision: Version|None
    scope: Literal['public','group']
    group_id: uuid.UUID|None


class Placement(DTO):
    membership_id: uuid.UUID
    expected_revision: Version
    item_id: uuid.UUID
    party_no: Annotated[Version,Field(le=2)]
    slot_no: Annotated[Version,Field(le=4)]


class Formation(DTO):
    expected_cycle_key: str
    expected_members_revision: Version
    expected_plan_revision: Version
    placements: list[Placement]


class Removal(completion.MembershipCommand):
    target_membership_id: uuid.UUID
    expected_target_revision: Version


def settings_view(db,room,actor):
    value=db.get(RoomSettings,room.id);leader=actor.id==room.leader_membership_id
    return dict(room_id=room.id,revision=value.revision,room_revision=room.revision,experience_level=value.experience_level,
        combat_requirement=dict(input_mode=value.combat_input_mode,dealer_min=value.dealer_min,support_min=value.support_min),
        continuation=dict(enabled=value.continuation_enabled,auto_open_enabled=value.auto_open_enabled,revision=value.continuation_revision,
            auto_open_effective_cycle=value.auto_open_effective_cycle),scope=room.scope,group_id=room.group_id,admission_mode=value.admission_mode,
        permissions={name:dict(allowed=leader,reason=None if leader else 'ROOM_LEADER_REQUIRED') for name in ('edit_settings','edit_continuation','change_visibility')})


def get_settings(principal,rid):
    with base.snapshot(principal) as (db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room)
        return settings_view(db,room,actor)


def command(principal,rid,key,data,operation):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room,leader=True);base.unscheduled(db,room)
        value=db.get(RoomSettings,rid)
        if data.expected_cycle_key!=graph.raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        for attr,actual in [('expected_room_revision',room.revision),('expected_members_revision',room.members_revision),('expected_plan_revision',room.plan_revision),('expected_settings_revision',value.revision)]:
            if hasattr(data,attr) and getattr(data,attr)!=actual:fail('REVISION_CONFLICT')
        if operation=='settings':
            value.experience_level=data.experience_level;value.combat_input_mode=data.combat_requirement.input_mode
            value.dealer_min=data.combat_requirement.dealer_min;value.support_min=data.combat_requirement.support_min;value.admission_mode=data.admission_mode;value.revision+=1
        elif operation=='visibility':
            if data.group_id!=room.group_id:fail('GROUP_LINK_IMMUTABLE')
            if data.scope=='group' and room.group_id is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)
            if room.group_id is not None:
                group=db.get(Group,room.group_id)
                if group is None or group.ended_at is not None:fail('GROUP_NOT_ACTIVE')
                if data.expected_group_revision!=group.revision:fail('REVISION_CONFLICT')
                if db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==group.id,GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)
            elif data.expected_group_revision is not None:fail('INVALID_REQUEST',400)
            room.scope=data.scope;value.revision+=1
        elif operation=='remove':
            if actor.revision!=data.expected_membership_revision:fail('REVISION_CONFLICT')
            target=db.get(graph.Member,data.target_membership_id)
            if target is None or target.room_id!=rid or target.ended_at is not None:fail('ROOM_MEMBER_NOT_FOUND',404)
            if target.id in (actor.id,room.leader_membership_id):fail('ROOM_REMOVAL_TARGET_INVALID')
            if target.revision!=data.expected_target_revision:fail('REVISION_CONFLICT')
            completion.drop_membership(db,room,target,stamp)
        elif operation=='formation':
            current=list(db.scalars(select(Assignment).join(graph.Round,graph.Round.id==Assignment.round_id).where(
                Assignment.room_id==rid,Assignment.state=='active',graph.Round.state=='active',graph.Round.cycle_key==graph.date.fromisoformat(data.expected_cycle_key))))
            by={(a.membership_id,a.item_id):a for a in current}
            if len(by)!=len(current) or len({(p.membership_id,p.item_id) for p in data.placements})!=len(data.placements) or {(p.membership_id,p.item_id) for p in data.placements}!=set(by):fail('ROOM_ITEMS_CHANGED')
            final={}
            for p in data.placements:
                a=by[p.membership_id,p.item_id];member=db.get(graph.Member,a.membership_id);rd=db.get(graph.Round,a.round_id)
                if member.revision!=p.expected_revision:fail('REVISION_CONFLICT')
                if p.party_no>min(room.app_capacity//4,rd.game_party_size//4):fail('ROOM_COMPOSITION_CONFLICT')
                # Validate current ownership/lifecycle, retain original power comparison.
                from app.game_accounts.profiles import owned_character
                from app.game_accounts.lifecycle import require_usable
                account,character=owned_character(db,a.user_id,a.character_id);require_usable(db,character)
                if account.ownership_revision!=a.ownership_revision or character.lifecycle_revision!=a.lifecycle_revision:fail('REVISION_CONFLICT')
                group=final.setdefault((a.round_id,p.party_no),[])
                if any(other.slot_no==p.slot_no for other,_ in group):fail('ROOM_COMPOSITION_CONFLICT')
                group.append((p,a))
            for slots in final.values():
                dealers=[a for p,a in slots if a.selected_role=='dealer'];supports=[a for p,a in slots if a.selected_role=='support']
                if len(dealers)>3 or len(supports)>1 or len({a.display['class_name'] for a in dealers})!=len(dealers):fail('ROOM_COMPOSITION_CONFLICT')
            # Partial unique slot index is immediate. Inactive temporary state is
            # never committed and does not release exact weekly ownership.
            for a in current:a.state='left';a.ended_at=stamp
            db.flush()
            for p in data.placements:
                a=by[p.membership_id,p.item_id];a.party_no=p.party_no;a.slot_no=p.slot_no;a.state='active';a.ended_at=None;a.revision+=1
            room.members_revision+=1
        room.revision+=1;room.plan_revision+=1;base.core.legacy.directory(db);db.flush()
        return 200,dict(command_id=key,outcome='applied',executed_at=stamp,revisions=[base.revision('room',room),base.revision('plan',room,room.plan_revision),dict(resource='settings',id=rid,revision=value.revision)])
    return base.execute(principal,operation,key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)
