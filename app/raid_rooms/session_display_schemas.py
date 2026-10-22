"""Opt-in display projections; existing command bodies and wire stay fixed."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, StrictBool, StrictInt, StringConstraints
from app.game_accounts.schemas import DTO
from app.raid_rooms import cycle_wire as wire

Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]
DisplayRef = Annotated[str, StringConstraints(strict=True, min_length=64, max_length=64, pattern=r'^[0-9a-f]{64}$')]


class ActualSessionDisplay(DTO):
    session_id: UUID
    revision: Version
    schedule_revision: Version
    state: Literal['unconfirmed', 'confirmed']
    required: StrictBool
    starts_at: AwareDatetime | None
    ends_at: AwareDatetime | None
    join_deadline: AwareDatetime | None
    permission: wire.Permission


class PreviewAlternative(DTO):
    preview_ref: DisplayRef
    session_id: None
    state: Literal['preview']
    weekday: Annotated[StrictInt, Field(ge=1, le=7)]
    starts_at: AwareDatetime | None
    ends_at: AwareDatetime | None
    time_state: Literal['bounded', 'undetermined', 'start_only']
    materialization: Literal['on_open', 'after_group_selection', 'after_coordination', 'not_scheduled']


class OpeningSchedulePreviewGroup(DTO):
    preview_group_ref: DisplayRef
    source_group_revision: Version
    planning_mode: Literal['manual', 'coordinated', 'unscheduled']
    occurrence_mode: Literal['one_of', 'each']
    day_scope: Literal['selected_weekdays', 'any_current_cycle']
    required: StrictBool
    alternatives: list[PreviewAlternative]


class DisplayBase(DTO):
    target_cycle_key: wire.CycleKey
    room_cycle_id: UUID
    target_generation: Version
    display_revision: DisplayRef


class ExistingSessionDisplay(DisplayBase):
    kind: Literal['existing']
    selection_mode: Literal['select_session_ids']
    plan_revision: Version
    sessions: Annotated[list[ActualSessionDisplay], Field(max_length=64)]
    previews: Annotated[list[OpeningSchedulePreviewGroup], Field(max_length=0)]


class OpeningPreviewDisplay(DisplayBase):
    kind: Literal['opening_preview']
    selection_mode: Literal['opening_implicit_enrolment']
    plan_revision: None
    sessions: Annotated[list[ActualSessionDisplay], Field(max_length=0)]
    previews: list[OpeningSchedulePreviewGroup]


class NoSelectionDisplay(DisplayBase):
    kind: Literal['none']
    selection_mode: Literal['no_session_selection']
    plan_revision: Version
    sessions: Annotated[list[ActualSessionDisplay], Field(max_length=0)]
    previews: Annotated[list[OpeningSchedulePreviewGroup], Field(max_length=0)]


SessionDisplay = Annotated[ExistingSessionDisplay | OpeningPreviewDisplay | NoSelectionDisplay, Field(discriminator='kind')]


class AdmissionDisplayData(wire.BAdmissionContext):
    session_display: SessionDisplay = Field(default=None, json_schema_extra=lambda s: s.pop('default', None))


class AdmissionDisplayContext(wire.OutputContract3GetV2RaidRoomsRoomIdAdmissionContext):
    data: AdmissionDisplayData


class ContinuationDisplayData(wire.ContinuationContextData):
    session_display: SessionDisplay = Field(default=None, json_schema_extra=lambda s: s.pop('default', None))


class ContinuationDisplayContext(wire.ContinuationContext):
    data: ContinuationDisplayData


class OpeningDisplayData(wire.OpeningContextData):
    session_display: SessionDisplay = Field(default=None, json_schema_extra=lambda s: s.pop('default', None))


class OpeningDisplayContext(wire.OpeningContext):
    data: OpeningDisplayData
