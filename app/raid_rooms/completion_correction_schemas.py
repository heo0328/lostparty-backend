"""Closed personal completion correction wire; independent of C/N room scope."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictStr, field_validator
from app.game_accounts.schemas import DTO
from app.raid_rooms.weekly_summary_schemas import SummaryCompletionSource, WeeklySummaryPermission, CycleKey
from app.raid_rooms.availability_schemas import Version
from app.raid_rooms.cycle_schemas import CanonicalCycles

Token = Annotated[StrictStr, Field(min_length=1, max_length=4096)]

class CorrectionCommand(CanonicalCycles, DTO):
    target_cycle_key: CycleKey
    expected_cycle_key: CycleKey
    expected_weekly_revision: Version
    expected_ownership_revision: Version
    expected_lifecycle_revision: Version
    correction_context_token: Token

    @field_validator('correction_context_token')
    @classmethod
    def bounded(cls, value):
        if len(value.encode()) > 4096: raise ValueError('Token too large')
        return value

class Confirmation(DTO):
    context_token: Token
    issued_at: AwareDatetime
    expires_at: AwareDatetime

class CorrectionContextData(DTO):
    character_id: UUID
    raid_id: Annotated[StrictStr, Field(min_length=1, max_length=64)]
    target_cycle_key: CycleKey
    weekly_revision: Version
    ownership_revision: Version
    lifecycle_revision: Version
    completion_sources: Annotated[list[SummaryCompletionSource], Field(max_length=2)]
    permission: WeeklySummaryPermission
    confirmation: Confirmation | None

class CorrectionContext(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    data: CorrectionContextData

class CorrectionResultData(DTO):
    command_id: UUID
    outcome: Literal['applied']
    correction_id: UUID
    character_id: UUID
    raid_id: StrictStr
    target_cycle_key: CycleKey
    weekly_revision: Version
    completion_sources: Annotated[list[SummaryCompletionSource], Field(max_length=0)]
    participation_restored: Literal[False]

class CorrectionResult(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    data: CorrectionResultData
