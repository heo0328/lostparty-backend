from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, LargeBinary, UniqueConstraint, ForeignKeyConstraint, UUID, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class GroupJoinSubject(Base):
    """Stable group-scoped handle, counter and block history; never a public user ID."""
    __tablename__ = 'group_join_subjects'
    id = pk()
    group_id = mapped_column(ForeignKey('groups.id'), nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    application_count = mapped_column(Integer, nullable=False, default=0)
    display = mapped_column(JSONB(none_as_null=True), nullable=True)
    blocked_at = stamp(nullable=True)
    created_at = stamp()
    updated_at = stamp()
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_join_subject'),
        UniqueConstraint('group_id', 'id', 'user_id', name='uq_group_join_subject_identity'),
        CheckConstraint('revision >= 1 AND application_count >= 0', name='ck_group_join_subject'),
    )


class GroupJoinRelation(Base):
    __tablename__ = 'group_join_relations'
    id = pk()
    group_id = mapped_column(ForeignKey('groups.id'), nullable=False)
    subject_id = mapped_column(UUID, nullable=False)
    target_user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    issuer_user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    issuer_membership_id = mapped_column(UUID, nullable=True)
    kind = mapped_column(String(16), nullable=False)
    state = mapped_column(String(24), nullable=False, default='pending')
    revision = mapped_column(Integer, nullable=False, default=1)
    selection = mapped_column(JSONB(none_as_null=True), nullable=True)
    display = mapped_column(JSONB(none_as_null=True), nullable=True)
    created_at = stamp()
    expires_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['group_id', 'subject_id', 'target_user_id'],
            ['group_join_subjects.group_id', 'group_join_subjects.id', 'group_join_subjects.user_id'],
            name='fk_group_relation_subject'),
        ForeignKeyConstraint(['group_id', 'issuer_membership_id'],
            ['group_memberships.group_id', 'group_memberships.id'], name='fk_group_relation_issuer'),
        CheckConstraint("(kind = 'application' AND selection IS NOT NULL AND issuer_membership_id IS NULL AND issuer_user_id = target_user_id) OR (kind = 'invitation' AND selection IS NULL AND issuer_membership_id IS NOT NULL)", name='ck_group_relation_selection'),
        Index('uq_group_pending_relation', 'group_id', 'target_user_id', unique=True,
              postgresql_where=text("state = 'pending'")),
        Index('ix_group_relation_target', 'target_user_id', 'created_at'),
        CheckConstraint("kind IN ('invitation','application') AND state IN ('pending','accepted','rejected','cancelled','expired','blocked','joined_by_code') AND revision >= 1", name='ck_group_join_relation'),
        CheckConstraint("expires_at > created_at AND ((state = 'pending' AND ended_at IS NULL) OR (state <> 'pending' AND ended_at IS NOT NULL))", name='ck_group_relation_end'),
    )


class GroupJoinCode(Base):
    __tablename__ = 'group_join_codes'
    id = pk()
    group_id = mapped_column(ForeignKey('groups.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    digest = mapped_column(String(64), nullable=False, unique=True)
    key_id = mapped_column(String(64), nullable=False)
    nonce = mapped_column(LargeBinary, nullable=False)
    ciphertext = mapped_column(LargeBinary, nullable=False)
    visible_to_members = mapped_column(Integer, nullable=False, default=0)
    created_at = stamp()
    revoked_at = stamp(nullable=True)
    __table_args__ = (
        Index('uq_group_active_join_code', 'group_id', unique=True, postgresql_where=text('revoked_at IS NULL')),
        CheckConstraint('revision >= 1 AND visible_to_members IN (0,1)', name='ck_group_join_code'),
    )
