"""Current schedule intent heads; retired group graphs remain evidence."""
from sqlalchemy import Boolean,ForeignKey,String
from sqlalchemy.orm import mapped_column
from app.auth.models import Base,stamp


class ScheduleHead(Base):
    __tablename__='recruitment_schedule_heads'
    group_id=mapped_column(ForeignKey('recruitment_schedule_groups.id'),primary_key=True)
    client_key=mapped_column(String(64),nullable=False)
    active=mapped_column(Boolean,nullable=False)
    ended_at=stamp(nullable=True)
