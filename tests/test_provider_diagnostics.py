"""Safe failure diagnostics and correlation through the real HTTP collector."""
import json
import uuid
import requests
import pytest
from sqlalchemy import select, func
from app.core.database import session
from app.game_accounts import provider, provider_diagnostics
from app.game_accounts.models import Verification, RequestResult, VerificationExecution
from tests.test_live_equipment_proof import live
from tests.test_game_accounts import world, change, VERIFY
from tests.test_game_account_primitives import transport


def diagnostic(caplog):
    entries = [r.message.removeprefix('Provider failure ') for r in caplog.records
               if r.name == 'app.game_accounts.provider_diagnostics']
    assert len(entries) == 1
    return json.loads(entries[0])


@pytest.mark.parametrize('failure,stage,reason,detail,status', [
    ('timeout', 'siblings_transport', 'UPSTREAM_UNAVAILABLE', 'transport_timeout', None),
    ('connection', 'siblings_transport', 'UPSTREAM_UNAVAILABLE', 'transport_connection', None),
    ('http', 'siblings_transport', 'UPSTREAM_UNAVAILABLE', None, 502),
    ('media', 'siblings_transport', 'UPSTREAM_INVALID_RESPONSE', 'content_type', 200),
    ('schema', 'siblings_schema', 'UPSTREAM_INVALID_RESPONSE', None, 200),
    ('armory_size', 'armory_transport', 'UPSTREAM_RESPONSE_TOO_LARGE', 'body_size', 200),
    ('equipment', 'armory_equipment', 'UPSTREAM_INVALID_RESPONSE', None, 200),
    ('profile', 'armory_profile', 'UPSTREAM_INVALID_RESPONSE', None, 200),
    ('rate', 'siblings_transport', 'UPSTREAM_RATE_LIMITED', None, 429),
    ('key', 'siblings_transport', 'LOSTARK_KEY_REJECTED', None, 401),
])
def test_failure_stage_and_response_correlation(client, live, monkeypatch, caplog,
                                               failure, stage, reason, detail, status):
    h, state = live
    original = provider.requests.get

    def get(url, **kwargs):
        if failure == 'timeout':
            raise requests.Timeout('private-name private-token private-url')
        if failure == 'connection':
            raise requests.ConnectionError('private-name private-token private-url')
        if failure in ('http', 'rate', 'key'):
            return transport(status=status)[1]
        if failure == 'media':
            return transport(media='private-content-type')[1]
        if failure == 'schema':
            return transport(body=b'[{"private-data":"private-name"}]')[1]
        if failure == 'armory_size' and not url.endswith('/siblings'):
            return transport(body=b'x' * (provider.MAX_BODY_BYTES + 1))[1]
        if failure == 'equipment':
            state['malformed'] = 'entry'
        if failure == 'profile':
            state['profile_server'] = 'private-name'
        return original(url, **kwargs)

    monkeypatch.setattr(provider.requests, 'get', get)
    response = change(client, h, 'post', VERIFY, dict(source='direct_input', character_name='a0'))
    assert response.status_code == (409 if failure == 'key' else 503)
    code = reason if failure in ('key', 'rate') else 'UPSTREAM_UNAVAILABLE'
    body = response.json()['error']
    assert body['code'] == code
    d = diagnostic(caplog)
    assert d['request_id'] == body['request_id']
    assert str(uuid.UUID(d['request_id'])) == d['request_id']
    assert (d['stage'], d['reason'], d['detail'], d['upstream_status']) == (stage, reason, detail, status)
    assert d['elapsed_ms'] >= 0 and d['stage_ms'][stage] >= 0
    assert sum(d['stage_ms'].values()) == pytest.approx(d['elapsed_ms'], abs=.02)
    if stage.startswith('armory'):
        assert 'siblings_transport' in d['stage_ms']
    for secret in ('private-name', 'private-token', 'private-url', 'private-data', 'private-content-type',
                   'test.member.signature', 'Authorization', 'ArmoryEquipment', 'sample-server'):
        assert secret not in caplog.text
        assert secret not in response.text
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Verification)) == 0
        assert db.scalar(select(RequestResult).where(RequestResult.operation == 'start')).state == 'retryable'
        e = db.scalar(select(VerificationExecution))
        assert (e.state, e.outcome_code) == ('failed', code)


def test_log_fields_are_allowlisted(caplog):
    e = provider.ProviderUnavailable('private-reason', http_status='private-status', diagnostic_reason='private-detail')
    e.diagnostic_stage = 'private-stage'
    e.diagnostic_elapsed_ms = float('nan')
    e.diagnostic_timings = {'private-name': 42, 'siblings_transport': float('inf')}
    rid = provider_diagnostics.record(e)
    d = diagnostic(caplog)
    assert d == dict(request_id=rid, stage='unknown', reason='unknown', detail=None,
                     upstream_status=None, elapsed_ms=None, stage_ms={'siblings_transport': None})
    assert 'private-' not in caplog.text
