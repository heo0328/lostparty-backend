from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool
from app.game_accounts.schemas import DTO, Version
from app.groups.commands import CreateGroup, RenameGroup
from app.member_limits.schemas import Nonnegative


class GroupCreateIn(CreateGroup):
    expected_limits_revision: Version
    expected_usage_revision: Version


class GroupRenameIn(RenameGroup):
    pass


class CharacterDisplay(DTO):
    server_name: str
    character_name: str
    class_name: str | None


class GroupRepresentative(DTO):
    display: CharacterDisplay
    status: Literal['valid', 'needs_update']


class GroupSummary(DTO):
    group_id: UUID
    name: str
    revision: Version
    member_count: Annotated[int, Field(ge=1)]
    representative: GroupRepresentative
    leader_display: CharacterDisplay | None


class MyMembership(DTO):
    membership_id: UUID
    role: Literal['leader', 'member']
    revision: Version
    joined_at: datetime


class Permission(DTO):
    allowed: StrictBool
    reason: str | None


class Permissions(DTO):
    rename: Permission
    list_members: Permission


class GroupCapacity(DTO):
    limit: Nonnegative
    used: Nonnegative
    remaining: Nonnegative
    state: Literal['within', 'at_limit', 'exceeded']


class GroupDetail(DTO):
    group: GroupSummary
    created_at: datetime
    leader_membership_id: UUID
    members_revision: Version
    my_membership: MyMembership
    permissions: Permissions
    capacity: GroupCapacity


class GroupMember(DTO):
    membership_id: UUID
    role: Literal['leader', 'member']
    revision: Version
    display: CharacterDisplay | None
    joined_at: datetime
    is_me: StrictBool


class GroupSummaryPage(DTO):
    items: list[GroupSummary]
    directory_revision: Version
    next_cursor: str | None


class MyGroupPage(DTO):
    items: list[GroupDetail]
    directory_revision: Version
    next_cursor: str | None


class GroupMemberPage(DTO):
    group_id: UUID
    group_revision: Version
    members_revision: Version
    items: list[GroupMember]
    next_cursor: str | None
