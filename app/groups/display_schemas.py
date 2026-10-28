"""Opt-in group display contracts; historical G1/G2 DTOs are unchanged."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from app.game_accounts.schemas import DTO, Version
from app.game_accounts.profile_schemas import AnalysisIssue, DecimalValue
from app.groups.schemas import GroupMember, GroupDetail, CharacterDisplay
from app.groups.admission_schemas import JoinSubject
from app.member_limits.schemas import Nonnegative


class GroupAnalysis(DTO):
    version: Version
    saved_at: datetime
    analyzed_at: datetime
    integrity_status: Literal['clean', 'review', 'error', 'unavailable']
    issues: list[AnalysisIssue]


class GroupRolePower(DTO):
    combat_power: DecimalValue | None
    source: Literal['stored_role_success', 'unavailable']
    trust: Literal['client_submitted'] | None
    observed_at: datetime | None
    saved_at: datetime | None
    power_revision: Version | None
    analysis: GroupAnalysis | None
    reason: Literal['ROLE_ANALYSIS_UNAVAILABLE', 'ROLE_ANALYSIS_INVALID'] | None


class CharacterSpec(DTO):
    character_id: UUID | None
    state: Literal['available', 'partial', 'unavailable']
    reason: Literal['CHARACTER_REFERENCE_UNAVAILABLE', 'CHARACTER_NOT_CURRENTLY_ELIGIBLE',
                    'CHARACTER_DATA_UNAVAILABLE', 'ROLE_ANALYSIS_UNAVAILABLE'] | None
    item_level: str | None
    item_level_source: Literal['stored_character_summary', 'unavailable']
    summary_fetched_at: datetime | None
    dealer: GroupRolePower
    support: GroupRolePower


class DisplayMember(GroupMember):
    character_spec: CharacterSpec


class DisplayMemberPage(DTO):
    profile: Literal['group-display-1']
    evaluated_at: datetime
    snapshot_revision: str
    group_id: UUID
    group_revision: Version
    members_revision: Version
    items: list[DisplayMember]
    next_cursor: str | None


class DisplaySubject(JoinSubject):
    character_spec: CharacterSpec


class DisplayBlockPage(DTO):
    profile: Literal['group-display-1']
    evaluated_at: datetime
    snapshot_revision: str
    items: list[DisplaySubject]
    next_cursor: str | None


class DisplayDetail(GroupDetail):
    profile: Literal['group-display-1']
    evaluated_at: datetime
    snapshot_revision: str
    last_activity_at: datetime | None


class DisplayMyGroupPage(DTO):
    profile: Literal['group-display-1']
    evaluated_at: datetime
    snapshot_revision: str
    directory_revision: Version
    items: list[DisplayDetail]
    next_cursor: str | None


class ActivityCharacter(DTO):
    character_id: UUID
    display: CharacterDisplay
    character_spec: CharacterSpec


class ActivityCharacterPage(DTO):
    group_id: UUID
    membership_id: UUID
    group_revision: Version
    members_revision: Version
    evaluated_at: datetime
    snapshot_revision: str
    items: list[ActivityCharacter]
    next_cursor: str | None


class GroupRequestCounts(DTO):
    evaluated_at: datetime
    counts_revision: str
    valid_until: datetime | None
    received_invitations: Nonnegative
    sent_applications: Nonnegative
    managed_applications: Nonnegative
    managed_invitations: Nonnegative
    action_required: Nonnegative


class GroupJoinRequestCounts(DTO):
    group_id: UUID
    group_revision: Version
    members_revision: Version
    evaluated_at: datetime
    counts_revision: str
    valid_until: datetime | None
    pending_applications: Nonnegative
    pending_invitations: Nonnegative
    action_required: Nonnegative
