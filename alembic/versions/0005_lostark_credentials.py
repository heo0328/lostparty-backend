"""Member credentials and member/version scoped provider cache; preserve old data."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0005_lostark_credentials'
down_revision = '0004_member_settings'
branch_labels = depends_on = None


def upgrade():
    op.create_table('lostark_credentials',
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ciphertext', sa.LargeBinary(), nullable=True),
        sa.Column('nonce', sa.LargeBinary(), nullable=True),
        sa.Column('key_id', sa.String(64), nullable=True),
        sa.Column('fingerprint', sa.String(64), nullable=True),
        sa.CheckConstraint('version >= 1'),
        sa.CheckConstraint('(ciphertext IS NULL AND nonce IS NULL AND key_id IS NULL AND fingerprint IS NULL) OR '
          '(ciphertext IS NOT NULL AND nonce IS NOT NULL AND key_id IS NOT NULL AND fingerprint IS NOT NULL AND octet_length(nonce) = 12)'))
    for name, lease in [('member_lostark_cache', False), ('member_lostark_fetch_leases', True)]:
        columns = [sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), primary_key=True),
                   sa.Column('credential_version', sa.Integer(), primary_key=True),
                   sa.Column('name', sa.String(64), primary_key=True)]
        if lease:
            columns += [sa.Column('generation', sa.Integer(), nullable=False),
                        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
                        sa.Column('completed', sa.Boolean(), nullable=False)]
        columns += [sa.Column('roster', postgresql.JSONB(), nullable=lease),
                    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=lease)]
        op.create_table(name, *columns)
        column = 'expires_at' if lease else 'fetched_at'
        op.create_index('ix_' + name + '_' + column, name, [column])
    op.add_column('character_power_cache', sa.Column('credential_version', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('character_power_cache', 'credential_version')
    op.drop_table('member_lostark_fetch_leases')
    op.drop_table('member_lostark_cache')
    op.drop_table('lostark_credentials')
