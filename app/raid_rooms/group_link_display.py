"""Optional retained group link on authorized detail/plan, in the same snapshot."""
from typing import Literal
from uuid import UUID
from app.game_accounts.schemas import DTO
from app.groups import features
from app.raid_rooms import admission_service as base, cycle_member_reads as members, membership_readers
from app.raid_rooms import cycle_wire, membership_action_schemas, application_display_schemas, resume_review_schemas
from app.raid_rooms.integrated_models import RecruitmentRoom


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


def get(principal, rid, key, kind, *, reader_profile=None, membership_id=None, cycle_member_id=None,
        include_resume_display=False):
    # Original reader owns authorization, including historical ownership anchors.
    with base.snapshot(principal) as snap:
        db, uid, stamp = snap
        features.ready(db)
        if reader_profile == 'membership-actions-1':
            result = membership_readers.get(principal,rid,key,kind,membership_id=membership_id,
                cycle_member_id=cycle_member_id,include_resume_display=include_resume_display,read_snapshot=snap)
        elif kind == 'detail':
            result = members.detail(principal,rid,key,reader_profile=reader_profile,read_snapshot=snap)
        else:
            result = members.plan(principal,rid,key,include_resume_display,read_snapshot=snap)
        room = db.get(RecruitmentRoom, rid)
        return dict(result, group_state=features.group_state(db,room.group_id))


class RoomGroupLink(DTO):
    room_id: UUID
    group_id: UUID | None


class ListGroupMetadata(DTO):
    group_states: list[GroupLinkState]
    room_groups: list[RoomGroupLink]


class GroupSearchPage(cycle_wire.OutputContract3PostV2RaidRoomsSearch,ListGroupMetadata):
    pass


class GroupApplicationPage(cycle_wire.OutputContract3GetV2RaidRoomsRoomIdApplications,ListGroupMetadata):
    pass


class GroupMembershipPage(cycle_wire.OutputContract3GetV2MeRaidRoomMemberships,ListGroupMetadata):
    pass


class GroupActionMembershipPage(membership_action_schemas.MembershipPage,ListGroupMetadata):
    pass
