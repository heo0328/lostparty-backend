"""Registration masking progress on disposable PostgreSQL, at both schema baselines."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from itertools import product
from threading import Event, Lock
from time import monotonic

import pytest
from sqlalchemy import event, inspect, select, text

from app.auth.models import User
from app.core import database
from app.core.database import session, now
from app.game_accounts import cleanup
from app.game_accounts.models import (
    Account, Activity, Audit, Character, Configuration, Registration,
    VerificationExecution,
)
from tests.test_raid_room_migrations import isolated_app_database, table_digests

MASK = {'preview': [], 'lookup_name': '[deleted]', 'label': '[deleted]'}


@pytest.fixture(params=['0023_recruitment_resume', '0034_group_features'])
def cleanup_db(request, monkeypatch):
    with isolated_app_database() as (engine, _, upgrade):
        upgrade(request.param)
        def set_timeouts(connection, record):
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '10s'")
                cursor.execute("SET lock_timeout = '5s'")
            connection.commit()
        event.listen(engine, 'connect', set_timeouts)
        monkeypatch.setattr(database, 'engine', lambda: engine)
        with session() as db, db.begin():
            stamp = now(db)
            uid, aid, cid, sid = (uuid.uuid4() for _ in range(4))
            db.add(User(id=uid, status='active', created_at=stamp,
                        updated_at=stamp, last_login_at=stamp))
            db.flush()
            db.add(Account(id=aid, owner_id=uid, verified_at=stamp))
            db.flush()
            db.add(Character(id=cid, account_id=aid, server_name='synthetic-server',
                             character_name='synthetic-character', summary={'level': 60},
                             fetched_at=stamp, confirmed_at=stamp))
            db.flush()
            db.add(Configuration(id=sid, user_id=uid, account_id=aid,
                                 representative_id=cid, state='configured'))
            db.flush()
            db.add(Activity(settings_id=sid, character_id=cid, account_id=aid))
            db.add(Audit(account_id=aid, new_owner=uid, revision=1, created_at=stamp))
            db.add(VerificationExecution(command_id=uuid.uuid4(), generation=1,
                actor_id=uid, operation='start', requested_target=aid,
                target_snapshot={'account_id': str(aid)}, started_at=stamp,
                finished_at=stamp, state='completed', http_status=200,
                outcome_code='VERIFIED'))
        monkeypatch.setattr(cleanup, 'now', lambda db: stamp)
        yield engine, stamp, uid, aid


def seed(context, count, *, offset=1, age=timedelta(days=2), masked=False):
    _, stamp, uid, aid = context
    ids = [uuid.UUID(int=offset+i) for i in range(count)]
    with session() as db, db.begin():
        # Reverse insertion order so heap order cannot satisfy the expected order.
        for rid in reversed(ids):
            db.add(Registration(id=rid, user_id=uid, account_id=aid,
                preview=[] if masked else [{'synthetic': True}],
                lookup_name='[deleted]' if masked else 'synthetic-character',
                label='[deleted]' if masked else 'synthetic-label', version=3,
                fetched_at=stamp-timedelta(days=3), created_at=stamp-timedelta(days=3),
                updated_at=stamp-timedelta(days=2),
                deleted_at=None if age is None else stamp-age))
    return ids


def rows():
    with session() as db:
        return {row['id']: dict(row) for row in db.execute(
            select(Registration.__table__)).mappings()}


def masked_ids():
    return {rid for rid, row in rows().items() if all(row[k] == v for k, v in MASK.items())}


def unrelated(context):
    engine = context[0]
    tables = set(inspect(engine).get_table_names()) - {'game_account_registrations'}
    return table_digests(engine, tables)


def assert_preserved(before, after):
    assert before.keys() == after.keys()
    for rid, original in before.items():
        # The existing DB trigger records real writes; domain timestamps stay intact.
        assert {k: v for k, v in after[rid].items() if k not in {*MASK, 'record_updated_at'}} == {
            k: v for k, v in original.items() if k not in {*MASK, 'record_updated_at'}}


def test_progress_order_preservation_and_completed_rerun(cleanup_db):
    completed = set(seed(cleanup_db, 200, offset=1, age=timedelta(days=4), masked=True))
    newer = seed(cleanup_db, 250, offset=201, age=timedelta(days=2))
    older = seed(cleanup_db, 200, offset=451, age=timedelta(days=3))
    before, other = rows(), unrelated(cleanup_db)
    for expected in (completed | set(older), completed | set(older+newer[:200]),
                     completed | set(older+newer)):
        cleanup.clean()
        assert masked_ids() == expected
    after = rows()
    assert_preserved(before, after)
    assert {rid: after[rid] for rid in completed} == {rid: before[rid] for rid in completed}
    assert unrelated(cleanup_db) == other
    cleanup.clean()
    assert rows() == after
    assert unrelated(cleanup_db) == other


def test_partial_masks_json_null_and_time_boundaries(cleanup_db):
    ids = seed(cleanup_db, 8)
    with session() as db, db.begin():
        for rid, flags in zip(ids, product((False, True), repeat=3)):
            row = db.get(Registration, rid)
            for (key, value), done in zip(MASK.items(), flags):
                if done:
                    setattr(row, key, value)
    null_id = seed(cleanup_db, 1, offset=20)[0]
    with session() as db, db.begin():
        row = db.get(Registration, null_id)
        row.preview = None  # JSONB's default encoding is JSON null, not SQL NULL.
        row.lookup_name = row.label = '[deleted]'
    with session() as db:
        assert db.scalar(text('SELECT preview = \'null\'::jsonb FROM game_account_registrations WHERE id=:id'),
                         {'id': null_id}) is True
    active = seed(cleanup_db, 1, offset=30, age=None)[0]
    grace = seed(cleanup_db, 1, offset=31, age=timedelta(hours=24)-timedelta(microseconds=1))[0]
    boundary = seed(cleanup_db, 1, offset=32, age=timedelta(hours=24))[0]
    before, other = rows(), unrelated(cleanup_db)
    cleanup.clean()
    after = rows()
    assert masked_ids() == set(ids+[null_id, boundary])
    assert after[active] == before[active] and after[grace] == before[grace]
    assert after[ids[-1]] == before[ids[-1]]  # Already complete, including write metadata.
    assert_preserved(before, after)
    assert unrelated(cleanup_db) == other
    cleanup.clean()
    assert rows() == after


def registration_update(statement):
    return statement.lstrip().startswith('UPDATE game_account_registrations SET')


def test_update_failure_rolls_back_and_retry_progresses(cleanup_db):
    seed(cleanup_db, 450)
    before, other = rows(), unrelated(cleanup_db)
    updates = []
    def fail_after_update(conn, cursor, statement, parameters, context, executemany):
        if registration_update(statement):
            updates.append(True)
            raise RuntimeError('synthetic cleanup interruption')
    engine = cleanup_db[0]
    event.listen(engine, 'after_cursor_execute', fail_after_update)
    try:
        with pytest.raises(RuntimeError, match='synthetic cleanup interruption'):
            cleanup.clean()
    finally:
        event.remove(engine, 'after_cursor_execute', fail_after_update)
    assert updates
    assert rows() == before  # New connection, after the aborted transaction closed.
    assert unrelated(cleanup_db) == other
    for count in (200, 400, 450):
        cleanup.clean()
        assert len(masked_ids()) == count
    assert_preserved(before, rows())


def test_concurrent_cleaners_serialize_and_advance(cleanup_db):
    seed(cleanup_db, 450)
    engine = cleanup_db[0]
    before, other = rows(), unrelated(cleanup_db)
    first_selected, second_lock, release = Event(), Event(), Event()
    guard = Lock()
    state = {'locks': 0}
    def before_sql(conn, cursor, statement, parameters, context, executemany):
        if 'pg_advisory_xact_lock' in statement:
            with guard:
                state['locks'] += 1
                if state['locks'] == 2:
                    second_lock.set()
    def after_sql(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith('SELECT game_account_registrations.') and 'FOR UPDATE' in statement:
            if not first_selected.is_set():
                first_selected.set()
                assert release.wait(10), 'Timed out releasing first cleaner'
    event.listen(engine, 'before_cursor_execute', before_sql)
    event.listen(engine, 'after_cursor_execute', after_sql)
    try:
        with ThreadPoolExecutor(2) as pool:
            try:
                first = pool.submit(cleanup.clean)
                assert first_selected.wait(10)
                second = pool.submit(cleanup.clean)
                assert second_lock.wait(10)
                deadline = monotonic()+5
                with engine.connect() as observer:
                    while not observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event='advisory'")):
                        assert monotonic() < deadline, 'Second cleaner did not wait on advisory lock'
                        release.wait(0.01)
                assert not second.done()
            finally:
                release.set()
            first.result(timeout=15)
            second.result(timeout=15)
    finally:
        release.set()
        event.remove(engine, 'before_cursor_execute', before_sql)
        event.remove(engine, 'after_cursor_execute', after_sql)
    assert len(masked_ids()) == 400
    cleanup.clean()
    assert len(masked_ids()) == 450
    assert_preserved(before, rows())
    assert unrelated(cleanup_db) == other


def test_locked_rows_are_skipped_then_retried(cleanup_db):
    ids = seed(cleanup_db, 450)
    before, other = rows(), unrelated(cleanup_db)
    engine = cleanup_db[0]
    with engine.connect() as holder, holder.begin():
        holder.execute(select(Registration.id).where(Registration.id.in_(ids[:10])).with_for_update())
        cleanup.clean()
        assert masked_ids() == set(ids[10:210])
    cleanup.clean()
    assert masked_ids() == set(ids[:400])
    cleanup.clean()
    assert masked_ids() == set(ids)
    assert_preserved(before, rows())
    assert unrelated(cleanup_db) == other
