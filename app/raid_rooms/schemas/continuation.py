"""Future intent is never a present assignment; opening uses stored authority."""

import uuid

from typing import Literal

from pydantic import StrictBool

from app.raid_rooms.schemas.availability_schemas import DTO
from app.raid_rooms.schemas.availability_schemas import Version

class ChoiceInput(DTO):
    item_id: uuid.UUID
    character_id: uuid.UUID
    selected_role: Literal['dealer','support']
    expected_ownership_revision: Version

class Replace(DTO):
    choice_id: uuid.UUID
    revision: Version

class ChoicesIn(DTO):
    target_cycle: str
    expected_membership_revision: Version
    expected_choices_revision: Version
    choices: list[ChoiceInput]
    replaces: list[Replace]

class ContinuationSettingsIn(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_continuation_revision: Version
    enabled: StrictBool
    auto_open_enabled: StrictBool

class OpeningIn(DTO):
    target_cycle: str
    expected_room_revision: Version
    expected_continuation_revision: Version
