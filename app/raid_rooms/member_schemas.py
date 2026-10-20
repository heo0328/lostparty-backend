from datetime import datetime
from uuid import UUID
from typing import Literal
from app.raid_rooms.admission_schemas import DTO,Version,Permission,MyMembership,PowerComparison
from app.raid_rooms.search_router import Card
from app.raid_rooms.management_router import Settings
from app.raid_rooms.availability_schemas import NormalizedInterval,SubmissionOut


class Assignment(DTO):
    assignment_id: UUID
    item_id: UUID
    round_id: UUID
    state: str
    party_no: int
    slot_no: int


class Character(DTO):
    character_id: UUID
    display: dict[str,str|None]
    selected_role: Literal['dealer','support']


class RoomMember(DTO):
    membership_id: UUID
    revision: Version
    room_role: Literal['leader','member']
    group_member: bool
    joined_at: datetime
    character: Character|None
    assignments: list[Assignment]
    comparison: PowerComparison|None
    build: dict|None
    is_me: bool
    status: str
    status_reason: str|None


class Access(DTO):
    state: str
    policy_snapshot: str
    evaluated_at: datetime
    issues: list[str]


class Detail(DTO):
    room: Card
    settings: Settings|None
    members_revision: Version
    members: list[RoomMember]
    my_membership: MyMembership|None
    plan_revision: Version
    permissions: dict[str,Permission]
    access: Access


class OwnAssignment(DTO):
    assignment_id: UUID
    revision: Version
    item_id: UUID
    round_id: UUID
    character_id: UUID
    selected_role: Literal['dealer','support']
    state: str


class Membership(DTO):
    membership_id: UUID
    revision: Version
    room_id: UUID
    state: Literal['current','ended']
    room_role: Literal['leader','member']
    joined_at: datetime
    ended_at: datetime|None
    current_week_state: Literal['participating','completed','stopped','next_week_only']
    next_week_choice_state: Literal['selected','not_selected','blocked']
    assignments: list[OwnAssignment]
    room: Card|None
    recovery_only: bool
    history_only: bool
    permissions: dict[str,Permission]


class MembershipPage(DTO):
    items: list[Membership]
    membership_head: Version
    next_cursor: str|None
    evaluated_at: datetime


class Origin(DTO):
    scope: Literal['public','group']|None
    group_id: UUID|None


class Application(DTO):
    application_id: UUID
    room_id: UUID
    revision: Version
    state: str
    created_at: datetime
    expires_at: datetime|None
    ended_at: datetime|None
    character_id: UUID
    selected_role: Literal['dealer','support']
    display: dict[str,str|None]
    admission_origin: Origin


class ApplicationPage(DTO):
    items: list[Application]
    applications_revision: Version
    next_cursor: str|None
    evaluated_at: datetime


class Busy(DTO):
    starts_at: datetime
    ends_at: datetime


class AnonymousBusy(DTO):
    state: Literal['ready','unavailable']
    revision: Version
    intervals: list[Busy]


class TimeMember(DTO):
    membership_id: UUID
    display: dict[str,str|None]|None
    submission: SubmissionOut
    anonymous_busy: AnonymousBusy


class TimeContext(DTO):
    room_id: UUID
    cycle_key: str
    members_revision: Version
    plan_revision: Version
    evaluated_at: datetime
    members: list[TimeMember]
    target_session_id: UUID|None
    permissions: dict[str,Permission]


class Endpoint(Busy):
    reservation_id: UUID
    room_id: UUID
    item_ids: list[UUID]
    session_id: UUID
    character_id: UUID
    character_display: dict[str,str|None]
    raid_display: dict[str,str]
    room_title: str


class Overlap(Busy):
    pair_id: str
    left: Endpoint
    right: Endpoint


class OverlapPage(DTO):
    cycle_key: str
    items: list[Overlap]
    pair_count: int
    affected_room_count: int
    reservation_count: int
    revision: str
    next_cursor: str|None
    evaluated_at: datetime


class ProjectionMember(DTO):
    raid_membership_id: UUID
    group_membership_id: UUID|None
    member_ref: str|None
    character_id: UUID
    display: dict[str,str|None]
    group_member: bool


class Projection(DTO):
    room_id: UUID
    members: list[ProjectionMember]


class ProjectionPage(DTO):
    group_id: UUID
    members_revision: Version
    evaluated_at: datetime
    rooms: list[Projection]
