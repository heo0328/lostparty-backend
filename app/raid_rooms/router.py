"""F2-B candidate router. Intentionally not included by app.main before F3."""
import json
import re
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from app.auth.router import authenticated, bearer
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.raid_rooms import queries, service, policies, runtime, schemas as s, http_schemas as h


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


async def strict_input(request: Request):
    allowed = set()
    path = request.url.path
    if request.method == 'GET':
        if path == '/v1/raid-rooms':
            allowed = {'scope', 'group_id', 'raid_id', 'difficulty_id', 'state', 'limit', 'cursor'}
        elif path in ('/v1/me/raid-room-memberships', '/v1/me/raid-room-applications') or path.endswith('/applications'):
            allowed = {'state', 'limit', 'cursor'}
        elif path.endswith('/admission-context'):
            allowed = {'character_id', 'selected_role', 'party_no', 'intent'}
    if (set(request.query_params) - allowed or
            any(len(request.query_params.getlist(k)) != 1 for k in request.query_params) or
            any(len(request.headers.getlist(k)) > 1 for k in ('authorization', 'idempotency-key'))):
        fail('INVALID_REQUEST', 400)
    for key in ('limit', 'party_no'):
        if key in request.query_params and not re.fullmatch(r'[0-9]+', request.query_params[key]):
            fail('INVALID_REQUEST', 400)
    body = await request.body()
    if request.method == 'GET' and body:
        fail('INVALID_REQUEST', 400)
    if request.method == 'POST' and body:
        try:
            json.loads(body, object_pairs_hook=unique_object)
        except (ValueError, UnicodeDecodeError):
            fail('INVALID_REQUEST', 400)


def optional_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    return authenticated(credentials) if 'authorization' in request.headers else None


