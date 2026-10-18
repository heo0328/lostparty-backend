from fastapi import APIRouter, Depends, Request

from app.core.errors import AuthError
from app.game_accounts.schemas import GameErrorOut
from app.raids import schemas, service


async def no_input(request: Request):
    if request.query_params or await request.body():
        raise AuthError('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1', tags=['raid-catalog'], dependencies=[Depends(no_input)])
errors = {400: {'model': GameErrorOut}}


@router.get('/raid-catalog', response_model=schemas.RaidCatalog, responses=errors)
def raid_catalog():
    return service.catalog()


@router.get('/raid-cycle', response_model=schemas.RaidCycle, responses=errors)
def raid_cycle():
    return service.cycle()
