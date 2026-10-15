from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from app.game_accounts.router import Principal, common
from app.game_accounts import schemas as s, lifecycle_reads
from app.game_accounts.support import fail


async def strict_read(request: Request):
    if set(request.query_params)-{'limit','cursor'} or any(len(request.query_params.getlist(k))!=1 for k in request.query_params):
        fail('INVALID_REQUEST',400)
    if await request.body():
        fail('INVALID_REQUEST',400)


router=APIRouter(prefix='/v2/me',tags=['game-accounts'],dependencies=[Depends(strict_read)])
Limit=Annotated[int,Query(ge=1,le=50)]
Cursor=Annotated[str|None,Query(max_length=2048)]


@router.get('/game-accounts/{registration_id}/characters',response_model=s.LifecycleCharactersOut,responses=common)
def characters(registration_id: UUID,principal: Principal,limit: Limit=50,cursor: Cursor=None):
    return lifecycle_reads.characters(principal,registration_id,limit,cursor)


@router.get('/character-retirements',response_model=s.RetirementPage,responses=common)
def retirements(principal: Principal,limit: Limit=50,cursor: Cursor=None):
    return lifecycle_reads.retirements(principal,limit,cursor)
