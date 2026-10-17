"""Preserve verification executions, including rejected ownership challenges."""
from alembic import op

revision = '0010_verification_executions'
down_revision = '0009_personal_presentation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE verification_executions (
        command_id UUID NOT NULL,
        generation INTEGER NOT NULL CHECK (generation > 0),
        actor_id UUID NOT NULL REFERENCES users(id),
        operation VARCHAR(16) NOT NULL CHECK (operation IN ('start','confirm','cancel')),
        requested_target UUID,
        challenge_id UUID,
        lookup_name VARCHAR(64),
        target_snapshot JSONB,
        started_at TIMESTAMPTZ NOT NULL,
        finished_at TIMESTAMPTZ,
        state VARCHAR(16) NOT NULL CHECK (state IN ('running','completed','failed')),
        http_status INTEGER,
        outcome_code VARCHAR(64),
        PRIMARY KEY (command_id, generation)
    )''')
    op.execute('CREATE INDEX ix_verification_executions_actor_id ON verification_executions (actor_id)')
    op.execute('CREATE INDEX ix_verification_executions_challenge_id ON verification_executions (challenge_id)')


def downgrade():
    raise RuntimeError('Verification execution history must not be discarded')
