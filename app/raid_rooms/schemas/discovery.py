"""Opt-in search DTOs; existing strict search/card models stay unchanged."""
from copy import deepcopy
from typing import Annotated, Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, create_model, model_validator
from app.raid_rooms.schemas import cycle_wire as wire
from app.raid_rooms.schemas.cycle_group_schemas import Metadata
from app.raid_rooms.schemas.group_link_display import GroupLinkState

PROFILE = 'discovery-1'


class CoordinationProgress(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra={'oneOf':[
        {'properties':{'status':{'const':'waiting_members'},'missing_members':{'type':'integer'}}},
        {'properties':{'status':{'enum':['coordinating','not_applicable']},'missing_members':{'type':'null'}}},
    ]})
    status: Literal['waiting_members', 'coordinating', 'not_applicable']
    missing_members: Annotated[StrictInt, Field(ge=1, le=8)] | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.status == 'waiting_members') != (self.missing_members is not None):
            raise ValueError('Only waiting_members carries a positive missing count')
        return self


class DiscoverySchedule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    coordination_state: Literal['base_committed', 'coordinating', 'early_confirmed', 'base_confirmed',
                                'proposal_confirmed', 'deadline_pending', 'needs_review', 'ended']
    effective_starts_at: AwareDatetime
    effective_ends_at: AwareDatetime
    admission_deadline: AwareDatetime
    confirmed_starts_at: AwareDatetime | None
    confirmed_ends_at: AwareDatetime | None
    coordination_progress: CoordinationProgress


# Copy the exact existing field constraints, without inheriting the rich card.
_fields = ('room_id', 'revision', 'title', 'scope', 'group_id', 'admission_mode', 'experience_level',
           'app_capacity', 'app_member_count', 'items', 'combat_requirement', 'continuation_enabled',
           'room_cycle_id', 'target_cycle_key', 'target_generation', 'target_revision', 'target_state',
           'restricted', 'schedule_summary', 'leader_display')
DiscoveryCard = create_model('DiscoveryCard', __config__=ConfigDict(extra='forbid'),
    **{key: (wire.BCard.model_fields[key].annotation, deepcopy(wire.BCard.model_fields[key])) for key in _fields},
    schedule=(DiscoverySchedule | None, ...), view_detail_permission=(wire.Permission, ...))


class DiscoveryData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: Annotated[list[DiscoveryCard], Field(max_length=50)]
    total_count: Annotated[StrictInt, Field(ge=0, le=9007199254740991)]
    directory_revision: wire.Version
    filter_scope_digest: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')] | None
    result_revision: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    next_cursor: Annotated[str, Field(max_length=2048)] | None
    evaluated_at: AwareDatetime


class DiscoveryPage(wire.PolicyEnvelope):
    model_config = ConfigDict(extra='forbid')
    scope: wire.Scope
    data: DiscoveryData


class DiscoveryGroupPage(DiscoveryPage):
    group_states: list[GroupLinkState]
    cycle_groups: list[Metadata]
