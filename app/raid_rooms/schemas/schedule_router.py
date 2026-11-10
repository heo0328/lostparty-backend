from uuid import UUID

from app.raid_rooms.schemas.admission_schemas import DTO
from app.raid_rooms.schemas.admission_schemas import Version

from datetime import datetime

from typing import Literal

class Candidate(DTO):
    group_id: UUID
    revision: Version
    plan_revision: Version
    evaluated_at: datetime
    state: Literal['ready','no_candidate','search_limited']
    earliest_start: datetime|None
    latest_start: datetime|None
