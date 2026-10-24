"""Synthetic API/job failures and real JSON formatting; no secret payloads in output."""
import asyncio
import io
import json
import logging
import logging.config
from pathlib import Path
import subprocess
import sys
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.core.errors import AuthError, register
from app.core import observability as obs

SECRET = 'private-token-personal-name-SQL-parameter'


@pytest.fixture
def output():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(obs.SafeJsonFormatter())
    previous = obs.logger.level
    obs.logger.setLevel(logging.INFO)
    obs.logger.addHandler(handler)
    yield lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
    obs.logger.removeHandler(handler)
    obs.logger.setLevel(previous)


def api():
    app = FastAPI()
    register(app)

    @app.get('/items/{item_id}')
    def get(item_id: uuid.UUID):
        return {'ok': True}

    @app.get('/reject')
    def reject():
        raise AuthError('ACCESS_INVALID')

    @app.get('/database')
    def database():
        error = SimpleNamespace(sqlstate='55P03')
        raise OperationalError(SECRET, {'password': SECRET}, error)

    @app.get('/crash')
    def crash():
        raise RuntimeError(SECRET)

    @app.get('/stream')
    def stream():
        return StreamingResponse(iter(['first', 'second']), media_type='text/plain')

    return app


def test_request_fields_exclude_values_headers_body_query_and_unmatched_paths(output):
    identifier = str(uuid.uuid4())
    with TestClient(api(), raise_server_exceptions=False) as client:
        result = client.get('/items/' + identifier, params={'token': SECRET},
                            headers={'Authorization': SECRET, 'X-Request-ID': SECRET, 'Cookie': SECRET})
        assert result.status_code == 200 and result.json() == {'ok': True}
        assert client.get('/' + SECRET).status_code == 404
    logs = output()
    requests = [line for line in logs if line['event'] == 'http_request']
    assert len(requests) == 2
    assert requests[0]['route'] == '/items/{item_id}' and requests[1]['route'] == 'unmatched'
    serialized = json.dumps(logs)
    assert SECRET not in serialized and identifier not in serialized
    assert requests[0]['duration_ms'] >= 0 and requests[0]['method'] == 'GET'


def test_rejection_correlates_existing_response_id_and_request_event(output):
    with TestClient(api()) as client:
        response = client.get('/reject')
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    assert response.headers['cache-control'] == 'no-store'
    assert set(response.json()) == {'error'}
    assert set(response.json()['error']) == {'code', 'message', 'request_id'}
    logs = output()
    assert {v['event'] for v in logs} == {'api_rejected', 'http_request'}
    assert {v['request_id'] for v in logs} == {response.json()['error']['request_id']}


def test_database_failure_is_classified_without_statement_or_exception(output):
    with TestClient(api()) as client:
        response = client.get('/database')
    assert response.status_code == 503 and response.json()['error']['code'] == 'SERVICE_UNAVAILABLE'
    logs = output()
    assert next(v for v in logs if v['event'] == 'database_error')['category'] == 'lock_unavailable'
    assert SECRET not in json.dumps(logs)
    assert {v['request_id'] for v in logs} == {response.json()['error']['request_id']}


def test_unhandled_error_keeps_500_and_is_logged_once(output):
    with TestClient(api(), raise_server_exceptions=False) as client:
        assert client.get('/crash').status_code == 500
    logs = output()
    assert len(logs) == 1 and logs[0]['status'] == 500 and logs[0]['outcome'] == 'failed'
    assert SECRET not in json.dumps(logs)


def test_streaming_body_is_preserved_and_context_does_not_bleed(output):
    with TestClient(api()) as client:
        assert client.get('/stream').text == 'firstsecond'
        assert client.get('/stream').text == 'firstsecond'
    assert len({line['request_id'] for line in output()}) == 2
    assert obs.request_context.get() is None


@pytest.mark.parametrize('state,expected', [('55P03','lock_unavailable'), ('57014','query_cancelled'),
    ('40P01','deadlock'), ('40001','serialization'), ('23505','constraint'), ('08006','connection'), ('XX000','database')])
def test_database_classification(state, expected):
    assert obs.category(OperationalError(SECRET, {}, SimpleNamespace(sqlstate=state))) == expected


def test_job_success_failure_and_partial_failure(output):
    assert obs.run_job('auth_cleanup', lambda: 17) == 17
    def bad():
        raise RuntimeError(SECRET)
    with pytest.raises(RuntimeError):
        obs.run_job('ownership_settlement', bad)
    obs.run_job('recruitment', lambda: obs.job_item_failed('cycle_rollover', RuntimeError(SECRET)))
    logs = output()
    completed = [v for v in logs if v['event'] == 'job_completed']
    assert [v['outcome'] for v in completed] == ['success', 'failed', 'partial_failure']
    assert completed[2]['failed_items'] == 1
    assert all(v['duration_ms'] >= 0 for v in completed)
    assert SECRET not in json.dumps(logs) and obs.job_context.get() is None


