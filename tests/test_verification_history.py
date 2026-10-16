"""Real PostgreSQL execution history remains separate from ownership authority."""
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import observations, verification_history
from app.game_accounts.models import VerificationExecution as Execution, Verification, Account, Audit, RequestResult
from app.game_accounts.provider import ProviderUnavailable
from tests.test_game_accounts import world, register, start, verify, change, another_user, VERIFY


def events():
    with session() as db:
        return list(db.scalars(select(Execution).order_by(Execution.started_at)))


def test_other_owner_rejection_has_durable_snapshot_without_transfer(client, world, monkeypatch, login):
    h, state = world
    verify(client, h, state)
    other = another_user(login, monkeypatch, client)
    state['binding'] = False
    response = change(client, other, 'post', VERIFY, dict(source='direct_input', character_name='a0'))
    assert response.status_code == 201
    e = events()[-1]
    assert e.state == 'completed' and e.outcome_code == 'PENDING'
    assert e.lookup_name == 'a0' and e.challenge_id == uuid.UUID(response.json()['challenge_id'])
    assert e.target_snapshot['context']['target'] == ['sample-server', 'a0']
    with session() as db:
        a = db.scalar(select(Account))
        assert e.actor_id != a.owner_id
        assert e.target_snapshot['conflicting_accounts'] == [dict(account_id=str(a.id), owner_id=str(a.owner_id), ownership_revision=a.ownership_revision)]
        assert db.scalar(select(func.count()).select_from(Verification)) == 2
        assert db.scalar(select(func.count()).select_from(Audit)) == 1


def test_provider_failure_retry_same_command_keeps_both_executions(client, world, monkeypatch, login):
    h, state = world
    key = uuid.uuid4()
    data = dict(source='direct_input', character_name='a0')
    original = observations.fetch
    def broken(*args, **kwargs):
        raise ProviderUnavailable('UPSTREAM_UNAVAILABLE')
    monkeypatch.setattr(observations, 'fetch', broken)
    assert change(client, h, 'post', VERIFY, data, key).status_code == 503
    first = events()[0]
    assert first.outcome_code == 'UPSTREAM_UNAVAILABLE' and first.target_snapshot is None
    monkeypatch.setattr(observations, 'fetch', original)
    r = change(client, h, 'post', VERIFY, data, key)
    assert r.status_code == 201
    executions = events()
    assert len(executions) == 2
    assert executions[0].command_id == executions[1].command_id
    assert [e.generation for e in executions] == [1, 2]
    assert executions[0].state == 'failed' and executions[1].state == 'completed'
    assert executions[1].challenge_id == uuid.UUID(r.json()['challenge_id'])
    assert change(client, h, 'post', VERIFY, data, key).json() == r.json()
    assert len(events()) == 2


@pytest.mark.parametrize('kind', ['mismatch', 'proof_pending', 'verified', 'expired', 'cancel'])
def test_challenge_outcomes_and_completed_replay(client, world, kind):
    h, state = world
    v = start(client, h)
    method, path = 'post', VERIFY + '/' + v['challenge_id'] + '/confirm'
    expected = 'REQUIRED_EQUIPMENT_PRESENT'
    if kind in ('proof_pending', 'verified'):
        state['removed'] = v['required_slots']
        state['validated'] = kind == 'verified'
        expected = 'VERIFIED' if kind == 'verified' else 'PROVIDER_EVIDENCE_PENDING'
    elif kind == 'expired':
        with session() as db, db.begin():
            db.get(Verification, uuid.UUID(v['challenge_id'])).expires_at = now(db)
        expected = 'VERIFICATION_EXPIRED'
    elif kind == 'cancel':
        method, path = 'delete', VERIFY + '/' + v['challenge_id']
        expected = 'CANCEL_ACKNOWLEDGED'
    key = uuid.uuid4()
    r = change(client, h, method, path, {} if method == 'post' else None, key)
    assert r.status_code == (409 if kind == 'expired' else 204 if kind == 'cancel' else 200)
    e = events()[-1]
    assert e.outcome_code == expected and e.state == 'completed'
    assert e.challenge_id == uuid.UUID(v['challenge_id'])
    assert e.started_at <= e.finished_at and e.http_status == r.status_code
    count = len(events())
    replay = change(client, h, method, path, {} if method == 'post' else None, key)
    assert replay.status_code == r.status_code
    assert len(events()) == count


