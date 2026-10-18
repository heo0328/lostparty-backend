import uuid
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, LargeBinary, UniqueConstraint, CheckConstraint, func, FetchedValue
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    # Storage metadata, separate from domain/API timestamps. NULL only for
    # legacy dates that were never recorded. PostgreSQL enforces update timing.
    record_created_at = mapped_column(DateTime(timezone=True), nullable=True,
                                     server_default=func.clock_timestamp())
    record_updated_at = mapped_column(DateTime(timezone=True), nullable=True,
                                     server_default=func.clock_timestamp(),
                                     server_onupdate=FetchedValue())


def pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def stamp(nullable=False, index=False):
    return mapped_column(DateTime(timezone=True), nullable=nullable, index=index)


class User(Base):
    __tablename__ = "users"
    id = pk()
    status = mapped_column(String(16), nullable=False, default="active")
    created_at = stamp()
    updated_at = stamp()
    last_login_at = stamp()
    __table_args__ = (CheckConstraint("status IN ('active','disabled')"),)


class Identity(Base):
    __tablename__ = "auth_identities"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider = mapped_column(String(16), nullable=False)
    issuer = mapped_column(String(128), nullable=False)
    subject = mapped_column(String(255), nullable=False)
    linked_at = stamp()
    __table_args__ = (UniqueConstraint("provider", "issuer", "subject"),)


class Transaction(Base):
    __tablename__ = "auth_transactions"
    id = pk()
    nonce_digest = mapped_column(String(64), unique=True, nullable=False)
    secret_digest = mapped_column(String(64), nullable=False)
    expires_at = stamp(index=True)
    consumed_at = stamp(nullable=True)


class Session(Base):
    __tablename__ = "auth_sessions"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    remember_me = mapped_column(Boolean, nullable=False)
    created_at = stamp()
    absolute_expires_at = stamp(index=True)
    idle_expires_at = stamp()
    revoked_at = stamp(nullable=True)
    revoked_reason = mapped_column(String(32), nullable=True)


class Credential(Base):
    __tablename__ = "refresh_credentials"
    id = pk()
    session_id = mapped_column(ForeignKey("auth_sessions.id"), nullable=False)
    generation = mapped_column(Integer, nullable=False)
    token_digest = mapped_column(String(64), unique=True, nullable=False)
    issued_at = stamp()
    expires_at = stamp()
    consumed_at = stamp(nullable=True)
    request_digest = mapped_column(String(64), nullable=True)
    successor_id = mapped_column(ForeignKey("refresh_credentials.id"), nullable=True)
    __table_args__ = (UniqueConstraint("session_id", "generation"),
                      UniqueConstraint("session_id", "request_digest"))


class Recovery(Base):
    __tablename__ = "refresh_recoveries"
    id = pk()
    old_id = mapped_column(ForeignKey("refresh_credentials.id"), nullable=False, unique=True)
    successor_id = mapped_column(ForeignKey("refresh_credentials.id"), nullable=False)
    request_digest = mapped_column(String(64), nullable=False)
    expires_at = stamp(index=True)
    resend_count = mapped_column(Integer, nullable=False, default=0)
    key_id = mapped_column(String(64), nullable=False)
    nonce = mapped_column(LargeBinary, nullable=False)
    ciphertext = mapped_column(LargeBinary, nullable=False)
    __table_args__ = (CheckConstraint("resend_count BETWEEN 0 AND 2"), UniqueConstraint("key_id", "nonce"))
