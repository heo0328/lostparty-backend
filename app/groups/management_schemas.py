from datetime import datetime, date
from typing import Literal
from uuid import UUID
from app.game_accounts.schemas import DTO, Version
from app.groups.commands import LeaveGroup
from app.groups.admission_schemas import CharacterSelection
from app.groups.schemas import MyMembership, Permission, GroupRepresentative, CharacterDisplay
from app.member_limits.schemas import Nonnegative


class DisbandGroupIn(LeaveGroup):
    pass


class RemoveGroupMemberIn(LeaveGroup):
    expected_target_membership_revision: Version


class ChangeGroupRepresentativeIn(LeaveGroup, CharacterSelection):
    pass


class GroupDisbandAck(DTO):
    group_id: UUID
    membership_id: UUID
    membership_revision: Version
    group_revision: Version
    members_revision: Version
    ended_at: datetime


class GroupRemoveAck(GroupDisbandAck):
    pass


class GroupRepresentativeAck(DTO):
    group_id: UUID
    group_revision: Version
    character_id: UUID
    representative: GroupRepresentative
    changed_at: datetime | None
    outcome: Literal['applied', 'noop']


class GroupRaidTarget(DTO):
    room_cycle_id: UUID
    target_cycle_key: date
    generation: Version | None
    target_revision: Version
    state: str
    leader_display: CharacterDisplay | None
    detail_available: bool


class GroupRaidRoom(DTO):
    room_id: UUID
    title: str
    scope: Literal['group']
    group_id: UUID
    room_revision: Version
    state: Literal['active', 'review_required']
    reason: str | None
    targets: list[GroupRaidTarget]


class GroupRaidRoomPage(DTO):
    group_id: UUID
    group_revision: Version
    members_revision: Version
    evaluated_at: datetime
    evidence_revision: str
    state: Literal['clear', 'blocked', 'unavailable']
    blocking_room_count: Nonnegative | None
    items: list[GroupRaidRoom]
    next_cursor: str | None


class ExtendedManagementPermissions(DTO):
    transfer_leadership: Permission
    leave: Permission
    disband: Permission
    remove_member: Permission
    change_representative: Permission


class ExtendedGroupManagement(DTO):
    profile: Literal['group-management-1']
    group_id: UUID
    group_revision: Version
    members_revision: Version
    my_membership: MyMembership
    permissions: ExtendedManagementPermissions
    recruitment_state: Literal['clear', 'blocked', 'unavailable']
    blocking_room_count: Nonnegative | None
    evidence_revision: str
