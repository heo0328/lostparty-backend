"""Agreed opt-in weekly resume review; fixed legacy wire remains unchanged."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictBool, StrictInt, StrictStr
from app.game_accounts.schemas import DTO
from app.raid_rooms import cycle_wire as wire
from app.raid_rooms.session_display_schemas import DisplayRef, Version

Clock = Annotated[StrictStr, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][05]$")]
Count = Annotated[StrictInt, Field(ge=0)]
Token = Annotated[StrictStr, Field(min_length=1, max_length=4096)]


class ResumeConfirmation(DTO):
    context_token: Token
    issued_at: AwareDatetime
    expires_at: AwareDatetime


class ResumeItem(DTO):
    item_id: UUID
    source_round_id: UUID
    raid_id: StrictStr
    difficulty_id: StrictStr
    catalog_version: StrictStr
    duration_minutes: Annotated[StrictInt, Field(gt=0)] | None
    duration_source: StrictStr | None


class ResumeAlternative(DTO):
    alternative_ref: DisplayRef
    weekday: Annotated[StrictInt, Field(ge=1, le=7)]
    starts_local: Clock | None
    leader_latest_start_local: Clock | None
    item_ids: list[UUID]
    session_id: None
    starts_at: AwareDatetime | None
    ends_at: AwareDatetime | None
    time_state: Literal['bounded', 'start_only', 'undetermined']
    materialization: Literal['on_apply', 'after_group_selection', 'after_coordination', 'not_scheduled']


class ResumeGroup(DTO):
    group_ref: DisplayRef
    planning_mode: wire.PlanningMode
    occurrence_mode: wire.OccurrenceMode
    day_scope: wire.DayScope
    required: StrictBool
    auto_confirm_additional_members: Annotated[StrictInt, Field(ge=1, le=7)] | None
    alternatives: list[ResumeAlternative]


class ResumeEffect(DTO):
    eligible_count: Count
    accepted_count: Count
    required_votes: Annotated[StrictInt, Field(ge=1)]
    new_round_count: Count | None
    new_assignment_count: Count | None
    completed_preserved_count: Count | None
    superseded_proposal_count: Count | None
    creator_accept_on_submit: StrictBool | None
    my_immediate_session_count_on_accept: Count | None


class ResumeDisplay(DTO):
    version: Literal[1]
    status: Literal['ready', 'stale', 'legacy_unverifiable']
    room_id: UUID
    room_cycle_id: UUID
    target_cycle_key: wire.CycleKey
    target_generation: Version
    proposal_id: UUID | None
    proposal_revision: Version | None
    proposal_plan_revision: Version | None
    origin: Literal['explicit', 'retained', 'legacy_unknown']
    settings_revision: Version | None
    basis_revision: DisplayRef | None
    display_revision: DisplayRef
    items: list[ResumeItem]
    groups: list[ResumeGroup]
    effect: ResumeEffect
    permission: wire.Permission


class ResumeReview(DTO):
    display: ResumeDisplay
    confirmation: ResumeConfirmation | None


class ResumePreviewData(DTO):
    kind: Literal['weekly_resume_preview']
    resume_review: ResumeReview


class ResumePreviewContext(DTO):
    scope: wire.Scope
    data: ResumePreviewData


class ResumeProposalReview(wire.BResumeProposal):
    resume_review: ResumeReview = Field(default=None, json_schema_extra=lambda s: s.pop('default', None))


class ResumePlanData(wire.BPlan):
    proposals: list[wire.BScheduleProposal | ResumeProposalReview]


class ResumePlanContext(wire.OutputContract3GetV2MeRaidRoomsRoomIdPlan):
    data: ResumePlanData
