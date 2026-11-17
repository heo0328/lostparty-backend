"""character-analysis-refresh-1: one command per character, role selected by server."""
from datetime import datetime
import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictInt, UUID4, model_validator, field_validator
from app.game_accounts.schemas.schemas import DTO
from app.game_accounts.schemas.profile_schemas import Role, RoleAnalysis

CommandID = Annotated[UUID4, Field(json_schema_extra={'format':'uuid','pattern':r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'})]
Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]


class ExpectedVersions(DTO):
    dealer: Version
    support: Version


class CandidateContext(DTO):
    candidate_id: UUID
    expected_generation: Version
    expected_policy_revision: Version
    expected_settings_version: Version
    purpose: Literal['automatic_candidate', 'manual_retry']


class AnalysisCommand(DTO):
    command_id: CommandID
    character_id: UUID
    expected_ownership_revision: Version
    expected_lifecycle_revision: Version
    expected_summary_versions: ExpectedVersions
    trigger: Literal['automatic', 'manual']
    candidate_context: CandidateContext = Field(default_factory=lambda: None)

    @model_validator(mode='after')
    def candidate_trigger(self):
        if 'candidate_context' in self.model_fields_set and self.candidate_context is None:
            raise ValueError('candidate_context cannot be null')
        if self.candidate_context and self.trigger != (
                'automatic' if self.candidate_context.purpose == 'automatic_candidate' else 'manual'):
            raise ValueError('candidate purpose/trigger mismatch')
        return self



    @field_validator('command_id','character_id',mode='before')
    @classmethod
    def canonical_uuid(cls,value):
        if isinstance(value,UUID):return value
        if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}',value):
            raise ValueError('Canonical UUID required')
        return value


class AnalysisRequest(DTO):
    items: Annotated[list[AnalysisCommand], Field(min_length=1, max_length=50)]

    @model_validator(mode='after')
    def distinct(self):
        if len({c.command_id for c in self.items}) != len(self.items) or len({c.character_id for c in self.items}) != len(self.items):
            raise ValueError('Duplicate command or character')
        return self


class AnalysisResult(DTO):
    character_id: UUID
    game_account_id: UUID
    ownership_revision: Version
    lifecycle_revision: Version
    role: Role
    analysis: RoleAnalysis

    @model_validator(mode='after')
    def consistent(self):
        if self.analysis.summary is None or self.analysis.detail is None:
            raise ValueError('Saved result requires a stored analysis')
        if self.role != self.analysis.detail.detection.detected_role or self.lifecycle_revision != self.analysis.summary.observed_lifecycle_revision:
            raise ValueError('Analysis role/lifecycle mismatch')
        return self


class AnalysisError(DTO):
    code: str
    message: str
    request_id: str
    retry_after_seconds: Annotated[StrictInt, Field(ge=1)] | None
    retry_at: datetime | None


CANDIDATE_OUTCOMES = {
    'ANALYSIS_CANDIDATE_NOT_FOUND': ('failed',404,'none'),
    'ANALYSIS_CANDIDATE_IN_PROGRESS': ('failed',409,'none'),
    'ANALYSIS_CANDIDATE_RETRY_REQUIRED': ('skipped',200,'none'),
    'ANALYSIS_CANDIDATE_COMPLETED': ('skipped',200,'none'),
    'ANALYSIS_CANDIDATE_RECONCILED': ('failed',409,'new_command'),
}


class AnalysisItem(DTO):
    command_id: CommandID
    character_id: UUID
    status: StrictInt
    state: Literal['saved', 'skipped', 'failed', 'not_processed', 'in_progress', 'unknown']
    detected_role: Role | None
    retry: Literal['none', 'same_command', 'new_command']
    result: AnalysisResult | None
    error: AnalysisError | None

    @model_validator(mode='after')
    def consistent(self):
        if self.error and self.error.code in CANDIDATE_OUTCOMES:
            if (self.state,self.status,self.retry)!=CANDIDATE_OUTCOMES[self.error.code]:
                raise ValueError('Invalid candidate outcome')
        if self.state == 'saved':
            if self.status != 200 or self.result is None or self.error is not None or self.retry != 'none':
                raise ValueError('Invalid saved result')
            if self.character_id != self.result.character_id or self.detected_role != self.result.role:
                raise ValueError('Result correlation mismatch')
        elif self.result is not None or self.error is None:
            raise ValueError('Non-saved item requires an error and null result')
        if self.state in ('not_processed', 'in_progress', 'unknown'):
            expected = {'not_processed':(503,'BATCH_NOT_PROCESSED'),'in_progress':(409,'REQUEST_IN_PROGRESS'),'unknown':(503,'SERVICE_UNAVAILABLE')}[self.state]
            if self.status != expected[0] or self.error.code != expected[1] or self.retry != 'same_command' or self.detected_role is not None:
                raise ValueError('Invalid unresolved command')
        if self.state == 'skipped' and (self.status != 200 or self.retry != 'none'):
            raise ValueError('Invalid skip')
        return self


class AnalysisResponse(DTO):
    evaluated_at: datetime
    items: Annotated[list[AnalysisItem], Field(min_length=1, max_length=50)]
