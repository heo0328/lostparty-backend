from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UUID
from sqlalchemy.orm import mapped_column

from app.auth.models import Base, stamp


class WeeklyState(Base):
    __tablename__ = 'raid_weekly_states'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    character_id = mapped_column(ForeignKey('game_characters.id'), primary_key=True)
    raid_id = mapped_column(String(64), primary_key=True)
    cycle_key = mapped_column(Date, primary_key=True)
    revision = mapped_column(Integer, nullable=False, default=1)
    manual_completed_at = stamp(nullable=True)
    manual_difficulty_id = mapped_column(String(64), nullable=True)
    party_completed_at = stamp(nullable=True)
    completed_party_id = mapped_column(UUID, nullable=True)
    party_difficulty_id = mapped_column(String(64), nullable=True)
    active_party_id = mapped_column(UUID, nullable=True)
    active_difficulty_id = mapped_column(String(64), nullable=True)
    joined_at = stamp(nullable=True)
    updated_at = stamp()
    __table_args__ = (
        CheckConstraint('revision >= 1', name='ck_weekly_revision'),
        CheckConstraint('EXTRACT(DOW FROM cycle_key) = 3', name='ck_weekly_wednesday'),
        CheckConstraint('manual_completed_at IS NOT NULL OR manual_difficulty_id IS NULL',
                        name='ck_weekly_manual'),
        CheckConstraint('''(party_completed_at IS NULL AND completed_party_id IS NULL AND party_difficulty_id IS NULL)
                        OR (party_completed_at IS NOT NULL AND completed_party_id IS NOT NULL AND party_difficulty_id IS NOT NULL)''',
                        name='ck_weekly_party_completion'),
        CheckConstraint('''(active_party_id IS NULL AND active_difficulty_id IS NULL AND joined_at IS NULL)
                        OR (active_party_id IS NOT NULL AND active_difficulty_id IS NOT NULL AND joined_at IS NOT NULL)''',
                        name='ck_weekly_participation'),
        CheckConstraint('active_party_id IS NULL OR (manual_completed_at IS NULL AND party_completed_at IS NULL)',
                        name='ck_weekly_completion_occupancy'),
    )
