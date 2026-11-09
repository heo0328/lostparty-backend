"""Small account-owned collection with durable replay, CAS and no GET writes."""

from typing import Annotated

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictInt
from pydantic import UUID4
from pydantic import field_validator

from app.game_accounts.common.support import fail

from app.raid_rooms.common import beta_text

from app.raid_rooms.schemas.beta_schemas import Memo
from app.raid_rooms.schemas.beta_schemas import MemoStored

class PresetItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID4
    text: Memo

    @field_validator('text')
    @classmethod
    def check_text(cls, value):
        beta_text.normalize(value, preset=True)
        return value  # Never normalize the idempotency payload.

class PresetPut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    items: Annotated[list[PresetItem], Field(max_length=5)]

    @field_validator('items', mode='before')
    @classmethod
    def check_limit(cls, value):
        if isinstance(value, list) and len(value)>5:
            fail('APPLICATION_PRESET_LIMIT_EXCEEDED', 400)
        return value

    @field_validator('items')
    @classmethod
    def check_ids(cls, value):
        if len({v.id for v in value})!=len(value):
            fail('INVALID_REQUEST', 400)
        return value

class StoredPresetItem(PresetItem):
    text: MemoStored

class PresetDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    items: Annotated[list[StoredPresetItem], Field(max_length=5)]
    saved_at: datetime | None
