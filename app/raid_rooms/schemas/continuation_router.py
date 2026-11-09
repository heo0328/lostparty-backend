from uuid import UUID

from app.raid_rooms.schemas.admission_schemas import DTO
from app.raid_rooms.schemas.admission_schemas import Version
from app.raid_rooms.schemas.admission_schemas import Permission

from typing import Literal

class ChoiceView(DTO):
    choice_id: UUID
    revision: Version
    item_id: UUID
    raid_id: str
    character_id: UUID
    selected_role: Literal['dealer','support']
    state: Literal['selected','blocked']
    blocked_reason: str|None

class Choices(DTO):
    room_id: UUID
    target_cycle: str
    membership_revision: Version
    revision: Version
    items: list[ChoiceView]
    permissions: dict[str,Permission]
