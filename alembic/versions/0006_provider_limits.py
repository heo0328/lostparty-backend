"""Token-specific provider deadline; no business data modifications."""
from alembic import op
import sqlalchemy as sa
revision = '0006_provider_limits'
down_revision = '0005_lostark_credentials'
branch_labels = depends_on = None


def upgrade():
    op.create_table('lostark_provider_limits',
        sa.Column('fingerprint', sa.String(64), primary_key=True),
        sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_lostark_provider_limits_blocked_until', 'lostark_provider_limits', ['blocked_until'])


def downgrade():
    op.drop_table('lostark_provider_limits')
