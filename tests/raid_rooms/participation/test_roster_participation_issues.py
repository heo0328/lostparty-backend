"""#17 observation/seat boundaries under disposable restricted PostgreSQL."""
import os
import subprocess
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import select, inspect, func
from app.core.database import session, now
from app.game_accounts.rosters import service
from app.game_accounts import roster_presence
from app.game_accounts.models import Character, Account, NameClaim, Registration
from app.game_accounts.support import GameError, lock
from app.raid_rooms.participation import character_issues
from app.raid_rooms.common import cycle_worker
from app.raid_rooms.reads import cycle_member_reads
from app.raid_rooms.participation import cycle_lifecycle as life
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from tests.raid_rooms.group_links.test_cycle_group_policy import policy_db, group_beta, beta, current, candidate, ready, sources, imported, people, worlds
from tests.raid_rooms.admissions.test_beta_recruitment import create_beta, beta_join
from tests.groups.test_group_foundation import actor
from tests.raid_rooms.common.test_raid_room_migrations import table_digests


@pytest.fixture
def presence_db(policy_db):
    engine, a, b = policy_db
    tables = set(inspect(engine).get_table_names()) - {'alembic_version'}
    before = table_digests(engine, tables)
    result = subprocess.run(['alembic', 'upgrade', '0036_roster_presence'],
        env={**os.environ, 'DATABASE_URL': engine.url.render_as_string(hide_password=False)},
        capture_output=True, timeout=90)
    assert result.returncode == 0, 'isolated roster-presence migration failed'
    assert table_digests(engine, tables) == before
    from app.raid_rooms.common.readiness import require_two_cycle_active
    with session() as db:
        require_two_cycle_active(db)
    return engine, a, b


def observe(w, *, absent=True, rollback=False):
    with session() as db, db.begin():
        lock(db, 'game-mutations-v1')
        target = db.get(Character, uuid.UUID(w['ids'][0]))
        account = db.get(Account, target.account_id)
        characters = list(db.scalars(select(Character).where(Character.account_id == account.id)))
        rows = [dict(c.summary, server_name=c.server_name, character_name=c.character_name)
                for c in characters if not absent or c.id != target.id]
        result = service.reconcile(db, account, SimpleNamespace(roster=rows, fetched_at=now(db)), owned=True)
        if rollback:
            raise RuntimeError('synthetic transaction failure')
        return result


def qualified(rid, key, w):
    with session() as db:
        row = db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid,
            RoomCycle.cycle_key == date.fromisoformat(key)))
        return life.qualify(db, db.get(Room, rid), row, life.actual_member(db, row, w['uid']))


def joined(a, b):
    rid, c, *_ = create_beta(a, combined=True)
    n = (date.fromisoformat(c) + timedelta(days=7)).isoformat()
    beta_join(b, rid, c); beta_join(b, rid, n)
    return rid, c, n


@pytest.mark.parametrize('who', ['leader', 'member'])
def test_missing_and_reappearance_preserve_seat_authority_and_worker(presence_db, who):
    engine, a, b = presence_db
    rid, c, n = joined(a, b)
    subject = a if who == 'leader' else b
    observe(subject)
    before = table_digests(engine, set(inspect(engine).get_table_names()) - {'alembic_version'})
    for key in (c, n):
        qualified(rid, key, subject)
        value = cycle_member_reads.detail(actor(a['uid']), rid, key)
        assert all(m['status'] == 'valid' for m in value['data']['members'])
    cycle_worker.process_room(rid)
    assert table_digests(engine, set(before)) == before
    summary = character_issues.summary(actor(subject['uid']))
    assert summary['has_issues'] and summary['affected_room_count'] == 1 and summary['affected_target_count'] == 2
    old_revision = summary['issues_revision']
    observe(subject, absent=False)
    for key in (c, n): qualified(rid, key, subject)
    summary = character_issues.summary(actor(subject['uid']))
    assert not summary['has_issues'] and summary['issues_revision'] != old_revision
    observe(subject)
    for key in (c, n): qualified(rid, key, subject)


