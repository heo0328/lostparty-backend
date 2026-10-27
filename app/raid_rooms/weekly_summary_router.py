"""First executable W2 read slice; no writes or unfinished v2 command routes."""
from fastapi import APIRouter
from app.game_accounts.router import Principal
from app.game_accounts.schemas import GameErrorOut
from app.raid_rooms.availability_router import AvailabilityRoute
from app.raid_rooms import weekly_summary as service, weekly_summary_schemas as s

router = APIRouter(prefix='/v2', tags=['recruitment-weekly-summary'], route_class=AvailabilityRoute)
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 404, 409, 413, 429, 503)}


@router.get('/raid-cycles', response_model=s.Cycles, responses=errors, operation_id='get__v2_raid-cycles',
            description='C/N metadata. Coarse permissions describe temporal policy, not character eligibility or command route readiness.')
def metadata(principal: Principal):
    return service.metadata(principal)


@router.post('/me/raid-weekly-summary', response_model=s.Summary, responses=errors,
             operation_id='post__v2_me_raid-weekly-summary',
             description='Read-only RR batch: 1..50 unique own verified characters and 1..2 actual C/N targets; maximum 500 entries. No Idempotency-Key, provider or bootstrap reload. Any inaccessible character rejects the whole batch with 403.')
def summary(data: s.SummaryRequest, principal: Principal):
    return service.summary(principal, data)
