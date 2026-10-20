"""Integrated R2-C DTOs. Scheduling execution is connected in R3."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from app.raid_rooms.availability_schemas import DTO, Version, Clock
from app.raid_rooms.participation_commands import Selection, Target
from app.raids.schemas import Identifier
from app.game_accounts.profile_schemas import AnalysisIssue
from app.raid_rooms import schedule_output as scheduling

DecimalValue=Annotated[StrictStr,Field(max_length=32,pattern=r'^[0-9]+(?:\.[0-9]+)?$')]
Experience=Literal['tryLevel','clearExp','multiClearExp','semiExperienced','experienced']


class Permission(DTO):
    allowed: StrictBool
    reason: str|None


class ContextRef(DTO):
    context_token: Annotated[StrictStr,Field(min_length=67,max_length=67)]


class Combat(DTO):
    input_mode: Literal['shared','per_role']
    dealer_min: DecimalValue|None
    support_min: DecimalValue|None

    @model_validator(mode='after')
    def shared(self):
        if self.input_mode=='shared' and self.dealer_min!=self.support_min:raise ValueError('shared values differ')
        return self


class Continuation(DTO):
    enabled: StrictBool
    auto_open_enabled: StrictBool

    @model_validator(mode='after')
    def enabled_auto(self):
        if self.auto_open_enabled and not self.enabled:raise ValueError('auto opening requires continuation')
        return self


class Alternative(DTO):
    client_alternative_key: Annotated[StrictStr,Field(min_length=1,max_length=64)]
    existing_session_id: UUID|None
    expected_session_revision: Version|None
    weekday: Annotated[StrictInt,Field(ge=1,le=7)]
    starts_local: Clock|None
    leader_latest_start_local: Clock|None
    item_order: list[Identifier]


class ScheduleGroup(DTO):
    client_group_key: Annotated[StrictStr,Field(min_length=1,max_length=64)]
    existing_group_id: UUID|None
    expected_group_revision: Version|None
    occurrence_mode: Literal['one_of','each']
    planning_mode: Literal['unscheduled','manual','coordinated']
    required: StrictBool
    auto_confirm_additional_members: Annotated[StrictInt,Field(ge=1,le=7)]|None
    day_scope: Literal['any_current_cycle','selected_weekdays']
    alternatives: list[Alternative]


class ItemChoice(DTO):
    raid_id: Identifier
    difficulty_id: Identifier


class CreateItem(ItemChoice):
    duration_minutes: Annotated[StrictInt,Field(ge=10,le=1440,multiple_of=5)]|None
    expected_weekly_revision: Version
    party_no: Annotated[Version,Field(le=2)]


class Create(DTO):
    title: Annotated[StrictStr,Field(min_length=1,max_length=60)]
    scope: Literal['public','group']
    group_id: UUID|None
    admission_mode: Literal['leader_only','direct_join']
    app_mode: Literal['single','mixed_bundle']
    items: Annotated[list[CreateItem],Field(min_length=1)]
    selection: Selection
    selection_context: ContextRef
    experience_level: Experience|None
    combat_requirement: Combat
    continuation: Continuation
    schedule_groups: list[ScheduleGroup]
    expected_cycle_key: str
    expected_catalog_version: str
    expected_group_revision: Version|None

    @model_validator(mode='after')
    def shape(self):
        if self.scope=='group' and self.group_id is None:
            raise ValueError('group scope requires matching group context')
        if (self.group_id is None)!=(self.expected_group_revision is None):raise ValueError('linked group context')
        if len({i.raid_id for i in self.items})!=len(self.items):raise ValueError('duplicate raid')
        if (self.app_mode=='single') != (len(self.items)==1):raise ValueError('app mode')
        return self


class Admission(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_members_revision: Version
    expected_plan_revision: Version
    expected_policy_snapshot: str
    expected_catalog_version: str
    selection_context: ContextRef
    selection: Selection
    target_items: Annotated[list[Target],Field(min_length=1)]
    target_session_ids: list[UUID]


class Approve(DTO):
    expected_cycle_key: str
    expected_application_revision: Version
    expected_room_revision: Version
    expected_members_revision: Version
    expected_plan_revision: Version


class ApplicationCAS(DTO):
    expected_application_revision: Version


class ResourceRevision(DTO):
    resource: Literal['room','members','plan','item','round','membership','assignment','application','session','participation','proposal','choice','weekly','continuation','ownership','settings']
    id: UUID
    revision: Version


class Ack(DTO):
    command_id: UUID
    outcome: Literal['applied','recorded','noop']
    revisions: list[ResourceRevision]
    executed_at: datetime


class ApplicationAck(DTO):
    command_id: UUID
    room_id: UUID
    application_id: UUID
    revision: Version
    state: Literal['pending','accepted','rejected','withdrawn','expired','cancelled']
    executed_at: datetime


class PowerComparison(DTO):
    selected_role: Literal['dealer','support']
    requirement: DecimalValue|None
    actual: DecimalValue|None
    state: Literal['unrestricted','missing','below','meets']
    source: Literal['flutter_analysis']
    trust: Literal['client_submitted']
    current_summary_version: Version
    success_summary_version: Version|None
    power_revision: Version
    observed_at: datetime|None
    success_saved_at: datetime|None
    success_issues: list[AnalysisIssue]
    current_issues: list[AnalysisIssue]


class CreateTarget(ItemChoice):
    expected_weekly_revision: Version


class ExperienceChoice(DTO):
    value: Experience
    label: str


class Defaults(DTO):
    auto_open_default: StrictBool
    experience_levels: list[ExperienceChoice]
    experience_unrestricted_value: None


class CreationContext(DTO):
    expected_cycle_key: str
    server_time: datetime
    catalog_version: str
    policy_snapshot: str
    context_token: str
    selection: Selection
    targets: list[CreateTarget]
    group_revision: Version|None
    settings_defaults: Defaults
    comparison: PowerComparison
    permissions: dict[str,Permission]


class AdmissionContext(DTO):
    room_id: UUID
    room_revision: Version
    members_revision: Version
    plan_revision: Version
    expected_cycle_key: str
    server_time: datetime
    catalog_version: str
    policy_snapshot: str
    context_token: str
    selection: Selection
    targets: list[Target]
    session_choices: list[dict]
    comparison: PowerComparison
    permissions: dict[str,Permission]


class GameItem(DTO):
    item_id: UUID
    revision: Version
    raid_id: str
    difficulty_id: str
    catalog_version: str
    game_party_size: Literal[4,8]
    round_id: UUID
    round_revision: Version
    round_state: str


class MyMembership(DTO):
    membership_id: UUID
    revision: Version
    room_role: Literal['leader','member']
    group_member: StrictBool


class AssignmentView(DTO):
    assignment_id: UUID
    revision: Version
    membership_id: UUID
    item_id: UUID
    round_id: UUID
    cycle_key: str
    character_id: UUID
    selected_role: Literal['dealer','support']
    state: str
    ended_at: datetime|None
    raid_participation_state: str
    completion_source: str|None
    completed_at: datetime|None


class Plan(DTO):
    room_id: UUID
    revision: Version
    members_revision: Version
    cycle_key: str
    server_time: datetime
    app_capacity: Literal[4,8]
    game_items: list[GameItem]
    schedule_state: Literal['unscheduled','unconfirmed','confirmed','change_pending']
    schedule_groups: list[scheduling.Group]
    sessions: list[scheduling.Session]
    session_segments: list[scheduling.SegmentSet]
    my_membership: MyMembership
    my_assignments: list[AssignmentView]
    my_participations: list[scheduling.Participation]
    proposals: list[scheduling.ScheduleProposal|scheduling.ResumeProposal]
    permissions: dict[str,Permission]


class ApplicationView(DTO):
    application_id: UUID
    room_id: UUID
    revision: Version
    state: str
    created_at: datetime
    expires_at: datetime
    ended_at: datetime|None
    display: dict[str,str|None]
    character_id: UUID
    selected_role: Literal['dealer','support']
    admission_origin: dict[str,str|None]


class Eligibility(DTO):
    evaluated_at: datetime
    state: Literal['eligible','blocked','unavailable']
    reasons: list[str]
    comparison: PowerComparison|None


class Review(DTO):
    application: ApplicationView
    room_revision: Version
    members_revision: Version
    plan_revision: Version
    server_time: datetime
    eligibility: Eligibility
    permissions: dict[str,Permission]
