"""Opt-in application display readers; base and command DTOs stay unchanged."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt

from app.game_accounts.profile_schemas import AnalysisIssue
from app.game_accounts.schemas import DTO
from app.raid_rooms import cycle_wire as wire

Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]


class ApplicationDisplayAnalysis(DTO):
    version: Version
    saved_at: AwareDatetime
    analyzed_at: AwareDatetime
    integrity_status: Literal['clean', 'review', 'error', 'unavailable']
    issues: Annotated[list[AnalysisIssue], Field(max_length=20)]


class ApplicationDisplayItem(wire.BApplication):
    comparison: wire.BPowerComparison | None
    analysis: ApplicationDisplayAnalysis | None
    display_reason: Literal['APPLICATION_CONTEXT_CHANGED', 'CHARACTER_DATA_UNAVAILABLE'] | None


class ApplicationDisplayPage(wire.BApplicationPage):
    items: Annotated[list[ApplicationDisplayItem], Field(max_length=50)]


class ApplicationDisplayPageResponse(DTO):
    scope: wire.Scope
    data: ApplicationDisplayPage


class ApplicationDisplayOwnApplication(DTO):
    application_id: UUID
    revision: Version
    state: Literal['pending', 'accepted', 'rejected', 'withdrawn', 'expired', 'cancelled']
    expires_at: AwareDatetime


class ApplicationDisplayDetail(wire.BDetail):
    my_application: ApplicationDisplayOwnApplication | None


class ApplicationDisplayDetailResponse(DTO):
    scope: wire.Scope
    data: ApplicationDisplayDetail
