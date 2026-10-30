"""Actual-cycle group policy, initialized only for each existing current generation."""
from alembic import op
from sqlalchemy import text

revision = '0035_cycle_group_policy'
down_revision = '0034_group_features'
branch_labels = None
depends_on = None


def upgrade():
    # A constant schema epoch distinguishes pre-cutover incomplete requests
    # without modifying their payload/hash/ACK or adding a second command ledger.
    cutover = op.get_bind().scalar(text('SELECT clock_timestamp()'))
    op.execute(f"""CREATE FUNCTION cycle_group_policy_cutover_at() RETURNS timestamptz
        LANGUAGE sql IMMUTABLE AS $$ SELECT '{cutover.isoformat()}'::timestamptz $$""")
    op.execute('''CREATE TABLE recruitment_cycle_group_policies (
        cycle_id UUID NOT NULL, generation INTEGER NOT NULL,
        scope VARCHAR(16) NOT NULL, group_id UUID REFERENCES groups(id), revision INTEGER NOT NULL,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        PRIMARY KEY(cycle_id,generation),
        FOREIGN KEY(cycle_id,generation) REFERENCES recruitment_cycle_generations(cycle_id,generation),
        CHECK(generation>0 AND revision>0),
        CHECK((scope='public' AND group_id IS NULL) OR (scope='group' AND group_id IS NOT NULL)))''')
    op.execute('CREATE INDEX ix_recruitment_cycle_group_policies_group_id ON recruitment_cycle_group_policies(group_id)')
    op.execute('''INSERT INTO recruitment_cycle_group_policies(cycle_id,generation,scope,group_id,revision)
        SELECT c.id,c.generation,r.scope,CASE WHEN r.scope='group' THEN r.group_id ELSE NULL END,1
        FROM recruitment_room_cycles c JOIN recruitment_rooms r ON r.id=c.room_id
        JOIN recruitment_cycle_generations g ON g.cycle_id=c.id AND g.generation=c.generation
        WHERE c.provenance='explicit' AND c.generation IS NOT NULL
        AND (r.scope='public' OR (r.scope='group' AND r.group_id IS NOT NULL))''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE
        ON recruitment_cycle_group_policies FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')

    op.execute("""CREATE TRIGGER cycle_group_activity AFTER INSERT OR UPDATE ON recruitment_cycle_group_policies
        FOR EACH ROW EXECUTE FUNCTION record_group_activity()""")


def downgrade():
    raise RuntimeError('Preserve per-generation policy; use a forward migration')
