"""Latest observed, successfully stored role power. Never a provider assertion.

Caller owns game-mutations lock and transaction. The public P1 head/response is
unchanged: null/failure can coexist with a retained, versioned success snapshot.
"""

from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UUID

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import mapped_column

from app.auth.models import Base
from app.auth.models import stamp

class RolePowerSuccess(Base):
    __tablename__ = 'character_role_power_successes'
    user_id = mapped_column(UUID, primary_key=True)
    character_id = mapped_column(UUID, primary_key=True)
    ownership_revision = mapped_column(Integer, primary_key=True)
    role = mapped_column(String(16), primary_key=True)
    power_revision = mapped_column(Integer, nullable=False)
    combat_power = mapped_column(String(32), nullable=False)
    observed_at = stamp()
    source_summary_version = mapped_column(Integer, nullable=False)
    source_saved_at = stamp()
    source_summary = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'character_id', 'ownership_revision', 'role'],
                             ['character_role_summaries.user_id', 'character_role_summaries.character_id',
                              'character_role_summaries.ownership_revision', 'character_role_summaries.role'], ondelete='CASCADE'),
        CheckConstraint("ownership_revision>=1 AND power_revision>=2 AND source_summary_version>=1 AND role IN ('dealer','support')"),
        CheckConstraint("combat_power ~ '^[0-9]+([.][0-9]+)?$'"),
        CheckConstraint("jsonb_typeof(source_summary)='object'"),
    )
