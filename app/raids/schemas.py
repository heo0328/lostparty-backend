from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

Identifier = Annotated[StrictStr, Field(min_length=1, max_length=64, pattern=r'^[a-z0-9_]+$')]
PositiveInt = Annotated[StrictInt, Field(ge=1)]
NonnegativeInt = Annotated[StrictInt, Field(ge=0)]
DecimalString = Annotated[StrictStr, Field(pattern=r'^[0-9]+(?:\.[0-9]+)?$')]


class CatalogDTO(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class RaidDifficulty(CatalogDTO):
    difficulty_id: Identifier
    name: StrictStr
    display_alias: StrictStr
    display_order: PositiveInt
    min_item_level: DecimalString
    clear_gold: NonnegativeInt
    bound_gold: NonnegativeInt
    is_active: StrictBool


class Raid(CatalogDTO):
    raid_id: Identifier
    official_name: StrictStr
    display_name: StrictStr
    aliases: tuple[StrictStr, ...]
    display_order: PositiveInt
    party_size: Literal[4, 8]
    party_count: Literal[1, 2]
    required_support_count: PositiveInt
    max_dealer_count_per_class: PositiveInt
    gate_count: PositiveInt
    is_active: StrictBool
    difficulties: Annotated[tuple[RaidDifficulty, ...], Field(min_length=1)]


class RaidCatalog(CatalogDTO):
    schema_version: Literal[2]
    catalog_version: Annotated[StrictStr, Field(min_length=1, max_length=64)]
    updated_at: datetime
    raids: Annotated[tuple[Raid, ...], Field(min_length=1)]


class RaidCycle(CatalogDTO):
    server_time: datetime
    cycle_key: Annotated[StrictStr, Field(pattern=r'^\d{4}-\d{2}-\d{2}$')]
    starts_at: datetime
    ends_at: datetime
    timezone: Literal['Asia/Seoul']
