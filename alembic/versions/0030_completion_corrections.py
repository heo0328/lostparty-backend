"""Append personal correction audit; retain every existing room/completion row."""
from alembic import op
revision='0030_completion_corrections'
down_revision='0029_cycle_outcomes'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""CREATE TABLE raid_completion_corrections (
        id UUID PRIMARY KEY,user_id UUID NOT NULL REFERENCES users(id),
        character_id UUID NOT NULL REFERENCES game_characters(id),raid_id VARCHAR(64) NOT NULL,
        cycle_key DATE NOT NULL,command_id UUID NOT NULL,before_revision INTEGER NOT NULL,
        after_revision INTEGER NOT NULL,sources JSONB NOT NULL,effective_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(before_revision>=1 AND after_revision=before_revision+1 AND jsonb_typeof(sources)='array' AND EXTRACT(DOW FROM cycle_key)=3))""")
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_completion_corrections FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE TRIGGER completion_correction_immutable BEFORE UPDATE OR DELETE ON raid_completion_corrections FOR EACH ROW EXECUTE FUNCTION protect_cycle_decision()')

def downgrade():raise RuntimeError('Preserve personal correction audit')
