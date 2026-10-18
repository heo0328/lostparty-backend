"""Add weekly raid state without copying or altering existing member/game data."""
from alembic import op

revision = '0011_raid_weekly_states'
down_revision = '0010_verification_executions'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE raid_weekly_states (
        user_id UUID NOT NULL REFERENCES users(id),
        character_id UUID NOT NULL REFERENCES game_characters(id),
        raid_id VARCHAR(64) NOT NULL,
        cycle_key DATE NOT NULL,
        revision INTEGER NOT NULL CONSTRAINT ck_weekly_revision CHECK (revision >= 1),
        manual_completed_at TIMESTAMPTZ,
        manual_difficulty_id VARCHAR(64),
        party_completed_at TIMESTAMPTZ,
        completed_party_id UUID,
        party_difficulty_id VARCHAR(64),
        active_party_id UUID,
        active_difficulty_id VARCHAR(64),
        joined_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (user_id, character_id, raid_id, cycle_key),
        CONSTRAINT ck_weekly_wednesday CHECK (EXTRACT(DOW FROM cycle_key) = 3),
        CONSTRAINT ck_weekly_manual CHECK (manual_completed_at IS NOT NULL OR manual_difficulty_id IS NULL),
        CONSTRAINT ck_weekly_party_completion CHECK (
            (party_completed_at IS NULL AND completed_party_id IS NULL AND party_difficulty_id IS NULL)
            OR (party_completed_at IS NOT NULL AND completed_party_id IS NOT NULL AND party_difficulty_id IS NOT NULL)),
        CONSTRAINT ck_weekly_participation CHECK (
            (active_party_id IS NULL AND active_difficulty_id IS NULL AND joined_at IS NULL)
            OR (active_party_id IS NOT NULL AND active_difficulty_id IS NOT NULL AND joined_at IS NOT NULL)),
        CONSTRAINT ck_weekly_completion_occupancy CHECK (
            active_party_id IS NULL OR (manual_completed_at IS NULL AND party_completed_at IS NULL))
    )''')


def downgrade():
    raise RuntimeError('Preserve weekly history; roll back API image without dropping ledger data')
