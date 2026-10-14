import re
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr, Field, field_validator
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.lostark_keys import service


class LostArkKeyOut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    configured: StrictBool
    version: Annotated[StrictInt, Field(ge=1)]
    updated_at: datetime | None


class LostArkKeyIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: StrictStr = Field(min_length=1, max_length=16384, pattern=r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')
    expected_version: Annotated[StrictInt, Field(ge=1)]

    def __repr__(self):
        return '<LostArkKeyIn redacted>'

    def __str__(self):
        return self.__repr__()

    @field_validator('token')
    @classmethod
    def compact(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', value):
            raise ValueError('Invalid compact JWT format')
        return value


async def query(request: Request):
    allowed = {'expected_version'} if request.method == 'DELETE' else set()
    if set(request.query_params) - allowed or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        fail('INVALID_REQUEST', 400)
    if request.method in ('GET', 'DELETE') and (await request.body()):
        fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1/me/lostark-api-key', tags=['lostark-keys'], dependencies=[Depends(query)])
common = {s: {'model': GameErrorOut} for s in (400, 401, 403, 409, 503)}


@router.get('', response_model=LostArkKeyOut, responses=common)
def get(principal: Principal):
    return service.get(principal)


@router.put('', response_model=LostArkKeyOut, responses=common)
def put(data: LostArkKeyIn, principal: Principal, key: Key):
    status, body = service.mutate(principal, key, data.expected_version, data.token)
    return JSONResponse(status_code=status, content=jsonable_encoder(body))


@router.delete('', response_model=LostArkKeyOut, responses=common)
def delete(principal: Principal, key: Key, expected_version: Annotated[int, Query(ge=1)]):
    status, body = service.mutate(principal, key, expected_version)
    return JSONResponse(status_code=status, content=jsonable_encoder(body))


class LostArkKeyRestoreIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: Annotated[StrictInt, Field(ge=1)]


class LostArkKeyRestoreOut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: StrictStr
    version: Annotated[StrictInt, Field(ge=1)]

    def __repr__(self):
        return '<LostArkKeyRestoreOut redacted>'

    def __str__(self):
        return self.__repr__()


@router.post('/restore', response_model=LostArkKeyRestoreOut, responses=common)
def restore(data: LostArkKeyRestoreIn, principal: Principal):
    return service.restore(principal, data.expected_version)
