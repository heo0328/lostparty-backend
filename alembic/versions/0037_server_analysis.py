"""One server analysis producer; refuses implicit legacy data deletion/conversion."""
from alembic import op
from sqlalchemy import text, Column
from sqlalchemy.dialects.postgresql import JSONB

revision = '0037_server_analysis'
down_revision = '0036_roster_presence'
branch_labels = None
depends_on = None

# Every row here is an old credential, key-scoped cache, analysis or linked snapshot.
# Refuse BEFORE DDL, rather than silently relabeling client analysis as server output.
INCOMPATIBLE = ('lostark_credentials', 'member_lostark_cache', 'member_lostark_fetch_leases',
    'scoped_roster_cache', 'scoped_roster_leases', 'scoped_character_power_cache', 'character_power_cache',
    'character_role_summaries', 'character_role_power_successes', 'game_account_verifications',
    'ownership_control_proofs', 'recruitment_assignments', 'recruitment_applications', 'recruitment_cycle_applications')


def upgrade():
    db = op.get_bind()
    occupied = [table for table in INCOMPATIBLE
                if db.scalar(text(f'SELECT EXISTS(SELECT 1 FROM {table})'))]
    if db.scalar(text("SELECT EXISTS(SELECT 1 FROM game_account_requests WHERE operation IN ('role-summary','lostark-key-put','lostark-key-delete'))")):
        occupied.append('game_account_requests:old-analysis-or-key')
    if occupied:
        raise RuntimeError('0037 requires separately approved data preparation; incompatible tables: ' + ', '.join(occupied))
    op.execute("ALTER TABLE lostark_provider_limits ADD COLUMN blocked_code VARCHAR(64) NOT NULL DEFAULT 'UPSTREAM_RATE_LIMITED', ADD COLUMN upstream_status INTEGER")
    op.add_column('character_role_summaries', Column('detail', JSONB(), nullable=False))
    for table in ('scoped_roster_cache', 'scoped_roster_leases', 'scoped_character_power_cache', 'character_power_cache'):
        names = list(db.scalars(text("SELECT conname FROM pg_constraint WHERE conrelid=CAST(:table AS regclass) AND contype='c' AND pg_get_constraintdef(oid) LIKE '%credential_version%'"), {'table': table}))
        for name in names:
            op.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{name.replace(chr(34),chr(34)*2)}"')
        op.execute(f'ALTER TABLE {table} RENAME COLUMN credential_version TO provider_generation')
        op.execute(f'ALTER TABLE {table} ALTER COLUMN provider_generation TYPE VARCHAR(64) USING provider_generation::text')
    op.execute('ALTER TABLE scoped_character_power_cache ADD CHECK(length(provider_generation)=64)')
    for table in ('character_role_power_successes','member_lostark_fetch_leases','member_lostark_cache','lostark_credentials'):
        op.drop_table(table)
    op.execute('''CREATE TABLE character_analysis_fetch_leases (
        id UUID PRIMARY KEY, actor_id UUID NOT NULL REFERENCES users(id), scope_digest VARCHAR(64) NOT NULL,
        generation INTEGER NOT NULL DEFAULT 1, state VARCHAR(16) NOT NULL DEFAULT 'running',
        expires_at TIMESTAMPTZ NOT NULL, result JSONB,
        record_created_at TIMESTAMPTZ DEFAULT clock_timestamp(), record_updated_at TIMESTAMPTZ DEFAULT clock_timestamp(),
        CHECK(state IN ('running','completed','failed') AND generation>0))''')
    op.execute('CREATE INDEX ix_analysis_fetch_scope ON character_analysis_fetch_leases(actor_id,scope_digest)')
    op.execute('CREATE INDEX ix_character_analysis_fetch_leases_expires_at ON character_analysis_fetch_leases(expires_at)')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON character_analysis_fetch_leases
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')
    op.execute('''CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON roster_participation_capabilities
        FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():
    raise RuntimeError('Server analysis cutover requires an approved restore, not implicit data loss')
