"""Two-cycle foundation. Shadow storage until the v2/worker cutover is complete.

Legacy graphs are immutable evidence. Unknown generations, authority, settings
and confirmations must not acquire executable defaults during forward migration.
"""
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String,
                        UniqueConstraint, UUID, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class RoomCycle(Base):
    __tablename__ = 'recruitment_room_cycles'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    cycle_key = mapped_column(Date, nullable=False)
    state = mapped_column(String(24), nullable=False)
    generation = mapped_column(Integer, nullable=True)
    revision = mapped_column(Integer, nullable=False)
    settings_revision = mapped_column(Integer, nullable=False)
    members_revision = mapped_column(Integer, nullable=False)
    plan_revision = mapped_column(Integer, nullable=False)
    settings_snapshot = mapped_column(JSONB(none_as_null=True), nullable=True)
    provenance = mapped_column(String(24), nullable=False)
    created_at = stamp()
    __table_args__ = (
        UniqueConstraint('room_id', 'cycle_key'),
        UniqueConstraint('room_id', 'cycle_key', 'id'),
        UniqueConstraint('room_id', 'id'),
        ForeignKeyConstraint(['id', 'generation'],
            ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation'],
            name='fk_room_cycle_generation', use_alter=True, deferrable=True, initially='DEFERRED'),
        CheckConstraint('EXTRACT(DOW FROM cycle_key)=3 AND revision>=1 AND settings_revision>=1 AND members_revision>=1 AND plan_revision>=1'),
        CheckConstraint("state IN ('open','closed','review_required') AND (generation IS NULL OR generation>=1)"),
        CheckConstraint("provenance IN ('explicit','legacy_unknown') AND (state='review_required' OR (generation IS NOT NULL AND provenance='explicit' AND settings_snapshot IS NOT NULL))"),
        Index('ix_recruitment_cycle_directory', 'cycle_key', 'state', 'room_id'),
    )


class CycleGeneration(Base):
    __tablename__ = 'recruitment_cycle_generations'
    cycle_id = mapped_column(ForeignKey('recruitment_room_cycles.id'), primary_key=True)
    generation = mapped_column(Integer, primary_key=True)
    state = mapped_column(String(24), nullable=False)
    leader_cycle_member_id = mapped_column(UUID, nullable=True)
    leadership_revision = mapped_column(Integer, nullable=False)
    next_join_order = mapped_column(BigInteger, nullable=True)
    opened_at = stamp()
    closed_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint('generation>=1 AND leadership_revision>=1 AND (next_join_order IS NULL OR next_join_order>=1)'),
        CheckConstraint("state IN ('open','completed','stopped','cancelled','review_required')"),
        CheckConstraint("(state='open' AND leader_cycle_member_id IS NOT NULL AND closed_at IS NULL) OR (state<>'open')"),
        CheckConstraint("state<>'cancelled' OR (leader_cycle_member_id IS NULL AND closed_at IS NOT NULL)"),
        ForeignKeyConstraint(['cycle_id', 'generation', 'leader_cycle_member_id'],
            ['recruitment_cycle_members.cycle_id', 'recruitment_cycle_members.generation', 'recruitment_cycle_members.id'],
            name='fk_cycle_generation_leader', use_alter=True, deferrable=True, initially='DEFERRED'),
    )


