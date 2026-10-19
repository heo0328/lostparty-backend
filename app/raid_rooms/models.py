from sqlalchemy import (CheckConstraint, Date, ForeignKey, ForeignKeyConstraint, Index,
                        Integer, String, UniqueConstraint, UUID, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class Room(Base):
    __tablename__ = 'raid_rooms'
    id = pk()
    round_id = mapped_column(UUID, nullable=False)
    leader_membership_id = mapped_column(UUID, nullable=False)
    title = mapped_column(String(60), nullable=False)
    scope = mapped_column(String(8), nullable=False)
    group_id = mapped_column(ForeignKey('groups.id'), nullable=True)
    creation_scope = mapped_column(String(8), nullable=False)
    creation_group_id = mapped_column(ForeignKey('groups.id'), nullable=True)
    admission_mode = mapped_column(String(16), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    members_revision = mapped_column(Integer, nullable=False, default=1)
    applications_revision = mapped_column(Integer, nullable=False, default=1)
    created_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint("(scope='public' AND group_id IS NULL) OR (scope='group' AND group_id IS NOT NULL)"),
        CheckConstraint("(creation_scope='public' AND creation_group_id IS NULL) OR (creation_scope='group' AND creation_group_id IS NOT NULL)"),
        CheckConstraint("admission_mode IN ('leader_only','direct_join') AND char_length(title) BETWEEN 1 AND 60"),
        CheckConstraint('revision>=1 AND members_revision>=1 AND applications_revision>=1'),
        ForeignKeyConstraint(['id', 'round_id'], ['raid_room_rounds.room_id', 'raid_room_rounds.id'],
            name='fk_room_current_round', use_alter=True, deferrable=True, initially='DEFERRED'),
        ForeignKeyConstraint(['id', 'leader_membership_id'], ['raid_room_memberships.room_id', 'raid_room_memberships.id'],
            name='fk_room_leader', use_alter=True, deferrable=True, initially='DEFERRED'),
    )


class Round(Base):
    __tablename__ = 'raid_room_rounds'
    id = pk()
    room_id = mapped_column(ForeignKey('raid_rooms.id'), nullable=False)
    raid_id = mapped_column(String(64), nullable=False)
    difficulty_id = mapped_column(String(64), nullable=False)
    catalog_version = mapped_column(String(64), nullable=False)
    cycle_key = mapped_column(Date, nullable=False)
    party_count = mapped_column(Integer, nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    starts_at = stamp()
    ends_at = stamp()
    created_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (UniqueConstraint('room_id', 'id'),
        CheckConstraint('revision>=1 AND party_count IN (1,2) AND starts_at<ends_at'),
        CheckConstraint('EXTRACT(DOW FROM cycle_key)=3'))


class Membership(Base):
    __tablename__ = 'raid_room_memberships'
    id = pk()
    room_id = mapped_column(ForeignKey('raid_rooms.id'), nullable=False)
    round_id = mapped_column(UUID, nullable=False)
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
    joined_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('room_id', 'id'),
        ForeignKeyConstraint(['room_id', 'round_id'], ['raid_room_rounds.room_id', 'raid_room_rounds.id']),
        CheckConstraint("selected_role IN ('dealer','support') AND party_no BETWEEN 1 AND 2 AND slot_no BETWEEN 1 AND 4"),
        CheckConstraint('revision>=1 AND ownership_revision>=1 AND lifecycle_revision>=1'),
        Index('uq_room_current_user', 'room_id', 'user_id', unique=True, postgresql_where=text('ended_at IS NULL')),
        Index('uq_room_current_slot', 'room_id', 'party_no', 'slot_no', unique=True, postgresql_where=text('ended_at IS NULL')),
        Index('ix_room_member_user', 'user_id', 'joined_at'),
    )


class Application(Base):
    __tablename__ = 'raid_room_applications'
    id = pk()
    room_id = mapped_column(ForeignKey('raid_rooms.id'), nullable=False)
    round_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    selection = mapped_column(JSONB, nullable=False)
    display = mapped_column(JSONB, nullable=False)
    state = mapped_column(String(16), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    created_at = stamp()
    expires_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(['room_id', 'round_id'], ['raid_room_rounds.room_id', 'raid_room_rounds.id']),
        CheckConstraint("state IN ('pending','accepted','rejected','withdrawn','expired','cancelled') AND revision>=1"),
        CheckConstraint("expires_at>created_at AND ((state='pending' AND ended_at IS NULL) OR (state<>'pending' AND ended_at IS NOT NULL))"),
        Index('uq_room_pending_application', 'room_id', 'user_id', unique=True, postgresql_where=text("state='pending'")),
    )


class DirectoryHead(Base):
    __tablename__ = 'raid_room_directory_head'
    id = mapped_column(Integer, primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint('id=1 AND revision>=1'),)


class MemberHead(Base):
    __tablename__ = 'raid_room_member_heads'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    membership_revision = mapped_column(Integer, nullable=False, default=1)
    application_revision = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint('membership_revision>=1 AND application_revision>=1'),)
