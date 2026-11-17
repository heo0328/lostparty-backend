"""Read projection for the optional, owner-scoped candidate policy."""
from datetime import datetime
from typing import Literal, Annotated
from uuid import UUID
from pydantic import Field
from app.game_accounts.schemas.schemas import DTO
from app.game_accounts.schemas.analysis_schemas import AnalysisCommand, AnalysisError, Version

class UnresolvedCommand(DTO):
    command: AnalysisCommand
    recovery: Literal['same_command','reconcile_required']

class CandidateOut(DTO):
    candidate_id: UUID
    character_id: UUID
    generation: Version
    reason: Literal['new_at_threshold','first_threshold','initial_verification']
    state: Literal['pending','running','succeeded','blocked']
    eligibility: Literal['eligible','nice_group_disabled','explicitly_excluded','character_unusable','command_unresolved']
    next_attempt_at: datetime | None
    last_error: AnalysisError | None
    unresolved_command: UnresolvedCommand | None
    completed_at: datetime | None
    completed_command_id: UUID | None

class CandidateProjection(DTO):
    policy_version: Literal['analysis-candidates-1']
    policy_revision: Version
    baseline: Literal['legacy','observed','not_initialized']
    game_account_id: UUID
    registration_id: UUID
    ownership_revision: Version
    settings_version: Version
    complete: Literal[True]
    candidates: Annotated[list[CandidateOut],Field(max_length=200)]
