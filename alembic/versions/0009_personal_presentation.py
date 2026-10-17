"""Add personal preferences and account presentation; no backfill or cleanup."""
from alembic import op

revision = '0009_personal_presentation'
down_revision = '0008_role_summaries'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE character_personal_preferences (
        user_id UUID NOT NULL REFERENCES users(id),
        character_id UUID NOT NULL REFERENCES game_characters(id),
        ownership_revision INTEGER NOT NULL,
        preferred_role VARCHAR(16),
        visible BOOLEAN NOT NULL,
        display_order INTEGER,
        version INTEGER NOT NULL,
        saved_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, character_id, ownership_revision),
        CHECK (preferred_role IS NULL OR preferred_role IN ('dealer','support')),
        CHECK (display_order IS NULL OR display_order >= 0),
        CHECK (ownership_revision > 0 AND version >= 1)
    )''')
    op.execute('''CREATE TABLE account_character_presentation (
        user_id UUID NOT NULL REFERENCES users(id),
        game_account_id UUID NOT NULL REFERENCES game_accounts(id),
        ownership_revision INTEGER NOT NULL,
        visible_count INTEGER NOT NULL,
        version INTEGER NOT NULL,
        saved_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, game_account_id, ownership_revision),
        CHECK (visible_count >= 1 AND visible_count <= 200),
        CHECK (ownership_revision > 0 AND version >= 1)
    )''')


def downgrade():
    raise RuntimeError('Restore an approved backup; do not discard personal preferences')
