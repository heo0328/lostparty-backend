from sqlalchemy import ForeignKey, Integer, LargeBinary, String, CheckConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, stamp


class Credential(Base):
    __tablename__ = 'lostark_credentials'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    version = mapped_column(Integer, nullable=False, default=1)
    updated_at = stamp(nullable=True)
    ciphertext = mapped_column(LargeBinary, nullable=True)
    nonce = mapped_column(LargeBinary, nullable=True)
    key_id = mapped_column(String(64), nullable=True)
    fingerprint = mapped_column(String(64), nullable=True)
    __table_args__ = (CheckConstraint('version >= 1'), CheckConstraint(
        '(ciphertext IS NULL AND nonce IS NULL AND key_id IS NULL AND fingerprint IS NULL) OR '
        '(ciphertext IS NOT NULL AND nonce IS NOT NULL AND key_id IS NOT NULL AND fingerprint IS NOT NULL '
        'AND octet_length(nonce) = 12)'),)


class MemberPreview(Base):
    __tablename__ = 'member_lostark_cache'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    credential_version = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(64), primary_key=True)
    roster = mapped_column(JSONB, nullable=False)
    fetched_at = stamp(index=True)


class MemberFetch(Base):
    __tablename__ = 'member_lostark_fetch_leases'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    credential_version = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(64), primary_key=True)
    generation = mapped_column(Integer, nullable=False, default=1)
    expires_at = stamp(index=True)
    completed = mapped_column(Boolean, nullable=False, default=False)
    roster = mapped_column(JSONB, nullable=True)
    fetched_at = stamp(nullable=True)
