"""Closed membership-action/profile wire from the agreed Issue25 design2.

Cross-resource authorization/CAS is enforced by the transactional service.
"""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictInt, StrictStr, StrictBool, AwareDatetime, model_validator
from app.game_accounts.schemas import DTO
from app.raid_rooms.weekly_summary_schemas import CycleKey
from app.raid_rooms import cycle_wire as legacy
from app.raid_rooms.resume_review_schemas import ResumePlanContext
from app.game_accounts.schemas import GameErrorOut

Action = Literal['leave_target', 'leave_all', 'dissolve_led_targets', 'recover_leadership']

class MembershipActionPermission(DTO):
    allowed: StrictBool
    reason: Annotated[StrictStr, Field(max_length=64)] | None
    next_change_at: AwareDatetime | None
Permission = MembershipActionPermission

class MembershipActionConfirmation(DTO):
    context_token: Annotated[StrictStr, Field(min_length=1, max_length=4096)]
    issued_at: AwareDatetime
    expires_at: AwareDatetime
Confirmation = MembershipActionConfirmation

class MembershipActionScope(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    view_cycle_key: CycleKey
    policy_version: Literal['membership-actions-1']
Scope = MembershipActionScope

class MembershipActionRevisionRule(DTO):
    before: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    comparison: Literal['equal', 'increase']
    exact_after: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
RevisionRule = MembershipActionRevisionRule

class MembershipActionLeadership(DTO):
    leader_cycle_member_id: UUID | None
    leader_membership_id: UUID | None
    leadership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
Leadership = MembershipActionLeadership

class MembershipActionPlannedLeadership(DTO):
    leader_cycle_member_id: UUID | None
    leader_membership_id: UUID | None
    leadership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    status: Literal['active', 'pending_review', 'closed']
    recovery_reason: Annotated[StrictStr, Field(max_length=64)] | None
PlannedLeadership = MembershipActionPlannedLeadership

class MembershipActionActor(DTO):
    membership_id: UUID
    membership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
Actor = MembershipActionActor

class MembershipActionCleanup(DTO):
    released_reservation_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
    ended_participation_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
    cancelled_application_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
    cancelled_session_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
Cleanup = MembershipActionCleanup

class MembershipActionSuccessor(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    cycle_member_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    planned_cycle_member_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    character_id: UUID
    character_name: Annotated[StrictStr, Field(max_length=64)] | None
    joined_order: Annotated[StrictStr, Field(max_length=20, pattern='^[1-9][0-9]*$')]
Successor = MembershipActionSuccessor

class MembershipActionMemberEffect(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    cycle_member_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    character_id: UUID | None
    character_name: Annotated[StrictStr, Field(max_length=64)] | None
    joined_order: Annotated[StrictStr, Field(max_length=20, pattern='^[1-9][0-9]*$')] | None
    revision_rule: RevisionRule
    planned_state: Literal['participating', 'review_required', 'cancelled', 'removed', 'completed', 'stopped']
    cancelled_assignment_ids: Annotated[list[UUID], Field(min_length=0, max_length=5)]
    preserved_completed_assignment_ids: Annotated[list[UUID], Field(min_length=0, max_length=5)]
    state: Literal['participating', 'review_required', 'cancelled', 'removed', 'completed', 'stopped']
MemberEffect = MembershipActionMemberEffect

class MembershipActionTargetRevisionRules(DTO):
    target: RevisionRule
    members: RevisionRule
    plan: RevisionRule
    leadership: RevisionRule
TargetRevisionRules = MembershipActionTargetRevisionRules

class MembershipActionTargetPlan(DTO):
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    target_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    members_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    plan_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    target_state: Literal['open', 'review_required', 'closed']
    generation_state: Literal['open', 'review_required', 'cancelled', 'completed', 'stopped']
    planned_target_state: Literal['open', 'review_required', 'closed']
    planned_generation_state: Literal['open', 'review_required', 'cancelled', 'completed', 'stopped']
    revision_rules: TargetRevisionRules
    leadership_before: Leadership
    transition: Literal['leave', 'automatic_successor', 'leadership_pending', 'close_empty', 'dissolve', 'recover', 'eligibility_cleanup']
    affected_members: Annotated[list[MemberEffect], Field(min_length=0, max_length=8)]
    successor: Successor | None
    leadership_after: PlannedLeadership
    cleanup: Cleanup
TargetPlan = MembershipActionTargetPlan

class MembershipActionRoomEffect(DTO):
    kind: Literal['preserve', 'preserve_review', 'end']
    actor_membership_will_end: StrictBool
    ended_persistent_membership_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
    preserves_unaffected_cycles: Literal[True]
    room_revision_rule: RevisionRule
    actor_membership_revision_rule: RevisionRule
RoomEffect = MembershipActionRoomEffect

class MembershipActionImpact(DTO):
    action: Action
    affected_cycle_keys: Annotated[list[CycleKey], Field(min_length=0, max_length=2)]
    targets: Annotated[list[TargetPlan], Field(min_length=0, max_length=2)]
    room_effect: RoomEffect
    existing_completion_preserved: Literal[True]
    display_revision: Annotated[StrictStr, Field(pattern='^[0-9a-f]{64}$')]
Impact = MembershipActionImpact

class MembershipActionOption(DTO):
    visible: StrictBool
    permission: Permission
    impact: Impact | None
    confirmation: Confirmation | None
Option = MembershipActionOption

class MembershipActionOptions(DTO):
    leave_target: Option
    leave_all: Option
    dissolve_led_targets: Option
    recover_leadership: Option
Options = MembershipActionOptions

class MembershipActionMenuData(DTO):
    room_id: UUID
    room_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    actor: Actor
    options: Options
MenuData = MembershipActionMenuData

class MembershipActionContext(DTO):
    scope: Scope
    data: MenuData
Context = MembershipActionContext

class MembershipActionCommand(DTO):
    expected_cycle_key: CycleKey
    view_cycle_key: CycleKey
    actor_membership_id: UUID
    expected_actor_membership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    action: Action
    context_token: Annotated[StrictStr, Field(min_length=1, max_length=4096)]

    @model_validator(mode="after")
    def command_bounds(self):
        if len(self.context_token.encode()) > 4096: raise ValueError("Token too large")
        return self
Command = MembershipActionCommand

class MembershipActionMemberResult(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    cycle_member_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    state: Literal['participating', 'review_required', 'cancelled', 'removed', 'completed', 'stopped']
    cancelled_assignment_ids: Annotated[list[UUID], Field(min_length=0, max_length=5)]
    preserved_completed_assignment_ids: Annotated[list[UUID], Field(min_length=0, max_length=5)]
MemberResult = MembershipActionMemberResult

class MembershipActionTargetResult(DTO):
    target_cycle_key: CycleKey
    room_cycle_id: UUID
    target_generation: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    target_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    members_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    plan_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    target_state: Literal['open', 'review_required', 'closed']
    generation_state: Literal['open', 'review_required', 'cancelled', 'completed', 'stopped']
    leadership: Leadership
    leadership_status: Literal['active', 'pending_review', 'closed']
    recovery_reason: Annotated[StrictStr, Field(max_length=64)] | None
    members: Annotated[list[MemberResult], Field(min_length=0, max_length=8)]
TargetResult = MembershipActionTargetResult

class MembershipActionResultData(DTO):
    command_id: UUID
    action: Action
    outcome: Literal['applied']
    executed_at: AwareDatetime
    room_id: UUID
    room_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    actor_membership_id: UUID
    actor_membership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    actor_membership_ended: StrictBool
    affected_cycle_keys: Annotated[list[CycleKey], Field(min_length=0, max_length=2)]
    effects: Annotated[list[TargetResult], Field(min_length=0, max_length=2)]
    room_ended: StrictBool
    ended_persistent_membership_count: Annotated[StrictInt, Field(ge=0, le=2147483647)]
ResultData = MembershipActionResultData

class MembershipActionResult(DTO):
    scope: Scope
    data: ResultData
Result = MembershipActionResult

class MembershipActionReaderScope(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    target_cycle_key: CycleKey
    policy_version: Literal['membership-actions-1']
    reader_kind: Literal['detail', 'plan', 'memberships']
ReaderScope = MembershipActionReaderScope

class MembershipActionRecordLocator(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    room_cycle_id: UUID
    target_cycle_key: CycleKey
    target_generation: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
RecordLocator = MembershipActionRecordLocator

class MembershipActionReaderTarget(DTO):
    room_id: UUID
    title: Annotated[StrictStr, Field(max_length=60)]
    room_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    room_state: Literal['active', 'ended']
    target_cycle_key: CycleKey
    room_cycle_id: UUID | None
    target_generation: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
    target_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
    target_state: Literal['open', 'review_required', 'closed'] | None
    generation_state: Literal['open', 'review_required', 'cancelled', 'completed', 'stopped'] | None
    leadership: Leadership | None
ReaderTarget = MembershipActionReaderTarget

class MembershipActionReaderRelation(DTO):
    membership_id: UUID
    membership_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    membership_state: Literal['active', 'ended']
    cycle_member_id: UUID | None
    cycle_member_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
    cycle_member_state: Literal['participating', 'review_required', 'cancelled', 'removed', 'completed', 'stopped', 'not_selected']
    joined_order: Annotated[StrictStr, Field(max_length=20, pattern='^[1-9][0-9]*$')] | None
    role: Literal['leader', 'member', 'none']
    mode: Literal['participant', 'retained', 'recovery', 'record', 'relation_only']
    record_locator: RecordLocator | None
ReaderRelation = MembershipActionReaderRelation

class MembershipActionReaderAccess(DTO):
    state: Literal['allowed']
    basis: Literal['current_membership', 'historical_membership', 'target_record']
    read_only: StrictBool
    evaluated_at: AwareDatetime
ReaderAccess = MembershipActionReaderAccess

class MembershipActionRecovery(DTO):
    state: Literal['none', 'leadership_pending', 'review_remaining', 'unverified']
    reason: Annotated[StrictStr, Field(max_length=64)] | None
    revision: Annotated[StrictInt, Field(ge=1, le=2147483647)] | None
    remaining_review_reasons: Annotated[list[Annotated[StrictStr, Field(max_length=64)]], Field(min_length=0, max_length=16)]
    menu_access: StrictBool
    can_request_recovery: Permission
Recovery = MembershipActionRecovery

class MembershipActionReaderPermissions(DTO):
    view_detail: Permission
    view_plan: Permission
    manage_target: Permission
    resume_weekly: Permission
    read_action_menu: Permission
ReaderPermissions = MembershipActionReaderPermissions

class MembershipActionRecordRound(DTO):
    item_id: UUID
    round_id: UUID
    raid_id: Annotated[StrictStr, Field(max_length=64)]
    difficulty_id: Annotated[StrictStr, Field(max_length=64)]
    catalog_version: Annotated[StrictStr, Field(max_length=64)]
    state: Literal['active', 'completed', 'stopped_incomplete', 'legacy_ended']
RecordRound = MembershipActionRecordRound

class MembershipActionRecordAssignment(DTO):
    assignment_id: UUID
    item_id: UUID
    round_id: UUID
    character_id: UUID
    character_name: Annotated[StrictStr, Field(max_length=64)] | None
    raid_id: Annotated[StrictStr, Field(max_length=64)]
    difficulty_id: Annotated[StrictStr, Field(max_length=64)]
    catalog_version: Annotated[StrictStr, Field(max_length=64)]
    state: Literal['active', 'completed', 'left', 'stopped_incomplete', 'legacy_ended']
    completion_source: Literal['manual', 'party'] | None
    completed_at: AwareDatetime | None
    ended_at: AwareDatetime | None
RecordAssignment = MembershipActionRecordAssignment

class MembershipActionRecordSegment(DTO):
    segment_id: UUID
    round_id: UUID
    session_id: UUID
    starts_at: AwareDatetime | None
    ends_at: AwareDatetime | None
    state: Literal['planned', 'released']
RecordSegment = MembershipActionRecordSegment

class MembershipActionRecordSnapshot(DTO):
    locator: RecordLocator
    rounds: Annotated[list[RecordRound], Field(min_length=0, max_length=5)]
    assignments: Annotated[list[RecordAssignment], Field(min_length=0, max_length=40)]
    schedule_segments: Annotated[list[RecordSegment], Field(min_length=0, max_length=40)]
RecordSnapshot = MembershipActionRecordSnapshot
LegacyDetail = legacy.OutputContract3GetV2RaidRoomsRoomIdDetail
LegacyPlan = ResumePlanContext
LegacyMembership = legacy.BMembership

class MembershipActionDetailProfileData(DTO):
    target: ReaderTarget
    viewer: ReaderRelation
    access: ReaderAccess
    recovery: Recovery
    permissions: ReaderPermissions
    content: LegacyDetail | None
    record: RecordSnapshot | None
DetailProfileData = MembershipActionDetailProfileData

class MembershipActionDetailReaderScope(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    target_cycle_key: CycleKey
    policy_version: Literal['membership-actions-1']
    reader_kind: Literal['detail']
DetailReaderScope = MembershipActionDetailReaderScope

class MembershipActionDetailProfile(DTO):
    scope: DetailReaderScope
    data: DetailProfileData
DetailProfile = MembershipActionDetailProfile

class MembershipActionPlanProfileData(DTO):
    target: ReaderTarget
    viewer: ReaderRelation
    access: ReaderAccess
    recovery: Recovery
    permissions: ReaderPermissions
    content: LegacyPlan | None
    record: RecordSnapshot | None
PlanProfileData = MembershipActionPlanProfileData

class MembershipActionPlanReaderScope(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    target_cycle_key: CycleKey
    policy_version: Literal['membership-actions-1']
    reader_kind: Literal['plan']
PlanReaderScope = MembershipActionPlanReaderScope

class MembershipActionPlanProfile(DTO):
    scope: PlanReaderScope
    data: PlanProfileData
PlanProfile = MembershipActionPlanProfile

class MembershipActionMembershipEntry(DTO):
    target: ReaderTarget
    viewer: ReaderRelation
    recovery: Recovery
    permissions: ReaderPermissions
    content: LegacyMembership | None
MembershipEntry = MembershipActionMembershipEntry

class MembershipActionMembershipPageData(DTO):
    items: Annotated[list[MembershipEntry], Field(min_length=0, max_length=50)]
    membership_head: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    next_cursor: Annotated[StrictStr, Field(max_length=2048)] | None
    evaluated_at: AwareDatetime
MembershipPageData = MembershipActionMembershipPageData

class MembershipActionMembershipReaderScope(DTO):
    server_now: AwareDatetime
    current_cycle_key: CycleKey
    target_cycle_key: CycleKey
    policy_version: Literal['membership-actions-1']
    reader_kind: Literal['memberships']
MembershipReaderScope = MembershipActionMembershipReaderScope

class MembershipActionMembershipPage(DTO):
    scope: MembershipReaderScope
    data: MembershipPageData
MembershipPage = MembershipActionMembershipPage
Error = GameErrorOut
