from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from app.game_accounts.schemas import DTO, RegistrationOut, LifecycleCharactersOut, RepresentativeOut
from app.game_accounts.profile_schemas import PersonalProfileOut, PresentationOut
from app.raid_weekly.schemas import WeeklyStates


class BootstrapUnavailable(DTO):
    character_id: UUID
    code: Literal['CHARACTER_UNUSABLE', 'IDENTITY_CONFLICT']


class BootstrapRegistration(DTO):
    registration: RegistrationOut
    characters: LifecycleCharactersOut
    representative: RepresentativeOut | None
    presentation: PresentationOut | None
    personal_profiles: list[PersonalProfileOut]
    unavailable_characters: list[BootstrapUnavailable]


class AccountBootstrap(DTO):
    server_now: datetime
    complete: Literal[True]
    registrations: list[BootstrapRegistration] = Field(max_length=20)
    weekly_states: WeeklyStates
