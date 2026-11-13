"""Closed personal reservation wire contract, independent of overlap pairs."""
from typing import Annotated, Literal
from pydantic import Field, StrictInt, StrictStr
from app.game_accounts.schemas.schemas import DTO

UUIDText = Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
Day = Annotated[StrictStr, Field(min_length=10, max_length=10, pattern=r'^\d{4}-\d{2}-\d{2}$')]
UTC = Annotated[StrictStr, Field(min_length=20, max_length=27, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')]
Identifier = Annotated[StrictStr, Field(min_length=1, max_length=64, pattern=r'^[a-z0-9_]+$')]
Name = Annotated[StrictStr, Field(min_length=1, max_length=128)]
Label = Annotated[StrictStr, Field(min_length=1, max_length=64)]

class ReservationRaid(DTO):
    raid_id: Identifier
    difficulty_id: Identifier
    display_name: Name | None

class ReservationDisplay(DTO):
    name: Name | None
    server_name: Label | None
    class_name: Label | None

class ReservationCharacter(DTO):
    character_id: UUIDText
    display: ReservationDisplay

class ReservationItem(DTO):
    reservation_id: UUIDText
    session_id: UUIDText
    segment_id: UUIDText
    room_id: UUIDText
    cycle_key: Day
    starts_at: UTC
    ends_at: UTC
    schedule_revision: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    raid: ReservationRaid
    character: ReservationCharacter

class ReservationScope(DTO):
    server_now: UTC
    current_cycle_key: Day
    current_calendar_week_key: Day
    calendar_week_key: Day
    timezone: Literal['Asia/Seoul']
    window_start: UTC
    window_end: UTC
    policy_version: Literal['personal-reservations-1']

class ReservationData(DTO):
    items: Annotated[list[ReservationItem], Field(max_length=200)]
    result_revision: Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
    next_cursor: Annotated[StrictStr, Field(min_length=1, max_length=8192, pattern=r'^[A-Za-z0-9_.-]+$')] | None
    evaluated_at: UTC

class ReservationPage(DTO):
    scope: ReservationScope
    data: ReservationData