class CycleMember(Base):
    __tablename__ = 'recruitment_cycle_members'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=True)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    state = mapped_column(String(24), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    joined_order = mapped_column(BigInteger, nullable=True)
    joined_at = stamp(nullable=True)
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('cycle_id', 'generation', 'id'),
        UniqueConstraint('cycle_id', 'generation', 'joined_order'),
        UniqueConstraint('room_id', 'cycle_id', 'generation', 'id', 'membership_id', 'user_id'),
        ForeignKeyConstraint(['room_id', 'cycle_id'], ['recruitment_room_cycles.room_id', 'recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id', 'generation'], ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        ForeignKeyConstraint(['room_id', 'membership_id', 'user_id'], ['recruitment_memberships.room_id', 'recruitment_memberships.id', 'recruitment_memberships.user_id']),
        CheckConstraint('revision>=1 AND (generation IS NULL OR generation>=1) AND (joined_order IS NULL OR joined_order>=1)'),
        CheckConstraint("state IN ('participating','completed','stopped','cancelled','removed','review_required')"),
        CheckConstraint("state='review_required' OR (generation IS NOT NULL AND joined_order IS NOT NULL AND joined_at IS NOT NULL)"),
        CheckConstraint("state<>'participating' OR ended_at IS NULL"),
        CheckConstraint("state NOT IN ('cancelled','removed') OR ended_at IS NOT NULL"),
        Index('uq_recruitment_current_cycle_member', 'cycle_id', 'generation', 'membership_id', unique=True,
              postgresql_where=text("state <> 'cancelled' AND state <> 'removed'")),
        Index('uq_recruitment_unknown_cycle_member', 'cycle_id', 'membership_id', unique=True,
              postgresql_where=text('generation IS NULL')),
    )


class CycleRound(Base):
    """Exact old Round -> target ownership; nullable generation means review only."""
    __tablename__ = 'recruitment_cycle_rounds'
    round_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    cycle_key = mapped_column(Date, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=True)
    is_current = mapped_column(Boolean, nullable=False)
    __table_args__ = (
        UniqueConstraint('room_id', 'cycle_id', 'generation', 'round_id'),
        ForeignKeyConstraint(['room_id', 'item_id', 'round_id', 'cycle_key'], ['recruitment_rounds.room_id', 'recruitment_rounds.item_id', 'recruitment_rounds.id', 'recruitment_rounds.cycle_key']),
        ForeignKeyConstraint(['room_id', 'cycle_key', 'cycle_id'], ['recruitment_room_cycles.room_id', 'recruitment_room_cycles.cycle_key', 'recruitment_room_cycles.id']),
        ForeignKeyConstraint(['cycle_id', 'generation'], ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        CheckConstraint('(generation IS NULL OR generation>=1) AND (generation IS NOT NULL OR NOT is_current)'),
        Index('uq_recruitment_current_cycle_item', 'cycle_id', 'generation', 'item_id', unique=True,
              postgresql_where=text('is_current')),
    )


class CycleDirectoryHead(Base):
    __tablename__ = 'recruitment_cycle_directory_heads'
    cycle_key = mapped_column(Date, primary_key=True)
    revision = mapped_column(BigInteger, nullable=False)
    __table_args__ = (CheckConstraint('EXTRACT(DOW FROM cycle_key)=3 AND revision>=1'),)


class CycleAssignment(Base):
    __tablename__ = 'recruitment_cycle_assignments'
    assignment_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=False)
    cycle_member_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'assignment_id', 'membership_id', 'user_id', 'item_id', 'round_id'],
            ['recruitment_assignments.room_id', 'recruitment_assignments.id', 'recruitment_assignments.membership_id',
             'recruitment_assignments.user_id', 'recruitment_assignments.item_id', 'recruitment_assignments.round_id']),
        ForeignKeyConstraint(['room_id', 'cycle_id', 'generation', 'round_id'],
            ['recruitment_cycle_rounds.room_id', 'recruitment_cycle_rounds.cycle_id', 'recruitment_cycle_rounds.generation', 'recruitment_cycle_rounds.round_id']),
        ForeignKeyConstraint(['room_id', 'cycle_id', 'generation', 'cycle_member_id', 'membership_id', 'user_id'],
            ['recruitment_cycle_members.room_id', 'recruitment_cycle_members.cycle_id', 'recruitment_cycle_members.generation',
             'recruitment_cycle_members.id', 'recruitment_cycle_members.membership_id', 'recruitment_cycle_members.user_id']),
    )


