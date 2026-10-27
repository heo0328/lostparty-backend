from datetime import datetime,timedelta
from typing import Annotated,Literal
from uuid import UUID
from pydantic import Field,StrictInt,StrictStr,field_validator
from app.raid_rooms.availability_schemas import DTO,Version,Clock
from app.raid_rooms.admission_schemas import ScheduleGroup,Alternative


class EditAlternative(DTO):
    client_alternative_key: Annotated[StrictStr,Field(min_length=1,max_length=64)]
    existing_session_id: UUID|None
    expected_session_revision: Version|None
    weekday: Annotated[StrictInt,Field(ge=1,le=7)]
    starts_local: Clock|None
    leader_latest_start_local: Clock|None
    item_ids: list[UUID]


class EditGroup(ScheduleGroup):
    alternatives: list[EditAlternative]


class EditGroups(DTO):
    expected_cycle_key: str
    expected_plan_revision: Version
    expected_members_revision: Version
    groups: list[EditGroup]


class SelectGroup(DTO):
    expected_cycle_key: str
    expected_group_revision: Version
    expected_plan_revision: Version
    expected_members_revision: Version
    alternative_id: UUID|None


class ItemDuration(DTO):
    item_id: UUID
    duration_minutes: Annotated[StrictInt,Field(ge=10,le=1440,multiple_of=5)]|None


class ProposedSession(DTO):
    session_id: UUID
    expected_schedule_revision: Version
    starts_at: datetime
    item_durations: list[ItemDuration]

    @field_validator('starts_at')
    @classmethod
    def utc(cls,value):
        if value.tzinfo is None or value.utcoffset()!=timedelta(0):raise ValueError('UTC required')
        return value


class Propose(DTO):
    expected_cycle_key: str
    expected_plan_revision: Version
    expected_members_revision: Version
    targets: Annotated[list[ProposedSession],Field(min_length=1)]


class Respond(DTO):
    expected_cycle_key: str
    expected_proposal_revision: Version
    expected_proposal_plan_revision: Version
    expected_membership_revision: Version
    response: Literal['accept','reject']


class Confirm(DTO):
    expected_cycle_key: str
    expected_schedule_revision: Version
    expected_membership_revision: Version
    expected_participation_revision: Version
