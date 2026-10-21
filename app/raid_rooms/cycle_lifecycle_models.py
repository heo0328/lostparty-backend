"""Immutable target decisions; neither a legacy choice nor automatic consent."""
from sqlalchemy import CheckConstraint,ForeignKey,ForeignKeyConstraint,Integer,String,UUID,UniqueConstraint,Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,pk,stamp


class CycleDecision(Base):
    __tablename__='recruitment_cycle_decisions'
    id=pk()
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    user_id=mapped_column(ForeignKey('users.id'),nullable=False)
    command_id=mapped_column(UUID,nullable=False)
    kind=mapped_column(String(32),nullable=False)
    effective_at=stamp()
    evidence=mapped_column(JSONB,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
        UniqueConstraint('cycle_id','generation','command_id','kind'),
        CheckConstraint("kind IN ('declined','leadership_transferred','automatic_successor','future_empty_cancelled') AND jsonb_typeof(evidence)='object'"),
        Index('ix_cycle_decision_actor','user_id','cycle_id','effective_at','id'),
    )


class CycleScheduleGroup(Base):
    __tablename__='recruitment_cycle_schedule_groups'
    group_id=mapped_column(UUID,primary_key=True)
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','group_id'],['recruitment_schedule_groups.room_id','recruitment_schedule_groups.id']),
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
    )


CYCLE_LIFECYCLE_MODELS=(CycleDecision,CycleScheduleGroup)
