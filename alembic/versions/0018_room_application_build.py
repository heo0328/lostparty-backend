"""Preserve application-time display snapshot without changing selection CAS."""
from alembic import op

revision = '0018_room_application_build'
down_revision = '0017_raid_room_foundation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE raid_room_applications ADD COLUMN build JSONB NULL')


def downgrade():
    raise RuntimeError('Snapshot removal requires an explicit data-retention decision')
