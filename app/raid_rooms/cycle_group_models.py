"""One group policy per actual cycle generation; never a room-wide authority."""
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, String, UUID
from sqlalchemy.orm import mapped_column
from app.auth.models import Base


class CycleGroupPolicy(Base):
    __tablename__ = 'recruitment_cycle_group_policies'
    cycle_id = mapped_column(UUID, primary_key=True)
    generation = mapped_column(Integer, primary_key=True)
    scope = mapped_column(String(16), nullable=False)
    group_id = mapped_column(ForeignKey('groups.id'), nullable=True, index=True)
    revision = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['cycle_id', 'generation'],
            ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        CheckConstraint('generation > 0 AND revision > 0'),
        CheckConstraint("(scope='public' AND group_id IS NULL) OR (scope='group' AND group_id IS NOT NULL)"),
    )