@pytest.mark.parametrize('target', ['challenge', 'registration'])
def test_unauthorized_target_does_not_capture_private_details(client, world, monkeypatch, login, target):
    h, state = world
    r = register(client, h)
    v = start(client, h, r['registration_id'])
    other = another_user(login, monkeypatch, client)
    if target == 'challenge':
        response = change(client, other, 'post', VERIFY + '/' + v['challenge_id'] + '/confirm', {})
    else:
        response = change(client, other, 'post', VERIFY, dict(source='registration', registration_id=r['registration_id']))
    assert response.status_code == 404
    e = events()[-1]
    assert e.state == 'failed'
    assert e.lookup_name is None and e.challenge_id is None and e.target_snapshot is None


def test_business_rollback_keeps_failure_and_no_success_audit(client, world, monkeypatch, login):
    h, state = world
    v = start(client, h)
    state['removed'] = v['required_slots']
    original = verification_history.complete
    def broken(db, ticket, status, body):
        original(db, ticket, status, body)
        raise RuntimeError('sensitive provider or token text must not be saved')
    monkeypatch.setattr(verification_history, 'complete', broken)
    assert change(client, h, 'post', VERIFY + '/' + v['challenge_id'] + '/confirm', {}).status_code == 500
    e = events()[-1]
    assert e.outcome_code == 'INTERNAL_ERROR' and e.http_status == 500 and e.state == 'failed'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account)) == 0
        assert db.scalar(select(func.count()).select_from(Audit)) == 0
        assert db.get(Verification, uuid.UUID(v['challenge_id'])).status == 'pending'


def test_history_survives_challenge_and_command_cleanup(client, world):
    h, state = world
    v = start(client, h)
    with session() as db, db.begin():
        challenge = db.get(Verification, uuid.UUID(v['challenge_id']))
        challenge.status, challenge.terminal_at = 'expired', now(db) - timedelta(days=4)
        for command in db.scalars(select(RequestResult)):
            command.completed_at = now(db) - timedelta(days=4)
    from app.game_accounts.cleanup import clean
    clean()
    assert len(events()) == 1 and events()[0].challenge_id == uuid.UUID(v['challenge_id'])
    with session() as db:
        assert db.get(Verification, uuid.UUID(v['challenge_id'])) is None
        assert db.scalar(select(func.count()).select_from(RequestResult)) == 0


def test_inflight_duplicate_does_not_create_second_execution(client, world, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    h, state = world
    entered, proceed = Event(), Event()
    original = observations.fetch
    def blocked(*args, **kwargs):
        entered.set()
        assert proceed.wait(10)
        return original(*args, **kwargs)
    monkeypatch.setattr(observations, 'fetch', blocked)
    key = uuid.uuid4()
    data = dict(source='direct_input', character_name='a0')
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(change, client, h, 'post', VERIFY, data, key)
        try:
            assert entered.wait(5)
            duplicate = change(client, h, 'post', VERIFY, data, key)
            assert duplicate.status_code == 409 and duplicate.json()['error']['code'] == 'REQUEST_IN_PROGRESS'
            assert len(events()) == 1 and events()[0].state == 'running'
        finally:
            proceed.set()
        assert pending.result().status_code == 201
    assert len(events()) == 1 and events()[0].state == 'completed'


def test_invalid_request_and_idempotency_conflict_are_not_new_executions(client, world):
    h, state = world
    assert client.post(VERIFY, json=dict(source='direct_input', character_name='a0')).status_code == 401
    assert change(client, h, 'post', VERIFY, dict(source='direct_input')).status_code == 400
    assert events() == []
    key = uuid.uuid4()
    assert change(client, h, 'post', VERIFY, dict(source='direct_input', character_name='a0'), key).status_code == 201
    conflict = change(client, h, 'post', VERIFY, dict(source='direct_input', character_name='a1'), key)
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert len(events()) == 1
