"""Persistent equipment control and product ownership disputes, separate from V1."""
from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class AccountHead(Base):
    __tablename__ = 'ownership_dispute_heads'
    account_id = mapped_column(ForeignKey('game_accounts.id'), primary_key=True)
    generation = mapped_column(Integer, nullable=False, default=1)
    sequence = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (CheckConstraint('generation >= 1 AND sequence >= 0'),)


class MemberHead(Base):
    __tablename__ = 'ownership_member_heads'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    proof_revision = mapped_column(Integer, nullable=False, default=1)
    dispute_revision = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint('proof_revision >= 1 AND dispute_revision >= 1'),)


class Proof(Base):
    __tablename__ = 'ownership_control_proofs'
    id = pk()
    actor_id = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    purpose = mapped_column(String(16), nullable=False)
    source = mapped_column(String(24), nullable=False)
    registration_id = mapped_column(ForeignKey('game_account_registrations.id'), nullable=True)
    source_registration_id = mapped_column(ForeignKey('game_account_registrations.id'), nullable=True)
    dispute_id = mapped_column(ForeignKey('ownership_disputes.id', use_alter=True, name='fk_proof_dispute'), nullable=True)
    candidate_id = mapped_column(ForeignKey('game_accounts.id'), nullable=True)
    lookup_name = mapped_column(String(64), nullable=False)
    version = mapped_column(Integer, nullable=False, default=1)
    status = mapped_column(String(16), nullable=False, default='pending')
    outcome = mapped_column(String(24), nullable=False, default='none')
    result_code = mapped_column(String(64), nullable=True)
    identity_snapshot = mapped_column(JSONB, nullable=False)
    baseline = mapped_column(JSONB, nullable=True)
    slots = mapped_column(JSONB, nullable=False)
    created_at = stamp()
    expires_at = stamp(index=True)
    ended_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint("purpose IN ('claim','defense') AND source IN ('direct_input','registration','dispute_defense')"),
        CheckConstraint("status IN ('pending','passed','expired','cancelled','invalidated') AND outcome IN ('none','verified','dispute_opened','defended','blocked') AND version >= 1"),
        CheckConstraint("expires_at > created_at AND ((status='pending' AND ended_at IS NULL) OR (status<>'pending' AND ended_at IS NOT NULL))"),
    )


class Dispute(Base):
    __tablename__ = 'ownership_disputes'
    id = pk()
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False, index=True)
    owner_id = mapped_column(ForeignKey('users.id'), nullable=False)
    challenger_id = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    ownership_revision = mapped_column(Integer, nullable=False)
    generation = mapped_column(Integer, nullable=False)
    sequence = mapped_column(Integer, nullable=False)
    slot = mapped_column(Integer, nullable=False)
    proof_id = mapped_column(ForeignKey('ownership_control_proofs.id'), nullable=False, unique=True)
    version = mapped_column(Integer, nullable=False, default=1)
    state = mapped_column(String(24), nullable=False, default='defending')
    reason = mapped_column(String(64), nullable=True)
    started_at = stamp()
    deadline = stamp(index=True)
    resolved_at = stamp(nullable=True)
    next_retry_at = stamp(nullable=True)
    lease_until = stamp(nullable=True)
    lease_generation = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint('slot BETWEEN 1 AND 3 AND ownership_revision >= 1 AND generation >= 1 AND sequence >= 1 AND version >= 1 AND lease_generation >= 0 AND owner_id <> challenger_id'),
        CheckConstraint("state IN ('defending','defended','transferred','cancelled','invalidated','review_required')"),
        CheckConstraint("deadline = started_at + interval '24 hours' AND ((state IN ('defending','review_required') AND resolved_at IS NULL) OR (state NOT IN ('defending','review_required') AND resolved_at IS NOT NULL))"),
        UniqueConstraint('account_id', 'sequence'),
        Index('uq_dispute_live_slot', 'account_id', 'slot', unique=True, postgresql_where=text("state IN ('defending','review_required')")),
        Index('uq_dispute_live_actor', 'account_id', 'challenger_id', unique=True, postgresql_where=text("state IN ('defending','review_required')")),
    )


class Event(Base):
    __tablename__ = 'ownership_dispute_events'
    id = pk()
    dispute_id = mapped_column(ForeignKey('ownership_disputes.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    kind = mapped_column(String(64), nullable=False)
    created_at = stamp()
    __table_args__ = (UniqueConstraint('dispute_id', 'revision'), CheckConstraint('revision >= 1'),)
