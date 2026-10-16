"""Run the real server collector/transport parser with fake HTTP, never game keys."""
import json
import uuid
from dataclasses import replace
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import observations, provider, service
from app.game_accounts.models import Account, Character, Audit, Verification, Registration, Configuration, VerificationExecution
from app.game_accounts.equipment import SLOTS
from tests.test_game_accounts import world, register, start, change, VERIFY, BASE
from tests.test_game_account_primitives import transport

LIVE_FETCH = observations.fetch


@pytest.fixture
def live(world, monkeypatch):
    h, _ = world
    state = dict(removed=(), malformed=None, profile_server='sample-server', changed=None, calls=[])
    monkeypatch.setattr(observations, 'fetch', LIVE_FETCH)
    def get(url, **kwargs):
        state['calls'].append('siblings' if url.endswith('/siblings') else 'armory')
        if url.endswith('/siblings'):
            body = [dict(ServerName='sample-server', CharacterName='a0', CharacterClassName='sample-class',
                         CharacterLevel=60, ItemAvgLevel='1700.00')]
        else:
            gear = [dict(Type=s, Name='sample-'+s, Grade='고대', Tooltip='variable') for s in SLOTS if s not in state['removed']]
            if state['changed']:
                next(item for item in gear if item['Type'] == state['changed'])['Name'] = 'changed-item'
            if state['malformed'] == 'null': gear = None
            if state['malformed'] == 'duplicate': gear.append(dict(gear[0]))
            if state['malformed'] == 'entry': gear.append(None)
            body = dict(ArmoryProfile=dict(CharacterName='a0', ServerName=state['profile_server']), ArmoryEquipment=gear)
        _, response = transport(body=json.dumps(body).encode())
        return response
    monkeypatch.setattr(provider.requests, 'get', get)
    return h, state


def confirm(client, h, v, key=None):
    return change(client, h, 'post', VERIFY+'/'+v['challenge_id']+'/confirm', {}, key)


def assert_no_ownership():
    with session() as db:
        for model in (Account, Character, Audit):
            assert db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize('registered', [True, False])
def test_real_collector_can_verify_new_roster_and_replay(client, live, registered):
    h, state = live
    r = register(client, h) if registered else None
    v = start(client, h, r['registration_id'] if r else None)
    with session() as db:
        challenge = db.get(Verification, uuid.UUID(v['challenge_id']))
        assert challenge.identity_snapshot['server_equipment_baseline']['method'] == 'server-equipment-removal-v1'
    state['removed'] = v['required_slots']
    key = uuid.uuid4()
    result = confirm(client, h, v, key)
    assert result.status_code == 200 and result.json()['status'] == 'verified'
    calls = len(state['calls'])
    assert confirm(client, h, v, key).json() == result.json()
    assert len(state['calls']) == calls
    with session() as db:
        account = db.scalar(select(Account))
        assert account.owner_id is not None
        assert db.scalar(select(func.count()).select_from(Character)) == 1
        assert db.scalar(select(func.count()).select_from(Audit)) == 1
        config = db.scalar(select(Configuration))
        assert config.state == 'unconfigured' and config.representative_id is None
        event = db.scalar(select(VerificationExecution).where(VerificationExecution.operation == 'confirm'))
        assert event.outcome_code == 'VERIFIED' and event.state == 'completed'
    listed = client.get(BASE, headers=h).json()['items']
    assert len(listed) == 1 and listed[0]['ownership_status'] == 'owned'


@pytest.mark.parametrize('malformed', ['null', 'duplicate', 'entry', 'profile'])
def test_bad_confirmation_http_never_issues_proof(client, live, malformed):
    h, state = live
    v = start(client, h)
    state['removed'] = v['required_slots']
    state['malformed'] = malformed
    if malformed == 'profile': state['profile_server'] = 'different-server'
    response = confirm(client, h, v)
    assert response.status_code == 503
    assert_no_ownership()
    with session() as db:
        assert db.get(Verification, uuid.UUID(v['challenge_id'])).status == 'pending'
        event = db.scalar(select(VerificationExecution).where(VerificationExecution.operation == 'confirm'))
        assert event.state == 'failed'


@pytest.mark.parametrize('kind', ['old_baseline', 'stale', 'future', 'changed_receipt', 'untyped'])
def test_missing_or_inconsistent_collection_evidence_stays_pending(client, live, monkeypatch, kind):
    h, state = live
    v = start(client, h)
    state['removed'] = v['required_slots']
    if kind == 'old_baseline':
        with session() as db, db.begin():
            challenge = db.get(Verification, uuid.UUID(v['challenge_id']))
            challenge.identity_snapshot = {k: value for k, value in challenge.identity_snapshot.items() if k != 'server_equipment_baseline'}
    original = observations.fetch
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        receipt = result.equipment_evidence
        if kind in ('stale', 'future'):
            at = result.fetched_at + timedelta(minutes=-11 if kind == 'stale' else 11)
            return replace(result, fetched_at=at, equipment_evidence=replace(receipt, fetched_at=at))
        if kind == 'changed_receipt':
            return replace(result, equipment_evidence=replace(receipt, equipment_digest='incorrect'))
        if kind == 'untyped':
            return replace(result, equipment_evidence={'valid': True}, proof_validated=True)
        return result
    monkeypatch.setattr(observations, 'fetch', changed)
    response = confirm(client, h, v)
    assert response.status_code == 200 and response.json()['result_code'] == 'PROVIDER_EVIDENCE_PENDING'
    assert_no_ownership()


