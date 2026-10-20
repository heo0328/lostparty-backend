"""Add exact weekly occupancy links without inventing historical assignments.

Frozen forward DDL. Existing ledger payloads and every existing row are unchanged.
"""
from alembic import op

revision = '0021_recruitment_weekly_links'
down_revision = '0020_recruitment_sources'
branch_labels = depends_on = None


def upgrade():
    op.execute('ALTER TABLE recruitment_items ADD CONSTRAINT uq_item_weekly_owner UNIQUE(room_id,id,raid_id)')
    op.execute('ALTER TABLE recruitment_rounds ADD CONSTRAINT uq_round_weekly_owner UNIQUE(room_id,item_id,id,cycle_key)')
    op.execute('ALTER TABLE recruitment_assignments ADD CONSTRAINT uq_assignment_weekly_owner UNIQUE(room_id,item_id,round_id,id,user_id,character_id)')
    op.execute('''CREATE TABLE recruitment_weekly_occupancies (
        user_id UUID NOT NULL, character_id UUID NOT NULL, raid_id VARCHAR(64) NOT NULL,
        cycle_key DATE NOT NULL, room_id UUID NOT NULL, item_id UUID NOT NULL,
        round_id UUID NOT NULL, assignment_id UUID NOT NULL UNIQUE,
        joined_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        PRIMARY KEY(user_id,character_id,raid_id,cycle_key),
        FOREIGN KEY(user_id,character_id,raid_id,cycle_key)
            REFERENCES raid_weekly_states(user_id,character_id,raid_id,cycle_key),
        FOREIGN KEY(room_id,item_id,round_id,assignment_id,user_id,character_id)
            REFERENCES recruitment_assignments(room_id,item_id,round_id,id,user_id,character_id),
        FOREIGN KEY(room_id,item_id,raid_id) REFERENCES recruitment_items(room_id,id,raid_id),
        FOREIGN KEY(room_id,item_id,round_id,cycle_key) REFERENCES recruitment_rounds(room_id,item_id,id,cycle_key)
    )''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write
        BEFORE INSERT OR UPDATE ON recruitment_weekly_occupancies
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():
    raise RuntimeError('Preserve recruitment occupancy evidence; destructive downgrade is unsupported')
