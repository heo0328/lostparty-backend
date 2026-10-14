from sqlalchemy import Boolean, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class MemberSettings(Base):
    __tablename__ = 'member_settings'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    nice_group_auto_refresh_enabled = mapped_column(Boolean, nullable=False, default=False)
    version = mapped_column(Integer, nullable=False, default=1)
    updated_at = stamp()
    __table_args__ = (CheckConstraint('version >= 1'),)
