"""Internal member limit/usage revision foundation. No existing data rewrite."""
from alembic import op

revision = '0013_member_usage_limits'
down_revision = '0012_group_foundation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE member_usage_limits (
        user_id UUID PRIMARY KEY REFERENCES users(id),
        revision INTEGER NOT NULL,
        group_capacity INTEGER NOT NULL,
        joined_groups INTEGER NOT NULL,
        raid_rooms INTEGER NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT ck_member_usage_limits CHECK (
            revision >= 1 AND group_capacity >= 0 AND joined_groups >= 0 AND raid_rooms >= 0)
    )''')
    op.execute('''CREATE TABLE member_usage_heads (
        user_id UUID PRIMARY KEY REFERENCES users(id),
        revision INTEGER NOT NULL,
        CONSTRAINT ck_member_usage_head CHECK (revision >= 1)
    )''')
    op.execute('''CREATE TABLE member_usage_limit_audits (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id),
        revision INTEGER NOT NULL,
        before JSONB NOT NULL,
        after JSONB NOT NULL,
        authority VARCHAR(80) NOT NULL,
        reason VARCHAR(200) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_member_limit_audit_revision UNIQUE (user_id,revision),
        CONSTRAINT ck_member_limit_audit_revision CHECK (revision >= 2)
    )''')


def downgrade():
    raise RuntimeError('Preserve member limit history; use a forward correction')
