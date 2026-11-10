from typing import Annotated
from typing import Literal
from uuid import UUID
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from app.game_accounts.api.router import Principal
from app.game_accounts.api.router import common
from app.game_accounts.schemas import schemas as s
from app.game_accounts.rosters import lifecycle_reads
from app.game_accounts.common.support import fail


async def strict_read(request: Request):
    if set(request.query_params)-({'limit','cursor','include_roster_presence'} if request.url.path.endswith('/characters') else {'limit','cursor'}) or any(len(request.query_params.getlist(k))!=1 for k in request.query_params):
        fail('INVALID_REQUEST',400)
    if await request.body():
        fail('INVALID_REQUEST',400)


router=APIRouter(prefix='/v2/me',tags=['game-accounts'],dependencies=[Depends(strict_read)])
Limit=Annotated[int,Query(ge=1,le=50)]
Cursor=Annotated[str|None,Query(max_length=2048)]


@router.get('/game-accounts/{registration_id}/characters',response_model=s.LifecycleCharactersOut,responses=common)
def characters(registration_id: UUID,principal: Principal,limit: Limit=50,cursor: Cursor=None,include_roster_presence:Literal['true','false']='false'):
    value=lifecycle_reads.characters(principal,registration_id,limit,cursor,include_roster_presence=='true')
    if include_roster_presence=='true':
        from fastapi.responses import JSONResponse
        from fastapi.encoders import jsonable_encoder
        return JSONResponse(jsonable_encoder(value))
    return value


@router.get('/character-retirements',response_model=s.RetirementPage,responses=common)
def retirements(principal: Principal,limit: Limit=50,cursor: Cursor=None):
    return lifecycle_reads.retirements(principal,limit,cursor)
