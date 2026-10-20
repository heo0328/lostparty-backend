from uuid import UUID
from datetime import datetime
from typing import Literal
from app.raid_rooms.admission_schemas import DTO,Version,Permission


class Impact(DTO):
    round_ids: list[UUID]
    membership_count: int
    assignment_count: int
    reservation_segment_count: int
    completed_preserved_count: int


class Continuation(DTO):
    required: bool
    choices_revision: Version|None
    current_choice: Literal['keep']|None


class Candidate(DTO):
    membership_id: UUID
    revision: Version
    display: dict[str,str|None]|None


class Leadership(DTO):
    required: bool
    transfer_candidates: list[Candidate]
    can_end: bool


class Context(DTO):
    room_id: UUID
    command: Literal['close_weekly','complete_item','personal_completion']
    cycle_key: str
    actor_membership_id: UUID
    actor_membership_revision: Version
    room_revision: Version
    members_revision: Version
    plan_revision: Version
    target_round_id: UUID|None
    effect_scope: Literal['room_current_week','personal_item','item_round']
    impact: Impact
    continuation: Continuation
    leadership: Leadership
    permission: Permission
    issued_at: datetime
    expires_at: datetime
    context_token: str
