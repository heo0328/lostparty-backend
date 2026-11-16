"""Stored personal-profile batch read contracts."""
from datetime import datetime
from uuid import UUID


from app.game_accounts.schemas.schemas import DTO
from app.game_accounts.schemas.profile_schemas import PersonalProfileOut


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
