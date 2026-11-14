"""Current-runtime personal calendar reads; no profile changes to overlaps."""
from typing import Annotated
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.game_accounts.api.router import Principal
from app.raid_rooms.api.availability_router import AvailabilityRoute, errors
from app.raid_rooms.schemas.personal_reservations import ReservationPage, Day
from app.raid_rooms.schedules import personal_reservations as service

class ReservationRoute(AvailabilityRoute):
    def allowed_query(self, request):
        return {'calendar_week_key', 'limit', 'cursor'}

router = APIRouter(prefix='/v2/me', tags=['personal-reservations'], route_class=ReservationRoute)

@router.get('/raid-reservations', response_model=ReservationPage, responses=errors,
    description='Read-only own unreleased reservations intersecting a KST Wednesday-midnight calendar week. '
    'Current/next calendar only; no activity/ownership filtering. 10000-row scan and 1MiB page bounds. '
    'Result revision excludes observation time and the 06:00 game-cycle transition. '
    'Cursor retains its original 600-second expiry. No provider or per-room reads.')
def get(principal: Principal, calendar_week_key: Day,
        limit: Annotated[int, Query(ge=1, le=200)]=100,
        cursor: Annotated[str | None, Query(min_length=1,max_length=8192,pattern=r'^[A-Za-z0-9_.-]+$')]=None):
    return JSONResponse(service.page(principal,calendar_week_key,limit,cursor), headers={'Cache-Control':'no-store'})
