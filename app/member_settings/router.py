from fastapi import APIRouter, Depends
from app.game_accounts.router import Principal, Key, strict_query
from app.game_accounts.schemas import GameErrorOut
from app.member_settings import schemas, service

router = APIRouter(prefix='/v1/me/settings', tags=['member-settings'],
                   dependencies=[Depends(strict_query)])
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 409, 503)}


@router.get('', response_model=schemas.MemberSettingsOut, responses=errors)
def get_settings(principal: Principal):
    return service.get(principal)


@router.put('', response_model=schemas.MemberSettingsOut, responses=errors)
def put_settings(data: schemas.MemberSettingsIn, principal: Principal, key: Key):
    _, body = service.put(principal, key, data.model_dump())
    return body
