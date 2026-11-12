"""Reuse common HTTP regression scenarios on the current app and DB0036.

Provider observations/Google verification are fabricated by the original fixtures.
The original DB0023 scenarios remain in their existing modules unchanged.
"""
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
    test_ownership_first_seed_no_cooldown_atomicity,
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
