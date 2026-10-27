"""Internal R2 inputs, matching R3 contract; no HTTP activation here."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field
from app.raid_rooms.availability_schemas import DTO, Version


class Selection(DTO):
    registration_id: UUID
    character_id: UUID
    selected_role: Literal['dealer','support']
    expected_registration_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_lifecycle_revision: Version
    expected_role_summary_version: Version
    expected_limits_revision: Version
    expected_usage_revision: Version


class Target(DTO):
    item_id: UUID
    round_id: UUID
    party_no: Annotated[Version, Field(le=2)]
    expected_round_revision: Version
    expected_weekly_revision: Version
