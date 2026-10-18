from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Request,Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.game_accounts.router import Principal,Key,common
from app.game_accounts.schemas import PreviewIn
from app.game_accounts.support import fail
from app.ownership_disputes import schemas as s,commands,reads


async def strict_input(request:Request):
    allowed=({'purpose','view','limit','cursor'} if request.url.path=='/v2/me/game-account-verifications' else
             {'role','view','limit','cursor'} if request.url.path=='/v2/me/ownership-disputes' else set()) if request.method=='GET' else set()
    if set(request.query_params)-allowed or any(len(request.query_params.getlist(k))!=1 for k in request.query_params):fail('INVALID_REQUEST',400)
    if request.method=='GET' and await request.body():fail('INVALID_REQUEST',400)


router=APIRouter(prefix='/v2',tags=['game-accounts'],dependencies=[Depends(strict_input)])
Limit=Annotated[int,Query(ge=1,le=100)]
Cursor=Annotated[str|None,Query(min_length=1,max_length=2048)]


def execute(principal,op,key,data,model,rid=None):
    status,body=commands.mutate(principal,op,key,jsonable_encoder(data.model_dump(exclude_unset=True)),rid)
    return JSONResponse(status_code=status,content=model.model_validate(body).model_dump(mode='json'))


@router.post('/game-accounts/preview',response_model=s.PreviewV2,responses=common)
def preview(data:PreviewIn,principal:Principal):return commands.preview(principal,data)


@router.post('/me/game-account-verifications',status_code=201,response_model=s.VerificationV2,responses=common)
def start(data:s.ClaimStartIn,principal:Principal,key:Key):return execute(principal,'start',key,data,s.VerificationV2)


@router.get('/me/game-account-verifications',response_model=s.VerificationPage,responses=common)
def proofs(principal:Principal,purpose:Literal['all','claim','defense']='all',view:Literal['active','all']='active',limit:Limit=20,cursor:Cursor=None):
    return reads.listing(principal,'proof',purpose,view,limit,cursor)


@router.get('/me/game-account-verifications/{proof_id}',response_model=s.VerificationV2,responses=common)
def proof(proof_id:UUID,principal:Principal):return reads.get(principal,'proof',proof_id)


@router.post('/me/game-account-verifications/{proof_id}/confirm',response_model=s.VerificationV2,responses=common)
def confirm(proof_id:UUID,data:s.VersionIn,principal:Principal,key:Key):return execute(principal,'confirm',key,data,s.VerificationV2,proof_id)


@router.post('/me/game-account-verifications/{proof_id}/cancel',response_model=s.VerificationV2,responses=common)
def cancel(proof_id:UUID,data:s.VersionIn,principal:Principal,key:Key):return execute(principal,'proof_cancel',key,data,s.VerificationV2,proof_id)


@router.get('/me/ownership-disputes',response_model=s.DisputePage,responses=common)
def disputes(principal:Principal,role:Literal['all','challenger','owner']='all',view:Literal['active','all']='active',limit:Limit=20,cursor:Cursor=None):
    return reads.listing(principal,'dispute',role,view,limit,cursor)


@router.get('/me/ownership-disputes/{dispute_id}',response_model=s.DisputeOut,responses=common)
def dispute(dispute_id:UUID,principal:Principal):return reads.get(principal,'dispute',dispute_id)


@router.post('/me/ownership-disputes/{dispute_id}/cancel',response_model=s.DisputeOut,responses=common)
def withdraw(dispute_id:UUID,data:s.VersionIn,principal:Principal,key:Key):return execute(principal,'dispute_cancel',key,data,s.DisputeOut,dispute_id)


@router.post('/me/ownership-disputes/{dispute_id}/defenses',status_code=201,response_model=s.VerificationV2,responses=common)
def defense(dispute_id:UUID,data:s.DefenseStartIn,principal:Principal,key:Key):return execute(principal,'defense',key,data,s.VerificationV2,dispute_id)


@router.post('/me/ownership-disputes/{dispute_id}/settle',response_model=s.DisputeOut,responses=common)
def settle(dispute_id:UUID,data:s.VersionIn,principal:Principal,key:Key):return execute(principal,'settle',key,data,s.DisputeOut,dispute_id)
