from uuid import UUID
from datetime import date
from fastapi import APIRouter
from app.game_accounts.router import Principal,Key
from app.raid_rooms import management as service
from app.raid_rooms import character_change
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms.admission_schemas import Ack,DTO,Version,Permission,Combat,Experience
from typing import Literal


class ContinuationSettings(DTO):
    enabled: bool
    auto_open_enabled: bool
    revision: Version
    auto_open_effective_cycle: date|None


class Settings(DTO):
    room_id: UUID
    revision: Version
    room_revision: Version
    experience_level: Experience|None
    combat_requirement: Combat
    continuation: ContinuationSettings
    scope: Literal['public','group']
    group_id: UUID|None
    admission_mode: Literal['leader_only','direct_join']
    permissions: dict[str,Permission]


router=APIRouter(prefix='/v1',tags=['recruitment-management'],route_class=AdmissionRoute)


@router.post('/raid-rooms/{room_id}/character-changes',response_model=Ack,responses=errors)
def change_character(room_id:UUID,data:character_change.Change,principal:Principal,key:Key):
    return character_change.change(principal,room_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/settings',response_model=Settings,responses=errors)
def settings(room_id:UUID,principal:Principal):return service.get_settings(principal,room_id)


@router.put('/raid-rooms/{room_id}/settings',response_model=Ack,responses=errors)
def edit(room_id:UUID,data:service.RoomSettingsIn,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'settings')[1]


@router.put('/raid-rooms/{room_id}/visibility',response_model=Ack,responses=errors)
def visibility(room_id:UUID,data:service.Visibility,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'visibility')[1]


@router.put('/raid-rooms/{room_id}/formation',response_model=Ack,responses=errors)
def formation(room_id:UUID,data:service.Formation,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'formation')[1]


@router.post('/raid-rooms/{room_id}/removals',response_model=Ack,responses=errors)
def remove(room_id:UUID,data:service.Removal,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'remove')[1]
