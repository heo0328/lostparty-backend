"""P1 client analysis summaries; never provider observations or permissions."""
import re
from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictInt, StrictStr, field_validator, model_validator
from app.game_accounts.schemas import DTO, Version

Role = Literal['dealer', 'support']
Identifier = Annotated[StrictStr, Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9._-]+$')]
DecimalValue = Annotated[StrictStr, Field(min_length=1, max_length=32, pattern=r'^[0-9]+(?:\.[0-9]+)?$')]


class AnalysisIssue(DTO):
    code: Annotated[StrictStr, Field(min_length=1, max_length=64, pattern=r'^[A-Z0-9_]+$')]
    severity: Literal['warning', 'error']


class RoleSummary(DTO):
    source: Literal['flutter_analysis']
    analysis_rules_version: Identifier
    analyzed_at: datetime
    combat_power: DecimalValue | None
    item_level: DecimalValue | None
    combat_power_observed_at: datetime | None
    item_level_observed_at: datetime | None
    integrity_status: Literal['clean', 'review', 'error', 'unavailable']
    catalog_version: Identifier | None
    issues: Annotated[list[AnalysisIssue], Field(max_length=20)]
    observed_lifecycle_revision: Version

    @field_validator('analyzed_at', 'combat_power_observed_at', 'item_level_observed_at', mode='before')
    @classmethod
    def utc_wire(cls, value):
        if value is not None and not isinstance(value, datetime):
            if not isinstance(value, str) or not re.fullmatch(
                    r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|\+00:00)', value):
                raise ValueError('UTC RFC3339 required')
        return value

    @field_validator('analyzed_at', 'combat_power_observed_at', 'item_level_observed_at')
    @classmethod
    def utc(cls, value):
        if value is not None and value.utcoffset() != timedelta(0):
            raise ValueError('UTC required')
        return value

    @model_validator(mode='after')
    def combinations(self):
        for value, stamp in ((self.combat_power, self.combat_power_observed_at),
                             (self.item_level, self.item_level_observed_at)):
            if (value is None) != (stamp is None):
                raise ValueError('Value and observation time must be present together')
        pairs = [(issue.code, issue.severity) for issue in self.issues]
        if len(set(pairs)) != len(pairs):
            raise ValueError('Duplicate issue')
        errors = any(issue.severity == 'error' for issue in self.issues)
        if ((self.integrity_status == 'clean' and self.issues) or
                (self.integrity_status == 'review' and (not self.issues or errors)) or
                (self.integrity_status == 'error' and not errors) or
                (self.integrity_status == 'unavailable' and errors)):
            raise ValueError('Invalid integrity status and issues')
        return self


class RoleSummaryIn(DTO):
    expected_version: Version
    expected_ownership_revision: Version
    expected_lifecycle_revision: Version
    summary: RoleSummary

    @model_validator(mode='after')
    def observed_revision(self):
        if self.summary.observed_lifecycle_revision != self.expected_lifecycle_revision:
            raise ValueError('Observation must match expected lifecycle')
        return self


class StoredRoleSummary(DTO):
    version: Version
    summary: RoleSummary | None
    saved_at: datetime | None


class PendingPersonalPreferences(DTO):
    """P2 not implemented: read-only virtual defaults, no persistence."""
    version: Literal[1]
    preferred_role: Literal[None]
    visible: Literal[True]
    display_order: Literal[None]
    saved_at: Literal[None]


class PersonalProfileOut(DTO):
    character_id: UUID
    game_account_id: UUID
    ownership_revision: Version
    lifecycle_revision: Version
    lifecycle_state: Literal['active', 'suspect']
    dealer: StoredRoleSummary
    support: StoredRoleSummary
    preferences: PendingPersonalPreferences


class RoleSummaryOut(StoredRoleSummary):
    character_id: UUID
    role: Role
    ownership_revision: Version
    lifecycle_revision: Version
    summary: RoleSummary
    saved_at: datetime
