"""Current-app management resource; old v1 DTOs/writers remain intact."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.game_accounts.api.router import Principal, Key
from app.raid_rooms.api.availability_router import AvailabilityRoute
from app.game_accounts.schemas.management_schemas import ManagementContext, ManagementPut, HistoricalManagementContext, HistoricalManagementPut, UUIDText
from app.game_accounts.schemas.schemas import GameErrorOut
from app.game_accounts.character_profiles import management
from uuid import UUID
class ManagementRoute(AvailabilityRoute):
    body_limit=65536
    def capture_body(self,request,value):
        if isinstance(value,dict) and value.get("activity_character_ids")==[]:
            from app.game_accounts.common.support import fail
            fail("EMPTY_ACTIVITY_SELECTION",400)
router=APIRouter(prefix='/v2/me/game-accounts',tags=['character-management'],route_class=ManagementRoute)
errors={status:{'model':GameErrorOut} for status in (400,401,403,404,409,413,429,503)}
@router.get('/{registration_id}/character-settings',response_model=ManagementContext,responses=errors,
    description='Read-only full non-retired context (max1000), policy2 main-only representative and stored residual activity IDs. No writes.')
def get(registration_id:UUIDText,principal:Principal):
    return JSONResponse(management.get(principal,UUID(registration_id)),headers={'Cache-Control':'no-store'})
@router.put('/{registration_id}/character-settings',response_model=ManagementContext|HistoricalManagementContext,responses=errors,
    description='Atomic activity/representative and optional exact movable-subset order. CAS+order digest; immutable 24h idempotency ACK. Omitted order preserves ranks; null is invalid; unchanged order is no-op.')
def put(registration_id:UUIDText,data:ManagementPut|HistoricalManagementPut,principal:Principal,key:Key):
    _,value=management.put(principal,UUID(registration_id),key,data.model_dump(exclude_unset=True))
    return JSONResponse(value,headers={'Cache-Control':'no-store'})
