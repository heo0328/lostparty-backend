from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class MemberUsageLimits(Base):
    __tablename__ = 'member_usage_limits'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    group_capacity = mapped_column(Integer, nullable=False)
    joined_groups = mapped_column(Integer, nullable=False)
    raid_rooms = mapped_column(Integer, nullable=False)
    updated_at = stamp()
    __table_args__ = (CheckConstraint(
        'revision >= 1 AND group_capacity >= 0 AND joined_groups >= 0 AND raid_rooms >= 0',
        name='ck_member_usage_limits'),)


class MemberUsageHead(Base):
    __tablename__ = 'member_usage_heads'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_member_usage_head'),)


class MemberUsageLimitAudit(Base):
    __tablename__ = 'member_usage_limit_audits'
    id = pk()
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    before = mapped_column(JSONB, nullable=False)
    after = mapped_column(JSONB, nullable=False)
    authority = mapped_column(String(80), nullable=False)
    reason = mapped_column(String(200), nullable=False)
    created_at = stamp()
    __table_args__ = (
        UniqueConstraint('user_id', 'revision', name='uq_member_limit_audit_revision'),
        CheckConstraint('revision >= 2', name='ck_member_limit_audit_revision'),
    )
