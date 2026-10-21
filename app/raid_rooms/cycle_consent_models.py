"""Immutable evidence for each explicit confirmation, including later re-consent."""
from sqlalchemy import CheckConstraint,ForeignKeyConstraint,Integer,UUID,UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,pk,stamp


class CycleConsent(Base):
    __tablename__='recruitment_cycle_consents'
    id=pk()
    room_id=mapped_column(UUID,nullable=False)
    cycle_id=mapped_column(UUID,nullable=False)
    generation=mapped_column(Integer,nullable=False)
    cycle_member_id=mapped_column(UUID,nullable=False)
    membership_id=mapped_column(UUID,nullable=False)
    user_id=mapped_column(UUID,nullable=False)
    participation_id=mapped_column(UUID,nullable=False)
    session_id=mapped_column(UUID,nullable=False)
    command_id=mapped_column(UUID,nullable=False)
    member_revision=mapped_column(Integer,nullable=False)
    participation_revision=mapped_column(Integer,nullable=False)
    schedule_revision=mapped_column(Integer,nullable=False)
    effective_at=stamp()
    evidence=mapped_column(JSONB,nullable=False)
    __table_args__=(
        ForeignKeyConstraint(['room_id','cycle_id','generation','cycle_member_id','membership_id','user_id'],
            ['recruitment_cycle_members.room_id','recruitment_cycle_members.cycle_id','recruitment_cycle_members.generation',
             'recruitment_cycle_members.id','recruitment_cycle_members.membership_id','recruitment_cycle_members.user_id']),
        ForeignKeyConstraint(['room_id','participation_id','session_id','membership_id','user_id'],
            ['recruitment_participations.room_id','recruitment_participations.id','recruitment_participations.session_id',
             'recruitment_participations.membership_id','recruitment_participations.user_id']),
        ForeignKeyConstraint(['room_id','cycle_id','generation','session_id'],
            ['recruitment_cycle_sessions.room_id','recruitment_cycle_sessions.cycle_id','recruitment_cycle_sessions.generation','recruitment_cycle_sessions.session_id']),
        UniqueConstraint('user_id','command_id'),
        UniqueConstraint('participation_id','participation_revision'),
        CheckConstraint("member_revision>=1 AND participation_revision>=1 AND schedule_revision>=1 AND jsonb_typeof(evidence)='object'"),
    )


CYCLE_CONSENT_MODELS=(CycleConsent,)
