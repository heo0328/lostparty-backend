"""Add beta scheduling, promise/copy evidence and self-owned application presets."""
from alembic import op
revision = '0032_beta_recruitment'
down_revision = '0031_membership_actions'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE SEQUENCE recruitment_beta_number_seq AS BIGINT MINVALUE 1 MAXVALUE 9007199254740991 NO CYCLE')
    op.execute("""CREATE TABLE recruitment_beta_schedules (
        cycle_id UUID PRIMARY KEY REFERENCES recruitment_room_cycles(id),generation INTEGER NOT NULL,
        session_id UUID NOT NULL UNIQUE REFERENCES recruitment_sessions(id),revision INTEGER NOT NULL,
        base_starts_at TIMESTAMPTZ NOT NULL,base_ends_at TIMESTAMPTZ NOT NULL,early_enabled BOOLEAN NOT NULL,
        early_additional_members INTEGER,confirmation_kind VARCHAR(24),needs_review BOOLEAN NOT NULL,
        number BIGINT NOT NULL UNIQUE DEFAULT nextval('recruitment_beta_number_seq'),password VARCHAR(5) NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK(revision>=1 AND base_starts_at<base_ends_at AND base_ends_at-base_starts_at<=interval '24 hours'),
        CHECK((early_enabled AND early_additional_members BETWEEN 1 AND 7) OR (NOT early_enabled AND early_additional_members IS NULL)),
        CHECK(confirmation_kind IS NULL OR confirmation_kind IN ('early_confirmed','base_confirmed','proposal_confirmed')),
        CHECK(NOT needs_review OR confirmation_kind IS NULL),
        CHECK(number BETWEEN 1 AND 9007199254740991 AND password ~ '^[0-9]{5}$'))""")
    op.execute('CREATE INDEX ix_beta_schedule_due ON recruitment_beta_schedules(base_starts_at) WHERE confirmation_kind IS NULL AND NOT needs_review')
    op.execute("""CREATE TABLE recruitment_beta_availability_copies (
        cycle_member_id UUID PRIMARY KEY REFERENCES recruitment_cycle_members(id),state VARCHAR(16) NOT NULL,
        source_personal_version INTEGER NOT NULL,copied_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(state IN ('unset','configured') AND source_personal_version>=1))""")
    op.execute("""CREATE TABLE recruitment_beta_application_memos (
        application_id UUID PRIMARY KEY REFERENCES recruitment_cycle_applications(id),memo VARCHAR(20),promise_revision INTEGER,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(promise_revision IS NULL OR promise_revision>=1))""")
    op.execute("""CREATE TABLE recruitment_beta_promise_reservations (
        reservation_id UUID PRIMARY KEY REFERENCES recruitment_reservations(id),cycle_id UUID NOT NULL REFERENCES recruitment_room_cycles(id),
        generation INTEGER NOT NULL,cycle_member_id UUID NOT NULL REFERENCES recruitment_cycle_members(id),
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        FOREIGN KEY(cycle_id,generation,cycle_member_id) REFERENCES recruitment_cycle_members(cycle_id,generation,id))""")
    op.execute("""CREATE TABLE member_application_message_presets (
        user_id UUID PRIMARY KEY REFERENCES users(id),version INTEGER NOT NULL,items JSONB NOT NULL,saved_at TIMESTAMPTZ,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(version>=1 AND jsonb_typeof(items)='array' AND jsonb_array_length(items)<=5))""")
    for name in ('recruitment_beta_schedules','recruitment_beta_availability_copies','recruitment_beta_application_memos',
                 'recruitment_beta_promise_reservations','member_application_message_presets'):
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {name} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    for name in ('recruitment_beta_application_memos','recruitment_beta_promise_reservations'):
        op.execute(f'CREATE TRIGGER beta_evidence_immutable BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()')


def downgrade():
    raise RuntimeError('Preserve beta identities, promises, memo snapshots and user presets')
