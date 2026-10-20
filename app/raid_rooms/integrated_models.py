"""Integrated recruitment storage, not yet mounted by the application router.

Legacy F1 tables remain intact. Imported schedules require explicit review;
importing a finite interval never implies consent or creates time reservations.
"""
from sqlalchemy import (CheckConstraint, ForeignKey, ForeignKeyConstraint, Index,
                        Integer, String, UniqueConstraint, UUID, Date, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class RecruitmentRoom(Base):
    __tablename__ = 'recruitment_rooms'
    id = pk()
    leader_membership_id = mapped_column(UUID, nullable=False)
    title = mapped_column(String(60), nullable=False)
    scope = mapped_column(String(8), nullable=False)
    group_id = mapped_column(ForeignKey('groups.id'), nullable=True)
    app_capacity = mapped_column(Integer, nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    members_revision = mapped_column(Integer, nullable=False, default=1)
    plan_revision = mapped_column(Integer, nullable=False, default=1)
    migration_state = mapped_column(String(24), nullable=False)
    created_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint("scope IN ('public','group') AND (scope<>'group' OR group_id IS NOT NULL)"),
        CheckConstraint('char_length(title) BETWEEN 1 AND 60'),
        CheckConstraint('app_capacity IN (4,8) AND revision>=1 AND members_revision>=1 AND plan_revision>=1'),
        CheckConstraint("migration_state IN ('ready','legacy_review_required')"),
        ForeignKeyConstraint(['id', 'leader_membership_id'],
                             ['recruitment_memberships.room_id', 'recruitment_memberships.id'],
                             name='fk_recruitment_leader', use_alter=True,
                             deferrable=True, initially='DEFERRED'),
    )


class RecruitmentItem(Base):
    __tablename__ = 'recruitment_items'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    raid_id = mapped_column(String(64), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    created_at = stamp()
    __table_args__ = (UniqueConstraint('room_id', 'id'), UniqueConstraint('room_id', 'raid_id'),
                      UniqueConstraint('room_id', 'id', 'raid_id'),
                      CheckConstraint('revision>=1'))


class RecruitmentRound(Base):
    __tablename__ = 'recruitment_rounds'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    cycle_key = mapped_column(Date, nullable=False)
    difficulty_id = mapped_column(String(64), nullable=False)
    catalog_version = mapped_column(String(64), nullable=False)
    game_party_size = mapped_column(Integer, nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    state = mapped_column(String(24), nullable=False)
    created_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('room_id', 'item_id', 'id'),
        UniqueConstraint('room_id', 'item_id', 'id', 'cycle_key'),
        ForeignKeyConstraint(['room_id', 'item_id'], ['recruitment_items.room_id', 'recruitment_items.id']),
        CheckConstraint('EXTRACT(DOW FROM cycle_key)=3 AND game_party_size IN (4,8) AND revision>=1'),
        CheckConstraint("state IN ('active','completed','stopped_incomplete','legacy_ended')"),
    )


class RecruitmentMembership(Base):
    __tablename__ = 'recruitment_memberships'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    joined_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('room_id', 'id'), UniqueConstraint('room_id', 'id', 'user_id'),
        CheckConstraint('revision>=1'),
        Index('uq_recruitment_current_user', 'room_id', 'user_id', unique=True,
              postgresql_where=text('ended_at IS NULL')),
    )


class RecruitmentAssignment(Base):
    __tablename__ = 'recruitment_assignments'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    membership_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False)
    selected_role = mapped_column(String(8), nullable=False)
    party_no = mapped_column(Integer, nullable=False)
    slot_no = mapped_column(Integer, nullable=False)
    display = mapped_column(JSONB, nullable=False)
    build = mapped_column(JSONB(none_as_null=True), nullable=True)
    ownership_revision = mapped_column(Integer, nullable=False)
    lifecycle_revision = mapped_column(Integer, nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    state = mapped_column(String(24), nullable=False)
    joined_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('round_id', 'membership_id'),
        UniqueConstraint('room_id', 'item_id', 'round_id', 'id', 'user_id', 'character_id'),
        ForeignKeyConstraint(['room_id', 'item_id', 'round_id'],
                             ['recruitment_rounds.room_id', 'recruitment_rounds.item_id', 'recruitment_rounds.id']),
        ForeignKeyConstraint(['room_id', 'membership_id', 'user_id'],
                             ['recruitment_memberships.room_id', 'recruitment_memberships.id', 'recruitment_memberships.user_id']),
        CheckConstraint("selected_role IN ('dealer','support') AND party_no BETWEEN 1 AND 2 AND slot_no BETWEEN 1 AND 4"),
        CheckConstraint('revision>=1 AND ownership_revision>=1 AND lifecycle_revision>=1'),
        CheckConstraint("(state='active' AND ended_at IS NULL) OR (state IN ('completed','left','stopped_incomplete','legacy_ended') AND ended_at IS NOT NULL)"),
        Index('uq_recruitment_active_slot', 'round_id', 'party_no', 'slot_no', unique=True,
              postgresql_where=text("state='active'")),
    )


class RecruitmentSession(Base):
    __tablename__ = 'recruitment_sessions'
    id = pk()
    room_id = mapped_column(ForeignKey('recruitment_rooms.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    schedule_revision = mapped_column(Integer, nullable=False, default=1)
    state = mapped_column(String(24), nullable=False)
    starts_at = stamp(nullable=True)
    ends_at = stamp(nullable=True)
    created_at = stamp()
    __table_args__ = (
        UniqueConstraint('room_id', 'id'),
        CheckConstraint('revision>=1 AND schedule_revision>=1'),
        CheckConstraint("state IN ('unconfirmed','confirmed','finished','cancelled','legacy_review_required')"),
        CheckConstraint('(starts_at IS NULL AND ends_at IS NULL) OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at<ends_at)'),
        CheckConstraint("state<>'confirmed' OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND ends_at-starts_at<=interval '24 hours')"),
    )


class RecruitmentSegment(Base):
    __tablename__ = 'recruitment_segments'
    id = pk()
    room_id = mapped_column(UUID, nullable=False)
    session_id = mapped_column(UUID, nullable=False)
    item_id = mapped_column(UUID, nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    ordinal = mapped_column(Integer, nullable=False)
    duration_minutes = mapped_column(Integer, nullable=True)
    duration_source = mapped_column(String(24), nullable=False)
    starts_at = stamp(nullable=True)
    ends_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('session_id', 'ordinal'), UniqueConstraint('session_id', 'item_id'),
        ForeignKeyConstraint(['room_id', 'session_id'], ['recruitment_sessions.room_id', 'recruitment_sessions.id']),
        ForeignKeyConstraint(['room_id', 'item_id', 'round_id'],
                             ['recruitment_rounds.room_id', 'recruitment_rounds.item_id', 'recruitment_rounds.id']),
        CheckConstraint('ordinal>=1'),
        CheckConstraint("duration_source IN ('explicit','difficulty_default','legacy_review_required')"),
        CheckConstraint("(duration_minutes IS NOT NULL AND duration_minutes BETWEEN 10 AND 1440 AND mod(duration_minutes,5)=0) OR (duration_minutes IS NULL AND duration_source='legacy_review_required')"),
        CheckConstraint('(starts_at IS NULL AND ends_at IS NULL) OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at<ends_at)'),
        CheckConstraint("duration_minutes IS NULL OR starts_at IS NULL OR ends_at-starts_at=duration_minutes*interval '1 minute'"),
    )
