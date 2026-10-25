"""Additive beta data; legacy rows and their ORM/ACK shapes stay unchanged."""
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, Sequence, String, UniqueConstraint, UUID, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp

recruitment_number = Sequence('recruitment_beta_number_seq', start=1, maxvalue=9007199254740991)


class BetaSchedule(Base):
    __tablename__ = 'recruitment_beta_schedules'
    cycle_id = mapped_column(ForeignKey('recruitment_room_cycles.id'), primary_key=True)
    generation = mapped_column(Integer, nullable=False)
    session_id = mapped_column(ForeignKey('recruitment_sessions.id'), nullable=False, unique=True)
    revision = mapped_column(Integer, nullable=False)
    base_starts_at = stamp()
    base_ends_at = stamp()
    early_enabled = mapped_column(Boolean, nullable=False)
    early_additional_members = mapped_column(Integer, nullable=True)
    confirmation_kind = mapped_column(String(24), nullable=True)
    needs_review = mapped_column(Boolean, nullable=False)
    number = mapped_column(BigInteger, recruitment_number, nullable=False, unique=True)
    password = mapped_column(String(5), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['cycle_id', 'generation'], ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        CheckConstraint('revision>=1 AND base_starts_at<base_ends_at AND base_ends_at-base_starts_at<=interval \'24 hours\''),
        CheckConstraint('(early_enabled AND early_additional_members BETWEEN 1 AND 7) OR (NOT early_enabled AND early_additional_members IS NULL)'),
        CheckConstraint("confirmation_kind IS NULL OR confirmation_kind IN ('early_confirmed','base_confirmed','proposal_confirmed')"),
        CheckConstraint('NOT needs_review OR confirmation_kind IS NULL'),
        CheckConstraint("number BETWEEN 1 AND 9007199254740991 AND password ~ '^[0-9]{5}$'"),
        Index('ix_beta_schedule_due', 'base_starts_at', postgresql_where=text('confirmation_kind IS NULL AND NOT needs_review')),
    )


class BetaAvailabilityCopy(Base):
    __tablename__ = 'recruitment_beta_availability_copies'
    cycle_member_id = mapped_column(ForeignKey('recruitment_cycle_members.id'), primary_key=True)
    state = mapped_column(String(16), nullable=False)
    source_personal_version = mapped_column(Integer, nullable=False)
    copied_at = stamp()
    __table_args__ = (CheckConstraint("state IN ('unset','configured') AND source_personal_version>=1"),)


class BetaApplicationMemo(Base):
    __tablename__ = 'recruitment_beta_application_memos'
    application_id = mapped_column(ForeignKey('recruitment_cycle_applications.id'), primary_key=True)
    memo = mapped_column(String(20), nullable=True)
    promise_revision = mapped_column(Integer, nullable=True)
    __table_args__ = (CheckConstraint('promise_revision IS NULL OR promise_revision>=1'),)


class BetaPromiseReservation(Base):
    __tablename__ = 'recruitment_beta_promise_reservations'
    reservation_id = mapped_column(ForeignKey('recruitment_reservations.id'), primary_key=True)
    cycle_id = mapped_column(ForeignKey('recruitment_room_cycles.id'), nullable=False)
    generation = mapped_column(Integer, nullable=False)
    cycle_member_id = mapped_column(ForeignKey('recruitment_cycle_members.id'), nullable=False)
    __table_args__ = (ForeignKeyConstraint(['cycle_id', 'generation', 'cycle_member_id'], ['recruitment_cycle_members.cycle_id', 'recruitment_cycle_members.generation', 'recruitment_cycle_members.id']),)


class ApplicationMessagePresets(Base):
    __tablename__ = 'member_application_message_presets'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    version = mapped_column(Integer, nullable=False)
    items = mapped_column(JSONB, nullable=False)
    saved_at = stamp(nullable=True)
    __table_args__ = (CheckConstraint("version>=1 AND jsonb_typeof(items)='array' AND jsonb_array_length(items)<=5"),)


BETA_MODELS = (BetaSchedule, BetaAvailabilityCopy, BetaApplicationMemo, BetaPromiseReservation, ApplicationMessagePresets)
