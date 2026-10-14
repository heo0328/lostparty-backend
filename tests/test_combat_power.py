import pytest

from app.game_accounts.combat_power import default_collection_target, parse_profile_power
from app.game_accounts.provider import ProviderUnavailable


@pytest.mark.parametrize('level,expected', [
    ('1699.99', False), ('1700', True), ('1,700.00', True),
    ('1700.01', True), (None, False), ('0', False),
])
def test_default_collection_boundary(level, expected):
    assert default_collection_target(level) is expected


@pytest.mark.parametrize('value,expected', [
    ('12,345.67', '12345.67'), ('0', '0'), (None, None),
])
def test_profile_power_value_or_unavailable(value, expected):
    raw = {'ServerName': 'sample-server', 'CharacterName': 'sample', 'CombatPower': value}
    assert parse_profile_power(raw, 'sample-server', 'sample') == expected


def test_missing_power_is_not_zero():
    assert parse_profile_power({'ServerName': 'sample-server', 'CharacterName': 'sample'},
                               'sample-server', 'sample') is None


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '', 1700, True, 'x' * 65])
def test_invalid_values_fail_without_becoming_zero(value):
    with pytest.raises(ProviderUnavailable):
        default_collection_target(value)
    with pytest.raises(ProviderUnavailable):
        parse_profile_power({'ServerName': 'sample-server', 'CharacterName': 'sample',
                             'CombatPower': value}, 'sample-server', 'sample')


@pytest.mark.parametrize('raw', [None, [], {},
    {'ServerName': 'other', 'CharacterName': 'sample', 'CombatPower': '100'},
    {'ServerName': 'sample-server', 'CharacterName': 'other', 'CombatPower': '100'},
])
def test_profile_identity_must_match(raw):
    with pytest.raises(ProviderUnavailable, match='UPSTREAM_INVALID_RESPONSE'):
        parse_profile_power(raw, 'sample-server', 'sample')

# Reuse isolated PostgreSQL registration fixtures without Flutter sources.
from tests.test_game_accounts import world, register, change, BASE, page, verify
from app.core.database import session, now
from app.game_accounts.models import PowerCache, Character, Registration
from app.game_accounts import power_service
from datetime import timedelta
from sqlalchemy import select, func
import uuid


def endpoint(r):
    return BASE + '/' + r['registration_id'] + '/combat-power/refresh'


def body(*names):
    return {'characters': [{'server_name': 'sample-server', 'character_name': name} for name in names]}


def seed_provider(monkeypatch, value='1234.56'):
    calls = []
    def fetch(pair):
        calls.append(pair)
        return 'available', value, None
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    return calls


def test_power_unverified_cache_replay_and_summary_preserves(client, world, monkeypatch):
    h, _ = world
    r = register(client, h)
    calls = seed_provider(monkeypatch, '0')
    key = uuid.uuid4()
    response = change(client, h, 'post', endpoint(r), body('a0', 'a0', 'a1'), key)
    assert response.status_code == 200, response.text
    items = response.json()['items']
    assert len(items) == 2 and items[0]['combat_power'] == '0'
    assert all(v['status'] == 'updated' and not v['power_stale'] for v in items)
    assert change(client, h, 'post', endpoint(r), body('a0', 'a0', 'a1'), key).json() == response.json()
    cached = change(client, h, 'post', endpoint(r), body('a0'))
    assert cached.json()['items'][0]['status'] == 'cached'
    assert len(calls) == 2
    p = page(client, h, r['registration_id'])
    assert p['characters']['items'][0]['character_id'] is None
    assert p['characters']['items'][0]['power_status'] == 'available'
    initial = items[0]['power_fetched_at']
    assert change(client, h, 'post', BASE + '/' + r['registration_id'] + '/refresh', {}).status_code == 200
    p = page(client, h, r['registration_id'])['characters']['items'][0]
    assert p['combat_power'] == '0' and p['power_fetched_at'] == initial
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Character)) == 0


