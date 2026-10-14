import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.auth.models import Session, User
from app.member_settings.models import MemberSettings
from app.member_settings import service
from app.game_accounts.support import GameError
from tests.test_game_accounts import PrivateHeaders

URL = '/v1/me/settings'


@pytest.fixture
def member(login):
    auth, _ = login()
    return PrivateHeaders(Authorization='Bearer ' + auth['access_token'])


def put(client, headers, value=True, version=1, key=None, body=None):
    return client.put(URL, headers={**headers, 'Idempotency-Key': str(key or uuid.uuid4())},
                      json=body if body is not None else {
                          'nice_group_auto_refresh_enabled': value, 'expected_version': version})


def test_default_is_read_only_and_has_no_provider_calls(client, member, monkeypatch):
    from app.game_accounts.provider import LostArkProvider
    def forbidden(*args): raise AssertionError('External call forbidden for settings')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    r = client.get(URL, headers=member)
    assert r.status_code == 200 and r.json() == {'nice_group_auto_refresh_enabled': False, 'version': 1}
    assert r.headers['Cache-Control'] == 'no-store'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(MemberSettings)) == 0
    assert put(client, member).status_code == 200


def test_explicit_value_changes_noop_and_original_replay(client, member):
    key = uuid.uuid4()
    a = put(client, member, True, 1, key)
    assert a.status_code == 200 and a.json()['version'] == 2
    assert put(client, member, True, 2).json() == a.json()
    b = put(client, member, False, 2)
    assert b.status_code == 200 and b.json()['version'] == 3
    # Replay stays historical and must not overwrite the latest preference.
    assert put(client, member, True, 1, key).json() == a.json()
    assert client.get(URL, headers=member).json() == b.json()
    conflict = put(client, member, False, 1, key)
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    stale = put(client, member, False, 2)
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'REVISION_CONFLICT'


def test_same_member_new_session_and_logout_preserve_preference(client, member, login):
    assert put(client, member).status_code == 200
    with session() as db, db.begin():
        for s in db.scalars(select(Session)):
            s.revoked_at = now(db)
    assert client.get(URL, headers=member).status_code == 401
    auth, _ = login()
    other_device = PrivateHeaders(Authorization='Bearer ' + auth['access_token'])
    assert client.get(URL, headers=other_device).json() == {'nice_group_auto_refresh_enabled': True, 'version': 2}
    assert put(client, other_device, False, 2).status_code == 200
    auth2, _ = login()
    assert client.get(URL, headers={'Authorization': 'Bearer ' + auth2['access_token']}).json()['nice_group_auto_refresh_enabled'] is False


def test_other_member_isolated_even_same_command_key(client, member, login, monkeypatch):
    from app.auth import service as auth_service
    key = uuid.uuid4()
    assert put(client, member, True, 1, key).status_code == 200
    monkeypatch.setattr(auth_service, 'verify_google', lambda *args: 'second-member')
    auth, _ = login()
    second = PrivateHeaders(Authorization='Bearer ' + auth['access_token'])
    assert client.get(URL, headers=second).json()['nice_group_auto_refresh_enabled'] is False
    assert put(client, second, False, 1, key).json()['version'] == 1
    assert client.get(URL, headers=member).json()['nice_group_auto_refresh_enabled'] is True


@pytest.mark.parametrize('body', [
    {}, {'nice_group_auto_refresh_enabled': True}, {'expected_version': 1},
    {'nice_group_auto_refresh_enabled': None, 'expected_version': 1},
    {'nice_group_auto_refresh_enabled': 1, 'expected_version': 1},
    {'nice_group_auto_refresh_enabled': 'true', 'expected_version': 1},
    {'nice_group_auto_refresh_enabled': True, 'expected_version': True},
    {'nice_group_auto_refresh_enabled': True, 'expected_version': 0},
    {'nice_group_auto_refresh_enabled': True, 'expected_version': '1'},
    {'nice_group_auto_refresh_enabled': True, 'expected_version': 1, 'user_id': str(uuid.uuid4())},
])
def test_strict_requests_never_write_defaults(client, member, body):
    assert put(client, member, body=body).status_code == 400
    assert client.get(URL, headers=member).json()['nice_group_auto_refresh_enabled'] is False
    with session() as db:
        assert db.scalar(select(func.count()).select_from(MemberSettings)) == 0


def test_query_key_and_unauthenticated_rejected(client, member):
    assert client.get(URL).status_code == 401
    assert put(client, {}).status_code == 401
    assert client.get(URL + '?user_id=other', headers=member).status_code == 400
    assert client.put(URL, headers=member, json={'nice_group_auto_refresh_enabled': True, 'expected_version': 1}).status_code == 400
    assert put(client, member, key=uuid.uuid1()).status_code == 400


@pytest.mark.parametrize('state,expected', [('expired', 401), ('revoked', 401), ('disabled', 403)])
def test_invalid_session_cannot_read_write_or_replay(client, member, state, expected):
    key = uuid.uuid4(); assert put(client, member, key=key).status_code == 200
    with session() as db, db.begin():
        s = db.scalar(select(Session))
        if state == 'expired': s.idle_expires_at = now(db) - timedelta(seconds=1)
        elif state == 'revoked': s.revoked_at = now(db)
        else: db.scalar(select(User)).status = 'disabled'
    assert client.get(URL, headers=member).status_code == expected
    assert put(client, member, key=key).status_code == expected
    with session() as db:
        assert db.scalar(select(MemberSettings)).nice_group_auto_refresh_enabled is True


def test_concurrent_devices_stale_version_has_one_winner(client, member):
    # Start from true/version2 so both commands really change the value.
    assert put(client, member).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: put(client, member, False, 2), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert client.get(URL, headers=member).json() == {'nice_group_auto_refresh_enabled': False, 'version': 3}


def test_fencing_failure_rolls_back_preference_and_preserves_retry(client, member, monkeypatch):
    original = service.commit_result
    def expired(*args): raise GameError('REQUEST_IN_PROGRESS', 409, 2)
    monkeypatch.setattr(service, 'commit_result', expired)
    key = uuid.uuid4()
    response = put(client, member, key=key)
    assert response.status_code == 409 and response.headers['Retry-After'] == '2'
    assert client.get(URL, headers=member).json()['nice_group_auto_refresh_enabled'] is False
    monkeypatch.setattr(service, 'commit_result', original)
    assert put(client, member, key=key).status_code == 200
