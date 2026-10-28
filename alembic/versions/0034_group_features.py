"""Add group display provenance and transactional activity; preserve old rows."""
from alembic import op

revision = '0034_group_features'
down_revision = '0033_reapplication_history'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE group_activity_heads (
        group_id UUID PRIMARY KEY REFERENCES groups(id), last_activity_at TIMESTAMPTZ NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(), record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp())''')
    op.execute('''CREATE TABLE group_subject_character_references (
        subject_id UUID PRIMARY KEY, group_id UUID NOT NULL, user_id UUID NOT NULL,
        character_id UUID NOT NULL REFERENCES game_characters(id),
        ownership_revision INTEGER NOT NULL CHECK(ownership_revision>=1),
        lifecycle_revision INTEGER NOT NULL CHECK(lifecycle_revision>=1),
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(), record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        FOREIGN KEY(group_id,subject_id,user_id) REFERENCES group_join_subjects(group_id,id,user_id))''')
    for name in ('group_activity_heads', 'group_subject_character_references'):
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {name} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    op.execute('''CREATE FUNCTION record_group_activity() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE gid UUID;
        BEGIN
            IF TG_OP='UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
            IF TG_TABLE_NAME='groups' THEN gid:=NEW.id; ELSE gid:=NEW.group_id; END IF;
            IF gid IS NOT NULL THEN
                INSERT INTO group_activity_heads(group_id,last_activity_at) VALUES(gid,clock_timestamp())
                ON CONFLICT(group_id) DO UPDATE SET last_activity_at=GREATEST(group_activity_heads.last_activity_at,EXCLUDED.last_activity_at);
            END IF;
            RETURN NEW;
        END; $$''')
    for name in ('groups','group_memberships','group_join_relations','group_join_subjects','group_join_codes'):
        op.execute(f'CREATE TRIGGER group_activity_after_write AFTER INSERT OR UPDATE ON {name} FOR EACH ROW EXECUTE FUNCTION record_group_activity()')
    op.execute('CREATE TRIGGER group_activity_after_insert AFTER INSERT ON recruitment_rooms FOR EACH ROW EXECUTE FUNCTION record_group_activity()')
    op.execute('''CREATE TRIGGER group_activity_after_visibility AFTER UPDATE ON recruitment_rooms
        FOR EACH ROW WHEN (OLD.scope IS DISTINCT FROM NEW.scope) EXECUTE FUNCTION record_group_activity()''')


def downgrade():
    raise RuntimeError('Preserve group provenance/activity and relationship history; fix forward')
