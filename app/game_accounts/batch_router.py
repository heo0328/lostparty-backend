"""Strict whole-envelope preflight; legacy route body/query rules are untouched."""
import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.routing import APIRoute

from app.game_accounts import batches, batch_schemas as s
from app.game_accounts.profile_router import common
from app.game_accounts.router import Principal
from app.game_accounts.support import fail

BODY_FIELDS = ('expected_version', 'expected_ownership_revision', 'expected_lifecycle_revision', 'summary')
EXAMPLE_ID = '00000000-0000-4000-8000-000000000001'
EXAMPLE_STAMP = '2026-11-03T09:00:00Z'
EXAMPLE_COMMAND = dict(character_id=EXAMPLE_ID, role='dealer',
    command_id='00000000-0000-4000-8000-000000000002', expected_version=1,
    expected_ownership_revision=1, expected_lifecycle_revision=1,
    summary=dict(source='flutter_analysis', analysis_rules_version='flutter-v1',
        analyzed_at=EXAMPLE_STAMP, combat_power='12345.00', item_level='1700',
        combat_power_observed_at=EXAMPLE_STAMP, item_level_observed_at=EXAMPLE_STAMP,
        integrity_status='clean', issues=[], catalog_version=None, observed_lifecycle_revision=1))
EXAMPLE_ERROR = dict(code='REVISION_CONFLICT', message='REVISION_CONFLICT',
                     request_id='synthetic-request', retry_after_seconds=None)
EXAMPLE_CORRELATION = {k: EXAMPLE_COMMAND[k] for k in ('character_id', 'role', 'command_id')}
EXAMPLE_RESULT = dict(character_id=EXAMPLE_ID, role='dealer', ownership_revision=1,
    lifecycle_revision=1, version=2, summary=EXAMPLE_COMMAND['summary'], saved_at=EXAMPLE_STAMP)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('INVALID_REQUEST', 400)
        result[key] = value
    return result


class BatchRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            if any(k != 'character_id' or request.method != 'GET' for k in request.query_params):
                fail('INVALID_REQUEST', 400)
            body = bytearray()
            async for chunk in request.stream():
                if request.method == 'GET' and chunk:
                    fail('INVALID_REQUEST', 400)
                if len(body) + len(chunk) > 524288:
                    fail('REQUEST_TOO_LARGE', 413)
                body.extend(chunk)
            request._body = bytes(body)
            if request.method == 'POST':
                try:
                    raw = json.loads(body.decode('utf-8'), object_pairs_hook=unique_object,
                                     parse_constant=lambda _: fail('INVALID_REQUEST', 400))
                    # Reject escaped lone surrogates, including metadata echoed in results.
                    json.dumps(raw, ensure_ascii=False).encode('utf-8')
                except (ValueError, UnicodeError, RecursionError):
                    fail('INVALID_REQUEST', 400)
                if isinstance(raw, dict) and isinstance(raw.get('items'), list):
                    for item in raw['items']:
                        if isinstance(item, dict):
                            command = {k: item[k] for k in BODY_FIELDS if k in item}
                            try:
                                size = len(json.dumps(command, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                            except (UnicodeError, RecursionError):
                                fail('INVALID_REQUEST', 400)
                            if size > 32768:
                                fail('REQUEST_TOO_LARGE', 413)
                request._json = raw
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


@router.post('/role-summary-batches', response_model=s.RoleSummaryBatchOut, responses=common,
    openapi_extra={
        'requestBody': {'content': {'application/json': {'example': {'items': [EXAMPLE_COMMAND]}}}},
        'responses': {'200': {'content': {'application/json': {'examples': {
            'success': {'value': {'items': [dict(**EXAMPLE_CORRELATION, status=200,
                                               result=EXAMPLE_RESULT, error=None)]}},
            'conflict': {'value': {'items': [dict(**EXAMPLE_CORRELATION, status=409,
                                                result=None, error=EXAMPLE_ERROR)]}}
        }}}}}},
    description=('1–50 commands, raw UTF-8 envelope <=524288 bytes; each RoleSummaryIn input subset '
        'compact JSON (ensure_ascii=false) <=32768 bytes. Duplicate JSON keys/command IDs/target roles '
        'reject before writes. Independent transactions; outer 200 includes per-item failures. '
        '20s budget checked between items, client response timeout 60s recommended. '
        'Same role-summary idempotency as single PUT, no batch key; retry original keys/bodies. '
        'BATCH_NOT_PROCESSED means unattempted; SERVICE_UNAVAILABLE may have committed. '
        'Historical ACK; use account-bootstrap for current state.'))
def put(request: Request, data: s.RoleSummaryBatchIn, principal: Principal):
    return batches.put(principal, data, request.state.log_request_id)
