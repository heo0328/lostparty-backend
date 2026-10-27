"""Immutable current-cycle completion/closure and resume source evidence."""
from sqlalchemy import CheckConstraint,ForeignKeyConstraint,ForeignKey,Integer,String,UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,pk,stamp


class CycleOutcome(Base):
    __tablename__='recruitment_cycle_outcomes'
    id=pk()
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    actor_id=mapped_column(ForeignKey('users.id'),nullable=False)
    command_id=mapped_column(UUID,nullable=False)
    kind=mapped_column(String(32),nullable=False)
    effective_at=stamp()
    evidence=mapped_column(JSONB,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
        CheckConstraint("kind IN ('personal_completion','complete_item','close_weekly','resume_applied') AND jsonb_typeof(evidence)='object'"),
    )


class CycleResume(Base):
    __tablename__='recruitment_cycle_resumes'
    proposal_id=mapped_column(UUID,primary_key=True)
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    content=mapped_column(JSONB,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id','generation','proposal_id'],['recruitment_cycle_proposals.room_id','recruitment_cycle_proposals.cycle_id','recruitment_cycle_proposals.generation','recruitment_cycle_proposals.proposal_id']),
        CheckConstraint("jsonb_typeof(content)='object'"),
    )


CYCLE_OUTCOME_MODELS=(CycleOutcome,CycleResume)