@pytest.mark.parametrize('kind', ['claim', 'owner', 'ownership_revision', 'unproven_revision', 'retired', 'registration'])
def test_roster_exception_cannot_bypass_other_guards(presence_db, kind):
    _, a, b = presence_db
    rid, c, _ = joined(a, b)
    observe(b)
    with session() as db, db.begin():
        char = db.get(Character, uuid.UUID(b['ids'][0])); account = db.get(Account, char.account_id)
        if kind == 'claim': db.delete(db.get(NameClaim, (char.server_name, char.character_name)))
        elif kind == 'owner': account.owner_id = a['uid']
        elif kind == 'ownership_revision': account.ownership_revision += 1
        elif kind == 'unproven_revision': char.lifecycle_revision += 1
        elif kind == 'retired': char.lifecycle_state = 'retired'
        elif kind == 'registration': db.get(Registration, b['rid']).deleted_at = now(db)
    with pytest.raises(GameError): qualified(rid, c, b)


def test_warnings_are_target_private_and_reads_have_no_writes(presence_db, people):
    engine, a, b = presence_db
    outsider = people('roster-warning-outsider')
    rid, c, _ = joined(a, b)
    observe(b)
    before = table_digests(engine, set(inspect(engine).get_table_names()) - {'alembic_version'})
    with session() as db:
        stamp = now(db)
        assert character_issues.for_target(db, outsider['uid'], rid, c, stamp) == []
        other = character_issues.for_target(db, a['uid'], rid, c, stamp)
        own = character_issues.for_target(db, b['uid'], rid, c, stamp)
        assert len(other) == len(own) == 1
        assert other[0]['registration_id'] is None
        assert own[0]['registration_id'] == uuid.UUID(str(b['rid']))
    assert not character_issues.summary(actor(a['uid']))['has_issues']
    assert not character_issues.summary(actor(outsider['uid']))['has_issues']
    assert table_digests(engine, set(before)) == before


def test_observation_rollback_and_repetition_do_not_forge_proof(presence_db):
    _, a, b = presence_db
    with pytest.raises(RuntimeError): observe(b, rollback=True)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(roster_presence.RosterTransition)) == 0
    observe(b); observe(b)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(roster_presence.RosterTransition).where(
            roster_presence.RosterTransition.state=='missing')) == 1
        before=db.scalar(select(func.count()).select_from(roster_presence.RosterTransition))
    observe(b)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(roster_presence.RosterTransition)) == before


def test_unknown_legacy_suspect_never_becomes_retained_authority(presence_db):
    _, a, b = presence_db
    rid, c, _ = joined(a, b)
    with session() as db, db.begin():
        char = db.get(Character, uuid.UUID(b['ids'][0]))
        char.lifecycle_state = char.status = 'suspect'; char.lifecycle_revision += 1
    observe(b)
    assert character_issues.summary(actor(b['uid']))['has_issues']
    with pytest.raises(GameError): qualified(rid, c, b)


