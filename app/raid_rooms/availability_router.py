"""R2 router, integrated application activation reserved for R5."""
import json
from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.raid_rooms import availability as service, availability_schemas as s


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


class AvailabilityRoute(APIRoute):
    body_limit = 32768

    def allowed_query(self, request):
        return set()

    def repeated_query(self, request):
        return set()

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            if (set(request.query_params)-self.allowed_query(request) or
                    any(len(request.query_params.getlist(k))>1 and k not in self.repeated_query(request) for k in request.query_params) or
                    any(len(request.headers.getlist(k)) > 1 for k in ('authorization', 'idempotency-key'))):
                fail('INVALID_REQUEST', 400)
            if len(request.scope.get('query_string',b''))>self.body_limit:
                fail('REQUEST_TOO_LARGE',413)
            body = bytearray()
            async for chunk in request.stream():
                if request.method == 'GET' and chunk:
                    fail('INVALID_REQUEST', 400)
                if len(body) + len(chunk) > self.body_limit:
                    fail('REQUEST_TOO_LARGE', 413)
                body.extend(chunk)
            request._body = bytes(body)
            if body:
                try:
                    json.loads(body, object_pairs_hook=unique_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, UnicodeDecodeError, RecursionError):
                    fail('INVALID_REQUEST', 400)
            return await handler(request)
        return bounded


router = APIRouter(prefix='/v1/me', tags=['recruitment-availability'], route_class=AvailabilityRoute)
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 404, 409, 413, 503)}


@router.get('/play-availability', response_model=s.PersonalOut, responses=errors)
def get_personal(principal: Principal):
    return service.get(principal)


@router.put('/play-availability', response_model=s.PersonalOut, responses=errors)
def put_personal(data: s.PersonalIn, principal: Principal, key: Key):
    return service.put(principal, key, data.model_dump())[1]


@router.get('/raid-rooms/{room_id}/availability-submission', response_model=s.SubmissionOut, responses=errors)
def get_submission(room_id: UUID, principal: Principal):
    return service.get(principal, room_id)


@router.put('/raid-rooms/{room_id}/availability-submission', response_model=s.SubmissionOut, responses=errors)
def put_submission(room_id: UUID, data: s.SubmissionIn, principal: Principal, key: Key):
    return service.put(principal, key, data.model_dump(), room_id)[1]
