"""Immutable actor-owned projection corrections, never room outcome rewrites."""
from sqlalchemy import CheckConstraint
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base
from app.auth.models import pk
from app.auth.models import stamp

class CompletionCorrection(Base):
    __tablename__='raid_completion_corrections'
    id=pk()
    user_id=mapped_column(ForeignKey('users.id'),nullable=False)
    character_id=mapped_column(ForeignKey('game_characters.id'),nullable=False)
    raid_id=mapped_column(String(64),nullable=False)
    cycle_key=mapped_column(Date,nullable=False)
    command_id=mapped_column(UUID,nullable=False)
    before_revision=mapped_column(Integer,nullable=False)
    after_revision=mapped_column(Integer,nullable=False)
    sources=mapped_column(JSONB,nullable=False)
    effective_at=stamp()
    __table_args__=(CheckConstraint("before_revision>=1 AND after_revision=before_revision+1 AND jsonb_typeof(sources)='array' AND EXTRACT(DOW FROM cycle_key)=3"),)
