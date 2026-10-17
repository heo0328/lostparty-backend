"""Add client analysis summaries only; no backfill or existing-data changes."""
from alembic import op

revision = '0008_role_summaries'
down_revision = '0007_character_lifecycle'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE character_role_summaries (
        user_id UUID NOT NULL REFERENCES users(id),
        character_id UUID NOT NULL REFERENCES game_characters(id),
        ownership_revision INTEGER NOT NULL,
        role VARCHAR(16) NOT NULL,
        version INTEGER NOT NULL,
        summary JSONB NOT NULL,
        saved_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, character_id, ownership_revision, role),
        CHECK (role IN ('dealer','support')),
        CHECK (ownership_revision > 0 AND version >= 1)
    )''')


def downgrade():
    raise RuntimeError('Restore an approved backup; do not discard stored role summaries')
