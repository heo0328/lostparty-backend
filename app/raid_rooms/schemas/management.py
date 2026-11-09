"""Room management mutates current resources without rewriting completed history."""
import app.raid_rooms.schemas.completion as completion_types

import uuid

from typing import Literal
from typing import Annotated

from pydantic import Field

from app.raid_rooms.schemas.admission_schemas import DTO
from app.raid_rooms.schemas.admission_schemas import Version
from app.raid_rooms.schemas.admission_schemas import Experience
from app.raid_rooms.schemas.admission_schemas import Combat

class RoomSettingsIn(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_settings_revision: Version
    experience_level: Experience|None
    combat_requirement: Combat
    admission_mode: Literal['direct_join','leader_only']

class Visibility(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_members_revision: Version
    expected_settings_revision: Version
    expected_group_revision: Version|None
    scope: Literal['public','group']
    group_id: uuid.UUID|None

class Placement(DTO):
    membership_id: uuid.UUID
    expected_revision: Version
    item_id: uuid.UUID
    party_no: Annotated[Version,Field(le=2)]
    slot_no: Annotated[Version,Field(le=4)]

class Formation(DTO):
    expected_cycle_key: str
    expected_members_revision: Version
    expected_plan_revision: Version
    placements: list[Placement]

class Removal(completion_types.MembershipCommand):
    target_membership_id: uuid.UUID
    expected_target_revision: Version
