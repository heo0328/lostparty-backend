"""F3-B: additive migrations and service operations as an authenticated app role.

Only the tmpfs compose.test PostgreSQL may host these disposable databases.
No production connection or existing database is modified by this fixture.
"""
import hashlib
import json
import os
import subprocess
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.core import database
from app.core.database import session, now
from app.core.errors import AuthError
from app.raid_rooms import core, queries, readiness, service, usage
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from app.member_limits.service import Limits
from tests.test_member_limits import change
from app.raid_rooms.models import Application, Room
from tests.test_group_admissions import group, worlds
from tests.test_group_foundation import actor
from tests.test_raid_room_foundation import (
    people, create, create_command, join, recover, decision, selection, explicit_test_policy,
)


@contextmanager
def isolated_app_database():
    source = make_url(os.environ['DATABASE_URL'])
    assert source.host == 'test-db' and source.database == 'lostparty_test'
    assert source.username == 'postgres'
    name = 'room_migration_test_' + uuid.uuid4().hex
    role = 'room_app_test_' + uuid.uuid4().hex
    # Fabricated credential, only for this temporary PostgreSQL role.
    password = uuid.uuid4().hex
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    target = None
    app_engine = None
    role_created = database_created = False
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(
                f'CREATE ROLE "{role}" LOGIN PASSWORD \'{password}\' NOSUPERUSER NOCREATEDB NOCREATEROLE')
            role_created = True
            connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
            database_created = True
        target = create_engine(source.set(database=name), hide_parameters=True)
        with target.begin() as connection:
            # Same schema grants as docker/init-db.sh; app owns its migration objects.
            connection.exec_driver_sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            connection.exec_driver_sql(f'GRANT USAGE, CREATE ON SCHEMA public TO "{role}"')
        app_url = source.set(database=name, username=role, password=password)
        app_engine = create_engine(app_url, hide_parameters=True)

        def upgrade(revision):
            env = {**os.environ, 'DATABASE_URL': app_url.render_as_string(hide_password=False)}
            result = subprocess.run(['alembic', 'upgrade', revision], env=env,
                                    capture_output=True, text=True, timeout=90)
            # Never include credentials or arbitrary database responses in failure output.
            assert result.returncode == 0, f'Isolated app-role migration failed: {revision}'
        yield app_engine, role, upgrade
    finally:
        if app_engine is not None:
            app_engine.dispose()
        if target is not None:
            target.dispose()
        with admin.connect() as connection:
            if database_created:
                connection.exec_driver_sql(f'DROP DATABASE "{name}"')
            if role_created:
                connection.exec_driver_sql(f'DROP ROLE "{role}"')
        admin.dispose()


def table_digests(engine, tables):
    """Compare all columns, including record timestamps, without exposing rows."""
    with engine.connect() as connection:
        return {
            table: hashlib.sha256('\n'.join(sorted(connection.execute(text(
                f'SELECT row_to_json(t)::text FROM "{table}" AS t'
            )).scalars())).encode()).hexdigest()
            for table in tables
        }


