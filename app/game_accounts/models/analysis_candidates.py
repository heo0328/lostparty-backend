"""Owner-generation policy facts; independent of registrations and command TTL."""
from sqlalchemy import String, Integer, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp

class CandidatePolicy(Base):
    __tablename__ = 'analysis_candidate_policies'
    id = pk()
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    ownership_revision = mapped_column(Integer, nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    baseline = mapped_column(String(16), nullable=False)
    __table_args__ = (UniqueConstraint('user_id','account_id','ownership_revision'),
                      CheckConstraint("revision>0 AND ownership_revision>0 AND baseline IN ('legacy','observed')"),)

class AnalysisCandidate(Base):
    __tablename__ = 'analysis_candidates'
    id = pk()
    policy_id = mapped_column(ForeignKey('analysis_candidate_policies.id'), nullable=False, index=True)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False)
    below_threshold = mapped_column(Boolean, nullable=False, default=False)
    legacy = mapped_column(Boolean, nullable=False, default=False)
    excluded = mapped_column(Boolean, nullable=False, default=False)
    reason = mapped_column(String(32), nullable=True)
    state = mapped_column(String(16), nullable=False, default='pending')
    generation = mapped_column(Integer, nullable=False, default=1)
    command_id = mapped_column(UUID, nullable=True)
    command_body = mapped_column(JSONB, nullable=True)
    lease_until = stamp(nullable=True)
    last_error = mapped_column(JSONB, nullable=True)
    completed_at = stamp(nullable=True)
    completed_command_id = mapped_column(UUID, nullable=True)
    __table_args__ = (UniqueConstraint('policy_id','character_id'),
        CheckConstraint("generation>0 AND state IN ('pending','running','succeeded','blocked')"),)