class CycleSubmission(Base):
    __tablename__ = 'recruitment_cycle_submissions'
    cycle_member_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(UUID, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    revision = mapped_column(Integer, nullable=False)
    source_personal_revision = mapped_column(Integer, nullable=False)
    intervals = mapped_column(JSONB, nullable=False)
    normalized_intervals = mapped_column(JSONB, nullable=False)
    submitted_at = stamp()
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'cycle_id', 'generation', 'cycle_member_id', 'membership_id', 'user_id'],
            ['recruitment_cycle_members.room_id', 'recruitment_cycle_members.cycle_id', 'recruitment_cycle_members.generation', 'recruitment_cycle_members.id', 'recruitment_cycle_members.membership_id', 'recruitment_cycle_members.user_id']),
        CheckConstraint("revision>=1 AND source_personal_revision>=1 AND jsonb_typeof(intervals)='array' AND jsonb_typeof(normalized_intervals)='array'"),
    )


class CycleOpening(Base):
    """Generation-scoped events; old opening/auto-enrolment rows stay untouched."""
    __tablename__ = 'recruitment_cycle_openings'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=True)
    item_id = mapped_column(UUID, nullable=False)
    legacy_event_id = mapped_column(ForeignKey('recruitment_opening_events.id'), nullable=True, unique=True)
    command_id = mapped_column(UUID, nullable=True)
    mode = mapped_column(String(24), nullable=False)
    state = mapped_column(String(24), nullable=False)
    effective_at = stamp()
    evidence = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'cycle_id'], ['recruitment_room_cycles.room_id', 'recruitment_room_cycles.id']),
        ForeignKeyConstraint(['room_id', 'item_id'], ['recruitment_items.room_id', 'recruitment_items.id']),
        ForeignKeyConstraint(['cycle_id', 'generation'], ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        UniqueConstraint('cycle_id', 'generation', 'item_id', 'mode'),
        CheckConstraint("mode IN ('open','reopen','legacy_manual','legacy_scheduled_auto') AND state IN ('applied','cancelled','review_required')"),
        CheckConstraint("(state='review_required' AND legacy_event_id IS NOT NULL) OR (generation IS NOT NULL AND command_id IS NOT NULL AND legacy_event_id IS NULL AND mode IN ('open','reopen'))"),
        Index('uq_recruitment_cycle_opening', 'cycle_id', 'generation', 'item_id', unique=True,
              postgresql_where=text("state='applied'")),
    )


class ParticipationEvent(Base):
    __tablename__ = 'recruitment_participation_events'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    cycle_id = mapped_column(UUID, nullable=False)
    generation = mapped_column(Integer, nullable=False)
    cycle_member_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    command_id = mapped_column(UUID, nullable=False)
    action = mapped_column(String(24), nullable=False)
    member_revision = mapped_column(Integer, nullable=False)
    effective_at = stamp()
    evidence = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'cycle_id', 'generation', 'cycle_member_id', 'membership_id', 'user_id'],
            ['recruitment_cycle_members.room_id', 'recruitment_cycle_members.cycle_id', 'recruitment_cycle_members.generation', 'recruitment_cycle_members.id', 'recruitment_cycle_members.membership_id', 'recruitment_cycle_members.user_id']),
        UniqueConstraint('cycle_member_id', 'member_revision'),
        UniqueConstraint('cycle_member_id', 'command_id', 'action'),
        CheckConstraint("member_revision>=1 AND action IN ('joined','cancelled','removed','completed','stopped','character_changed') AND jsonb_typeof(evidence)='object'"),
    )


class LegacyCycleEvidence(Base):
    """Classification only; never treated as a verified consent/authority source."""
    __tablename__ = 'recruitment_legacy_cycle_evidence'
    source_kind = mapped_column(String(24), primary_key=True)
    source_id = mapped_column(UUID, primary_key=True)
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    cycle_id = mapped_column(UUID, nullable=True)
    reason = mapped_column(String(64), nullable=False)
    evidence = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'cycle_id'], ['recruitment_room_cycles.room_id', 'recruitment_room_cycles.id']),
        CheckConstraint("source_kind IN ('assignment','session','application','submission','proposal','resume','choice') AND jsonb_typeof(evidence)='object'"),
    )


CYCLE_MODELS = (RoomCycle, CycleGeneration, CycleMember, CycleRound, CycleAssignment,
                CycleDirectoryHead, CycleSubmission, CycleOpening,
                ParticipationEvent, LegacyCycleEvidence)
