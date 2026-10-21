"""Exact proposal/vote ownership and append-only schedule editing evidence."""
from sqlalchemy import Integer,String,UUID,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,pk,stamp


class CycleProposal(Base):
    __tablename__='recruitment_cycle_proposals'
    proposal_id=mapped_column(UUID,primary_key=True)
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    content=mapped_column(JSONB,nullable=False)
    __table_args__=(
        UniqueConstraint('room_id','cycle_id','generation','proposal_id'),
        ForeignKeyConstraint(['room_id','proposal_id'],['recruitment_schedule_proposals.room_id','recruitment_schedule_proposals.id']),
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
        CheckConstraint("jsonb_typeof(content)='array'"),
    )


class CycleVote(Base):
    __tablename__='recruitment_cycle_votes'
    id=pk()
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    proposal_id=mapped_column(UUID,nullable=False)
    cycle_member_id=mapped_column(UUID,nullable=False)
    membership_id=mapped_column(UUID,nullable=False)
    user_id=mapped_column(UUID,nullable=False)
    member_revision=mapped_column(Integer,nullable=False)
    revision=mapped_column(Integer,nullable=False)
    command_id=mapped_column(UUID,nullable=False)
    response=mapped_column(String(8),nullable=False)
    effective_at=stamp()
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id','generation','proposal_id'],
            ['recruitment_cycle_proposals.room_id','recruitment_cycle_proposals.cycle_id','recruitment_cycle_proposals.generation','recruitment_cycle_proposals.proposal_id']),
        ForeignKeyConstraint(['room_id','cycle_id','generation','cycle_member_id','membership_id','user_id'],
            ['recruitment_cycle_members.room_id','recruitment_cycle_members.cycle_id','recruitment_cycle_members.generation','recruitment_cycle_members.id','recruitment_cycle_members.membership_id','recruitment_cycle_members.user_id']),
        UniqueConstraint('proposal_id','cycle_member_id','revision'),
        UniqueConstraint('proposal_id','user_id','command_id'),
        CheckConstraint("member_revision>=1 AND revision>=1 AND response IN ('accept','reject')"),
    )


class CycleScheduleEvent(Base):
    __tablename__='recruitment_cycle_schedule_events'
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
        CheckConstraint("kind IN ('groups_edited','initial_confirmed','proposal_created','proposal_applied','proposal_obsolete') AND jsonb_typeof(evidence)='object'"),
    )


class CycleAlternative(Base):
    __tablename__='recruitment_cycle_alternatives'
    alternative_id=mapped_column(UUID,primary_key=True)
    group_id=mapped_column(UUID,nullable=False)
    edition=mapped_column(Integer,nullable=False)
    client_key=mapped_column(String(64),nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['group_id','alternative_id'],['recruitment_schedule_alternatives.group_id','recruitment_schedule_alternatives.id']),
        UniqueConstraint('group_id','edition','client_key'),
        CheckConstraint('edition>=1'),
    )


CYCLE_PLANNING_MODELS=(CycleProposal,CycleVote,CycleScheduleEvent,CycleAlternative)
