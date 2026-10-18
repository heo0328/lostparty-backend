from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.groups import schemas, http_service
from app.member_limits import schemas as limit_schemas, service as limits


async def strict_input(request: Request):
    path = request.url.path
    allowed = set()
    if request.method == 'GET':
        if path in ('/v1/groups', '/v1/me/groups') or path.endswith('/members'):
            allowed = {'limit', 'cursor'}
        if path == '/v1/groups':
            allowed.add('q')
    if (set(request.query_params)-allowed or
            any(len(request.query_params.getlist(key)) != 1 for key in request.query_params) or
            (request.method == 'GET' and await request.body())):
        fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1', tags=['groups'], dependencies=[Depends(strict_input)])
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 404, 409, 503)}
Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(min_length=1, max_length=2048)]


@router.get('/me/usage-limits', response_model=limit_schemas.UsageLimits, responses=errors)
def usage_limits(principal: Principal):
    return limits.get(principal)


@router.post('/groups', status_code=201, response_model=schemas.GroupDetail, responses=errors)
def create(data: schemas.GroupCreateIn, principal: Principal, key: Key):
    return http_service.create(principal, key, data)[1]


@router.get('/groups', response_model=schemas.GroupSummaryPage, responses=errors)
def public_list(q: Annotated[str, Query(max_length=64)] = '', limit: Limit = 20, cursor: Cursor = None):
    return http_service.public_list(q, limit, cursor)


@router.get('/groups/{group_id}', response_model=schemas.GroupSummary, responses=errors)
def public_detail(group_id: UUID):
    return http_service.get_public(group_id)


@router.get('/me/groups', response_model=schemas.MyGroupPage, responses=errors)
def my_list(principal: Principal, limit: Limit = 20, cursor: Cursor = None):
    return http_service.my_list(principal, limit, cursor)


@router.get('/me/groups/{group_id}', response_model=schemas.GroupDetail, responses=errors)
def private_detail(group_id: UUID, principal: Principal):
    return http_service.get_private(principal, group_id)


@router.get('/groups/{group_id}/members', response_model=schemas.GroupMemberPage, responses=errors)
def members(group_id: UUID, principal: Principal, limit: Limit = 20, cursor: Cursor = None):
    return http_service.members(principal, group_id, limit, cursor)


@router.patch('/groups/{group_id}', response_model=schemas.GroupDetail, responses=errors)
def rename(group_id: UUID, data: schemas.GroupRenameIn, principal: Principal, key: Key):
    return http_service.rename(principal, group_id, key, data)[1]
