"""Candidate F2 read DTOs. Not mounted in the development application."""
from datetime import datetime, date
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool
from app.game_accounts.schemas import DTO, Version
from app.game_accounts.profile_schemas import RoleSummary, Role
from app.groups.schemas import CharacterDisplay, Permission
from app.raid_rooms.commands import Schedule, Selection

Count = Annotated[int, Field(strict=True, ge=0)]
Party = Annotated[int, Field(strict=True, ge=1, le=2)]
Phase = Literal['current', 'cycle_closed', 'ended']


class RoomSummary(DTO):
    room_id: UUID
    revision: Version
    round_id: UUID
    round_revision: Version
    members_revision: Version
    title: str
    state: Literal['active', 'ended']
    phase: Phase
    scope: Literal['public', 'group']
    group_id: UUID | None
    raid_id: str
    difficulty_id: str
    catalog_version: str
    cycle_key: date
    admission_mode: Literal['leader_only', 'direct_join']
    schedule: Schedule
    party_count: Party
    member_count: Annotated[int, Field(strict=True, ge=0, le=8)]
    support_count: Annotated[int, Field(strict=True, ge=0, le=2)]
    leader_display: CharacterDisplay | None
    restricted: StrictBool
    created_at: datetime


class RoomPage(DTO):
    items: list[RoomSummary]
    directory_revision: Version
    next_cursor: str | None


class BuildDisplay(DTO):
    role: Role
    version: Version
    summary: RoleSummary | None
    saved_at: datetime | None
    stale: StrictBool


class RoomMember(DTO):
    membership_id: UUID
    revision: Version
    party_no: Party
    slot_no: Annotated[int, Field(strict=True, ge=1, le=4)]
    room_role: Literal['leader', 'member']
    selected_role: Role
    character_id: UUID
    display: CharacterDisplay
    joined_at: datetime
    status: Literal['valid', 'needs_review']
    status_reason: str | None
    build: BuildDisplay
    is_me: StrictBool


class MemberRef(DTO):
    membership_id: UUID
    display: CharacterDisplay | None


class RoomLimitIssue(DTO):
    code: str
    dimension: Literal['raid_rooms', 'joined_groups', 'group_capacity']
    used: Count
    limit: Count
    member_ref: MemberRef | None
    origin_group_id: UUID | None


class RoomAccess(DTO):
    state: Literal['normal', 'restricted']
    policy_snapshot: str
    evaluated_at: datetime
    issues: list[RoomLimitIssue]


class Permissions(DTO):
    apply: Permission
    join: Permission
    approve: Permission
    reject: Permission
    leave: Permission
    transfer_leadership: Permission
    end: Permission
    complete: Permission
    change_character: Permission
    move_slot: Permission
    repeat: Permission
    change_scope: Permission


class RoomDetail(DTO):
    room: RoomSummary
    members: Annotated[list[RoomMember], Field(max_length=8)]
    my_membership_id: UUID
    access: RoomAccess
    permissions: Permissions


class MembershipRecord(DTO):
    room_id: UUID
    round_id: UUID
    membership_id: UUID
    revision: Version
    character_id: UUID
    selected_role: Role
    party_no: Party
    joined_at: datetime
    ended_at: datetime | None
    end_reason: Literal['left', 'room_ended'] | None
    relation: Literal['current', 'ended']
    round_cycle_key: date
    round_phase: Phase
    access_state: Literal['full', 'recovery_only', 'history_only']
    group_id: UUID | None


class MembershipPage(DTO):
    items: list[MembershipRecord]
    membership_head: Version
    next_cursor: str | None


class ApplicationPermissions(DTO):
    approve: Permission
    reject: Permission
    withdraw: Permission


class Application(DTO):
    application_id: UUID
    room_id: UUID
    revision: Version
    state: Literal['pending', 'accepted', 'rejected', 'withdrawn', 'expired', 'cancelled']
    created_at: datetime
    expires_at: datetime
    ended_at: datetime | None
    display: CharacterDisplay
    character_id: UUID
    party_no: Party
    selected_role: Role
    build: BuildDisplay
    permissions: ApplicationPermissions


class ApplicationPage(DTO):
    items: list[Application]
    applications_revision: Version
    next_cursor: str | None


class MyMembership(DTO):
    membership_id: UUID
    revision: Version
    room_role: Literal['leader', 'member']


class TransferCandidate(DTO):
    membership_id: UUID
    revision: Version
    display: CharacterDisplay | None


class ManagementPermissions(DTO):
    leave: Permission
    transfer_leadership: Permission
    end: Permission


class RoomManagement(DTO):
    room_id: UUID
    revision: Version
    members_revision: Version
    my_membership: MyMembership
    round_id: UUID
    round_revision: Version
    round_phase: Phase
    transfer_candidates: list[TransferCandidate]
    permissions: ManagementPermissions


class AdmissionContext(DTO):
    room_id: UUID
    round_id: UUID
    room_revision: Version
    round_revision: Version
    members_revision: Version
    policy_snapshot: str
    catalog_version: str
    cycle_key: date
    selection: Selection
    eligibility: Permission
    evaluated_at: datetime
