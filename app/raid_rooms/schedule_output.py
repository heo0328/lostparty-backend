"""Typed schedule graph output shared by the canonical plan response."""
from datetime import datetime
from uuid import UUID
from typing import Literal
from app.raid_rooms.availability_schemas import DTO,Version,Clock


class Permission(DTO):
    allowed: bool
    reason: str|None


class Alternative(DTO):
    alternative_id: UUID
    session_id: UUID|None
    weekday: int
    starts_local: Clock|None
    leader_latest_start_local: Clock|None
    item_ids: list[UUID]


class Group(DTO):
    group_id: UUID
    revision: Version
    client_group_key: str
    occurrence_mode: Literal['one_of','each']
    planning_mode: Literal['unscheduled','manual','coordinated']
    day_scope: Literal['any_current_cycle','selected_weekdays']
    required: bool
    auto_confirm_additional_members: int|None
    alternatives: list[Alternative]
    selected_session_id: UUID|None
    resolution: Literal['selected','all','unresolved']
    candidate_state: Literal['ready','no_candidate','search_limited','not_evaluated']
    permissions: dict[str,Permission]


class Session(DTO):
    session_id: UUID
    revision: Version
    round_ids: list[UUID]
    required: bool
    mode: Literal['unscheduled','manual','coordinated']
    state: Literal['unconfirmed','confirmed','finished','cancelled','legacy_review_required']
    schedule_revision: Version
    starts_at: datetime|None
    ends_at: datetime|None
    duration_minutes: int
    duration_source: str
    duration_policy_version: str
    earliest_start: datetime|None
    latest_start: datetime|None
    join_deadline: datetime|None
    candidate_state: Literal['ready','no_candidate','search_limited','not_evaluated']
    permissions: dict[str,Permission]


class Segment(DTO):
    segment_id: UUID
    item_id: UUID
    round_id: UUID
    starts_at: datetime|None
    ends_at: datetime|None
    duration_minutes: int|None
    duration_source: str
    policy_version: str
    state: Literal['planned','released']
    released_reason: str|None


class SegmentSet(DTO):
    session_id: UUID
    segments: list[Segment]


class Participation(DTO):
    participation_id: UUID
    revision: Version
    session_id: UUID
    assignment_ids: list[UUID]
    state: Literal['active','ended']
    required: bool
    participating: bool
    confirmation_state: Literal['not_required','confirmation_pending','confirmed']
    confirmed_at: datetime|None
    confirmed_schedule_revision: Version|None
    reservation_state: Literal['active','partial','released','none']
    overlap_warning: bool
    warnings: list[Literal['TIME_OVERLAP','OUTSIDE_AVAILABILITY']]
    permissions: dict[str,Permission]


class BaseSchedule(DTO):
    session_id: UUID
    schedule_revision: Version


class Vote(DTO):
    session_id: UUID
    eligible_count: int
    accepted_count: int
    required_votes: int
    satisfied: bool


class Response(DTO):
    proposal_id: UUID
    proposal_plan_revision: Version
    membership_id: UUID
    membership_generation: Version
    response: Literal['pending','accept','reject']
    response_revision: Version
    responded_at: datetime|None
    response_set: Literal['existing','newcomer']


class ScheduleProposal(DTO):
    proposal_id: UUID
    revision: Version
    proposal_plan_revision: Version
    created_from_plan_revision: Version
    state: Literal['pending','applied','cancelled','obsolete']
    target_session_ids: list[UUID]
    base_schedules: list[BaseSchedule]
    proposed_sessions: list[SegmentSet]
    votes: list[Vote]
    my_response: Response
    permissions: dict[str,Permission]


class ResumeProposal(DTO):
    proposal_id: UUID
    kind: Literal['weekly_resume']
    revision: Version
    proposal_plan_revision: Version
    created_from_plan_revision: Version
    state: Literal['pending','applied','obsolete']
    target_round_ids: list[UUID]
    eligible_count: int
    accepted_count: int
    required_votes: int
    my_response: Literal['pending','accept','reject']
    permissions: dict[str,Permission]
