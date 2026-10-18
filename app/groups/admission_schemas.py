from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import StrictBool
from app.game_accounts.schemas import DTO, Name, Version
from app.groups.schemas import CharacterDisplay, GroupSummary, Permission
from app.member_limits.schemas import Nonnegative


class CharacterSelection(DTO):
    registration_id: UUID
    character_id: UUID
    expected_registration_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_lifecycle_revision: Version


class ApplyIn(CharacterSelection):
    expected_group_revision: Version


class InviteIn(DTO):
    target_character_id: UUID
    expected_target_ownership_revision: Version
    expected_target_lifecycle_revision: Version
    expected_group_revision: Version
    expected_membership_revision: Version


class RelationAction(DTO):
    expected_relation_revision: Version
    expected_group_revision: Version
    expected_members_revision: Version


class RejectIn(RelationAction):
    block_future: StrictBool = False


class AcceptIn(CharacterSelection, RelationAction):
    expected_limits_revision: Version
    expected_usage_revision: Version


class BlockIn(DTO):
    expected_subject_revision: Version
    expected_group_revision: Version
    expected_membership_revision: Version


class CodeCommand(DTO):
    expected_group_revision: Version
    expected_membership_revision: Version
    expected_code_id: UUID | None
    expected_code_revision: Version


class CreateCodeIn(CodeCommand):
    visible_to_members: StrictBool = False


class CodeVisibilityIn(CodeCommand):
    visible_to_members: StrictBool


class CodeInput(DTO):
    code: Name


class CodeJoinIn(CharacterSelection, CodeInput):
    expected_group_revision: Version
    expected_members_revision: Version
    expected_code_id: UUID
    expected_code_revision: Version
    expected_limits_revision: Version
    expected_usage_revision: Version


class InviteCandidate(DTO):
    target_character_id: UUID
    display: CharacterDisplay
    ownership_revision: Version
    lifecycle_revision: Version
    item_level: str | None
    combat_power: str | None


class InviteCandidates(DTO):
    items: list[InviteCandidate]


class RelationPermissions(DTO):
    accept: Permission
    approve: Permission
    reject: Permission
    cancel: Permission
    block: Permission


class GroupRelation(DTO):
    relation_id: UUID
    subject_id: UUID
    kind: Literal['invitation', 'application']
    state: Literal['pending', 'accepted', 'rejected', 'cancelled', 'expired', 'blocked', 'joined_by_code']
    revision: Version
    group: GroupSummary
    members_revision: Version
    display: CharacterDisplay | None
    created_at: datetime
    expires_at: datetime
    ended_at: datetime | None
    application_count: Nonnegative
    permissions: RelationPermissions


class RelationPage(DTO):
    items: list[GroupRelation]
    next_cursor: str | None


class JoinSubject(DTO):
    subject_id: UUID
    revision: Version
    display: CharacterDisplay | None
    application_count: Nonnegative
    blocked: StrictBool
    blocked_at: datetime | None


class BlockPage(DTO):
    items: list[JoinSubject]
    next_cursor: str | None


class JoinCode(DTO):
    code_id: UUID | None
    revision: Version
    active: StrictBool
    visible_to_members: StrictBool
    code: str | None
    created_at: datetime | None
    regenerate_available_at: datetime | None


class CodePreview(DTO):
    group: GroupSummary
    members_revision: Version
    code_id: UUID
    code_revision: Version
