"""Internal commands only; not a published or enabled REST schema."""
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID
from pydantic import StrictStr, Field, field_validator
from app.game_accounts.schemas import DTO, Version
from app.raids.schemas import Identifier


class Selection(DTO):
    registration_id: UUID
    character_id: UUID
    selected_role: Literal['dealer', 'support']
    party_no: Version = Field(le=2)
    expected_registration_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_lifecycle_revision: Version
    expected_role_summary_version: Version
    expected_weekly_revision: Version
    expected_limits_revision: Version
    expected_usage_revision: Version


class Schedule(DTO):
    starts_at: datetime | None
    ends_at: datetime | None

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def utc(cls, value):
        if value is not None and value.utcoffset() != timedelta(0):
            raise ValueError('UTC time required')
        return value


class Create(DTO):
    title: StrictStr = Field(min_length=1, max_length=60)
    raid_id: Identifier
    difficulty_id: Identifier
    expected_catalog_version: StrictStr
    expected_cycle_key: StrictStr
    admission_mode: Literal['leader_only', 'direct_join']
    scope: Literal['public', 'group']
    group_id: UUID | None
    schedule: Schedule
    selection: Selection

    @field_validator('title', mode='before')
    @classmethod
    def title_value(cls, value):
        import unicodedata
        if not isinstance(value, str):
            raise ValueError('Title must be a string')
        value = value.strip()
        if not value or any(unicodedata.category(c) == 'Cc' or c in '\u2028\u2029' for c in value):
            raise ValueError('Invalid title')
        return value


class Admission(DTO):
    selection: Selection
    expected_room_revision: Version
    expected_round_revision: Version
    expected_members_revision: Version
    expected_policy_snapshot: StrictStr
    expected_cycle_key: StrictStr
    expected_catalog_version: StrictStr


class Decision(DTO):
    expected_application_revision: Version
    expected_room_revision: Version
    expected_round_revision: Version
    expected_members_revision: Version
    expected_policy_snapshot: StrictStr
    expected_cycle_key: StrictStr


class Withdraw(DTO):
    expected_application_revision: Version


class MembershipCAS(DTO):
    expected_room_revision: Version
    expected_round_id: UUID
    expected_round_revision: Version
    expected_members_revision: Version
    expected_membership_id: UUID
    expected_membership_revision: Version


class Transfer(MembershipCAS):
    target_membership_id: UUID
    expected_target_membership_revision: Version