def test_existing_data_and_0017_pending_survive_app_role_migrations(
    isolated, client, people, monkeypatch,
):
    with isolated_app_database() as (app_engine, role, upgrade):
        upgrade('0016_record_timestamps')
        # All session() users now connect by LOGIN as the restricted role; no SET ROLE.
        with monkeypatch.context() as patch:
            patch.setattr(database, 'engine', lambda: app_engine)
            a, b = people('migration-a'), people('migration-b')
            gid = group(client, a)
            change(a['uid'], Limits(15, 5, 10))
            with session() as db, db.begin():
                stamp = now(db)
                db.add(WeeklyState(user_id=a['uid'], character_id=uuid.UUID(a['ids'][2]),
                    raid_id='horizon_cathedral', cycle_key=core.weekly.parse_cycle(raids.cycle(stamp).cycle_key),
                    revision=3, manual_completed_at=stamp, manual_difficulty_id='stage1', updated_at=stamp))
            old_tables = set(inspect(app_engine).get_table_names()) - {'alembic_version'}
            before = table_digests(app_engine, old_tables)
            with app_engine.connect() as connection:
                identity = connection.execute(text('''
                    SELECT current_user, session_user, rolsuper, rolcreatedb, rolcreaterole
                    FROM pg_roles WHERE rolname=current_user
                ''')).one()
                assert identity == (role, role, False, False, False)
                for table in ('users', 'auth_sessions', 'game_accounts', 'game_characters',
                              'groups', 'group_memberships', 'raid_weekly_states', 'member_usage_limits'):
                    assert connection.scalar(text(f'SELECT count(*) FROM "{table}"')) > 0

            upgrade('0017_raid_room_foundation')
            assert table_digests(app_engine, old_tables) == before
            with session() as db:
                with pytest.raises(AuthError):
                    readiness.require_ready(db)
            rid = uuid.UUID(create(a, create_command(a, mode='leader_only'))[1]['room_id'])
            aid = uuid.uuid4()
            with app_engine.begin() as connection:
                # Genuine 0017 row: build does not exist yet, no fabricated backfill.
                connection.execute(text('''
                    INSERT INTO raid_room_applications
                    (id,room_id,round_id,user_id,selection,display,state,revision,created_at,expires_at)
                    SELECT :id,id,round_id,:uid,CAST(:selection AS jsonb),
                           (SELECT display FROM raid_room_memberships WHERE room_id=:rid LIMIT 1),
                           'pending',1,clock_timestamp(),clock_timestamp()+interval '1 day'
                    FROM raid_rooms WHERE id=:rid
                '''), {'id': aid, 'uid': b['uid'], 'rid': rid,
                      'selection': json.dumps(selection(b).model_dump(mode='json'))})
            tables_0017 = set(inspect(app_engine).get_table_names()) - {'alembic_version', 'raid_room_applications'}
            before_0018 = table_digests(app_engine, tables_0017)
            with app_engine.connect() as connection:
                pending_before = dict(connection.execute(text(
                    'SELECT * FROM raid_room_applications WHERE id=:id'), {'id': aid}).mappings().one())
            upgrade('0018_room_application_build')
            assert table_digests(app_engine, tables_0017) == before_0018
            with session() as db:
                readiness.require_ready(db)
                pending_after = dict(db.execute(text(
                    'SELECT * FROM raid_room_applications WHERE id=:id'), {'id': aid}).mappings().one())
                assert pending_after.pop('build') is None
                assert pending_after == pending_before
                assert usage.count(db, a['uid']) == 1
            # Missing legacy build fails private detail closed; cleanup stays available.
            with pytest.raises(AuthError) as error:
                queries.application(actor(b['uid']), aid)
            assert error.value.status == 503 and error.value.code == 'SERVICE_UNAVAILABLE'
            rejected = service.decide(actor(a['uid']), aid, uuid.uuid4(), decision(aid))
            assert rejected[1]['state'] == 'rejected'
            new_aid = uuid.UUID(join(b, rid, applying=True)[1]['application_id'])
            service.decide(actor(a['uid']), new_aid, uuid.uuid4(), decision(new_aid),
                           approve=True, policy=explicit_test_policy)
            assert queries.room_summary(rid)['member_count'] == 2
            with session() as db:
                row = db.get(Application, new_aid)
                assert row.build is not None
                assert row.record_created_at is not None and row.record_updated_at is not None
                assert usage.count(db, b['uid']) == 1
            recover(b, rid)
            recover(a, rid, 'end')
            with session() as db:
                assert usage.count(db, a['uid']) == usage.count(db, b['uid']) == 0
                assert db.get(Room, rid).ended_at is not None
                readiness.require_ready(db)
            # Existing group remains queryable through the original authenticated API.
            assert client.get('/v1/me/groups/'+gid, headers=a['headers']).status_code == 200
