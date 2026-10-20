"""R2 availability contract; router activation belongs to integrated handoff."""
from typing import Annotated, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]
Clock = Annotated[StrictStr, Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][05]$')]


class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Interval(DTO):
    weekday: Annotated[StrictInt, Field(ge=1, le=7)]
    start: Clock
    end: Clock
    end_day_offset: Annotated[StrictInt, Field(ge=0, le=1)]

    @model_validator(mode='after')
    def duration(self):
        def minutes(value):
            h, m = map(int, value.split(':'))
            return h * 60 + m
        if not 0 < minutes(self.end) + self.end_day_offset * 1440 - minutes(self.start) <= 1440:
            raise ValueError('interval duration must be positive and at most 24 hours')
        return self


class NormalizedInterval(DTO):
    start_minute: Annotated[StrictInt, Field(ge=0, lt=10080)]
    end_minute: Annotated[StrictInt, Field(gt=0, le=10080)]

    @model_validator(mode='after')
    def positive(self):
        if self.start_minute >= self.end_minute:
            raise ValueError('normalized interval must be positive')
        return self


class PersonalIn(DTO):
    expected_version: Version
    timezone: Literal['Asia/Seoul']
    intervals: list[Interval]


class PersonalOut(DTO):
    exists: bool
    version: Version
    timezone: Literal['Asia/Seoul']
    intervals: list[Interval]
    normalized_intervals: list[NormalizedInterval]
    updated_at: datetime | None


class SubmissionIn(DTO):
    expected_personal_version: Version
    expected_submission_revision: Version
    expected_membership_revision: Version


class SubmissionOut(DTO):
    membership_id: UUID
    state: Literal['missing', 'ready', 'unavailable']
    revision: Version
    source_personal_version: Version | None
    intervals: list[Interval]
    normalized_intervals: list[NormalizedInterval]
    submitted_at: datetime | None
