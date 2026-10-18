"""Common storage timestamps; preserve data and unknown legacy history.

No retention policy, deletion, or worker is introduced by this revision.
"""
from alembic import op
import sqlalchemy as sa

revision = '0016_record_timestamps'
down_revision = '0015_ownership_disputes'
branch_labels = None
depends_on = None

TABLES = ('account_character_presentation', 'activity_characters', 'auth_identities', 'auth_sessions', 'auth_transactions', 'character_history_heads', 'character_name_claims', 'character_personal_preferences', 'character_power_cache', 'character_retirements', 'character_role_summaries', 'character_settings', 'game_account_cache', 'game_account_fetch_leases', 'game_account_limit_events', 'game_account_registrations', 'game_account_requests', 'game_account_verifications', 'game_accounts', 'game_characters', 'group_directory_head', 'group_join_codes', 'group_join_relations', 'group_join_subjects', 'group_memberships', 'groups', 'lostark_credentials', 'lostark_provider_limits', 'member_lostark_cache', 'member_lostark_fetch_leases', 'member_settings', 'member_usage_heads', 'member_usage_limit_audits', 'member_usage_limits', 'ownership_audits', 'ownership_control_proofs', 'ownership_dispute_events', 'ownership_dispute_heads', 'ownership_disputes', 'ownership_member_heads', 'raid_weekly_states', 'refresh_credentials', 'refresh_recoveries', 'scoped_character_power_cache', 'scoped_roster_cache', 'scoped_roster_leases', 'users', 'verification_executions')
HAS_CREATED_AT = ('auth_sessions', 'game_account_limit_events', 'game_account_registrations', 'game_account_verifications', 'group_join_codes', 'group_join_relations', 'group_join_subjects', 'groups', 'member_usage_limit_audits', 'ownership_audits', 'ownership_control_proofs', 'ownership_dispute_events', 'users')
HAS_UPDATED_AT = ('game_account_registrations', 'group_join_subjects', 'lostark_credentials', 'member_settings', 'member_usage_limits', 'raid_weekly_states', 'users')


def upgrade():
    op.execute("""
        CREATE FUNCTION maintain_record_timestamps() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                NEW.record_created_at := clock_timestamp();
                NEW.record_updated_at := NEW.record_created_at;
            ELSE
                -- Neither callers nor a timestamp-only UPDATE can rewrite history.
                NEW.record_created_at := OLD.record_created_at;
                NEW.record_updated_at := OLD.record_updated_at;
                IF NEW IS DISTINCT FROM OLD THEN
                    NEW.record_updated_at := clock_timestamp();
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    for table in TABLES:
        # Add without defaults first: old rows must not acquire invented dates.
        op.add_column(table, sa.Column('record_created_at', sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column('record_updated_at', sa.DateTime(timezone=True), nullable=True))
        if table in HAS_CREATED_AT:
            op.execute(f'UPDATE "{table}" SET record_created_at = created_at')
        if table in HAS_UPDATED_AT:
            op.execute(f'UPDATE "{table}" SET record_updated_at = updated_at')
        for column in ('record_created_at', 'record_updated_at'):
            op.alter_column(table, column, server_default=sa.text('clock_timestamp()'))
        op.execute(f'''CREATE TRIGGER record_timestamps_before_write
            BEFORE INSERT OR UPDATE ON "{table}"
            FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()''')


def downgrade():
    raise RuntimeError('Preserve recorded timestamps; use a forward correction')
