"""Immutable weekly-resume source set and explicit membership-generation votes."""
from sqlalchemy import ForeignKey,Integer,String,CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,pk,stamp


class ResumeProposal(Base):
    __tablename__='recruitment_resume_proposals'
    id=pk()
    room_id=mapped_column(ForeignKey('recruitment_rooms.id'),nullable=False)
    creator_membership_id=mapped_column(ForeignKey('recruitment_memberships.id'),nullable=False)
    revision=mapped_column(Integer,nullable=False)
    created_from_plan_revision=mapped_column(Integer,nullable=False)
    state=mapped_column(String(16),nullable=False)
    content=mapped_column(JSONB,nullable=False)
    responses=mapped_column(JSONB,nullable=False)
    created_at=stamp()
    __table_args__=(CheckConstraint("revision>=1 AND created_from_plan_revision>=1 AND state IN ('pending','applied','obsolete')"),)
