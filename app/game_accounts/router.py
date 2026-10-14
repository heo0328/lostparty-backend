from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query, Response, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import UUID4
from app.auth.router import authenticated
from app.game_accounts import schemas as s, service

def strict_query(request: Request):
    path=request.url.path
    allowed={'limit','cursor'} if request.method=='GET' and (path.endswith('/game-accounts') or path.endswith('/characters')) else {'expected_version'} if request.method=='DELETE' and '/game-accounts/' in path else set()
    if set(request.query_params)-allowed or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        from app.game_accounts.support import fail
        fail('INVALID_REQUEST',400)


router=APIRouter(prefix='/v1',tags=['game-accounts'],dependencies=[Depends(strict_query)])
Principal=Annotated[tuple,Depends(authenticated)]
Key=Annotated[UUID4,Header(alias='Idempotency-Key')]
Limit=Annotated[int,Query(ge=1,le=100)]
Cursor=Annotated[str|None,Query(max_length=2048)]
common={status:{'model':s.GameErrorOut} for status in (400,401,403,404,409,429,503)}


def result(principal, operation, key, data, model=None, rid=None):
    status, body=service.mutate(principal,operation,key,jsonable_encoder(data),rid)
    if status==204:
        return Response(status_code=204)
    if status<400 and model:
        body=jsonable_encoder(model.model_validate(body))
    return JSONResponse(status_code=status,content=body)


@router.post('/game-accounts/preview',response_model=s.PreviewOut,responses=common)
def preview(data:s.PreviewIn,principal:Principal):
    return service.preview(principal,data)


@router.get('/me/game-accounts',response_model=s.RegistrationPage,responses=common)
def registrations(principal:Principal,limit:Limit=50,cursor:Cursor=None):
    return service.registrations(principal,limit,cursor)


@router.post('/me/game-accounts',response_model=s.RegistrationOut,status_code=201,responses=common)
def register(data:s.RegisterIn,principal:Principal,key:Key):
    return result(principal,'register',key,data.model_dump(),s.RegistrationOut)


@router.patch('/me/game-accounts/{registration_id}',response_model=s.RegistrationOut,responses=common)
def patch(registration_id:UUID,data:s.PatchIn,principal:Principal,key:Key):
    return result(principal,'patch',key,data.model_dump(exclude_unset=True),s.RegistrationOut,registration_id)


@router.delete('/me/game-accounts/{registration_id}',status_code=204,responses=common)
def remove(registration_id:UUID,principal:Principal,key:Key,expected_version:Annotated[int,Query(ge=1)]):
    return result(principal,'delete',key,{'expected_version':expected_version},rid=registration_id)


@router.get('/me/game-accounts/{registration_id}/characters',response_model=s.CharactersOut,responses=common)
def characters(registration_id:UUID,principal:Principal,limit:Limit=50,cursor:Cursor=None):
    return service.characters(principal,registration_id,limit,cursor)


@router.post('/me/game-accounts/{registration_id}/refresh',response_model=s.RefreshOut,responses=common)
def refresh(registration_id:UUID,data:s.Empty,principal:Principal,key:Key):
    return result(principal,'refresh',key,{},s.RefreshOut,registration_id)


@router.post('/me/game-account-verifications',response_model=s.VerificationOut,status_code=201,responses=common)
def start(data:s.StartIn,principal:Principal,key:Key):
    return result(principal,'start',key,data.model_dump(),s.VerificationOut)


@router.get('/me/game-account-verifications/{challenge_id}',response_model=s.VerificationOut,responses=common)
def verification(challenge_id:UUID,principal:Principal):
    return service.verification(principal,challenge_id)


@router.post('/me/game-account-verifications/{challenge_id}/confirm',response_model=s.VerificationOut,responses=common)
def confirm(challenge_id:UUID,data:s.Empty,principal:Principal,key:Key):
    return result(principal,'confirm',key,{},s.VerificationOut,challenge_id)


@router.delete('/me/game-account-verifications/{challenge_id}',status_code=204,responses=common)
def cancel(challenge_id:UUID,principal:Principal,key:Key):
    return result(principal,'cancel',key,{},rid=challenge_id)


@router.put('/me/game-accounts/{registration_id}/character-settings',response_model=s.SettingsOut,responses=common)
def save(registration_id:UUID,data:s.SettingsIn,principal:Principal,key:Key):
    return result(principal,'settings',key,data.model_dump(),s.SettingsOut,registration_id)
