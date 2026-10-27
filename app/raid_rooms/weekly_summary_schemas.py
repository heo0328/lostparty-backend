"""Implemented metadata/summary slice of the agreed two-cycle 0.4.1 contract."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, StrictStr, model_validator
from app.game_accounts.schemas import DTO
from app.raid_rooms.availability_schemas import Version

CycleKey = Annotated[StrictStr, Field(pattern=r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$',
                                     json_schema_extra={'format': 'date'})]


class WeeklySummaryPermission(DTO):
    allowed: StrictBool
    reason: str | None
    next_change_at: datetime | None


class CyclePermissions(DTO):
    read: WeeklySummaryPermission
    create: WeeklySummaryPermission
    admit: WeeklySummaryPermission
    complete: WeeklySummaryPermission


class CycleMeta(DTO):
    cycle_key: CycleKey
    starts_at: datetime
    ends_at: datetime
    playable_from: datetime
    permissions: CyclePermissions


class Cycles(DTO):
    server_now: datetime
    current: CycleMeta
    next: CycleMeta
    policy_version: Literal['two-cycle-contract-4']


class SummaryRequest(DTO):
    character_ids: Annotated[list[UUID], Field(min_length=1, max_length=50, json_schema_extra={'uniqueItems': True})]
    target_cycle_keys: Annotated[list[CycleKey], Field(min_length=1, max_length=2, json_schema_extra={'uniqueItems': True})]

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.character_ids)) != len(self.character_ids) or len(set(self.target_cycle_keys)) != len(self.target_cycle_keys):
            raise ValueError('Duplicate character or target')
        return self


class SummaryCompletionSource(DTO):
    source: Literal['manual', 'party']
    completed_at: datetime
    difficulty_id: str | None
    party_id: UUID | None


class SummaryParticipation(DTO):
    room_id: UUID
    round_id: UUID
    assignment_id: UUID
    difficulty_id: str
    status: Literal['confirmed', 'review_required']
    room_title: str | None
    can_view_detail: StrictBool


class SummaryPermissions(DTO):
    mark_completed: WeeklySummaryPermission
    clear_manual_completion: WeeklySummaryPermission
    view_participation: WeeklySummaryPermission


class SummaryEntry(DTO):
    character_id: UUID
    raid_id: str
    target_cycle_key: CycleKey
    weekly_revision: Version
    ownership_revision: Version
    lifecycle_revision: Version
    completion_sources: Annotated[list[SummaryCompletionSource], Field(max_length=2)]
    participation: SummaryParticipation | None
    continuation_state: Literal['not_selected', 'declined', 'legacy_intent', 'confirmed', 'blocked']
    permissions: SummaryPermissions


class Summary(DTO):
    server_now: datetime
    current_cycle_key: CycleKey
    target_cycle_keys: Annotated[list[CycleKey], Field(min_length=1, max_length=2, json_schema_extra={'uniqueItems': True})]
    catalog_version: str
    entries: Annotated[list[SummaryEntry], Field(max_length=500)]
