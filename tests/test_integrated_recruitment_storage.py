"""R1: real PostgreSQL forward import as a restricted LOGIN; no app DB changes."""
import uuid
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from app.core import database
from app.core.database import session
from app.raid_rooms import readiness
from app.raid_rooms.integrated_models import (
    RecruitmentRoom, RecruitmentItem, RecruitmentRound, RecruitmentMembership,
    RecruitmentAssignment, RecruitmentSession, RecruitmentSegment,
)
from tests.test_raid_room_migrations import isolated_app_database, table_digests
from tests.test_group_admissions import worlds, group
from tests.test_raid_room_foundation import people, create, create_command, selection, join, recover

MODELS = (RecruitmentRoom, RecruitmentItem, RecruitmentRound, RecruitmentMembership,
          RecruitmentAssignment, RecruitmentSession, RecruitmentSegment)


@pytest.fixture
def imported(people, monkeypatch, client):
    with isolated_app_database() as (target, role, upgrade):
        upgrade('0018_room_application_build')
        with monkeypatch.context() as patch:
            patch.setattr(database, 'engine', lambda: target)
            a, b = people('r1-a'), people('r1-b')
            gid = uuid.UUID(group(client, a))
            rid = uuid.UUID(create(a)[1]['room_id'])
            join(b, rid)
            second = uuid.UUID(create(a, create_command(a, offset=3, selection=selection(a, index=1)))[1]['room_id'])
            third = uuid.UUID(create(b, create_command(b, offset=6, selection=selection(b, index=1)))[1]['room_id'])
            recover(b, third, 'end')
            with target.begin() as c:
                # Preserve a legal legacy interval that has no valid new 5-minute duration.
                c.execute(text("UPDATE raid_room_rounds SET ends_at=starts_at+interval '11 minutes' WHERE room_id=:id"), {'id': second})
            old = set(inspect(target).get_table_names()) - {'alembic_version'}
            before = table_digests(target, old)
            upgrade('0019_integrated_recruitment')
            assert table_digests(target, old) == before
            yield target, rid, second, third, a, b, gid


def test_import_preserves_all_old_rows_and_distinct_lifetimes(imported):
    target, rid, second, third, a, b, gid = imported
    with target.connect() as c:
        assert c.scalar(text('SELECT current_user= session_user AND NOT rolsuper FROM pg_roles WHERE rolname=current_user'))
        assert c.scalar(text('SELECT count(*) FROM recruitment_rooms')) == 3
        assert c.scalar(text('SELECT count(*) FROM recruitment_memberships')) == 4
        assert c.scalar(text('SELECT count(*) FROM recruitment_assignments')) == 4
        assert c.scalar(text('SELECT count(*) FROM recruitment_items')) == 3
        assert c.scalar(text("SELECT count(*) FROM recruitment_sessions WHERE state='confirmed'")) == 0
        assert c.scalar(text("SELECT count(*) FROM recruitment_rooms WHERE migration_state='legacy_review_required'")) == 3
        assert c.scalar(text('SELECT count(*) FROM recruitment_assignments a JOIN recruitment_memberships m ON m.id=a.membership_id WHERE a.user_id<>m.user_id')) == 0
        assert c.scalar(text('SELECT count(*) FROM recruitment_assignments a JOIN raid_room_memberships m ON a.membership_id=m.id WHERE a.display IS DISTINCT FROM m.display OR a.build IS DISTINCT FROM m.build')) == 0
        assert c.execute(text('SELECT duration_minutes,duration_source FROM recruitment_segments WHERE room_id=:id'), {'id': second}).one() == (None, 'legacy_review_required')
        assert c.scalar(text('SELECT duration_minutes FROM recruitment_segments WHERE room_id=:id'), {'id': rid}) == 60
        assert c.scalar(text('SELECT ended_at IS NOT NULL FROM recruitment_memberships WHERE room_id=:id'), {'id': third})
        assert c.scalar(text("SELECT state FROM recruitment_assignments WHERE room_id=:id"), {'id': third}) == 'legacy_ended'
        # Persistent membership contains no round/character binding.
        columns = {v['name'] for v in inspect(c).get_columns('recruitment_memberships')}
        assert not {'round_id', 'character_id', 'cycle_key'} & columns
        for model in MODELS:
            actual = {v['name']: v for v in inspect(c).get_columns(model.__tablename__)}
            assert set(actual) == set(model.__table__.columns.keys())
            for col in model.__table__.columns:
                assert actual[col.name]['nullable'] == col.nullable
                assert str(actual[col.name]['type'].compile(dialect=target.dialect)) == str(col.type.compile(dialect=target.dialect))
        assert c.scalar(text('SELECT count(*) FROM recruitment_memberships n JOIN raid_room_memberships o USING(id) WHERE n.record_created_at IS DISTINCT FROM o.record_created_at OR n.record_updated_at IS DISTINCT FROM o.record_updated_at')) == 0
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        readiness.require_ready(db, integrated=True)  # Full new schema + restricted role, read only.


@pytest.mark.parametrize('mutation', [
    "UPDATE recruitment_segments SET room_id=:other WHERE room_id=:room",
    "UPDATE recruitment_assignments SET user_id=:user WHERE membership_id=(SELECT leader_membership_id FROM recruitment_rooms WHERE id=:room)",
    "UPDATE recruitment_segments SET duration_minutes=NULL,duration_source='explicit' WHERE room_id=:room",
    "UPDATE recruitment_segments SET duration_minutes=11 WHERE room_id=:room",
    "UPDATE recruitment_sessions SET state='confirmed',ends_at=starts_at+interval '25 hours' WHERE room_id=:room",
    "UPDATE recruitment_assignments SET slot_no=1 WHERE room_id=:room",
])
def test_cross_room_owner_slot_and_duration_guards(imported, mutation):
    target, rid, second, third, a, b, gid = imported
    with target.begin() as c:
        with pytest.raises(IntegrityError):
            with c.begin_nested():
                c.execute(text(mutation), {'room': rid, 'other': second, 'user': b['uid']})
        assert c.scalar(text('SELECT count(*) FROM recruitment_memberships WHERE room_id=:id'), {'id': rid}) == 2


def test_linked_public_room_and_distinct_overlapping_sessions_are_representable(imported):
    target, rid, second, third, a, b, gid = imported
    # Public + linked group must not inherit the old "public requires NULL" check.
    with target.begin() as c:
        c.execute(text('UPDATE recruitment_rooms SET group_id=:gid WHERE id=:id'), {'gid': gid, 'id': rid})
        assert c.scalar(text('SELECT scope FROM recruitment_rooms WHERE id=:id'), {'id': rid}) == 'public'
        original = c.execute(text('SELECT * FROM recruitment_sessions WHERE room_id=:id'), {'id': rid}).mappings().one()
        c.execute(text('''INSERT INTO recruitment_sessions
            (id,room_id,revision,schedule_revision,state,starts_at,ends_at,created_at)
            VALUES (:id,:room_id,1,1,'confirmed',:starts_at,:ends_at,:created_at)'''),
            {**original, 'id': uuid.uuid4()})
        assert c.scalar(text('SELECT count(*) FROM recruitment_sessions WHERE room_id=:id'), {'id': rid}) == 2
