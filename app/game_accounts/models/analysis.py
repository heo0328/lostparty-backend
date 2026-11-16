from sqlalchemy import String, Integer, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class AnalysisFetch(Base):
    __tablename__ = 'character_analysis_fetch_leases'
    id = pk()
    actor_id = mapped_column(ForeignKey('users.id'), nullable=False)
    scope_digest = mapped_column(String(64), nullable=False)
    generation = mapped_column(Integer, nullable=False, default=1)
    state = mapped_column(String(16), nullable=False, default='running')
    expires_at = stamp(index=True)
    result = mapped_column(JSONB, nullable=True)
    __table_args__ = (CheckConstraint("state IN ('running','completed','failed') AND generation>0"),
                     Index('ix_analysis_fetch_scope', 'actor_id', 'scope_digest'))
