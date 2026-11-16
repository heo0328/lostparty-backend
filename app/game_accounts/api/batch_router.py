"""Stored personal-profile batch reads with strict query/body validation."""
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from fastapi.routing import APIRoute

from app.game_accounts.rosters import batches
from app.game_accounts.schemas import batch_schemas as s
from app.game_accounts.api.profile_router import common
from app.game_accounts.api.router import Principal
from app.game_accounts.common.support import fail


class BatchRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            if any(k != 'character_id' or request.method != 'GET' for k in request.query_params):
                fail('INVALID_REQUEST', 400)
            async for chunk in request.stream():
                if chunk:
                    fail('INVALID_REQUEST', 400)
            request.state.log_request_id = getattr(request.state, 'log_request_id', None) or str(uuid.uuid4())
            return await handler(request)
        return bounded


router = APIRouter(prefix='/v2/me', tags=['character-profiles'], route_class=BatchRoute)


@router.get('/characters/personal-profiles', response_model=s.PersonalProfilesOut, responses=common,
    description='1–50 distinct character_id values; one read-only snapshot, no provider calls. Per-item status/profile/error; no-store.')
def get(request: Request, principal: Principal,
        character_id: Annotated[list[UUID], Query(min_length=1, max_length=50)]):
    if len(set(character_id)) != len(character_id):
        fail('INVALID_REQUEST', 400)
    return batches.get(principal, character_id, request.state.log_request_id)
