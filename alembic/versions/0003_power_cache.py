"""Add display-only member-scoped power cache; preserve existing data."""
from alembic import op

revision = '0003_power_cache'
down_revision = '0002_game_accounts'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE character_power_cache (
        actor_id UUID NOT NULL REFERENCES users(id),
        server_name VARCHAR(64) NOT NULL, character_name VARCHAR(64) NOT NULL,
        value VARCHAR(64), fetched_at TIMESTAMPTZ, checked_at TIMESTAMPTZ,
        status VARCHAR(16) NOT NULL, reason VARCHAR(40),
        generation INTEGER NOT NULL, lease_expires_at TIMESTAMPTZ,
        PRIMARY KEY (actor_id, server_name, character_name),
        CHECK (status IN ('unknown','available','unavailable','failed') AND generation >= 0)
    )''')


def downgrade():
    op.drop_table('character_power_cache')
