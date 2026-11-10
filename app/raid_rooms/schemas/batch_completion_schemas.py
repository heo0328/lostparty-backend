"""Agreed Issue47 v3; independent of all original single-command DTOs."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, StrictStr, UUID4, field_validator

from app.game_accounts.schemas.schemas import DTO
from app.raid_rooms.schemas.availability_schemas import Version
from app.raid_rooms.schemas.cycle_schemas import CanonicalCycles
from app.raid_rooms.schemas.cycle_wire import Scope, Leadership, Permission
from app.raid_rooms.schemas.cycle_group_schemas import Envelope
from app.raid_rooms.schemas.atomic_member_schemas import Successor
from app.raid_rooms.schemas.completion_correction_schemas import Confirmation, Token
from app.raid_rooms.schemas.weekly_summary_schemas import CycleKey

Digest = Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
RoundIds = Annotated[list[UUID], Field(min_length=1, max_length=5, json_schema_extra={'uniqueItems': True})]
Ids = Annotated[list[UUID], Field(max_length=40, json_schema_extra={'uniqueItems': True})]
PersonalIds = Annotated[list[UUID], Field(max_length=5, json_schema_extra={'uniqueItems': True})]


class BatchCommand(CanonicalCycles, DTO):
    expected_cycle_key: CycleKey
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Version
    expected_target_revision: Version
    actor_cycle_member_id: UUID
    expected_cycle_member_revision: Version
    round_ids: RoundIds
    context_token: Token

    @field_validator('round_ids')
    @classmethod
    def unique_rounds(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Duplicate round')
        return value

    @field_validator('context_token')
    @classmethod
    def bounded_token(cls, value):
        if len(value.encode()) > 4096:
            raise ValueError('Token too large')
        return value


class BatchHistoryRaid(DTO):
    raid_id: StrictStr
    raid_name: StrictStr
    assignment_count: Annotated[StrictInt, Field(ge=1)]
    digest: Digest


class BatchHistory(DTO):
    assignment_count: Annotated[StrictInt, Field(ge=0)]
    digest: Digest
    raids: list[BatchHistoryRaid]


class BatchImpact(DTO):
    completed_assignment_ids: Annotated[list[UUID], Field(min_length=1, max_length=40)]
    cancelled_assignment_ids: Ids
    preserved_active_assignment_ids: Ids
    released_reservation_count: Annotated[StrictInt, Field(ge=0)]
    preserves_other_cycles: Literal[True]
    preserves_global_membership: Literal[True]
    preserved_completed: BatchHistory


class BatchPartyImpact(BatchImpact):
    cancelled_assignment_ids: Annotated[list[UUID], Field(max_length=0)]


class BatchPersonalImpact(BatchImpact):
    completed_assignment_ids: Annotated[list[UUID], Field(min_length=1, max_length=5)]
    cancelled_assignment_ids: Annotated[list[UUID], Field(max_length=4)]
    preserved_active_assignment_ids: Annotated[list[UUID], Field(max_length=0)]


class BatchRoundDisplay(DTO):
    round_id: UUID
    item_id: UUID
    raid_id: StrictStr
    raid_name: StrictStr
    difficulty_id: StrictStr
    difficulty_name: StrictStr
    catalog_version: StrictStr


class BatchAssignmentDisplay(DTO):
    assignment_id: UUID
    round_id: UUID
    membership_id: UUID
    cycle_member_id: UUID
    character_id: UUID
    character_name: StrictStr | None
    effect: Literal['complete', 'cancel', 'preserve_active']


class BatchDisplay(DTO):
    rounds: Annotated[list[BatchRoundDisplay], Field(min_length=1, max_length=5)]
    assignments: Annotated[list[BatchAssignmentDisplay], Field(min_length=1, max_length=40)]
    display_revision: Digest


class BatchPersonalDisplay(BatchDisplay):
    assignments: Annotated[list[BatchAssignmentDisplay], Field(min_length=1, max_length=5)]


class BatchState(DTO):
    target_state: Literal['open', 'closed']
    generation_state: Literal['open', 'completed', 'cancelled']
    actor_cycle_member_state: Literal['participating', 'completed', 'cancelled']


class BatchExpectedAfter(DTO):
    state: BatchState
    leader_cycle_member_id: UUID | None
    leader_membership_id: UUID | None


class BatchDeparture(DTO):
    effect: Literal['leave', 'automatic_successor', 'close_completed', 'close_incomplete']
    successor: Successor | None


class BatchRevision(DTO):
    resource: Literal['target', 'members', 'plan', 'leadership', 'cycle_membership', 'round', 'assignment']
    id: UUID
    revision: Version


Revisions = Annotated[list[BatchRevision], Field(min_length=5, max_length=64)]


class BatchContextData(DTO):
    action: Literal['batch_completion']
    room_id: UUID
    actor_cycle_member_id: UUID
    actor_cycle_member_revision: Version
    round_ids: RoundIds
    display: BatchDisplay
    impact: BatchPartyImpact
    departure: None
    state: BatchState
    leadership: Leadership
    expected_after: BatchExpectedAfter | None
    revisions: Revisions
    permission: Permission
    confirmation: Confirmation | None


class BatchPersonalContextData(BatchContextData):
    action: Literal['batch_personal_completion_departure']
    display: BatchPersonalDisplay
    impact: BatchPersonalImpact
    departure: BatchDeparture


class BatchScope(Scope):
    target_revision: Version
    room_cycle_id: UUID
    target_generation: Version


class BatchPartyContext(Envelope, DTO):
    scope: BatchScope
    data: BatchContextData


class BatchPersonalContext(Envelope, DTO):
    scope: BatchScope
    data: BatchPersonalContextData


class BatchAckData(DTO):
    action: Literal['batch_completion']
    command_id: UUID4
    outcome: Literal['applied']
    executed_at: AwareDatetime
    room_id: UUID
    actor_cycle_member_id: UUID
    round_ids: RoundIds
    impact: BatchPartyImpact
    departure: None
    state: BatchState
    leadership: Leadership
    revisions: Revisions


class BatchPersonalAckData(BatchAckData):
    action: Literal['batch_personal_completion_departure']
    impact: BatchPersonalImpact
    departure: BatchDeparture


class BatchPartyAck(Envelope, DTO):
    scope: BatchScope
    data: BatchAckData


class BatchPersonalAck(Envelope, DTO):
    scope: BatchScope
    data: BatchPersonalAckData
