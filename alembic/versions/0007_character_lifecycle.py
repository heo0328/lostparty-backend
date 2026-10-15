"""Lifecycle foundations; apply only to isolated DB until explicitly approved."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = '0007_character_lifecycle'
down_revision = '0006_provider_limits'
branch_labels = depends_on = None


def upgrade():
    connection = op.get_bind()
    # Report only a fixed failure, never existing character/user values.
    if connection.execute(sa.text('SELECT 1 FROM game_characters GROUP BY server_name, character_name HAVING count(*) > 1 LIMIT 1')).first():
        raise RuntimeError('LIFECYCLE_CLAIM_PREFLIGHT_CONFLICT')
    op.add_column('game_characters', sa.Column('lifecycle_state', sa.String(16), nullable=False, server_default='active'))
    op.add_column('game_characters', sa.Column('lifecycle_revision', sa.Integer(), nullable=False, server_default='1'))
    op.execute("UPDATE game_characters SET lifecycle_state='suspect' WHERE status IN ('suspect','missing')")
    op.alter_column('game_characters', 'lifecycle_state', server_default=None)
    op.alter_column('game_characters', 'lifecycle_revision', server_default=None)
    op.create_check_constraint('ck_character_lifecycle', 'game_characters', "lifecycle_state IN ('active','suspect','retired') AND lifecycle_revision > 0")
    op.create_unique_constraint('uq_character_identity_address', 'game_characters', ['id','server_name','character_name'])
    op.create_table('character_name_claims',
        sa.Column('server_name',sa.String(64),primary_key=True),
        sa.Column('character_name',sa.String(64),primary_key=True),
        sa.Column('character_id',sa.UUID(),nullable=False,unique=True),
        sa.Column('revision',sa.Integer(),nullable=False),
        sa.ForeignKeyConstraint(['character_id','server_name','character_name'], ['game_characters.id','game_characters.server_name','game_characters.character_name']),
        sa.CheckConstraint('revision > 0'))
    op.execute('INSERT INTO character_name_claims SELECT server_name, character_name, id, 1 FROM game_characters')
    constraints=sa.inspect(connection).get_unique_constraints('game_characters')
    for constraint in constraints:
        if constraint['column_names']==['server_name','character_name']:
            op.drop_constraint(constraint['name'],'game_characters',type_='unique')
    op.add_column('game_account_verifications',sa.Column('identity_snapshot',pg.JSONB(),nullable=True))
    op.create_table('character_history_heads',
        sa.Column('user_id',sa.UUID(),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('revision',sa.Integer(),nullable=False),sa.CheckConstraint('revision > 0'))
    op.create_table('character_retirements',
        sa.Column('id',sa.UUID(),primary_key=True),
        sa.Column('character_id',sa.UUID(),sa.ForeignKey('game_characters.id'),nullable=False,unique=True),
        sa.Column('user_id',sa.UUID(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('account_id',sa.UUID(),sa.ForeignKey('game_accounts.id'),nullable=False),
        sa.Column('server_name',sa.String(64),nullable=False),sa.Column('character_name',sa.String(64),nullable=False),
        sa.Column('class_name',sa.String(64),nullable=False),sa.Column('combat_power',sa.String(64)),sa.Column('item_level',sa.String(64)),
        sa.Column('power_fetched_at',sa.DateTime(timezone=True)),sa.Column('item_level_fetched_at',sa.DateTime(timezone=True)),
        sa.Column('retired_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('lifecycle_revision',sa.Integer(),nullable=False),sa.Column('history_revision',sa.Integer(),nullable=False),
        sa.CheckConstraint('lifecycle_revision > 0 AND history_revision > 0'))
    op.create_index('ix_character_retirements_user_id','character_retirements',['user_id'])
    op.create_table('scoped_character_power_cache',
        sa.Column('actor_id',sa.UUID(),sa.ForeignKey('users.id'),primary_key=True),sa.Column('scope_key',sa.String(64),primary_key=True),
        sa.Column('character_id',sa.UUID(),sa.ForeignKey('game_characters.id')),
        sa.Column('lifecycle_revision',sa.Integer()),
        sa.Column('registration_id',sa.UUID(),sa.ForeignKey('game_account_registrations.id'),nullable=False),
        sa.Column('preview_version',sa.Integer()),sa.Column('credential_version',sa.Integer(),nullable=False),
        sa.Column('server_name',sa.String(64),nullable=False),sa.Column('character_name',sa.String(64),nullable=False),
        sa.Column('value',sa.String(64)),sa.Column('fetched_at',sa.DateTime(timezone=True)),
        sa.Column('checked_at',sa.DateTime(timezone=True)),sa.Column('status',sa.String(16),nullable=False),
        sa.Column('reason',sa.String(40)),sa.Column('generation',sa.Integer(),nullable=False),sa.Column('lease_expires_at',sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('unknown','available','unavailable','failed') AND generation >= 0"),
        sa.CheckConstraint('credential_version > 0'),
        sa.CheckConstraint('(character_id IS NOT NULL AND lifecycle_revision IS NOT NULL AND lifecycle_revision > 0 AND preview_version IS NULL) OR (character_id IS NULL AND lifecycle_revision IS NULL AND preview_version IS NOT NULL AND preview_version > 0)'))
    for name,lease in [('scoped_roster_cache',False),('scoped_roster_leases',True)]:
        columns=[sa.Column('user_id',sa.UUID(),sa.ForeignKey('users.id'),primary_key=True),
                 sa.Column('credential_version',sa.Integer(),primary_key=True),sa.Column('scope_key',sa.String(64),primary_key=True),
                 sa.Column('name',sa.String(64),primary_key=True)]
        if lease: columns += [sa.Column('generation',sa.Integer(),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('completed',sa.Boolean(),nullable=False)]
        columns += [sa.Column('roster',pg.JSONB(),nullable=lease),sa.Column('fetched_at',sa.DateTime(timezone=True),nullable=lease)]
        op.create_table(name,*columns)
        column='expires_at' if lease else 'fetched_at'
        op.create_index('ix_'+name+'_'+column,name,[column])


def downgrade():
    raise RuntimeError('Lifecycle downgrade requires a separate data recovery plan')
