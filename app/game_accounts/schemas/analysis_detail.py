from typing import Annotated, Literal
from pydantic import Field, StrictBool, StrictInt
from app.game_accounts.schemas.schemas import DTO

Role = Literal['dealer', 'support']
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9._-]+$')]
Count = Annotated[StrictInt, Field(ge=0)]


class Detection(DTO):
    status: Literal['detected', 'unsupported_class', 'branch_not_found', 'ambiguous']
    catalog_version: Identifier
    class_id: Identifier | None
    branch_id: Identifier | None
    branch_display_name: str | None
    detected_role: Role | None
    matched_tier1_node: str | None
    matched_related_nodes: list[str]


class Gem(DTO):
    slot: Count
    level: Count
    target: str
    descriptions: list[str]
    category: Literal['normal', 'passive_or_identity', 'unknown']
    validation_status: Literal['verified', 'same_class_target_unverified', 'foreign_class', 'unavailable']


class GridCore(DTO):
    name: str
    grade: str
    point: Count
    minimum_point: Count
    recommended_point: Count


class GridCondition(DTO):
    core_name: str
    condition_text: str
    required_passive_names: list[str]
    missing_passive_names: list[str]


class GridMinimum(DTO):
    order_sun_point: Count | None
    order_moon_point: Count | None
    required_point: Literal[14]


class Notice(DTO):
    code: str
    severity: Literal['info', 'warning']
    message: str


class AnalysisDetail(DTO):
    detection: Detection
    rune_count: Count
    equipped_gem_count: Count | None
    gem_effects_source_available: StrictBool
    gems: list[Gem]
    ark_grid_core_points: list[GridCore]
    ark_grid_conditions: list[GridCondition]
    ark_grid_minimum: GridMinimum | None
    notices: list[Notice]