def test_formatter_never_renders_raw_messages_tracebacks_or_arbitrary_extras():
    record = logging.LogRecord('uvicorn.error', logging.ERROR, '', 0, SECRET, (),
                               (RuntimeError, RuntimeError(SECRET), None))
    record.safe_fields = {'password': SECRET, 'request_id': SECRET, 'route': '/bad?' + SECRET,
                          'category': {'secret': SECRET}}
    data = json.loads(obs.SafeJsonFormatter().format(record))
    assert data['event'] == 'server_event' and SECRET not in json.dumps(data)
    assert set(data) == {'time', 'level', 'event'}


def test_real_log_config_discards_uvicorn_access_and_redacts_exception_text():
    # Subprocess avoids modifying pytest/caplog's global handlers.
    code = '''import json,logging,logging.config
from pathlib import Path
logging.config.dictConfig(json.loads(Path('app/core/logging.json').read_text()))
logging.getLogger('uvicorn.access').info('private-access-token')
try: raise ValueError('private-exception-token')
except ValueError: logging.getLogger('uvicorn.error').exception('private-raw-message')
from app.core.observability import emit
emit('job_completed', job='auth_cleanup', outcome='success', duration_ms=1)
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
    logs = [json.loads(line) for line in result.stdout.splitlines()]
    assert [v['event'] for v in logs] == ['server_event', 'job_completed']
    assert 'private-' not in result.stdout + result.stderr


def test_asgi_cancellation_is_recorded_and_reraised(output):
    async def cancelled(scope, receive, send):
        raise asyncio.CancelledError()
    async def run():
        with pytest.raises(asyncio.CancelledError):
            await obs.RequestLoggingMiddleware(cancelled)({'type':'http','method':'GET'}, None, None)
        assert obs.request_context.get() is None
    asyncio.run(run())
    assert output()[0]['outcome'] == 'cancelled'


def test_concurrent_asgi_requests_keep_independent_context(output):
    ids = []
    async def application(scope, receive, send):
        before = obs.request_context.get()
        await asyncio.sleep(0)
        assert obs.request_context.get() == before
        ids.append(before)
        await send({'type':'http.response.start', 'status':200, 'headers':[]})
        await send({'type':'http.response.body', 'body':b'ok'})
    async def send(message):
        pass
    async def run():
        middleware = obs.RequestLoggingMiddleware(application)
        await asyncio.gather(*(middleware({'type':'http','method':'GET'}, None, send) for _ in range(2)))
    asyncio.run(run())
    assert len(set(ids)) == 2 and {v['request_id'] for v in output()} == set(ids)


@pytest.mark.parametrize('name', ['auth_cleanup', 'ownership_settlement', 'recruitment'])
def test_actual_worker_loops_continue_after_safe_failure(name, monkeypatch, output):
    from app.auth import cleanup
    from app.ownership_disputes import worker as ownership
    from app.raid_rooms import worker as recruitment
    monkeypatch.setenv('OWNERSHIP_WORKER_ENABLED', '1')
    monkeypatch.setenv('RECRUITMENT_WORKER_ENABLED', '1')
    count = 0
    sleeps = 0
    def step():
        nonlocal count
        count += 1
        if count == 1:
            raise RuntimeError(SECRET)
    async def sleep(seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 3:
            raise asyncio.CancelledError()
    monkeypatch.setattr(asyncio, 'sleep', sleep)
    if name == 'auth_cleanup':
        monkeypatch.setattr(cleanup, 'cleanup_all', step)
        coroutine = cleanup.run()
    elif name == 'ownership_settlement':
        monkeypatch.setattr(ownership, 'tick', step)
        coroutine = ownership.run()
    else:
        coroutine = recruitment.run(step)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(coroutine)
    completed = [v for v in output() if v['event'] == 'job_completed']
    assert count == 2 and [v['outcome'] for v in completed] == ['failed', 'success']
    assert {v['job'] for v in completed} == {name}
    assert SECRET not in json.dumps(output())


def test_health_database_error_keeps_response(client, monkeypatch, output):
    import psycopg
    from app import main
    def unavailable():
        raise psycopg.OperationalError(SECRET)
    monkeypatch.setattr(main, 'connect', unavailable)
    result = client.get('/health')
    assert result.status_code == 503 and result.json() == {'status':'unhealthy','database':'unavailable'}
    logs = output()
    assert any(v.get('category') == 'connection' for v in logs)
    assert SECRET not in json.dumps(logs)
