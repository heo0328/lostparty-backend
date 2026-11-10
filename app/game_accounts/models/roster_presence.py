"""Owned-roster observations, not proof of deletion, rename or transfer.

Only reconcile of a validated owned observation records these transitions. The
revision chain permits an existing seat to survive *only* this cause; it is not
a general lifecycle/ownership bypass. Callers own the mutation lock/transaction.
"""

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import mapped_column

from app.auth.models import Base
from app.auth.models import pk
from app.auth.models import stamp

class RosterTransition(Base):
    __tablename__ = 'character_roster_transitions'
    id = pk()
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False, index=True)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    owner_id = mapped_column(ForeignKey('users.id'), nullable=False)
    ownership_revision = mapped_column(Integer, nullable=False)
    from_revision = mapped_column(Integer, nullable=False)
    to_revision = mapped_column(Integer, nullable=False)
    state = mapped_column(String(16), nullable=False)
    source_usable = mapped_column(Boolean, nullable=False)
    observed_at = stamp()
    __table_args__ = (
        UniqueConstraint('character_id', 'ownership_revision', 'to_revision'),
        CheckConstraint("state IN ('missing','present') AND from_revision>0 AND to_revision>=from_revision AND ownership_revision>0"),
    )

class RosterRoomRecovery(Base):
    __tablename__ = 'roster_participation_recoveries'
    id = pk()
    cycle_id = mapped_column(ForeignKey('recruitment_room_cycles.id'), nullable=False)
    generation = mapped_column(Integer, nullable=False)
    evidence = mapped_column(JSONB, nullable=False)
    observed_at = stamp()
    __table_args__ = (
        ForeignKeyConstraint(['cycle_id', 'generation'],
            ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        CheckConstraint("generation>0 AND jsonb_typeof(evidence)='object'"),
    )
