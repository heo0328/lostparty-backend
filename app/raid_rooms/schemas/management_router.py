from uuid import UUID

from datetime import date

from app.raid_rooms.schemas.admission_schemas import DTO
from app.raid_rooms.schemas.admission_schemas import Version
from app.raid_rooms.schemas.admission_schemas import Permission
from app.raid_rooms.schemas.admission_schemas import Combat
from app.raid_rooms.schemas.admission_schemas import Experience

from typing import Literal

class ContinuationSettings(DTO):
    enabled: bool
    auto_open_enabled: bool
    revision: Version
    auto_open_effective_cycle: date|None

class Settings(DTO):
    room_id: UUID
    revision: Version
    room_revision: Version
    experience_level: Experience|None
    combat_requirement: Combat
    continuation: ContinuationSettings
    scope: Literal['public','group']
    group_id: UUID|None
    admission_mode: Literal['leader_only','direct_join']
    permissions: dict[str,Permission]