def test_power_partial_unavailable_failure_preserves_good_value(client, world, monkeypatch):
    h, _ = world; r = register(client, h)
    seed_provider(monkeypatch)
    assert change(client, h, 'post', endpoint(r), body('a0', 'a1')).status_code == 200
    with session() as db, db.begin():
        for c in db.scalars(select(PowerCache)):
            c.checked_at -= timedelta(hours=1)
    def fetch(pair):
        return ('unavailable', None, 'COMBAT_POWER_UNAVAILABLE') if pair[1] == 'a0' else ('failed', None, 'UPSTREAM_UNAVAILABLE')
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    response = change(client, h, 'post', endpoint(r), body('a0', 'a1', 'a2'))
    assert response.status_code == 200, response.text
    items = response.json()['items']
    assert items[0]['status'] == 'unavailable' and items[1]['status'] == 'failed'
    assert items[0]['combat_power'] == items[1]['combat_power'] == '1234.56'
    assert items[2]['combat_power'] is None
    assert all(i['power_stale'] for i in items)
    assert all(i['power_checked_at'] for i in items)
    assert page(client, h, r['registration_id'])['characters']['items'][1]['power_status'] == 'failed'


@pytest.mark.parametrize('bad', [body('a0', 'outside'), {'characters': []}, body(*(['a0'] * 21)),
    {'characters': [{'server_name': 'sample-server', 'character_name': 'a0', 'combat_power': '100'}]}])
def test_power_whole_input_scope_and_boundaries(client, world, monkeypatch, bad):
    h, _ = world; r = register(client, h)
    calls = seed_provider(monkeypatch)
    assert change(client, h, 'post', endpoint(r), bad).status_code == 400
    assert calls == []


def test_power_default_level_skips_without_external_call(client, world, monkeypatch):
    h, _ = world; r = register(client, h)
    with session() as db, db.begin():
        reg = db.get(Registration, uuid.UUID(r['registration_id']))
        rows = [dict(v) for v in reg.preview]
        rows[0]['item_level'], rows[1]['item_level'] = '1699.99', None
        reg.preview = rows
    calls = seed_provider(monkeypatch)
    response = change(client, h, 'post', endpoint(r), body('a0', 'a1', 'a2'))
    assert response.status_code == 200
    assert [i['status'] for i in response.json()['items']] == ['skipped', 'skipped', 'updated']
    assert len(calls) == 1
    assert response.json()['items'][1]['reason'] == 'ITEM_LEVEL_UNAVAILABLE'


def test_power_budget_deferred_does_not_late_write(client, world, monkeypatch):
    from threading import Event
    h, _ = world; r = register(client, h)
    entered, finish = Event(), Event()
    def fetch(pair):
        entered.set(); finish.wait(5)
        return 'available', '999', None
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    monkeypatch.setattr(power_service, 'BUDGET_SECONDS', 1.1)
    response = change(client, h, 'post', endpoint(r), body('a0', 'a1', 'a2'))
    finish.set()
    assert response.status_code == 200, response.text
    assert all(i['status'] == 'deferred' for i in response.json()['items'])
    with session() as db:
        assert all(c.value is None for c in db.scalars(select(PowerCache)))


def test_power_revision_changed_during_network_rolls_back(client, world, monkeypatch):
    h, _ = world; r = register(client, h)
    def fetch(pair):
        with session() as db, db.begin():
            reg = db.get(Registration, uuid.UUID(r['registration_id']))
            reg.version += 1
        return 'available', '999', None
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    response = change(client, h, 'post', endpoint(r), body('a0'))
    assert response.status_code == 409 and response.json()['error']['code'] == 'REVISION_CONFLICT'
    with session() as db:
        assert all(c.value is None for c in db.scalars(select(PowerCache)))


def test_power_quota_exhaustion_deferred_no_call(client, world, monkeypatch):
    from app.game_accounts.support import GameError
    h, _ = world; r = register(client, h)
    calls = seed_provider(monkeypatch)
    def quota(*args): raise GameError('RATE_LIMITED', 429, 2)
    monkeypatch.setattr(power_service, 'quota', quota)
    response = change(client, h, 'post', endpoint(r), body('a0', 'a1'))
    assert response.status_code == 200
    assert all(i['reason'] == 'RATE_LIMITED' for i in response.json()['items'])
    assert not calls


def test_power_owned_get_and_representative_overlay(client, world, monkeypatch):
    from tests.test_game_accounts import save_data
    h, state = world; r = register(client, h)
    verify(client, h, state, r['registration_id'])
    p = page(client, h, r['registration_id'])
    assert change(client, h, 'put', BASE + '/' + r['registration_id'] + '/character-settings', save_data(p)).status_code == 200
    seed_provider(monkeypatch, '777')
    assert change(client, h, 'post', endpoint(r), body('a0', 'a1', 'a2')).status_code == 200
    assert all(i['combat_power'] == '777' and i['character_id'] for i in page(client, h, r['registration_id'])['characters']['items'])
    assert client.get(BASE, headers=h).json()['items'][0]['representative_summary']['combat_power'] == '777'


