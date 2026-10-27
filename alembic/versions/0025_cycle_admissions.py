"""Add isolated target applications and exact session/segment generation FKs."""
from alembic import op
revision='0025_cycle_admissions'
down_revision='0024_recruitment_cycles'
branch_labels=depends_on=None


def upgrade():
    op.execute('''CREATE TABLE recruitment_cycle_applications (
        id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        user_id UUID NOT NULL REFERENCES users(id),revision INTEGER NOT NULL,selection JSONB NOT NULL,
        targets JSONB NOT NULL,session_ids JSONB NOT NULL,display JSONB NOT NULL,build JSONB,
        origin_scope VARCHAR(8) NOT NULL,origin_group_id UUID REFERENCES groups(id),state VARCHAR(16) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,expires_at TIMESTAMPTZ NOT NULL,ended_at TIMESTAMPTZ,
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK(revision>=1 AND jsonb_typeof(targets)='array' AND jsonb_typeof(session_ids)='array'),
        CHECK(origin_scope IN ('public','group') AND (origin_scope<>'group' OR origin_group_id IS NOT NULL)),
        CHECK(state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND expires_at>created_at),
        CHECK((state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL))
    )''')
    op.execute("CREATE UNIQUE INDEX uq_cycle_pending_application ON recruitment_cycle_applications(cycle_id,generation,user_id) WHERE state='pending'")
    op.execute('CREATE INDEX ix_cycle_own_application ON recruitment_cycle_applications(user_id,cycle_id,created_at,id)')
    op.execute('''CREATE TABLE recruitment_cycle_sessions (
        session_id UUID PRIMARY KEY REFERENCES recruitment_sessions(id),room_id UUID NOT NULL,
        cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        UNIQUE(room_id,cycle_id,generation,session_id),
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(room_id,session_id) REFERENCES recruitment_sessions(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation)
    )''')
    op.execute('''CREATE TABLE recruitment_cycle_session_segments (
        segment_id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        session_id UUID NOT NULL,item_id UUID NOT NULL,round_id UUID NOT NULL,
        FOREIGN KEY(room_id,segment_id,session_id,item_id,round_id) REFERENCES recruitment_segments(room_id,id,session_id,item_id,round_id),
        FOREIGN KEY(room_id,cycle_id,generation,session_id) REFERENCES recruitment_cycle_sessions(room_id,cycle_id,generation,session_id),
        FOREIGN KEY(room_id,cycle_id,generation,round_id) REFERENCES recruitment_cycle_rounds(room_id,cycle_id,generation,round_id)
    )''')
    for table in ('recruitment_cycle_applications','recruitment_cycle_sessions','recruitment_cycle_session_segments'):
        op.execute(f'''ALTER TABLE {table} ADD COLUMN record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
            ADD COLUMN record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()''')
        op.execute(f'''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():raise RuntimeError('Preserve target application and schedule evidence')
