from app.raid_rooms.cycle_group_schemas import Envelope as PolicyEnvelope, PolicyCandidate
"""Closed wire for the atomic member actions (#22/#23)."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictStr, UUID4, AwareDatetime, field_validator
from app.game_accounts.schemas import DTO
from app.raid_rooms.cycle_schemas import CanonicalCycles
from app.raid_rooms.cycle_wire import Scope, Leadership, Permission
from app.raid_rooms.weekly_summary_schemas import CycleKey
from app.raid_rooms.availability_schemas import Version
from app.raid_rooms.completion_correction_schemas import Confirmation, Token

Ids = Annotated[list[UUID], Field(max_length=5)]
class AtomicCommand(CanonicalCycles, DTO):
    expected_cycle_key: CycleKey
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Version
    expected_target_revision: Version
    context_token: Token

    @field_validator('context_token')
    @classmethod
    def token_bytes(cls, value):
        if len(value.encode()) > 4096: raise ValueError('Token too large')
        return value

class DepartureCommand(AtomicCommand):
    actor_cycle_member_id: UUID
    expected_cycle_member_revision: Version
    round_id: UUID

class RemovalCommand(AtomicCommand):
    target_membership_id: UUID
    target_cycle_member_id: UUID
    expected_target_cycle_member_revision: Version
    mode: Literal['current_only','both']

class DepartureSubject(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    cycle_member_revision: Version
    character_id: UUID
    round_id: UUID
    assignment_id: UUID
    assignment_revision: Version

class Successor(DTO):
    cycle_member_id: UUID
    revision: Version
    joined_order: Annotated[StrictStr, Field(pattern=r'^[1-9][0-9]*$')]
    character_id: UUID
    character_name: StrictStr | None

class DepartureImpact(DTO):
    complete_assignment_ids: Annotated[list[UUID], Field(min_length=1,max_length=1)]
    cancel_assignment_ids: Annotated[list[UUID], Field(max_length=4)]
    preserved_completed_assignment_ids: Ids
    released_reservation_count: Annotated[int, Field(ge=0,strict=True)]
    departure_effect: Literal['leave','automatic_successor','close_completed','close_incomplete']
    successor: Successor | None
    preserves_other_cycles: Literal[True]
    preserves_global_membership: Literal[True]

class AssignmentDisplay(DTO):
    assignment_id: UUID
    round_id: UUID
    item_id: UUID
    character_id: UUID
    character_name: StrictStr | None
    raid_id: StrictStr
    raid_name: StrictStr
    difficulty_id: StrictStr
    difficulty_name: StrictStr
    catalog_version: StrictStr
    effect: Literal['complete','cancel','preserve_completed']

class DepartureDisplay(DTO):
    character_id: UUID
    character_name: StrictStr | None
    assignments: Annotated[list[AssignmentDisplay], Field(min_length=1,max_length=5)]
    display_revision: Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]

class DepartureData(DTO):
    action: Literal['personal_completion_departure']
    room_id: UUID
    subject: DepartureSubject
    leadership: Leadership
    impact: DepartureImpact
    display: DepartureDisplay
    permission: Permission
    confirmation: Confirmation | None

class DepartureContext(PolicyEnvelope, DTO):
    scope: Scope
    data: DepartureData

class RemovalTarget(DTO):
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Version
    target_revision: Version
    actor_cycle_member_id: UUID
    actor_cycle_member_revision: Version
    target_cycle_member_id: UUID
    target_cycle_member_revision: Version
    character_id: UUID
    character_name: StrictStr | None
    leadership: Leadership

class OppositeRelation(DTO):
    target_cycle_key: CycleKey
    status: Literal['none','participating','review_required']
    target: RemovalTarget | None

class RemovalEffect(DTO):
    target_cycle_key: CycleKey
    cycle_member_id: UUID
    cancel_assignment_ids: Ids
    preserved_completed_assignment_ids: Ids
    released_reservation_count: Annotated[int, Field(ge=0,strict=True)]

class RemovalImpact(DTO):
    mode: Literal['current_only','both']
    affected_cycle_keys: Annotated[list[CycleKey], Field(min_length=1,max_length=2)]
    targets: Annotated[list[RemovalEffect], Field(min_length=1,max_length=2)]
    preserves_completed: Literal[True]
    preserves_global_membership: Literal[True]

class RemovalOption(DTO):
    permission: Permission
    impact: RemovalImpact | None
    confirmation: Confirmation | None

class RemovalOptions(DTO):
    current_only: RemovalOption
    both: RemovalOption

class RemovalData(DTO):
    action: Literal['member_removal']
    room_id: UUID
    target_membership_id: UUID
    source: RemovalTarget
    opposite_relation: OppositeRelation
    options: RemovalOptions

class RemovalContext(PolicyEnvelope, DTO):
    scope: Scope
    data: RemovalData

class ActionEffect(DTO):
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Version
    target_revision: Version
    cycle_member_id: UUID
    cycle_member_revision: Version
    state: Literal['cancelled','removed']
    leadership: Leadership
    completed_assignment_ids: Annotated[list[UUID], Field(max_length=1)]
    cancelled_assignment_ids: Ids
    preserved_completed_assignment_ids: Ids

class ActionResultData(DTO):
    command_id: UUID4
    action: Literal['personal_completion_departure','member_removal']
    outcome: Literal['applied']
    executed_at: AwareDatetime
    room_id: UUID
    subject_membership_id: UUID
    affected_cycle_keys: Annotated[list[CycleKey], Field(min_length=1,max_length=2)]
    effects: Annotated[list[ActionEffect], Field(min_length=1,max_length=2)]

class ActionResult(PolicyEnvelope, DTO):
    scope: Scope
    data: ActionResultData
