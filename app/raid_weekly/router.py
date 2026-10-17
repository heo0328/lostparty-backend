from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.raid_weekly import schemas, service


async def strict_input(request: Request):
    allowed = {'character_id', 'cycle_key'} if request.method == 'GET' else set()
    if (set(request.query_params) - allowed or
            len(request.query_params.getlist('cycle_key')) > 1 or
            (request.method == 'GET' and await request.body())):
        fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1/me', tags=['raid-weekly'], dependencies=[Depends(strict_input)])
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 404, 409, 503)}


@router.get('/raid-weekly-states', response_model=schemas.WeeklyStates, responses=errors)
def weekly_states(principal: Principal,
                  character_id: Annotated[list[UUID], Query(min_length=1, max_length=50)],
                  cycle_key: Annotated[str | None, Query(pattern=r'^\d{4}-\d{2}-\d{2}$')] = None):
    return service.get(principal, character_id, cycle_key)


@router.put('/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion',
            response_model=schemas.WeeklyEntry, responses=errors)
def manual_completion(character_id: UUID, raid_id: str, data: schemas.ManualCompletionIn,
                      principal: Principal, key: Key):
    _, body = service.put(principal, character_id, raid_id, key, data.model_dump())
    return body
