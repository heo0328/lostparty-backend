"""Retain stopped generation evidence and weekly resume agreements."""
from alembic import op
revision='0023_recruitment_resume'
down_revision='0022_recruitment_schedule_heads'
branch_labels=depends_on=None


def upgrade():
    op.execute('''CREATE TABLE recruitment_resume_proposals (
        id UUID PRIMARY KEY,room_id UUID NOT NULL REFERENCES recruitment_rooms(id),
        creator_membership_id UUID NOT NULL REFERENCES recruitment_memberships(id),
        revision INTEGER NOT NULL,created_from_plan_revision INTEGER NOT NULL,
        state VARCHAR(16) NOT NULL,content JSONB NOT NULL,responses JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(revision>=1 AND created_from_plan_revision>=1 AND state IN ('pending','applied','obsolete'))
    )''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON recruitment_resume_proposals
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():raise RuntimeError('Resume agreement history must be preserved')
