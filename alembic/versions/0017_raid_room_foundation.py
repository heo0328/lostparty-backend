"""F1 recruitment storage. Apply only to isolated tests until explicitly activated."""
from alembic import op

revision = "0017_raid_room_foundation"
down_revision = "0016_record_timestamps"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE raid_rooms (
        id UUID NOT NULL,
        round_id UUID NOT NULL,
        leader_membership_id UUID NOT NULL,
        title VARCHAR(60) NOT NULL,
        scope VARCHAR(8) NOT NULL,
        group_id UUID,
        creation_scope VARCHAR(8) NOT NULL,
        creation_group_id UUID,
        admission_mode VARCHAR(16) NOT NULL,
        revision INTEGER NOT NULL,
        members_revision INTEGER NOT NULL,
        applications_revision INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        ended_at TIMESTAMP WITH TIME ZONE,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (id),
        CHECK ((scope='public' AND group_id IS NULL) OR (scope='group' AND group_id IS NOT NULL)),
        CHECK ((creation_scope='public' AND creation_group_id IS NULL) OR (creation_scope='group' AND creation_group_id IS NOT NULL)),
        CHECK (admission_mode IN ('leader_only','direct_join') AND char_length(title) BETWEEN 1 AND 60),
        CHECK (revision>=1 AND members_revision>=1 AND applications_revision>=1),
        FOREIGN KEY(group_id) REFERENCES groups (id),
        FOREIGN KEY(creation_group_id) REFERENCES groups (id)
    )
    """)
    op.execute("""
    CREATE TABLE raid_room_rounds (
        id UUID NOT NULL,
        room_id UUID NOT NULL,
        raid_id VARCHAR(64) NOT NULL,
        difficulty_id VARCHAR(64) NOT NULL,
        catalog_version VARCHAR(64) NOT NULL,
        cycle_key DATE NOT NULL,
        party_count INTEGER NOT NULL,
        revision INTEGER NOT NULL,
        starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
        ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        ended_at TIMESTAMP WITH TIME ZONE,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (id),
        UNIQUE (room_id, id),
        CHECK (revision>=1 AND party_count IN (1,2) AND starts_at<ends_at),
        CHECK (EXTRACT(DOW FROM cycle_key)=3),
        FOREIGN KEY(room_id) REFERENCES raid_rooms (id)
    )
    """)
    op.execute("""
    CREATE TABLE raid_room_memberships (
        id UUID NOT NULL,
        room_id UUID NOT NULL,
        round_id UUID NOT NULL,
        user_id UUID NOT NULL,
        character_id UUID NOT NULL,
        selected_role VARCHAR(8) NOT NULL,
        party_no INTEGER NOT NULL,
        slot_no INTEGER NOT NULL,
        display JSONB NOT NULL,
        build JSONB,
        ownership_revision INTEGER NOT NULL,
        lifecycle_revision INTEGER NOT NULL,
        revision INTEGER NOT NULL,
        joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
        ended_at TIMESTAMP WITH TIME ZONE,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (id),
        UNIQUE (room_id, id),
        FOREIGN KEY(room_id, round_id) REFERENCES raid_room_rounds (room_id, id),
        CHECK (selected_role IN ('dealer','support') AND party_no BETWEEN 1 AND 2 AND slot_no BETWEEN 1 AND 4),
        CHECK (revision>=1 AND ownership_revision>=1 AND lifecycle_revision>=1),
        FOREIGN KEY(room_id) REFERENCES raid_rooms (id),
        FOREIGN KEY(user_id) REFERENCES users (id),
        FOREIGN KEY(character_id) REFERENCES game_characters (id)
    )
    """)
    op.execute("""
    CREATE TABLE raid_room_applications (
        id UUID NOT NULL,
        room_id UUID NOT NULL,
        round_id UUID NOT NULL,
        user_id UUID NOT NULL,
        selection JSONB NOT NULL,
        display JSONB NOT NULL,
        state VARCHAR(16) NOT NULL,
        revision INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        ended_at TIMESTAMP WITH TIME ZONE,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (id),
        FOREIGN KEY(room_id, round_id) REFERENCES raid_room_rounds (room_id, id),
        CHECK (state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND revision>=1),
        CHECK (expires_at>created_at AND ((state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL))),
        FOREIGN KEY(room_id) REFERENCES raid_rooms (id),
        FOREIGN KEY(user_id) REFERENCES users (id)
    )
    """)
    op.execute("""
    CREATE TABLE raid_room_directory_head (
        id SERIAL NOT NULL,
        revision INTEGER NOT NULL,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (id),
        CHECK (id=1 AND revision>=1)
    )
    """)
    op.execute("""
    CREATE TABLE raid_room_member_heads (
        user_id UUID NOT NULL,
        membership_revision INTEGER NOT NULL,
        application_revision INTEGER NOT NULL,
        record_created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp(),
        PRIMARY KEY (user_id),
        CHECK (membership_revision>=1 AND application_revision>=1),
        FOREIGN KEY(user_id) REFERENCES users (id)
    )
    """)
    op.execute('ALTER TABLE raid_rooms ADD CONSTRAINT fk_room_current_round FOREIGN KEY(id, round_id) REFERENCES raid_room_rounds (room_id, id) DEFERRABLE INITIALLY DEFERRED')
    op.execute('ALTER TABLE raid_rooms ADD CONSTRAINT fk_room_leader FOREIGN KEY(id, leader_membership_id) REFERENCES raid_room_memberships (room_id, id) DEFERRABLE INITIALLY DEFERRED')
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_rooms FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_room_rounds FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE INDEX ix_room_member_user ON raid_room_memberships (user_id, joined_at)')
    op.execute('CREATE UNIQUE INDEX uq_room_current_slot ON raid_room_memberships (room_id, party_no, slot_no) WHERE ended_at IS NULL')
    op.execute('CREATE UNIQUE INDEX uq_room_current_user ON raid_room_memberships (room_id, user_id) WHERE ended_at IS NULL')
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_room_memberships FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute("CREATE UNIQUE INDEX uq_room_pending_application ON raid_room_applications (room_id, user_id) WHERE state='pending'")
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_room_applications FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_room_directory_head FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON raid_room_member_heads FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('INSERT INTO raid_room_directory_head(id,revision) VALUES (1,1)')


def downgrade():
    raise RuntimeError("Preserve room membership/application history; use a forward correction")
