from app.raid_rooms.schemas.search_router import Search
from app.raid_rooms.schemas.search_router import FilterContext
from app.raid_rooms.schemas.search_router import Page

from uuid import UUID

from typing import Annotated

from fastapi import APIRouter
from fastapi import Query

from app.game_accounts.api.router import Principal

from app.raid_rooms.api.router import OptionalPrincipal

from app.raid_rooms.api.admission_router import AdmissionRoute
from app.raid_rooms.api.admission_router import errors

from app.raid_rooms.reads import search as service

from app.game_accounts.common.support import fail

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
