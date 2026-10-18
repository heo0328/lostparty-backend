from fastapi import APIRouter, Depends, Request, Response
from app.game_accounts.router import Principal
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.bootstrap_schemas import AccountBootstrap
from app.game_accounts import bootstrap
from app.game_accounts.support import fail


async def strict_read(request: Request):
    if request.query_params:
        fail('INVALID_REQUEST', 400)
    async for chunk in request.stream():
        if chunk:
            fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v2/me', tags=['game-accounts'], dependencies=[Depends(strict_read)])


@router.get('/account-bootstrap', response_model=AccountBootstrap,
            responses={code: {'model': GameErrorOut} for code in (400, 401, 403, 409, 503)})
def account_bootstrap(principal: Principal):
    return Response(content=bootstrap.get(principal), media_type='application/json')
