import app.raid_rooms.schemas.continuation as continuation_types
from app.raid_rooms.schemas.continuation_router import Choices

from uuid import UUID

from fastapi import APIRouter

from app.game_accounts.api.router import Principal
from app.game_accounts.api.router import Key

from app.raid_rooms.admissions import continuation as service

from app.raid_rooms.api.admission_router import AdmissionRoute
from app.raid_rooms.api.admission_router import errors

from app.raid_rooms.schemas.admission_schemas import Ack

class ContinuationRoute(AdmissionRoute):
    def allowed_query(self,request):
        if request.method=='GET' and request.url.path.endswith('/continuation-choices'):return {'target_cycle'}
        return super().allowed_query(request)

router=APIRouter(prefix='/v1',tags=['recruitment-continuation'],route_class=ContinuationRoute)

@router.get('/me/raid-rooms/{room_id}/continuation-choices',response_model=Choices,responses=errors)
def get(room_id:UUID,principal:Principal,target_cycle:str|None=None):return service.get(principal,room_id,target_cycle)

@router.put('/me/raid-rooms/{room_id}/continuation-choices',response_model=Choices,responses=errors)
def put(room_id:UUID,data:continuation_types.ChoicesIn,principal:Principal,key:Key):return service.put(principal,room_id,key,data)[1]

@router.put('/raid-rooms/{room_id}/continuation-settings',response_model=Ack,responses=errors)
def settings(room_id:UUID,data:continuation_types.ContinuationSettingsIn,principal:Principal,key:Key):return service.settings(principal,room_id,key,data)[1]

@router.post('/raid-rooms/{room_id}/recruitment-openings',response_model=Ack,responses=errors)
def opening(room_id:UUID,data:continuation_types.OpeningIn,principal:Principal,key:Key):return service.opening(principal,room_id,key,data)[1]
