"""Closed wire additions; absent fields remain absent for stored original ACKs."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator


class State(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: Literal['public','group']
    group_id: UUID | None
    revision: StrictInt | None = Field(default=None, exclude_if=lambda v:v is None)


class Metadata(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_id: UUID
    target_cycle_key: date
    room_cycle_id: UUID
    generation: StrictInt | None
    scope: Literal['public','group'] | None
    group_id: UUID | None
    revision: StrictInt | None
    state: Literal['known','unavailable']


class Effect(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_id: UUID
    target_cycle_key: date
    room_cycle_id: UUID
    generation: StrictInt
    before: State
    after: State


class Envelope(BaseModel):
    group_policy_version: Literal['cycle-group-policy-1'] | None = Field(default=None, exclude_if=lambda v:v is None)
    group_policy: Metadata | None = Field(default=None, exclude_if=lambda v:v is None)
    group_policy_effect: Effect | None = Field(default=None, exclude_if=lambda v:v is None)
    group_policy_effects: list[Effect] | None = Field(default=None, exclude_if=lambda v:v is None)


class PolicyCandidate(BaseModel):
    group_policy_effect: Effect | None = Field(default=None, exclude_if=lambda v:v is None)


class GroupChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: Literal['public','group']
    group_id: UUID | None
    expected_revision: StrictInt = Field(ge=1, le=2147483647)

    @model_validator(mode='after')
    def valid_pair(self):
        if (self.scope=='group') != (self.group_id is not None):raise ValueError('scope/group pair required')
        return self


class Permission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    allowed: bool
    reason: str | None
    next_change_at: datetime | None


class Scope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    server_now: datetime
    current_cycle_key: date
    target_cycle_key: date
    playable_from: datetime
    phase: Literal['current','future']
    target_revision: int | None
    policy_version: str
    room_cycle_id: UUID | None
    target_generation: int | None


class SettingsContextData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_id: UUID
    context_token: str
    issued_at: datetime
    expires_at: datetime
    permission: Permission


class SettingsContext(Envelope):
    model_config = ConfigDict(extra='forbid')
    scope: Scope
    data: SettingsContextData


class TitleCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_cycle_key: str
    expected_room_revision: StrictInt = Field(ge=1,le=2147483647)
    context_token: str = Field(min_length=1,max_length=4096)
    title: StrictStr = Field(min_length=1,max_length=60)
