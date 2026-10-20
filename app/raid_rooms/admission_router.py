"""Integrated R2-C HTTP draft, deliberately unmounted until R5."""
import json
from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Query,Request
from pydantic import TypeAdapter,ValidationError
from app.game_accounts.router import Principal,Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.raid_rooms.availability_router import AvailabilityRoute,unique_pairs
from app.raid_rooms import admission_schemas as s,admission_service as service


class AdmissionRoute(AvailabilityRoute):
    def allowed_query(self,request):
        if request.method!='GET':return set()
        if request.url.path.endswith('/raid-room-creation-context'):return {'character_id','selected_role','items','group_id'}
        if request.url.path.endswith('/admission-context'):return {'character_id','selected_role','intent'}
        return set()


router=APIRouter(prefix='/v1',tags=['recruitment-commands'],route_class=AdmissionRoute)
errors={code:{'model':GameErrorOut} for code in (400,401,403,404,409,413,503)}
Role=Literal['dealer','support']


@router.get('/me/raid-room-creation-context',response_model=s.CreationContext,responses=errors)
def creation_context(principal:Principal,character_id:UUID,selected_role:Role,items:Annotated[str,Query(max_length=32768)],group_id:UUID|None=None):
    try:choices=TypeAdapter(list[s.ItemChoice]).validate_python(json.loads(items,object_pairs_hook=unique_pairs))
    except (ValueError,TypeError,ValidationError,RecursionError):fail('INVALID_REQUEST',400)
    return service.creation_context(principal,character_id,selected_role,choices,group_id)


@router.get('/raid-rooms/{room_id}/admission-context',response_model=s.AdmissionContext,responses=errors)
def admission_context(room_id:UUID,principal:Principal,character_id:UUID,selected_role:Role,intent:Literal['apply','join']):
    return service.admission_context(principal,room_id,character_id,selected_role,intent)


@router.post('/raid-rooms',response_model=s.Ack,status_code=201,responses=errors)
def create(data:s.Create,principal:Principal,key:Key):return service.create(principal,key,data)[1]


@router.post('/raid-rooms/{room_id}/join',response_model=s.Ack,responses=errors)
def join(room_id:UUID,data:s.Admission,principal:Principal,key:Key):return service.admit(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/applications',response_model=s.ApplicationAck,status_code=201,responses=errors)
def apply(room_id:UUID,data:s.Admission,principal:Principal,key:Key):return service.admit(principal,room_id,key,data,applying=True)[1]


@router.post('/raid-room-applications/{application_id}/approve',response_model=s.Ack,responses=errors)
def approve(application_id:UUID,data:s.Approve,principal:Principal,key:Key):return service.approve(principal,application_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/plan',response_model=s.Plan,responses=errors)
def plan(room_id:UUID,principal:Principal):return service.plan(principal,room_id)


@router.get('/raid-room-applications/{application_id}',response_model=s.ApplicationView|s.Review,responses=errors)
def application(application_id:UUID,principal:Principal):return service.application(principal,application_id)


@router.post('/raid-room-applications/{application_id}/reject',response_model=s.ApplicationAck,responses=errors)
def reject(application_id:UUID,data:s.Approve,principal:Principal,key:Key):return service.finish_application(principal,application_id,key,data)[1]


@router.post('/raid-room-applications/{application_id}/withdraw',response_model=s.ApplicationAck,responses=errors)
def withdraw(application_id:UUID,data:s.ApplicationCAS,principal:Principal,key:Key):return service.finish_application(principal,application_id,key,data,withdrawing=True)[1]
