"""Preserve explicit declines and leadership/empty-future decisions."""
from alembic import op
revision='0026_cycle_lifecycle'
down_revision='0025_cycle_admissions'
branch_labels=depends_on=None


def upgrade():
    op.execute('''CREATE TABLE recruitment_cycle_decisions (
        id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        user_id UUID NOT NULL REFERENCES users(id),command_id UUID NOT NULL,kind VARCHAR(32) NOT NULL,
        effective_at TIMESTAMPTZ NOT NULL,evidence JSONB NOT NULL,
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        UNIQUE(cycle_id,generation,command_id,kind),
        CHECK(kind IN ('declined','leadership_transferred','automatic_successor','future_empty_cancelled') AND jsonb_typeof(evidence)='object'),
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
    )''')
    op.execute('CREATE INDEX ix_cycle_decision_actor ON recruitment_cycle_decisions(user_id,cycle_id,effective_at,id)')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON recruitment_cycle_decisions
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''CREATE FUNCTION protect_cycle_decision() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Cycle decisions are immutable'; END $$''')
    op.execute('''CREATE TRIGGER cycle_decision_immutable BEFORE UPDATE OR DELETE ON recruitment_cycle_decisions
        FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()''')
    op.execute('''CREATE TABLE recruitment_cycle_schedule_groups (
        group_id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
        FOREIGN KEY(room_id,group_id) REFERENCES recruitment_schedule_groups(room_id,id),
        FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
    )''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON recruitment_cycle_schedule_groups
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''INSERT INTO recruitment_cycle_schedule_groups(group_id,room_id,cycle_id,generation)
        SELECT g.id,g.room_id,c.id,c.generation FROM recruitment_schedule_groups g
        JOIN recruitment_room_cycles c ON c.room_id=g.room_id AND c.cycle_key=g.cycle_key
        WHERE c.provenance='explicit' AND c.generation=1''')


def downgrade():raise RuntimeError('Preserve explicit cycle decisions')
