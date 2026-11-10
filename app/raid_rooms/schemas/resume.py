"""Weekly resume creates new generations; completed history is immutable."""

from app.raid_rooms.schemas.completion import MembershipCommand

from app.raid_rooms.schemas.schedule_schemas import EditGroup

class ResumeRequest(MembershipCommand):
    # null retains the stopped intent; [] explicitly resumes without sessions.
    schedule_groups: list[EditGroup]|None
