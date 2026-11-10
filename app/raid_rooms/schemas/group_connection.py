"""Current own-group evidence for the existing common-settings command."""

from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from app.raid_rooms.schemas import cycle_wire as wire

class TargetGroup(BaseModel):
    model_config=ConfigDict(extra='forbid')
    group_id:UUID
    group_revision:wire.Version
    members_revision:wire.Version
    membership_id:UUID
    membership_revision:wire.Version
    permission:wire.Permission

class GroupConnectionContext(wire.CommonContext):
    target_group:TargetGroup
