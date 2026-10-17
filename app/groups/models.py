from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, UUID, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class Group(Base):
    __tablename__ = 'groups'
    id = pk()
    name = mapped_column(String(20), nullable=False)
    revision = mapped_column(Integer, nullable=False, default=1)
    members_revision = mapped_column(Integer, nullable=False, default=1)
    leader_membership_id = mapped_column(UUID, nullable=False)
    representative_character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False)
    representative_user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    representative_display = mapped_column(JSONB, nullable=False)
    created_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint('revision >= 1 AND members_revision >= 1', name='ck_group_revisions'),
        CheckConstraint('char_length(name) BETWEEN 1 AND 20', name='ck_group_name'),
        ForeignKeyConstraint(['id', 'leader_membership_id'],
                             ['group_memberships.group_id', 'group_memberships.id'],
                             name='fk_group_leader_member', use_alter=True,
                             deferrable=True, initially='DEFERRED'),
    )


class GroupMembership(Base):
    __tablename__ = 'group_memberships'
    id = pk()
    group_id = mapped_column(ForeignKey('groups.id'), nullable=False)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=True)
    display = mapped_column(JSONB(none_as_null=True), nullable=True)
    revision = mapped_column(Integer, nullable=False, default=1)
    joined_at = stamp()
    ended_at = stamp(nullable=True)
    __table_args__ = (
        Index('uq_active_group_member_user', 'group_id', 'user_id', unique=True,
              postgresql_where=text('ended_at IS NULL')),
        UniqueConstraint('group_id', 'id', name='uq_group_member_identity'),
        CheckConstraint('revision >= 1', name='ck_group_member_revision'),
    )


class GroupDirectoryHead(Base):
    __tablename__ = 'group_directory_head'
    id = mapped_column(Integer, primary_key=True)
    revision = mapped_column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint('id = 1 AND revision >= 1', name='ck_group_directory_head'),
    )
