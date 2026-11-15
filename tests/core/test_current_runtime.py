"""Reuse common HTTP regression scenarios on the current app and DB0036.

Provider observations/Google verification are fabricated by the original fixtures.
The original DB0023 scenarios remain in their existing modules unchanged.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.core import database
from app.main import create_app
from tests.raid_rooms.common.test_raid_room_migrations import isolated_app_database
from tests.game_accounts.test_game_accounts import world
from tests.game_accounts.test_representative import selection
from tests.game_accounts.test_role_summaries import owned
from tests.member_settings.test_member_settings import member
from tests.raid_weekly.test_raid_weekly import weekly_clock
from tests.auth.test_auth import (
    test_login_and_no_guest,
    test_refresh_recovery_and_limits,
    test_actor_extra_and_access_forgery,
)
from tests.member_settings.test_member_settings import (
    test_explicit_value_changes_noop_and_original_replay,
    test_other_member_isolated_even_same_command_key,
)
from tests.game_accounts.test_game_accounts import (
    test_registration_duplicate_main_delete_replay,
    register, verify, page, change, save_data, BASE, VERIFY,
)
from tests.game_accounts.test_account_bootstrap import test_empty_strict_auth_and_no_implicit_rows
from tests.groups.test_groups_http import (
    test_http_create_public_private_members_lists_replay_no_provider,
    test_private_authorization_and_revoked_replay,
)
from tests.raid_weekly.test_raid_weekly import (
    test_manual_completion_correction_noop_difficulty_and_historical_ack,
    test_batch_all_or_nothing_other_actor_and_session_authority,
)
from tests.raids.test_raid_catalog import test_public_reads_need_no_session_key_database_or_provider


@pytest.fixture
def client(monkeypatch):
    with isolated_app_database() as (target, role, upgrade):
        upgrade('0036_roster_presence')
        monkeypatch.setattr(database, 'engine', lambda: target)
        with TestClient(create_app(), raise_server_exceptions=False) as http:
            yield http


@pytest.mark.parametrize('main', [False, True], ids=['subordinate', 'main'])
def test_ownership_first_seed_no_cooldown_atomicity(client, world, main):
    """Current policy: no subordinate representative; main selection is explicit.

    Keep the original legacy scenario untouched in test_game_accounts.py.
    """
    headers, state = world
    registration = register(client, headers, main=main)
    rid = registration['registration_id']
    path = BASE + '/' + rid + '/character-settings'
    initial = page(client, headers, rid)
    assert all(row['character_id'] is None for row in initial['characters']['items'])
    verify(client, headers, state, rid)
    before = page(client, headers, rid)
    assert before['settings']['configuration_state'] == 'unconfigured'

    if not main:
        # New nonnull subordinate representative must fail without seeding data.
        forbidden = change(client, headers, 'put', path, save_data(before))
        assert forbidden.status_code == 409
        assert forbidden.json()['error']['code'] == 'MAIN_REGISTRATION_CHANGED'
        assert page(client, headers, rid)['settings'] == before['settings']

    first_body = save_data(before) | {'representative_character_id': None}
    first_key = uuid.uuid4()
    first = change(client, headers, 'put', path, first_body, first_key)
    assert first.status_code == 200, first.text
    first_value = first.json()
    assert first_value['next_change_at'] is None
    assert first_value['configuration_state'] == 'configured'
    assert first_value['settings_version'] == before['settings']['settings_version'] + 1
    current = page(client, headers, rid)
    ids = current['settings']['activity_character_ids']
    original = current['settings']['representative_character_id'] if main else ids[0]
    assert (current['settings']['representative_character_id'] is not None) == main
    replacement = next(cid for cid in ids if cid != original)

    # Consecutive valid writes have no cooldown, with branch-specific semantics.
    second_body = save_data(current, ids, replacement) | {
        'representative_character_id': replacement if main else None}
    second = change(client, headers, 'put', path, second_body)
    assert second.status_code == 200, second.text
    assert second.json()['next_change_at'] is None
    assert second.json()['representative_character_id'] == (replacement if main else None)
    current = page(client, headers, rid)
    if main:
        # Removing a valid representative remains forbidden atomically.
        rejected = change(client, headers, 'put', path, save_data(current, [original], original))
        assert rejected.status_code == 400
        assert rejected.json()['error']['code'] == 'REPRESENTATIVE_REQUIRED'
        assert page(client, headers, rid)['settings'] == current['settings']
        # First choose another active representative, then remove other activity.
        selected = change(client, headers, 'put', path, save_data(current, ids, original))
        assert selected.status_code == 200, selected.text
        assert selected.json()['next_change_at'] is None
        current = page(client, headers, rid)

    reduced = save_data(current, [original], original) | {
        'representative_character_id': original if main else None}
    result = change(client, headers, 'put', path, reduced)
    assert result.status_code == 200, result.text
    assert result.json()['next_change_at'] is None
    current = page(client, headers, rid)
    assert current['settings']['activity_character_ids'] == [original]

    # An invalid mixed selection or stale write cannot partially change settings.
    invalid = save_data(current, [original, str(uuid.uuid4())], original) | {
        'representative_character_id': original if main else None}
    assert change(client, headers, 'put', path, invalid).status_code == 404
    assert page(client, headers, rid)['settings'] == current['settings']
    stale = change(client, headers, 'put', path, first_body)
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'REVISION_CONFLICT'
    replay = change(client, headers, 'put', path, first_body, first_key)
    assert replay.status_code == 200 and replay.json() == first_value
    assert page(client, headers, rid)['settings'] == current['settings']

    blocked = change(client, headers, 'post', VERIFY,
                     dict(source='registration', registration_id=rid))
    assert blocked.status_code == 409 and blocked.json()['error']['code'] == 'ALREADY_VERIFIED'
    after = page(client, headers, rid)
    assert after['settings'] == current['settings']
    assert after['roster_revision'] == current['roster_revision']
    assert after['ownership_status'] == current['ownership_status']
