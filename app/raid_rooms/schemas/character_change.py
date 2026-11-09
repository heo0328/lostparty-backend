"""Replace an actor's unfinished bundle selection under exact source CAS."""

import uuid

from app.raid_rooms.schemas.admission_schemas import Admission
from app.raid_rooms.schemas.admission_schemas import DTO
from app.raid_rooms.schemas.admission_schemas import Version

class AssignmentCAS(DTO):
    assignment_id: uuid.UUID
    expected_revision: Version

class ChoiceCAS(DTO):
    choice_id: uuid.UUID
    expected_revision: Version

class Change(Admission):
    expected_membership_revision: Version
    assignments: list[AssignmentCAS]
    choices: list[ChoiceCAS]
