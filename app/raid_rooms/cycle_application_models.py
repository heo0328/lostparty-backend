"""V2-only application and schedule ownership. Legacy command rows stay intact."""
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, UUID, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class CycleApplication(Base):
    __tablename__='recruitment_cycle_applications'
    id=pk()
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    user_id=mapped_column(ForeignKey('users.id'),nullable=False)
    revision=mapped_column(Integer,nullable=False)
    selection=mapped_column(JSONB,nullable=False)
    targets=mapped_column(JSONB,nullable=False)
    session_ids=mapped_column(JSONB,nullable=False)
    display=mapped_column(JSONB,nullable=False)
    build=mapped_column(JSONB(none_as_null=True),nullable=True)
    origin_scope=mapped_column(String(8),nullable=False)
    origin_group_id=mapped_column(ForeignKey('groups.id'),nullable=True)
    state=mapped_column(String(16),nullable=False)
    created_at=stamp()
    expires_at=stamp()
    ended_at=stamp(nullable=True)
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
        CheckConstraint("revision>=1 AND jsonb_typeof(targets)='array' AND jsonb_typeof(session_ids)='array'"),
        CheckConstraint("origin_scope IN ('public','group') AND (origin_scope<>'group' OR origin_group_id IS NOT NULL)"),
        CheckConstraint("state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND expires_at>created_at"),
        CheckConstraint("(state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL)"),
        Index('uq_cycle_pending_application','cycle_id','generation','user_id',unique=True,postgresql_where=text("state='pending'")),
        Index('ix_cycle_own_application','user_id','cycle_id','created_at','id'),
    )


class CycleSession(Base):
    __tablename__='recruitment_cycle_sessions'
    session_id=mapped_column(ForeignKey('recruitment_sessions.id'),primary_key=True)
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    __table_args__=(
        UniqueConstraint('room_id','cycle_id','generation','session_id'),
        ForeignKeyConstraint(['room_id','cycle_id'],['recruitment_room_cycles.room_id','recruitment_room_cycles.id']),
        ForeignKeyConstraint(['room_id','session_id'],['recruitment_sessions.room_id','recruitment_sessions.id']),
        ForeignKeyConstraint(['cycle_id','generation'],['recruitment_cycle_generations.cycle_id','recruitment_cycle_generations.generation']),
    )


class CycleSessionSegment(Base):
    __tablename__='recruitment_cycle_session_segments'
    segment_id=mapped_column(UUID,primary_key=True)
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    session_id=mapped_column(UUID,nullable=False)
    item_id=mapped_column(UUID,nullable=False)
    round_id=mapped_column(UUID,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','segment_id','session_id','item_id','round_id'],
            ['recruitment_segments.room_id','recruitment_segments.id','recruitment_segments.session_id','recruitment_segments.item_id','recruitment_segments.round_id']),
        ForeignKeyConstraint(['room_id','cycle_id','generation','session_id'],
            ['recruitment_cycle_sessions.room_id','recruitment_cycle_sessions.cycle_id','recruitment_cycle_sessions.generation','recruitment_cycle_sessions.session_id']),
        ForeignKeyConstraint(['room_id','cycle_id','generation','round_id'],
            ['recruitment_cycle_rounds.room_id','recruitment_cycle_rounds.cycle_id','recruitment_cycle_rounds.generation','recruitment_cycle_rounds.round_id']),
    )


CYCLE_ADMISSION_MODELS=(CycleApplication,CycleSession,CycleSessionSegment)
