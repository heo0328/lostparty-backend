"""Preserve retired schedule intent graphs while selecting current heads."""
from alembic import op
revision='0022_recruitment_schedule_heads'
down_revision='0021_recruitment_weekly_links'
branch_labels=depends_on=None


def upgrade():
    op.execute('''CREATE TABLE recruitment_schedule_heads (
        group_id UUID PRIMARY KEY REFERENCES recruitment_schedule_groups(id),
        client_key VARCHAR(64) NOT NULL,active BOOLEAN NOT NULL,ended_at TIMESTAMPTZ,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
    )''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON recruitment_schedule_heads
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():raise RuntimeError('Retained schedule history cannot be destructively downgraded')
