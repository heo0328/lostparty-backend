"""Closed character-management-1 DTOs; legacy settings remain unchanged."""
from typing import Annotated, Literal
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from app.game_accounts.schemas.schemas import DTO
UUIDText=Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
Version=Annotated[StrictInt,Field(ge=1,le=2147483647)]
Digest=Annotated[StrictStr,Field(pattern=r'^[0-9a-f]{64}$')]
class ManagementCharacter(DTO):
    character_id: UUIDText
    display_order: Annotated[StrictInt,Field(ge=0,le=2147483647)]|None
    item_level: Annotated[StrictStr,Field(min_length=1,max_length=64,pattern=r'^(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$')]|None
    character_name: Annotated[StrictStr,Field(min_length=1,max_length=64)]
    usable: StrictBool
    blocked_reason: Literal['CHARACTER_UNUSABLE','IDENTITY_CONFLICT']|None
class ManagementScope(DTO):
    registration_id: UUIDText
    game_account_id: UUIDText
    registration_version: Version
    settings_version: Version
    ownership_revision: Version
    roster_revision: Version
    policy_version: Literal['character-management-1']
class ManagementData(DTO):
    configuration_state: Literal['unconfigured','configured','needs_reconfiguration']
    activity_character_ids: Annotated[list[UUIDText],Field(max_length=200)]
    representative_character_id: UUIDText|None
    ordered_all_character_ids: Annotated[list[UUIDText],Field(max_length=1000)]
    order_digest: Digest
    characters: Annotated[list[ManagementCharacter],Field(max_length=1000)]
    evaluated_at: Annotated[StrictStr,Field(min_length=20,max_length=27,pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')]
class ManagementContext(DTO):
    scope: ManagementScope
    data: ManagementData
class ManagementPut(DTO):
    activity_character_ids: Annotated[list[UUIDText],Field(min_length=1,max_length=200)]
    representative_character_id: UUIDText
    expected_registration_version: Version
    expected_settings_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_order_digest: Digest
    ordered_character_ids: list[UUIDText]=Field(default_factory=lambda:None,max_length=199)
    @model_validator(mode='after')
    def unique(self):
        for values in (self.activity_character_ids,self.ordered_character_ids):
            if values is not None and len(values)!=len(set(values)):raise ValueError('Duplicate character')
        return self