@pytest.mark.parametrize('kind', ['required', 'other'])
def test_server_receipt_does_not_bypass_equipment_comparison(client, live, kind):
    h, state = live
    v = start(client, h)
    if kind == 'other':
        state['removed'] = v['required_slots']
        state['changed'] = next(s for s in SLOTS if s not in state['removed'])
    response = confirm(client, h, v)
    assert response.status_code == 200
    assert response.json()['result_code'] == ('REQUIRED_EQUIPMENT_PRESENT' if kind == 'required' else 'NON_REQUIRED_EQUIPMENT_CHANGED')
    assert_no_ownership()


def test_expiry_during_final_database_work_rolls_back_all_ownership(client, live, monkeypatch):
    h, state = live
    r = register(client, h)
    v = start(client, h, r['registration_id'])
    state['removed'] = v['required_slots']
    original_reconcile, original_now = service.reconcile, service.now
    clock = dict(expired=False)
    def delayed(*args, **kwargs):
        result = original_reconcile(*args, **kwargs)
        clock['expired'] = True
        return result
    monkeypatch.setattr(service, 'reconcile', delayed)
    monkeypatch.setattr(service, 'now', lambda db: original_now(db) + (timedelta(minutes=11) if clock['expired'] else timedelta()))
    response = confirm(client, h, v)
    assert response.status_code == 409 and response.json()['error']['code'] == 'VERIFICATION_EXPIRED'
    assert_no_ownership()
    with session() as db:
        assert db.get(Registration, uuid.UUID(r['registration_id'])).account_id is None
        challenge = db.get(Verification, uuid.UUID(v['challenge_id']))
        assert challenge.status == 'expired' and challenge.attempt_count == 1
        assert db.scalar(select(func.count()).select_from(Configuration)) == 0
        e = db.scalar(select(VerificationExecution).where(VerificationExecution.operation == 'confirm'))
        assert e.outcome_code == 'VERIFICATION_EXPIRED'


def test_claimed_roster_still_requires_separate_binding(client, live):
    h, state = live
    v = start(client, h)
    state['removed'] = v['required_slots']
    assert confirm(client, h, v).json()['status'] == 'verified'
    state['removed'] = ()
    response = change(client, h, 'post', VERIFY, dict(source='direct_input', character_name='a0'))
    assert response.status_code == 409 and response.json()['error']['code'] == 'ACCOUNT_BINDING_EVIDENCE_PENDING'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Account)) == 1
        assert db.scalar(select(func.count()).select_from(Audit)) == 1


def test_http_success_flags_are_not_accepted_as_evidence(client, live):
    h, state = live
    v = start(client, h)
    response = change(client, h, 'post', VERIFY+'/'+v['challenge_id']+'/confirm', dict(proof_validated=True))
    assert response.status_code == 400
    assert_no_ownership()


def test_late_confirmation_does_not_expire_already_verified_challenge(client, live, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock
    h, state = live
    v = start(client, h)
    state['removed'] = v['required_slots']
    entered, proceed, guard = Event(), Event(), Lock()
    first = dict(value=True)
    original_lookup, original_now = service.lookup, service.now
    def blocked(*args, **kwargs):
        observed = original_lookup(*args, **kwargs)
        with guard:
            wait = first['value']
            first['value'] = False
        if wait:
            entered.set()
            assert proceed.wait(10)
        return observed
    monkeypatch.setattr(service, 'lookup', blocked)
    with ThreadPoolExecutor(1) as pool:
        waiting = pool.submit(confirm, client, h, v)
        try:
            assert entered.wait(5)
            # Different explicit confirm commands still obey the 5 second quota.
            from app.game_accounts.models import LimitEvent
            from sqlalchemy import delete
            with session() as db, db.begin():
                db.execute(delete(LimitEvent).where(LimitEvent.scope == 'confirm:'+v['challenge_id']))
            winner = confirm(client, h, v)
            assert winner.status_code == 200 and winner.json()['status'] == 'verified'
            monkeypatch.setattr(service, 'now', lambda db: original_now(db) + timedelta(minutes=11))
        finally:
            proceed.set()
        result = waiting.result()
    assert result.status_code == 200 and result.json()['status'] == 'verified'
    with session() as db:
        assert db.get(Verification, uuid.UUID(v['challenge_id'])).status == 'verified'
        assert db.scalar(select(func.count()).select_from(Account)) == 1
        assert db.scalar(select(func.count()).select_from(Audit)) == 1
