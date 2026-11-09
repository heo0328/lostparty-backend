"""One current selection, immutable historical assignments and generation capability.

The caller owns its snapshot or serialized command transaction. Request capability
is never an authorization bypass; it is signed into new character contexts.
"""

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import UniqueConstraint
from sqlalchemy import Uuid

from sqlalchemy.orm import mapped_column

from app.auth.models import Base
from app.auth.models import pk
from app.auth.models import stamp

class Capability(Base):
    __tablename__ = 'roster_participation_capabilities'
    id = pk()
    cycle_id = mapped_column(Uuid, nullable=False)
    generation = mapped_column(Integer, nullable=False)
    created_at = stamp()
    __table_args__ = (ForeignKeyConstraint(['cycle_id', 'generation'],
        ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        UniqueConstraint('cycle_id', 'generation'))
