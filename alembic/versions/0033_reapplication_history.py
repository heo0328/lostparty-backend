"""Keep completed assignments as history, separate from current participation."""
from alembic import op
revision='0033_reapplication_history'
down_revision='0032_beta_recruitment'
branch_labels=None
depends_on=None


def upgrade():
    # A narrower predicate retains current/stopped uniqueness without rewriting rows.
    op.drop_index('uq_recruitment_current_assignment',table_name='recruitment_assignments')
    op.execute("CREATE UNIQUE INDEX uq_recruitment_current_assignment ON recruitment_assignments(round_id,membership_id) WHERE state <> 'left' AND state <> 'legacy_ended' AND state <> 'completed'")


def downgrade():
    raise RuntimeError('Preserve completed history and fresh participation; fix forward')