OptionalPrincipal = Annotated[tuple | None, Depends(optional_principal)]
Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(min_length=1, max_length=2048)]
Identifier = Annotated[str | None, Query(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9._-]+$')]
router = APIRouter(prefix='/v1', tags=['raid-rooms'], dependencies=[Depends(strict_input)])
errors = {code: {'model': GameErrorOut, 'headers': {
    'Cache-Control': {'schema': {'type': 'string', 'const': 'no-store'}},
    **({'WWW-Authenticate': {'schema': {'type': 'string', 'const': 'Bearer'}}} if code == 401 else {}),
    **({'Retry-After': {'description': 'REQUEST_IN_PROGRESS only', 'schema': {'type': 'integer', 'const': 2}}}
       if code == 409 else {}),
}} for code in (400, 401, 403, 404, 409, 503)}


def create_policy(data):
    def policy(db, uid, room, round, selection, character):
        if data.min_combat_power.dealer is not None or data.min_combat_power.support is not None:
            fail('COMBAT_REQUIREMENT_UNAVAILABLE')
        policies.public_finite(db, uid, room, round, selection, character)
    return policy


@router.get('/raid-rooms', response_model=s.RoomPage, responses=errors)
def room_list(principal: OptionalPrincipal, scope: Literal['public', 'group'] = 'public',
              group_id: UUID | None = None, raid_id: Identifier = None, difficulty_id: Identifier = None,
              state: Literal['active', 'ended', 'all'] = 'active', limit: Limit = 20, cursor: Cursor = None):
    return queries.room_list(principal, scope=scope, group_id=group_id, raid_id=raid_id,
                             difficulty_id=difficulty_id, state=state, limit=limit, cursor=cursor)


@router.post('/raid-rooms', status_code=201, response_model=h.RoomCommandAck, responses=errors)
def create(data: h.RoomCreateIn, principal: Principal, key: Key):
    return service.create(principal, key, data, policy=runtime.admission_policy(create_policy(data)))[1]


@router.get('/raid-rooms/{room_id}', response_model=s.RoomSummary, responses=errors)
def summary(room_id: UUID, principal: OptionalPrincipal):
    return queries.room_summary(room_id, principal)


@router.get('/me/raid-rooms/{room_id}', response_model=s.RoomDetail, responses=errors)
def detail(room_id: UUID, principal: Principal):
    return queries.room_detail(principal, room_id)


@router.get('/me/raid-room-memberships', response_model=s.MembershipPage, responses=errors)
def memberships(principal: Principal, state: Literal['current', 'ended', 'all'] = 'current',
                limit: Limit = 20, cursor: Cursor = None):
    return queries.memberships(principal, state=state, limit=limit, cursor=cursor)


@router.get('/raid-rooms/{room_id}/admission-context', response_model=s.AdmissionContext, responses=errors)
def context(room_id: UUID, character_id: UUID, selected_role: Literal['dealer', 'support'],
            party_no: Annotated[int, Query(ge=1, le=2)], intent: Literal['apply', 'join'], principal: Principal):
    return queries.admission_context(principal, room_id, character_id=character_id,
                                     selected_role=selected_role, party_no=party_no, intent=intent)


@router.post('/raid-rooms/{room_id}/applications', status_code=201, response_model=h.ApplicationAck, responses=errors)
def apply(room_id: UUID, data: h.AdmissionIn, principal: Principal, key: Key):
    return service.admit(principal, room_id, key, data, applying=True, policy=runtime.admission_policy(policies.public_finite))[1]


@router.post('/raid-rooms/{room_id}/join', response_model=h.RoomCommandAck, responses=errors)
def join(room_id: UUID, data: h.AdmissionIn, principal: Principal, key: Key):
    return service.admit(principal, room_id, key, data, policy=runtime.admission_policy(policies.public_finite))[1]


@router.get('/me/raid-room-applications', response_model=s.ApplicationPage, responses=errors)
def my_applications(principal: Principal, state: Literal['pending', 'ended', 'all'] = 'pending',
                    limit: Limit = 20, cursor: Cursor = None):
    return queries.applications(principal, state=state, limit=limit, cursor=cursor)


@router.get('/raid-rooms/{room_id}/applications', response_model=s.ApplicationPage, responses=errors)
def applications(room_id: UUID, principal: Principal, state: Literal['pending', 'ended', 'all'] = 'pending',
                 limit: Limit = 20, cursor: Cursor = None):
    return queries.applications(principal, room_id=room_id, state=state, limit=limit, cursor=cursor)


@router.get('/raid-room-applications/{application_id}', response_model=s.Application, responses=errors)
def application(application_id: UUID, principal: Principal):
    return queries.application(principal, application_id)


@router.post('/raid-room-applications/{application_id}/approve', response_model=h.RoomCommandAck, responses=errors)
def approve(application_id: UUID, data: h.DecisionIn, principal: Principal, key: Key):
    return service.decide(principal, application_id, key, data, approve=True, policy=runtime.admission_policy(policies.public_finite))[1]


@router.post('/raid-room-applications/{application_id}/reject', response_model=h.ApplicationAck, responses=errors)
def reject(application_id: UUID, data: h.DecisionIn, principal: Principal, key: Key):
    return service.decide(principal, application_id, key, data)[1]


@router.post('/raid-room-applications/{application_id}/withdraw', response_model=h.ApplicationAck, responses=errors)
def withdraw(application_id: UUID, data: h.WithdrawIn, principal: Principal, key: Key):
    return service.withdraw(principal, application_id, key, data)[1]


@router.get('/me/raid-rooms/{room_id}/management', response_model=s.RoomManagement, responses=errors)
def management(room_id: UUID, principal: Principal):
    return queries.management(principal, room_id)


@router.post('/raid-rooms/{room_id}/leave', response_model=h.MembershipEndAck, responses=errors)
def leave(room_id: UUID, data: h.MembershipIn, principal: Principal, key: Key):
    return service.recover(principal, room_id, key, data, 'leave')[1]


@router.post('/raid-rooms/{room_id}/leadership-transfer', response_model=h.RoomCommandAck, responses=errors)
def transfer(room_id: UUID, data: h.TransferIn, principal: Principal, key: Key):
    return service.recover(principal, room_id, key, data, 'transfer')[1]


@router.post('/raid-rooms/{room_id}/end', response_model=h.RoomEndAck, responses=errors)
def end(room_id: UUID, data: h.MembershipIn, principal: Principal, key: Key):
    return service.recover(principal, room_id, key, data, 'end')[1]
