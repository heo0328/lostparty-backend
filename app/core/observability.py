"""Allowlisted JSON events. Never format messages, traceback, SQL or request data."""
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import math
import re
from time import perf_counter
import uuid

logger = logging.getLogger('lostparty')
request_context = ContextVar('log_request_id', default=None)
job_context = ContextVar('log_job', default=None)
EVENTS = {'http_request', 'api_rejected', 'database_error', 'job_completed', 'job_item_failed',
          'provider_failure', 'google_verification', 'server_event', 'library_event'}
JOBS = {'auth_cleanup', 'ownership_settlement', 'recruitment', 'legacy_opening', 'cycle_rollover'}
CATEGORIES = {'connection', 'lock_unavailable', 'query_cancelled', 'deadlock', 'serialization',
              'constraint', 'database', 'internal', 'cancelled'}
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}


def safe_uuid(value):
    if not isinstance(value, (str, uuid.UUID)):
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def category(error):
    from sqlalchemy.exc import SQLAlchemyError, OperationalError
    import psycopg
    if isinstance(error, (SQLAlchemyError, psycopg.Error)):
        original = getattr(error, 'orig', error)
        state = getattr(original, 'sqlstate', None)
        fixed = {'55P03': 'lock_unavailable', '57014': 'query_cancelled',
                 '40P01': 'deadlock', '40001': 'serialization'}
        if isinstance(state, str) and state in fixed:
            return fixed[state]
        if isinstance(state, str) and state.startswith('23'):
            return 'constraint'
        if (isinstance(state, str) and state.startswith('08')) or (state is None and isinstance(error, (OperationalError, psycopg.OperationalError))):
            return 'connection'
        return 'database'
    return 'internal'


class SafeJsonFormatter(logging.Formatter):
    def format(self, record):
        event = getattr(record, 'safe_event', None)
        if not isinstance(event, str) or event not in EVENTS:
            event = 'server_event' if record.name.startswith('uvicorn') else 'library_event'
        result = {'time': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                  'level': record.levelname, 'event': event}
        fields = getattr(record, 'safe_fields', {})
        if not isinstance(fields, dict):
            fields = {}
        request_id = safe_uuid(fields.get('request_id'))
        if request_id:
            result['request_id'] = request_id
        for key in ('status', 'upstream_status'):
            value = fields.get(key)
            if type(value) is int and 100 <= value <= 599:
                result[key] = value
        for key in ('duration_ms', 'elapsed_ms'):
            value = fields.get(key)
            if type(value) in (int, float) and math.isfinite(value) and value >= 0:
                result[key] = round(value, 3)
        for key, allowed in (
            ('method', METHODS | {'OTHER'}), ('job', JOBS), ('category', CATEGORIES),
            ('outcome', {'success', 'failed', 'partial_failure', 'cancelled'}),
        ):
            if isinstance(fields.get(key), str) and fields[key] in allowed:
                result[key] = fields[key]
        route = fields.get('route')
        # Only application-owned route templates, never scope.path or query strings.
        if isinstance(route, str) and len(route) <= 256 and re.fullmatch(r'[A-Za-z0-9_/{\}:.-]+', route):
            result['route'] = route
        code = fields.get('code')
        if isinstance(code, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code):
            result['code'] = code
        if type(fields.get('failed_items')) is int and fields['failed_items'] >= 0:
            result['failed_items'] = fields['failed_items']
        # Existing provider diagnostic vocabulary is already part of the internal contract.
        if event == 'provider_failure':
            from app.game_accounts.provider_diagnostics import STAGES, REASONS, DETAILS, milliseconds
            for key, allowed in (('stage', STAGES), ('reason', REASONS), ('detail', DETAILS)):
                if isinstance(fields.get(key), str) and fields[key] in allowed:
                    result[key] = fields[key]
            timings = fields.get('stage_ms', {})
            if isinstance(timings, dict):
                result['stage_ms'] = {k: milliseconds(timings[k]) for k in sorted(STAGES) if k in timings}
        if event == 'google_verification' and isinstance(fields.get('stage'), str) and fields['stage'] in {
            'algorithm', 'signature_audience_time', 'issuer', 'subject', 'nonce', 'azp_allowlist',
        }:
            result['stage'] = fields['stage']
        return json.dumps(result, separators=(',', ':'), ensure_ascii=True)


def emit(event, *, level=logging.INFO, **fields):
    if 'request_id' not in fields:
        fields['request_id'] = request_context.get()
    logger.log(level, event, extra={'safe_event': event, 'safe_fields': fields})


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        rid = str(uuid.uuid4())
        state = scope.setdefault('state', {})
        state['log_request_id'] = rid
        token = request_context.set(rid)
        started = perf_counter()
        status = 500
        outcome = 'success'
        failure = None

        async def observed_send(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except BaseException as error:
            import asyncio
            outcome = 'cancelled' if isinstance(error, asyncio.CancelledError) else 'failed'
            failure = 'cancelled' if outcome == 'cancelled' else category(error)
            raise
        finally:
            if outcome == 'success' and status >= 400:
                outcome = 'failed'
            route = getattr(scope.get('route'), 'path', 'unmatched')
            emit('http_request', level=logging.ERROR if status >= 500 else logging.INFO,
                 request_id=state['log_request_id'], method=scope['method'] if scope['method'] in METHODS else 'OTHER',
                 route=route, status=status, outcome=outcome, category=failure,
                 duration_ms=(perf_counter() - started) * 1000)
            request_context.reset(token)


def job_item_failed(job, error):
    context = job_context.get()
    if context is not None:
        context['failed_items'] += 1
    emit('job_item_failed', level=logging.WARNING, job=job, category=category(error))


def run_job(job, function):
    started = perf_counter()
    context = {'failed_items': 0}
    token = job_context.set(context)
    outcome = 'success'
    failure = None
    try:
        return function()
    except BaseException as error:
        outcome = 'failed'
        failure = category(error)
        raise
    finally:
        if outcome == 'success' and context['failed_items']:
            outcome = 'partial_failure'
        emit('job_completed', level=logging.INFO if outcome == 'success' else logging.WARNING,
             job=job, outcome=outcome, category=failure, failed_items=context['failed_items'],
             duration_ms=(perf_counter() - started) * 1000)
        job_context.reset(token)
