"""Strict bounded envelope before reserving any character-analysis command."""
import json
import uuid
from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from app.game_accounts.api.router import Principal, common
from app.game_accounts.common.support import fail
from app.game_accounts.schemas.analysis_schemas import AnalysisRequest, AnalysisResponse
from app.game_accounts.schemas.schemas import GameErrorOut
from app.game_accounts.analysis import service


def unique(pairs):
    value = {}
    for name, item in pairs:
        if name in value:
            fail('INVALID_REQUEST', 400)
        value[name] = item
    return value


class AnalysisRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def bounded(request):
            if request.query_params:
                fail('INVALID_REQUEST', 400)
            if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                fail('INVALID_REQUEST', 400)
            body = bytearray()
            async for part in request.stream():
                if len(body)+len(part) > 524288:
                    fail('REQUEST_TOO_LARGE', 413)
                body.extend(part)
            try:
                value = json.loads(body.decode('utf-8'), object_pairs_hook=unique,
                    parse_constant=lambda _: fail('INVALID_REQUEST', 400))
                json.dumps(value, ensure_ascii=False).encode('utf-8')
            except (ValueError, UnicodeError, RecursionError):
                fail('INVALID_REQUEST', 400)
            request._body = bytes(body)
            request._json = value
            request.state.log_request_id = getattr(request.state, 'log_request_id', None) or str(uuid.uuid4())
            return await handler(request)
        return bounded


router = APIRouter(prefix='/v2/me', tags=['character-analysis'], route_class=AnalysisRoute)


@router.post('/character-analysis/refresh', response_model=AnalysisResponse, responses={**common,413:{'model':GameErrorOut,'description':'REQUEST_TOO_LARGE'}},
    description='character-analysis-refresh-1; 1..50 distinct characters/commands, <=524288 UTF-8 bytes; independent commands, 20s budget, 2 concurrent fresh observations. Item IDs own idempotency; same ID/body for unresolved commands, no automatic retry of terminal failures. No-store; client timeout 60s.')
def refresh(request: Request, data: AnalysisRequest, principal: Principal):
    return service.refresh(principal, data, request.state.log_request_id)
