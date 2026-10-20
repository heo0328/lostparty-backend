from uuid import UUID
from datetime import datetime
from fastapi import APIRouter
from app.game_accounts.router import Principal,Key
from app.raid_rooms import continuation as service
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms.admission_schemas import Ack,DTO,Version,Permission
from typing import Literal


class ContinuationRoute(AdmissionRoute):
    def allowed_query(self,request):
        if request.method=='GET' and request.url.path.endswith('/continuation-choices'):return {'target_cycle'}
        return super().allowed_query(request)


class ChoiceView(DTO):
    choice_id: UUID
    revision: Version
    item_id: UUID
    raid_id: str
    character_id: UUID
    selected_role: Literal['dealer','support']
    state: Literal['selected','blocked']
    blocked_reason: str|None


class Choices(DTO):
    room_id: UUID
    target_cycle: str
    membership_revision: Version
    revision: Version
    items: list[ChoiceView]
    permissions: dict[str,Permission]


router=APIRouter(prefix='/v1',tags=['recruitment-continuation'],route_class=ContinuationRoute)


@router.get('/me/raid-rooms/{room_id}/continuation-choices',response_model=Choices,responses=errors)
def get(room_id:UUID,principal:Principal,target_cycle:str|None=None):return service.get(principal,room_id,target_cycle)


@router.put('/me/raid-rooms/{room_id}/continuation-choices',response_model=Choices,responses=errors)
def put(room_id:UUID,data:service.ChoicesIn,principal:Principal,key:Key):return service.put(principal,room_id,key,data)[1]


@router.put('/raid-rooms/{room_id}/continuation-settings',response_model=Ack,responses=errors)
def settings(room_id:UUID,data:service.ContinuationSettingsIn,principal:Principal,key:Key):return service.settings(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/recruitment-openings',response_model=Ack,responses=errors)
def opening(room_id:UUID,data:service.OpeningIn,principal:Principal,key:Key):return service.opening(principal,room_id,key,data)[1]
