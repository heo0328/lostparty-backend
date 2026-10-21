"""DB-enforced storage clocks, independent of application write paths."""
import uuid

from sqlalchemy import inspect, text

from app.auth.models import Base, Transaction
from app.core.database import engine, session


def test_all_application_tables_have_database_clocks():
    with engine().connect() as c:
        schema = inspect(c)
        from app.raid_rooms.cycle_models import CYCLE_MODELS
        from app.raid_rooms.cycle_application_models import CYCLE_ADMISSION_MODELS
        from app.raid_rooms.cycle_lifecycle_models import CYCLE_LIFECYCLE_MODELS
        from app.raid_rooms.cycle_consent_models import CYCLE_CONSENT_MODELS
        staged = {m.__tablename__ for m in CYCLE_MODELS+CYCLE_ADMISSION_MODELS+CYCLE_LIFECYCLE_MODELS+CYCLE_CONSENT_MODELS}
        runtime_tables = set(Base.metadata.tables) - staged
        assert runtime_tables == set(schema.get_table_names()) - {'alembic_version'}
        for table in runtime_tables:
            columns = {v['name']: v for v in schema.get_columns(table)}
            for name in ('record_created_at', 'record_updated_at'):
                assert columns[name]['type'].timezone
                assert 'clock_timestamp()' in columns[name]['default']
            assert c.scalar(text("SELECT count(*) FROM pg_trigger WHERE tgrelid=CAST(:name AS regclass) AND tgname='record_timestamps_before_write' AND NOT tgisinternal"), {'name':table}) == 1


def test_sql_writes_noop_read_and_rollback():
    row_id = uuid.uuid4()
    with engine().begin() as c:
        # Explicit timestamp injection must not forge a new record's age.
        before = c.scalar(text('SELECT clock_timestamp()'))
        original = c.execute(text("""INSERT INTO auth_transactions
            (id,nonce_digest,secret_digest,expires_at,record_created_at,record_updated_at)
            VALUES (:id,'timestamp-nonce','timestamp-secret',now()+interval '10 minutes',
                    '2000-01-01','2000-01-01') RETURNING *"""), {'id':row_id}).mappings().one()
        assert original['record_created_at'] >= before
        assert original['record_updated_at'] == original['record_created_at']
        unchanged = c.execute(text("""UPDATE auth_transactions SET nonce_digest=nonce_digest,
            record_created_at='2000-01-01', record_updated_at='2000-01-01'
            WHERE id=:id RETURNING *"""), {'id':row_id}).mappings().one()
        assert dict(original) == dict(unchanged)
        changed = c.execute(text("""UPDATE auth_transactions SET consumed_at=clock_timestamp()
            WHERE id=:id RETURNING *"""), {'id':row_id}).mappings().one()
        assert changed['record_created_at'] == original['record_created_at']
        assert changed['record_updated_at'] > original['record_updated_at']
        assert c.execute(text('SELECT * FROM auth_transactions WHERE id=:id'), {'id':row_id}).mappings().one() == changed
    with engine().connect() as c:
        tx = c.begin()
        c.execute(text("UPDATE auth_transactions SET secret_digest='rolled-back' WHERE id=:id"), {'id':row_id})
        tx.rollback()
        assert c.execute(text('SELECT * FROM auth_transactions WHERE id=:id'), {'id':row_id}).mappings().one() == changed


def test_orm_writes_and_age_filters():
    with session() as db, db.begin():
        current = db.scalar(text('SELECT clock_timestamp()'))
        row = Transaction(nonce_digest='orm-timestamp-nonce', secret_digest='orm-timestamp-secret',
                          expires_at=current)
        db.add(row)
        db.flush()
        assert row.record_created_at is not None
        created = row.record_created_at
        first_update = row.record_updated_at
        row.consumed_at = current
        db.flush()
        db.refresh(row)
        assert row.record_created_at == created
        assert row.record_updated_at > first_update
        # Preview-style predicates only. No retention deletion is implemented.
        for column in ('record_created_at', 'record_updated_at'):
            assert db.scalar(text(f"SELECT count(*) FROM auth_transactions WHERE {column} IS NOT NULL AND {column} < clock_timestamp()-interval '30 days'")) == 0