def test_power_twenty_targets_and_membership_session_isolation(client, world, monkeypatch, login):
    from tests.test_game_accounts import PrivateHeaders
    from app.auth import service as auth_service
    h, state = world; state['count'] = 20
    r = register(client, h); calls = seed_provider(monkeypatch)
    assert change(client, h, 'post', endpoint(r), body(*[f'a{i}' for i in range(20)])).status_code == 200
    assert len(calls) == 20
    assert client.post(endpoint(r), json=body('a0')).status_code == 401
    monkeypatch.setattr(auth_service, 'verify_google', lambda token, nonce: 'other-member')
    auth, _ = login()
    other = PrivateHeaders(Authorization='Bearer ' + auth['access_token'])
    assert change(client, other, 'post', endpoint(r), body('a0')).status_code == 404
    # Another member's own preview does not inherit the first member's cache.
    other_r = register(client, other)
    assert page(client, other, other_r['registration_id'])['characters']['items'][0]['combat_power'] is None


@pytest.mark.parametrize('change_kind', ['delete', 'logout', 'lease'])
def test_power_rechecks_deleted_session_and_fencing(client, world, monkeypatch, change_kind):
    from app.auth.models import Session
    h, _ = world; r = register(client, h)
    def fetch(pair):
        with session() as db, db.begin():
            if change_kind == 'delete':
                reg = db.get(Registration, uuid.UUID(r['registration_id']))
                reg.deleted_at = now(db)
            elif change_kind == 'logout':
                s = db.scalar(select(Session)); s.revoked_at = now(db)
            else:
                c = db.scalar(select(PowerCache)); c.generation += 1
        return 'available', '999', None
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    response = change(client, h, 'post', endpoint(r), body('a0'))
    assert response.status_code == {'delete': 404, 'logout': 401, 'lease': 409}[change_kind], response.text
    if change_kind == 'lease':
        assert response.headers['Retry-After'] == '2'
    with session() as db:
        assert all(c.value is None for c in db.scalars(select(PowerCache)))


def test_power_overlap_merges_without_duplicate_profile_call(client, world, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    h, _ = world; r = register(client, h)
    entered, finish = Event(), Event()
    calls = []
    def fetch(pair):
        calls.append(pair); entered.set(); finish.wait(5)
        return 'available', '123', None
    monkeypatch.setattr(power_service, 'fetch_power', fetch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(change, client, h, 'post', endpoint(r), body('a0'))
        assert entered.wait(3)
        second = change(client, h, 'post', endpoint(r), body('a0'))
        finish.set()
        assert first.result().status_code == 200
    assert second.status_code == 200 and second.json()['items'][0]['reason'] == 'FETCH_IN_PROGRESS'
    assert len(calls) == 1


def test_power_profile_only_transport_and_safe_failure(monkeypatch):
    from tests.test_game_account_primitives import transport
    from app.game_accounts.provider import LostArkProvider
    wire, _ = transport(body=b'{"ServerName":"sample-server","CharacterName":"sample","CombatPower":"0"}')
    assert LostArkProvider('test-only', wire).profile('sample')['CombatPower'] == '0'
    assert wire.get.call_args.args[0].endswith('/armories/characters/sample/profiles')
    class Broken:
        def __init__(self, token): pass
        def profile(self, name): raise RuntimeError('private credential/profile')
    monkeypatch.setattr(power_service, 'LostArkProvider', Broken)
    assert power_service.fetch_power(('sample-server', 'sample')) == ('failed', None, 'UPSTREAM_UNAVAILABLE')



def test_power_retention_keeps_good_and_active_claims(client, world, monkeypatch):
    from app.game_accounts.cleanup import clean
    h, _ = world; r = register(client, h)
    seed_provider(monkeypatch)
    assert change(client, h, 'post', endpoint(r), body('a0', 'a1')).status_code == 200
    with session() as db, db.begin():
        stale = db.scalar(select(PowerCache).where(PowerCache.character_name == 'a0'))
        stale.checked_at = now(db) - timedelta(days=91)
    clean()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(PowerCache)) == 1
        assert db.scalar(select(PowerCache)).character_name == 'a1'
