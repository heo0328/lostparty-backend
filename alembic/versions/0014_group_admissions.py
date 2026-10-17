"""Group request/code foundation; retain prior membership episodes."""
from alembic import op

revision = '0014_group_admissions'
down_revision = '0013_member_usage_limits'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE group_memberships DROP CONSTRAINT uq_group_member_user')
    op.execute('CREATE UNIQUE INDEX uq_active_group_member_user ON group_memberships(group_id,user_id) WHERE ended_at IS NULL')
    op.execute('''CREATE TABLE group_join_subjects (
        id UUID PRIMARY KEY, group_id UUID NOT NULL REFERENCES groups(id),
        user_id UUID NOT NULL REFERENCES users(id), revision INTEGER NOT NULL,
        application_count INTEGER NOT NULL, display JSONB, blocked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_group_join_subject UNIQUE(group_id,user_id),
        CONSTRAINT uq_group_join_subject_identity UNIQUE(group_id,id,user_id),
        CONSTRAINT ck_group_join_subject CHECK(revision >= 1 AND application_count >= 0)
    )''')
    op.execute('''CREATE TABLE group_join_relations (
        id UUID PRIMARY KEY, group_id UUID NOT NULL REFERENCES groups(id),
        subject_id UUID NOT NULL,
        target_user_id UUID NOT NULL REFERENCES users(id), issuer_user_id UUID NOT NULL REFERENCES users(id),
        issuer_membership_id UUID,
        kind VARCHAR(16) NOT NULL, state VARCHAR(24) NOT NULL, revision INTEGER NOT NULL,
        selection JSONB, display JSONB, created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ,
        CONSTRAINT fk_group_relation_subject FOREIGN KEY(group_id,subject_id,target_user_id) REFERENCES group_join_subjects(group_id,id,user_id),
        CONSTRAINT fk_group_relation_issuer FOREIGN KEY(group_id,issuer_membership_id) REFERENCES group_memberships(group_id,id),
        CONSTRAINT ck_group_relation_selection CHECK((kind = 'application' AND selection IS NOT NULL AND issuer_membership_id IS NULL AND issuer_user_id = target_user_id) OR (kind = 'invitation' AND selection IS NULL AND issuer_membership_id IS NOT NULL)),
        CONSTRAINT ck_group_join_relation CHECK(kind IN ('invitation','application') AND state IN ('pending','accepted','rejected','cancelled','expired','blocked','joined_by_code') AND revision >= 1),
        CONSTRAINT ck_group_relation_end CHECK(expires_at > created_at AND ((state = 'pending' AND ended_at IS NULL) OR (state <> 'pending' AND ended_at IS NOT NULL)))
    )''')
    op.execute("CREATE UNIQUE INDEX uq_group_pending_relation ON group_join_relations(group_id,target_user_id) WHERE state = 'pending'")
    op.execute('CREATE INDEX ix_group_relation_target ON group_join_relations(target_user_id,created_at)')
    op.execute('''CREATE TABLE group_join_codes (
        id UUID PRIMARY KEY, group_id UUID NOT NULL REFERENCES groups(id),
        revision INTEGER NOT NULL, digest VARCHAR(64) NOT NULL UNIQUE,
        key_id VARCHAR(64) NOT NULL, nonce BYTEA NOT NULL, ciphertext BYTEA NOT NULL,
        visible_to_members INTEGER NOT NULL, created_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ,
        CONSTRAINT ck_group_join_code CHECK(revision >= 1 AND visible_to_members IN (0,1))
    )''')
    op.execute('CREATE UNIQUE INDEX uq_group_active_join_code ON group_join_codes(group_id) WHERE revoked_at IS NULL')


def downgrade():
    raise RuntimeError('Preserve group request/code/member history; use a forward correction')
