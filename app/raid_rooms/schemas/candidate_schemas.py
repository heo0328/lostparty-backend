"""Allowlisted group activity candidates, independent of target participation."""
from datetime import datetime
from typing import Annotated
from typing import Literal
from uuid import UUID
from pydantic import Field
from pydantic import StringConstraints
from pydantic import model_validator
from app.game_accounts.schemas.profile_schemas import AnalysisIssue
from app.game_accounts.schemas.schemas import DTO
from app.game_accounts.schemas.schemas import Version

CandidateToken = Annotated[str, StringConstraints(strict=True, min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')]
Number = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64, pattern=r'^[0-9]+(?:\.[0-9]+)?$')]


class CandidateDisplay(DTO):
    server_name: str
    character_name: str
    class_name: str | None


class CandidateAlias(DTO):
    group_id: UUID
    group_membership_id: UUID


class CandidatePower(DTO):
    value: Number | None
    source: Literal['server_analysis', 'unavailable', 'not_disclosed']
    trust: Literal['server_computed'] | None
    observed_at: datetime | None
    saved_at: datetime | None
    summary_version: Version | None
    integrity_status: Literal['clean', 'review', 'error', 'unavailable'] | None

    issues: list[AnalysisIssue]

    @model_validator(mode='after')
    def provenance(self):
        provenance = (self.trust, self.saved_at, self.summary_version, self.integrity_status)
        if self.source == 'server_analysis':
            if any(v is None for v in provenance) or ((self.value is None) != (self.observed_at is None)):
                raise ValueError('Stored analysis requires correlated provenance')
        elif any(v is not None for v in (self.value,self.observed_at,*provenance)) or self.issues:
            raise ValueError('Absent power must not expose metadata')
        return self


class CandidateCharacter(DTO):
    character_id: UUID
    server_name: str
    character_name: str
    class_name: str | None
    role_family: None
    item_level: Number | None
    item_level_source: Literal['stored_character_summary', 'unavailable']
    summary_fetched_at: datetime
    ownership_revision: Version
    lifecycle_revision: Version
    ownership_state: Literal['owned']
    activity_state: Literal['selected']
    lifecycle_state: Literal['active']
    dealer: CandidatePower
    support: CandidatePower


class CandidateMemberChunk(DTO):
    member_ref: CandidateToken
    alias: CandidateAlias
    display: CandidateDisplay | None
    continues_from_previous: bool
    continues_on_next: bool
    characters: Annotated[list[CandidateCharacter], Field(max_length=100)]


class CandidatePage(DTO):
    group_id: UUID
    filter_context_token: CandidateToken
    scope_digest: CandidateToken
    candidate_token: CandidateToken
    evaluated_at: datetime
    groups: Annotated[list[CandidateMemberChunk], Field(max_length=100)]
    next_cursor: Annotated[str, StringConstraints(min_length=1, max_length=2048)] | None
