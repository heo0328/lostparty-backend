"""Explicit recovery resolution and immutable new-command audit; no legacy rewrites."""
from sqlalchemy import Integer, String, UUID, ForeignKey, ForeignKeyConstraint, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class LeadershipRecovery(Base):
    __tablename__ = 'recruitment_leadership_recovery'
    cycle_id = mapped_column(UUID, primary_key=True)
    generation = mapped_column(Integer, primary_key=True)
    state = mapped_column(String(24), nullable=False)
    reason = mapped_column(String(64), nullable=True)
    remaining_review_reasons = mapped_column(JSONB, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['cycle_id','generation'], ['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
        CheckConstraint("generation>=1 AND revision>=1 AND state IN ('active','pending_review','review_remaining','closed') AND jsonb_typeof(remaining_review_reasons)='array'"),
    )


class MembershipActionAudit(Base):
    __tablename__ = 'recruitment_membership_action_audit'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    actor_membership_id = mapped_column(ForeignKey('recruitment_memberships.id'), nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    command_id = mapped_column(UUID, nullable=False)
    action = mapped_column(String(32), nullable=False)
    evidence = mapped_column(JSONB, nullable=False)
    effective_at = stamp()
    __table_args__ = (
        UniqueConstraint('user_id','command_id'),
        CheckConstraint("action IN ('leave_target','leave_all','dissolve_led_targets','recover_leadership') AND jsonb_typeof(evidence)='object'"),
    )
