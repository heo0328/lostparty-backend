import app.raid_rooms.schemas.character_change as character_change_types
import app.raid_rooms.schemas.management as management_types
from app.raid_rooms.schemas.management_router import Settings

from uuid import UUID

from fastapi import APIRouter

from app.game_accounts.api.router import Principal
from app.game_accounts.api.router import Key

from app.raid_rooms.participation import management as service

from app.raid_rooms.participation import character_change

from app.raid_rooms.api.admission_router import AdmissionRoute
from app.raid_rooms.api.admission_router import errors

from app.raid_rooms.schemas.admission_schemas import Ack

router=APIRouter(prefix='/v1',tags=['recruitment-management'],route_class=AdmissionRoute)

@router.post('/raid-rooms/{room_id}/character-changes',response_model=Ack,responses=errors)
def change_character(room_id:UUID,data:character_change_types.Change,principal:Principal,key:Key):
    return character_change.change(principal,room_id,key,data)[1]

@router.get('/me/raid-rooms/{room_id}/settings',response_model=Settings,responses=errors)
def settings(room_id:UUID,principal:Principal):return service.get_settings(principal,room_id)

@router.put('/raid-rooms/{room_id}/settings',response_model=Ack,responses=errors)
def edit(room_id:UUID,data:management_types.RoomSettingsIn,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'settings')[1]

@router.put('/raid-rooms/{room_id}/visibility',response_model=Ack,responses=errors)
def visibility(room_id:UUID,data:management_types.Visibility,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'visibility')[1]

@router.put('/raid-rooms/{room_id}/formation',response_model=Ack,responses=errors)
def formation(room_id:UUID,data:management_types.Formation,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'formation')[1]

@router.post('/raid-rooms/{room_id}/removals',response_model=Ack,responses=errors)
def remove(room_id:UUID,data:management_types.Removal,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'remove')[1]
