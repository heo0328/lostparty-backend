"""Add member preferences only; no backfill or existing data modification."""
from alembic import op

revision = '0004_member_settings'
down_revision = '0003_power_cache'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE member_settings (
        user_id UUID NOT NULL PRIMARY KEY REFERENCES users(id),
        nice_group_auto_refresh_enabled BOOLEAN NOT NULL,
        version INTEGER NOT NULL CHECK (version >= 1),
        updated_at TIMESTAMPTZ NOT NULL
    )''')


def downgrade():
    op.drop_table('member_settings')
