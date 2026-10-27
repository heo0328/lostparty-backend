from uuid import UUID
from typing import Annotated,Literal
from fastapi import APIRouter,Query
from app.game_accounts.router import Principal
from app.raid_rooms.router import OptionalPrincipal
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms import member_reads as service,search,member_schemas as s
from app.raid_rooms.search_router import Search,Page
from app.raid_rooms.search_router import Card
from app.game_accounts.support import fail


class ReadRoute(AdmissionRoute):
    def allowed_query(self,request):
        path=request.url.path
        if request.method=='GET':
            if path=='/v1/raid-rooms':return {'scope','group_id','raid_id','difficulty_id','limit','cursor'}
            if path.endswith(('/raid-room-memberships','/raid-room-applications','/applications')):return {'state','limit','cursor'}
            if path.endswith('/raid-schedule-overlaps'):return {'limit','cursor'}
            if path.endswith('/schedule-context'):return {'target_session_id'}
            if path.endswith('/raid-room-member-projections'):return {'room_ids','filter_context_token','group_ids'}
        return super().allowed_query(request)


router=APIRouter(prefix='/v1',tags=['recruitment-reads'],route_class=ReadRoute)
Limit=Annotated[int,Query(ge=1,le=50)]
Cursor=Annotated[str|None,Query(max_length=2048)]


@router.get('/raid-rooms',response_model=Page,responses=errors)
def listing(principal:OptionalPrincipal,scope:Literal['public','group']='public',group_id:UUID|None=None,raid_id:str|None=None,difficulty_id:str|None=None,limit:Limit=20,cursor:Cursor=None):
    return search.search(principal,Search(category='all',admission_scope=scope,group_ids=[group_id] if group_id else [],filter_context_token=None,member_conditions=[],raid_ids=[raid_id] if raid_id else [],difficulty_ids=[difficulty_id] if difficulty_id else [],limit=limit,cursor=cursor))


@router.get('/raid-rooms/{room_id}',response_model=Card,responses=errors)
def summary(room_id:UUID,principal:OptionalPrincipal):return service.summary(principal,room_id)


@router.get('/raid-rooms/{room_id}/detail',response_model=s.Detail,responses=errors)
def detail(room_id:UUID,principal:Principal):return service.detail(principal,room_id)


@router.get('/groups/{group_id}/raid-room-member-projections',response_model=s.ProjectionPage,responses=errors)
def projections(group_id:UUID,principal:Principal,room_ids:Annotated[str,Query(max_length=32768)],filter_context_token:str|None=None,group_ids:Annotated[str|None,Query(max_length=32768)]=None):
    try:
        rids=[UUID(r) for r in room_ids.split(',')]
        gids=[UUID(g) for g in group_ids.split(',')] if group_ids is not None else None
    except ValueError:fail('INVALID_REQUEST',400)
    return service.projections(principal,group_id,rids,filter_context_token,gids)


@router.get('/me/raid-room-memberships',response_model=s.MembershipPage,responses=errors)
def memberships(principal:Principal,state:Literal['current','ended','all']='current',limit:Limit=20,cursor:Cursor=None):return service.memberships(principal,state,limit,cursor)


@router.get('/me/raid-room-applications',response_model=s.ApplicationPage,responses=errors)
def applications(principal:Principal,state:Literal['pending','approved','rejected','withdrawn','expired','all']='pending',limit:Limit=20,cursor:Cursor=None):return service.applications(principal,None,state,limit,cursor)


@router.get('/raid-rooms/{room_id}/applications',response_model=s.ApplicationPage,responses=errors)
def room_applications(room_id:UUID,principal:Principal,state:Literal['pending','approved','rejected','withdrawn','expired','all']='pending',limit:Limit=20,cursor:Cursor=None):return service.applications(principal,room_id,state,limit,cursor)


@router.get('/me/raid-rooms/{room_id}/schedule-context',response_model=s.TimeContext,responses=errors)
def time_context(room_id:UUID,principal:Principal,target_session_id:UUID|None=None):return service.time_context(principal,room_id,target_session_id)


@router.get('/me/raid-schedule-overlaps',response_model=s.OverlapPage,responses=errors)
def overlaps(principal:Principal,limit:Limit=20,cursor:Cursor=None):return service.overlaps(principal,limit,cursor)
