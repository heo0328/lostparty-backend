"""Cutover migrations operate only on disposable restricted-role PostgreSQL DBs."""
import os
import subprocess
import uuid
from sqlalchemy import inspect, text
from tests.raid_rooms.common.test_raid_room_migrations import isolated_app_database


def upgrade(engine):
    return subprocess.run(['alembic','upgrade','0037_server_analysis'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,text=True,timeout=90)


def seed_user(engine):
    ident=uuid.uuid4()
    with engine.begin() as c:
        c.execute(text("INSERT INTO users(id,status,created_at,updated_at,last_login_at) VALUES(:id,'active',now(),now(),now())"),{'id':ident})
    return ident


def test_empty_cutover_preserves_users_and_installs_one_producer():
    with isolated_app_database() as (engine,role,migrate):
        migrate('0036_roster_presence');uid=seed_user(engine)
        with engine.connect() as c:before=dict(c.execute(text('SELECT * FROM users WHERE id=:id'),{'id':uid}).mappings().one())
        result=upgrade(engine)
        assert result.returncode==0,'Isolated 0037 cutover failed'
        with engine.connect() as c:
            assert dict(c.execute(text('SELECT * FROM users WHERE id=:id'),{'id':uid}).mappings().one())==before
            assert c.scalar(text('SELECT version_num FROM alembic_version'))=='0037_server_analysis'
            schema=inspect(c);names=set(schema.get_table_names())
            assert 'character_analysis_fetch_leases' in names
            assert not names & {'character_role_power_successes','lostark_credentials','member_lostark_cache','member_lostark_fetch_leases'}
            assert 'detail' in {x['name'] for x in schema.get_columns('character_role_summaries')}
            assert 'provider_generation' in {x['name'] for x in schema.get_columns('scoped_roster_cache')}


def test_old_credentials_stop_cutover_before_any_schema_or_data_change():
    with isolated_app_database() as (engine,role,migrate):
        migrate('0036_roster_presence');uid=seed_user(engine)
        with engine.begin() as c:c.execute(text('INSERT INTO lostark_credentials(user_id,version) VALUES(:id,1)'),{'id':uid})
        result=upgrade(engine)
        assert result.returncode!=0
        with engine.connect() as c:
            assert c.scalar(text('SELECT version_num FROM alembic_version'))=='0036_roster_presence'
            assert c.scalar(text('SELECT count(*) FROM lostark_credentials'))==1
            assert 'detail' not in {x['name'] for x in inspect(c).get_columns('character_role_summaries')}
            assert 'character_analysis_fetch_leases' not in inspect(c).get_table_names()
