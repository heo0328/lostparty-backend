"""Exact integrated assignment ownership of an existing weekly ledger entry."""
from sqlalchemy import Date, ForeignKeyConstraint, String, UniqueConstraint, UUID
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class WeeklyOccupancy(Base):
    __tablename__ = 'recruitment_weekly_occupancies'
    user_id = mapped_column(UUID, primary_key=True)
    character_id = mapped_column(UUID, primary_key=True)
    raid_id = mapped_column(String(64), primary_key=True)
    cycle_key = mapped_column(Date, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    assignment_id = mapped_column(UUID, nullable=False)
    joined_at = stamp()
    __table_args__ = (
        UniqueConstraint('assignment_id'),
        ForeignKeyConstraint(['user_id','character_id','raid_id','cycle_key'],
            ['raid_weekly_states.user_id','raid_weekly_states.character_id','raid_weekly_states.raid_id','raid_weekly_states.cycle_key']),
        ForeignKeyConstraint(['room_id','item_id','round_id','assignment_id','user_id','character_id'],
            ['recruitment_assignments.room_id','recruitment_assignments.item_id','recruitment_assignments.round_id',
             'recruitment_assignments.id','recruitment_assignments.user_id','recruitment_assignments.character_id']),
        ForeignKeyConstraint(['room_id','item_id','raid_id'],
            ['recruitment_items.room_id','recruitment_items.id','recruitment_items.raid_id']),
        ForeignKeyConstraint(['room_id','item_id','round_id','cycle_key'],
            ['recruitment_rounds.room_id','recruitment_rounds.item_id','recruitment_rounds.id','recruitment_rounds.cycle_key']),
    )
