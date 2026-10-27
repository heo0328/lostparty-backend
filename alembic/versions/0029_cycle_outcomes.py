"""Preserve completion and explicit stopped-round resume evidence."""
from alembic import op
revision='0029_cycle_outcomes'
down_revision='0028_cycle_planning'
branch_labels=depends_on=None


def upgrade():
    clocks='record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()'
    tables={
        'recruitment_cycle_outcomes':"""id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,
            actor_id UUID NOT NULL REFERENCES users(id),command_id UUID NOT NULL,kind VARCHAR(32) NOT NULL,effective_at TIMESTAMPTZ NOT NULL,evidence JSONB NOT NULL,
            FOREIGN KEY(room_id,cycle_id) REFERENCES recruitment_room_cycles(room_id,id),
            FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
            CHECK(kind IN ('personal_completion','complete_item','close_weekly','resume_applied') AND jsonb_typeof(evidence)='object')""",
        'recruitment_cycle_resumes':"""proposal_id UUID PRIMARY KEY,room_id UUID NOT NULL,cycle_id UUID NOT NULL,generation INTEGER NOT NULL,content JSONB NOT NULL,
            FOREIGN KEY(room_id,cycle_id,generation,proposal_id) REFERENCES recruitment_cycle_proposals(room_id,cycle_id,generation,proposal_id),
            CHECK(jsonb_typeof(content)='object')""",
    }
    for table,definition in tables.items():
        op.execute(f'CREATE TABLE {table} ({definition},{clocks})')
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
        op.execute(f'CREATE TRIGGER cycle_outcome_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()')


def downgrade():raise RuntimeError('Preserve completion and resume source history')
