"""Additive group metadata: legacy Group/Subject mappings remain DB0023-safe."""
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, UUID, CheckConstraint
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class GroupActivityHead(Base):
    __tablename__ = 'group_activity_heads'
    group_id = mapped_column(ForeignKey('groups.id'), primary_key=True)
    last_activity_at = stamp()


class SubjectCharacterReference(Base):
    __tablename__ = 'group_subject_character_references'
    subject_id = mapped_column(UUID, primary_key=True)
    group_id = mapped_column(UUID, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False)
    ownership_revision = mapped_column(Integer, nullable=False)
    lifecycle_revision = mapped_column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['group_id', 'subject_id', 'user_id'],
            ['group_join_subjects.group_id', 'group_join_subjects.id', 'group_join_subjects.user_id']),
        CheckConstraint('ownership_revision>=1 AND lifecycle_revision>=1'),
    )
