"""Additive startup refresh contracts; single-command bodies stay unchanged."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field
from pydantic import StrictStr
from pydantic import UUID4
from pydantic import model_validator

from app.game_accounts.schemas.schemas import DTO
from app.game_accounts.schemas.profile_schemas import PersonalProfileOut
from app.game_accounts.schemas.profile_schemas import RoleSummaryIn
from app.game_accounts.schemas.profile_schemas import RoleSummaryOut


class BatchItemError(DTO):
    code: str
    message: str
    request_id: str
    retry_after_seconds: int | None


class PersonalProfileItem(DTO):
    character_id: UUID
    status: int
    profile: PersonalProfileOut | None
    error: BatchItemError | None


class PersonalProfilesOut(DTO):
    evaluated_at: datetime
    items: list[PersonalProfileItem]


class RoleSummaryCommand(RoleSummaryIn):
    character_id: UUID
    role: StrictStr
    command_id: UUID4


class RoleSummaryBatchIn(DTO):
    items: Annotated[list[RoleSummaryCommand], Field(min_length=1, max_length=50)]

    @model_validator(mode='after')
    def distinct_commands(self):
        keys = [item.command_id for item in self.items]
        targets = [(item.character_id, item.role) for item in self.items]
        if len(set(keys)) != len(keys) or len(set(targets)) != len(targets):
            raise ValueError('Duplicate command or target role')
        return self


class RoleSummaryItem(DTO):
    character_id: UUID
    role: str
    command_id: UUID4
    status: int
    result: RoleSummaryOut | None
    error: BatchItemError | None


class RoleSummaryBatchOut(DTO):
    items: list[RoleSummaryItem]