@pytest.mark.parametrize('cause', ['roster', 'unknown', 'changed_assignment', 'foreign_generation', 'review_member'])
def test_only_proven_review_cause_can_recover(presence_db, cause):
    from fastapi.encoders import jsonable_encoder
    from app.raid_rooms.participation import roster_recovery
    from app.raid_rooms.cycle_models import CycleGeneration, LegacyCycleEvidence
    _, a, b = presence_db
    rid, c, _ = joined(a, b)
    observe(b)
    with session() as db, db.begin():
        row = db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid,
            RoomCycle.cycle_key == date.fromisoformat(c)))
        cm = life.actual_member(db, row, b['uid']); assignment = life.assignments(db, row, cm)[0]
        row.state = db.get(CycleGeneration, (row.id, row.generation)).state = 'review_required'
        saved = dict(cycle_member_id=cm.id, revision=cm.revision, assignment=life.assignment_snapshot(assignment))
        if cause == 'changed_assignment': saved['assignment']['revision'] += 1
        if cause == 'foreign_generation': saved['cycle_member_id'] = uuid.uuid4()
        if cause == 'review_member': cm.state = 'review_required'
        db.add(LegacyCycleEvidence(source_kind='assignment', source_id=assignment.id,
            room_id=rid, cycle_id=row.id, reason='CHARACTER_UNUSABLE' if cause != 'unknown' else 'UNKNOWN_SOURCE',
            evidence=jsonable_encoder(saved)))
        account_id = db.get(Character, assignment.character_id).account_id
        db.flush()
        expected = [row.id] if cause == 'roster' else []
        assert roster_recovery.recover(db, account_id, now(db)) == expected
        assert row.state == ('open' if cause == 'roster' else 'review_required')
        assert db.get(LegacyCycleEvidence, ('assignment', assignment.id)) is not None


def test_full_manual_replacement_clears_only_the_target(presence_db):
    from app.raid_rooms.participation import cycle_character
    from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import change_body
    _, a, b = presence_db
    rid, c, n = joined(a, b)
    observe(b)
    ctx = cycle_character.get(actor(b['uid']), rid, c, uuid.UUID(b['ids'][1]), 'dealer')
    plan = cycle_member_reads.plan(actor(b['uid']), rid, c)
    assert ctx['data']['permissions']['change_character']['allowed']
    assert cycle_character.execute(actor(b['uid']), rid, uuid.uuid4(), change_body(ctx, plan))[0] == 200
    assert character_issues.summary(actor(b['uid']))['affected_target_count'] == 1
    qualified(rid, c, b); qualified(rid, n, b)


def test_completion_and_departure_clear_only_unfinished_warnings(presence_db):
    from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import complete
    from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import cancel_member
    _, a, b = presence_db
    rid, c, n = joined(a, b)
    observe(a); observe(b)
    assert complete(a, rid, c, kind='complete_item')[0] == 200
    assert character_issues.summary(actor(b['uid']))['affected_target_count'] == 1
    assert cancel_member(b, rid, n)[0] == 200
    assert not character_issues.summary(actor(b['uid']))['has_issues']


def test_missing_participants_keep_schedule_and_leader_actions(presence_db):
    from app.raid_rooms.participation import cycle_management, cycle_leadership
    from app.raid_rooms.schedules import beta_schedule
    from tests.raid_rooms.schedules.test_recruitment_cycle_times import confirm, save_personal, submit
    _, a, b = presence_db
    rid, c, n = joined(a, b)
    # A confirmation command requires an actually confirmed schedule. Advance
    # only this synthetic reconciliation clock, not the host/service clock.
    with session() as db, db.begin():
        row = db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid,
            RoomCycle.cycle_key == date.fromisoformat(c)))
        saved = beta_schedule.get(db, row)
        beta_schedule.reconcile(db, db.get(Room, rid), row, saved.base_starts_at - timedelta(minutes=20))
    observe(a); observe(b)
    assert cycle_management.get(actor(a['uid']), rid, c)
    assert cycle_leadership.get_transfer(actor(a['uid']), rid, n)['data']['permission']['allowed']
    save_personal(b)
    assert submit(b, rid, c)[0] == 200
    assert confirm(b, rid, c)[0] == 200


def test_new_selection_stays_blocked_and_observation_history_is_immutable(presence_db):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from app.raid_rooms.admissions.admission_context import selection
    _, a, b = presence_db
    observe(b)
    with session() as db, pytest.raises(GameError) as caught:
        selection(db, b['uid'], uuid.UUID(b['ids'][0]), 'dealer')
    assert caught.value.code == 'CHARACTER_UNUSABLE'
    with pytest.raises(DBAPIError), session() as db, db.begin():
        db.execute(text("UPDATE character_roster_transitions SET source_usable=false"))
