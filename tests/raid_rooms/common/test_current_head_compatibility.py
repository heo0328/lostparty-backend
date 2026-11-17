"""Keep existing recruitment workflows in the default current-head regression set."""
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from app.core.database import session
from tests.raid_rooms.group_links.test_cycle_group_policy import (
    policy_db, group_beta, beta, current, candidate, ready, sources, imported, people, worlds,
    test_private_target_visibility_search_and_group_metadata as check_visibility,
    test_ended_membership_full_profiles_preserve_relation_only_and_cursor as check_memberships,
)
from tests.raid_rooms.reads.test_discovery import (
    test_profiles_group_labels_coordination_and_permission as check_search,
)
from tests.raid_rooms.admissions.test_reapplication_history import (
    reapplication_ready,
    test_reentry_http_candidates_context_join_and_historical_reader as check_reentry,
    test_mixed_completed_left_bundle_creates_all_fresh_assignments as check_completed_history,
)


def assert_current_head():
    """A passing historical fixture must not substitute for the deployed schema."""
    expected = ScriptDirectory.from_config(Config('alembic.ini')).get_current_head()
    with session() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == expected


def test_current_head_discovery_http(policy_db, client):
    assert_current_head()
    check_search(policy_db, client)


def test_current_head_group_scope_and_read_only(policy_db, client, monkeypatch):
    assert_current_head()
    check_visibility(policy_db, client, monkeypatch)


def test_current_head_memberships_http(policy_db):
    assert_current_head()
    check_memberships(policy_db, 'mixed')


def test_current_head_reentry_http_and_original_history(reapplication_ready):
    assert_current_head()
    check_reentry(reapplication_ready)


def test_current_head_mixed_completed_history(reapplication_ready):
    assert_current_head()
    check_completed_history(reapplication_ready)
