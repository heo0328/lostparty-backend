from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, StrictStr, model_validator
from app.game_accounts.schemas import DTO, Version
from app.raids.schemas import Identifier, RaidCycle

CycleKey = Annotated[StrictStr, Field(pattern=r'^\d{4}-\d{2}-\d{2}$')]
CatalogVersion = Annotated[StrictStr, Field(min_length=1, max_length=64)]


class ManualCompletionIn(DTO):
    completed: StrictBool
    difficulty_id: Identifier | None
    expected_cycle_key: CycleKey
    expected_catalog_version: CatalogVersion
    expected_revision: Version
    expected_ownership_revision: Version
    expected_lifecycle_revision: Version

    @model_validator(mode='after')
    def correction_has_no_difficulty(self):
        if not self.completed and self.difficulty_id is not None:
            raise ValueError('Correction clears manual evidence only')
        return self


class CompletionSource(DTO):
    source: Literal['manual', 'party']
    completed_at: datetime
    difficulty_id: Identifier | None
    party_id: UUID | None


class Participation(DTO):
    party_id: UUID
    difficulty_id: Identifier
    joined_at: datetime


class WeeklyEntry(DTO):
    character_id: UUID
    raid_id: Identifier
    cycle_key: CycleKey
    revision: Version
    ownership_revision: Version
    lifecycle_revision: Version
    state: Literal['incomplete', 'participating', 'completed']
    completion_sources: list[CompletionSource]
    participation: Participation | None
    can_mark_completed: StrictBool
    can_clear_manual_completion: StrictBool
    mark_blocked_reason: Literal['CURRENT_CYCLE_REQUIRED', 'RAID_INACTIVE', 'CHARACTER_UNUSABLE',
                                 'PARTICIPATION_CONFIRMATION_REQUIRED'] | None


class WeeklyStates(DTO):
    current_cycle: RaidCycle
    cycle_key: CycleKey
    catalog_version: CatalogVersion
    entries: list[WeeklyEntry]
