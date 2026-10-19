"""Candidate HTTP inputs/ACKs; public installation remains a separate checkpoint."""
import re
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictStr, field_validator, model_validator
from app.game_accounts.schemas import DTO, Version
from app.game_accounts.profile_schemas import DecimalValue
from app.raid_rooms import commands as c

CycleKey = Annotated[StrictStr, Field(min_length=10, max_length=10, pattern=r'^\d{4}-\d{2}-\d{2}$')]
CatalogVersion = Annotated[StrictStr, Field(min_length=1, max_length=64)]
PolicySnapshot = Annotated[StrictStr, Field(min_length=1, max_length=128)]


class WireSchedule(c.Schedule):
    @field_validator('starts_at', 'ends_at', mode='before')
    @classmethod
    def wire_utc(cls, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(
                r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)', value)):
            raise ValueError('UTC RFC3339 string required')
        return value


class MinimumCombatPower(DTO):
    dealer: DecimalValue | None
    support: DecimalValue | None


class CycleInput(DTO):
    expected_cycle_key: CycleKey

    @field_validator('expected_cycle_key')
    @classmethod
    def calendar_date(cls, value):
        date.fromisoformat(value)
        return value


class RoomCreateIn(c.Create, CycleInput):
    expected_cycle_key: CycleKey
    expected_catalog_version: CatalogVersion
    expected_group_revision: Version | None
    expected_group_membership_id: UUID | None
    expected_group_membership_revision: Version | None
    min_combat_power: MinimumCombatPower
    schedule: WireSchedule

    @model_validator(mode='after')
    def group_fields(self):
        values = (self.group_id, self.expected_group_revision, self.expected_group_membership_id,
                  self.expected_group_membership_revision)
        if (self.scope == 'public' and any(v is not None for v in values)) or (
                self.scope == 'group' and any(v is None for v in values)):
            raise ValueError('Scope and group fields must agree')
        return self


class AdmissionIn(c.Admission, CycleInput):
    expected_cycle_key: CycleKey
    expected_catalog_version: CatalogVersion
    expected_policy_snapshot: PolicySnapshot


class DecisionIn(c.Decision, CycleInput):
    expected_cycle_key: CycleKey
    expected_policy_snapshot: PolicySnapshot


class WithdrawIn(c.Withdraw):
    pass


class MembershipIn(c.MembershipCAS):
    pass


class TransferIn(c.Transfer):
    pass


class RoomCommandAck(DTO):
    room_id: UUID
    round_id: UUID
    actor_membership_id: UUID
    affected_membership_id: UUID
    room_revision: Version
    round_revision: Version
    members_revision: Version
    actor_membership_revision: Version
    affected_membership_revision: Version
    application_id: UUID | None
    application_revision: Version | None
    executed_at: datetime


class ApplicationAck(DTO):
    room_id: UUID
    application_id: UUID
    application_revision: Version
    state: Literal['pending', 'accepted', 'rejected', 'withdrawn', 'expired', 'cancelled']
    executed_at: datetime


class MembershipEndAck(DTO):
    room_id: UUID
    round_id: UUID
    membership_id: UUID
    membership_revision: Version
    ended_at: datetime


class RoomEndAck(MembershipEndAck):
    room_revision: Version
    round_revision: Version
