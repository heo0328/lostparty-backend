from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64, strip_whitespace=True)]
Label = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=40, strip_whitespace=True)]
Version = Annotated[StrictInt, Field(ge=1)]


class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Empty(DTO):
    pass


class PreviewIn(DTO):
    character_name: Name


class RegisterIn(DTO):
    lookup_character_name: Name
    label: Label
    is_main: StrictBool = False


class PatchIn(DTO):
    label: Label | None = None
    is_main: StrictBool | None = None
    expected_version: Version

    @model_validator(mode='after')
    def values(self):
        if not ({'label', 'is_main'} & self.model_fields_set) or any(
            getattr(self, k) is None for k in ('label','is_main') if k in self.model_fields_set
        ):
            raise ValueError('At least one non-null change required')
        return self


class StartIn(DTO):
    source: Literal['registration', 'direct_input']
    registration_id: UUID | None = None
    character_name: Name | None = None

    @model_validator(mode='after')
    def source_matches(self):
        if self.source == 'registration':
            valid = self.registration_id is not None and self.character_name is None
        else:
            valid = self.character_name is not None and self.registration_id is None
        if not valid:
            raise ValueError('Exactly one source required')
        return self


class SettingsIn(DTO):
    activity_character_ids: Annotated[list[UUID], Field(max_length=200)]
    representative_character_id: UUID | None
    expected_settings_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version


class Summary(DTO):
    server_name: str
    character_name: str
    class_name: str
    character_level: int
    item_level: str | None
    combat_power: str | None = None


class CharacterOut(Summary):
    character_id: UUID | None
    roster_status: Literal['preview', 'confirmed', 'suspect', 'missing']
    summary_fetched_at: datetime
    last_confirmed_at: datetime | None
    requires_refresh: bool
    eligible: bool
    power_stale: bool = True
    power_fetched_at: datetime | None


class SettingsOut(DTO):
    configuration_state: Literal['unconfigured', 'configured', 'needs_reconfiguration']
    activity_character_ids: list[UUID]
    representative_character_id: UUID | None
    settings_version: int
    ownership_revision: int | None
    next_change_at: datetime | None
    selection_complete: Literal[True] = True
    ineligible_character_ids: list[UUID]


class RegistrationOut(DTO):
    registration_id: UUID
    label: str
    is_main: bool
    version: int
    game_account_id: UUID | None
    verification_status: Literal['unverified','verified']
    ownership_status: Literal['unverified','owned','ownership_lost']
    ownership_revision: int | None
    roster_revision: int | None
    settings: SettingsOut
    representative_summary: Summary | None
    character_count: int
    server_fetched_at: datetime


class RegistrationPage(DTO):
    items: list[RegistrationOut]
    next_cursor: str | None


class CharacterPage(DTO):
    items: list[CharacterOut]
    next_cursor: str | None


class CharactersOut(DTO):
    characters: CharacterPage
    settings: SettingsOut
    ownership_status: Literal['unverified','owned','ownership_lost']
    roster_revision: int
    server_fetched_at: datetime


class PreviewOut(DTO):
    characters: list[Summary]
    server_fetched_at: datetime
    expires_at: datetime


class RefreshOut(DTO):
    registration: RegistrationOut
    added_count: int
    suspect_count: int
    requires_refresh: bool


class VerificationOut(DTO):
    challenge_id: UUID
    status: Literal['pending','verified','expired','cancelled']
    required_slots: list[str]
    expires_at: datetime
    remaining_seconds: int
    result_code: str | None
    result_reference: UUID | None
    registration_id: UUID | None


class GameErrorDetail(DTO):
    code: str
    message: str
    request_id: UUID


class GameErrorOut(DTO):
    error: GameErrorDetail
