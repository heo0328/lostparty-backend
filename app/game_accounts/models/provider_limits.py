from sqlalchemy import String, Integer
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class ProviderLimit(Base):
    __tablename__ = 'lostark_provider_limits'
    fingerprint = mapped_column(String(64), primary_key=True)
    blocked_until = stamp(index=True)
    blocked_code = mapped_column(String(64), nullable=False, server_default='UPSTREAM_RATE_LIMITED')
    upstream_status = mapped_column(Integer, nullable=True)
