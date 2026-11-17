"""Non-destructive owner-generation analysis policy baseline and candidates."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
revision='0038_analysis_candidates'
down_revision='0037_server_analysis'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('analysis_candidate_policies',
        sa.Column('id',UUID(),primary_key=True),
        sa.Column('user_id',UUID(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('account_id',UUID(),sa.ForeignKey('game_accounts.id'),nullable=False),
        sa.Column('ownership_revision',sa.Integer(),nullable=False),
        sa.Column('revision',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('baseline',sa.String(16),nullable=False),
        sa.Column('record_created_at',sa.DateTime(timezone=True),server_default=sa.func.clock_timestamp()),
        sa.Column('record_updated_at',sa.DateTime(timezone=True),server_default=sa.func.clock_timestamp()),
        sa.UniqueConstraint('user_id','account_id','ownership_revision'),
        sa.CheckConstraint("revision>0 AND ownership_revision>0 AND baseline IN ('legacy','observed')"))
    op.create_table('analysis_candidates',
        sa.Column('id',UUID(),primary_key=True),
        sa.Column('policy_id',UUID(),sa.ForeignKey('analysis_candidate_policies.id'),nullable=False),
        sa.Column('character_id',UUID(),sa.ForeignKey('game_characters.id'),nullable=False),
        sa.Column('below_threshold',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('legacy',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('excluded',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('reason',sa.String(32)),
        sa.Column('state',sa.String(16),nullable=False,server_default='pending'),
        sa.Column('generation',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('command_id',UUID()),sa.Column('command_body',JSONB()),
        sa.Column('lease_until',sa.DateTime(timezone=True)),sa.Column('last_error',JSONB()),
        sa.Column('completed_at',sa.DateTime(timezone=True)),sa.Column('completed_command_id',UUID()),
        sa.Column('record_created_at',sa.DateTime(timezone=True),server_default=sa.func.clock_timestamp()),
        sa.Column('record_updated_at',sa.DateTime(timezone=True),server_default=sa.func.clock_timestamp()),
        sa.UniqueConstraint('policy_id','character_id'),
        sa.CheckConstraint("generation>0 AND state IN ('pending','running','succeeded','blocked')"))
    op.create_index('ix_analysis_candidates_policy_id','analysis_candidates',['policy_id'])
    for table in ('analysis_candidate_policies','analysis_candidates'):
        op.execute(f'CREATE TRIGGER record_timestamps_before_write BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION maintain_record_timestamps()')
    # Existing canonical characters are unknown historical observations, never new.
    op.execute("""INSERT INTO analysis_candidate_policies(id,user_id,account_id,ownership_revision,baseline)
        SELECT gen_random_uuid(),owner_id,id,ownership_revision,'legacy' FROM game_accounts WHERE owner_id IS NOT NULL""")
    op.execute("""INSERT INTO analysis_candidates(id,policy_id,character_id,legacy)
        SELECT gen_random_uuid(),p.id,c.id,true FROM game_characters c JOIN analysis_candidate_policies p ON p.account_id=c.account_id""")

def downgrade():
    raise RuntimeError('Candidate policy history requires an explicitly approved restore')
