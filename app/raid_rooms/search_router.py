from uuid import UUID
from datetime import datetime
from typing import Annotated,Literal
from pydantic import Field,StrictInt,field_validator
from fastapi import APIRouter,Query
from app.game_accounts.router import Principal
from app.raid_rooms.router import OptionalPrincipal
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms.admission_schemas import DTO,Version,Permission,Combat,Experience
from app.raid_rooms import search as service
from app.game_accounts.support import fail


class Condition(DTO):
    member_ref: Annotated[str,Field(min_length=64,max_length=64)]
    character_ids: list[UUID]


class Sort(DTO):
    criterion: Literal['member_count']='member_count'
    direction: Literal['ascending','descending']='descending'


class Search(DTO):
    category: Literal['general','group_linked','all']
    admission_scope: Literal['public','group']|None
    group_ids: list[UUID]
    filter_context_token: Annotated[str,Field(min_length=64,max_length=64)]|None
    member_conditions: list[Condition]
    raid_ids: list[str]
    difficulty_ids: list[str]
    sort: Sort=Field(default_factory=Sort)
    remaining_slot_counts: list[Annotated[StrictInt,Field(ge=1,le=7)]]=Field(default_factory=list)
    limit: Annotated[StrictInt,Field(ge=1,le=50)]
    cursor: Annotated[str,Field(max_length=2048)]|None

    @field_validator('remaining_slot_counts')
    @classmethod
    def unique_slots(cls,value):
        if len(set(value))!=len(value):raise ValueError('duplicate slot count')
        return value


class FilterGroup(DTO):
    group_id: UUID
    revision: Version
    members_revision: Version


class Alias(DTO):
    group_id: UUID
    group_membership_id: UUID


class FilterMember(DTO):
    member_ref: str
    aliases: list[Alias]
    display: dict[str,str|None]|None


class FilterContext(DTO):
    filter_context_token: str
    scope_digest: str
    evaluated_at: datetime
    groups: list[FilterGroup]
    members: list[FilterMember]


class CardItem(DTO):
    item_id: UUID
    raid_id: str
    difficulty_id: str
    game_party_size: Literal[4,8]


class Summary(DTO):
    mode: str
    occurrence_mode: Literal['one_of','each']|None
    confirmed_starts_at: list[datetime]
    earliest_start: datetime|None
    latest_start: datetime|None


class Card(DTO):
    room_id: UUID
    revision: Version
    title: str
    scope: Literal['public','group']
    group_id: UUID|None
    admission_mode: Literal['leader_only','direct_join']
    experience_level: Experience|None
    app_capacity: Literal[4,8]
    app_member_count: int
    state: Literal['active','ended']
    items: list[CardItem]
    game_items: list[CardItem]
    leader_display: dict[str,str|None]|None
    created_at: datetime
    cycle_key: str
    phase: Literal['current','ended']
    restricted: bool
    schedule_summary: Summary
    combat_requirement: Combat
    continuation_enabled: bool
    permissions: dict[str,Permission]


class Page(DTO):
    items: list[Card]
    directory_revision: Version
    filter_scope_digest: str|None
    next_cursor: str|None
    evaluated_at: datetime


class SearchRoute(AdmissionRoute):
    def allowed_query(self,request):
        if request.method=='GET' and request.url.path.endswith('/raid-room-filter-context'):return {'group_ids'}
        return super().allowed_query(request)


router=APIRouter(prefix='/v1',tags=['recruitment-search'],route_class=SearchRoute)


@router.get('/me/raid-room-filter-context',response_model=FilterContext,responses=errors)
def filter_context(principal:Principal,group_ids:Annotated[str,Query(max_length=32768)]):
    try:gids=[UUID(v) for v in group_ids.split(',')]
    except ValueError:fail('INVALID_REQUEST',400)
    return service.get_context(principal,gids)


@router.post('/raid-rooms/search',response_model=Page,responses=errors)
def search(data:Search,principal:OptionalPrincipal):return service.search(principal,data)
