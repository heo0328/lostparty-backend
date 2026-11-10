"""Optional retained group link on authorized detail/plan, in the same snapshot."""

from typing import Literal

from pydantic import Field
from pydantic import model_validator

from app.raid_rooms.schemas.cycle_group_schemas import Metadata

from uuid import UUID

from app.game_accounts.schemas.schemas import DTO

from app.raid_rooms.schemas import cycle_wire
from app.raid_rooms.schemas import membership_action_schemas
from app.raid_rooms.schemas import application_display_schemas
from app.raid_rooms.schemas import resume_review_schemas

class GroupLinkState(DTO):
    group_id: UUID
    name: str | None
    state: Literal['active', 'ended', 'unavailable']

class GroupLinkedDetail(cycle_wire.OutputContract3GetV2RaidRoomsRoomIdDetail):
    group_state: GroupLinkState | None

class GroupLinkedMembershipDetail(membership_action_schemas.DetailProfile):
    group_state: GroupLinkState | None

class GroupLinkedApplicationDetail(application_display_schemas.ApplicationDisplayDetailResponse):
    group_state: GroupLinkState | None

class GroupLinkedPlan(resume_review_schemas.ResumePlanContext):
    group_state: GroupLinkState | None

class GroupLinkedMembershipPlan(membership_action_schemas.PlanProfile):
    group_state: GroupLinkState | None

class RoomGroupLink(DTO):
    room_id: UUID
    group_id: UUID | None

class ListGroupMetadata(DTO):
    group_states: list[GroupLinkState]
    room_groups: list[RoomGroupLink] | None = Field(default=None,exclude_if=lambda v:v is None)
    cycle_groups: list[Metadata] | None = Field(default=None,exclude_if=lambda v:v is None)

    @model_validator(mode='after')
    def exactly_one_mapping(self):
        if (self.room_groups is None)==(self.cycle_groups is None):raise ValueError('one explicit group mapping required')
        return self

class GroupSearchPage(cycle_wire.OutputContract3PostV2RaidRoomsSearch,ListGroupMetadata):
    pass

class GroupApplicationPage(cycle_wire.OutputContract3GetV2RaidRoomsRoomIdApplications,ListGroupMetadata):
    pass

class GroupMembershipPage(cycle_wire.OutputContract3GetV2MeRaidRoomMemberships,ListGroupMetadata):
    pass

class GroupActionMembershipPage(membership_action_schemas.MembershipPage,ListGroupMetadata):
    pass
