"""Group/member identity foundation; apply to isolated tests first, no API exposure."""
from alembic import op

revision = '0012_group_foundation'
down_revision = '0011_raid_weekly_states'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE groups (
        id UUID PRIMARY KEY,
        name VARCHAR(20) NOT NULL,
        revision INTEGER NOT NULL,
        members_revision INTEGER NOT NULL,
        leader_membership_id UUID NOT NULL,
        representative_character_id UUID NOT NULL REFERENCES game_characters(id),
        representative_user_id UUID NOT NULL REFERENCES users(id),
        representative_display JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        ended_at TIMESTAMPTZ,
        CONSTRAINT ck_group_revisions CHECK (revision >= 1 AND members_revision >= 1),
        CONSTRAINT ck_group_name CHECK (char_length(name) BETWEEN 1 AND 20)
    )''')
    op.execute('''CREATE TABLE group_memberships (
        id UUID PRIMARY KEY,
        group_id UUID NOT NULL REFERENCES groups(id),
        user_id UUID NOT NULL REFERENCES users(id),
        character_id UUID REFERENCES game_characters(id),
        display JSONB,
        revision INTEGER NOT NULL,
        joined_at TIMESTAMPTZ NOT NULL,
        ended_at TIMESTAMPTZ,
        CONSTRAINT uq_group_member_user UNIQUE (group_id,user_id),
        CONSTRAINT uq_group_member_identity UNIQUE (group_id,id),
        CONSTRAINT ck_group_member_revision CHECK (revision >= 1)
    )''')
    op.execute('''ALTER TABLE groups ADD CONSTRAINT fk_group_leader_member
        FOREIGN KEY (id,leader_membership_id) REFERENCES group_memberships(group_id,id)
        DEFERRABLE INITIALLY DEFERRED''')
    op.execute('''CREATE TABLE group_directory_head (
        id INTEGER PRIMARY KEY,
        revision INTEGER NOT NULL,
        CONSTRAINT ck_group_directory_head CHECK (id=1 AND revision>=1)
    )''')
    op.execute('INSERT INTO group_directory_head (id,revision) VALUES (1,1)')


def downgrade():
    raise RuntimeError('Preserve group history; roll back API code without dropping group data')
