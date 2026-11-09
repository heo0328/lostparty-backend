from app.raid_rooms.schemas.application_presets import PresetPut
from app.raid_rooms.schemas.application_presets import PresetDocument
from app.raid_rooms.admissions.application_presets import get
from app.raid_rooms.admissions.application_presets import put

"""Small account-owned collection with durable replay, CAS and no GET writes."""

from fastapi import APIRouter

from app.game_accounts.api.router import Principal
from app.game_accounts.api.router import Key

from app.raid_rooms.schemas import cycle_wire

from app.raid_rooms.api.cycle_router import CycleRoute

class PresetRoute(CycleRoute):
    def allowed_query(self,request):return set()
    def repeated_query(self,request):return set()

router=APIRouter(prefix='/v2/me/application-message-presets',tags=['application-message-presets'],route_class=PresetRoute)

errors={code:{'model':cycle_wire.Error} for code in (400,401,403,404,409,413,429,503)}

@router.get('',response_model=PresetDocument,responses=errors)
def read_presets(principal:Principal):
    return get(principal)

@router.put('',response_model=PresetDocument,responses=errors)
def write_presets(data:PresetPut,principal:Principal,key:Key):
    return put(principal,key,data)[1]
