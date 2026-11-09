"""Completion, whole-membership cleanup and weekly closure are distinct effects."""

import uuid

from typing import Literal
from typing import Annotated

from pydantic import Field

from app.raid_rooms.common import command_context as contexts

from app.raid_rooms.schemas.availability_schemas import DTO
from app.raid_rooms.schemas.availability_schemas import Version

class ContextRequest(DTO):
    expected_cycle_key: str
    context_token: Annotated[str,Field(max_length=contexts.MAX_TOKEN_BYTES)]

class ContinuationResolution(DTO):
    action: Literal['keep','release']
    expected_choices_revision: Version

class LeadershipResolution(DTO):
    action: Literal['transfer','end']
    target_membership_id: uuid.UUID|None
    expected_target_revision: Version|None

class Personal(ContextRequest):
    continuation_resolution: ContinuationResolution|None
    leadership_resolution: LeadershipResolution|None

class MembershipCommand(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_members_revision: Version
    expected_plan_revision: Version
    expected_membership_revision: Version

class Transfer(MembershipCommand):
    target_membership_id: uuid.UUID
    expected_target_revision: Version
