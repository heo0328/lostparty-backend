from sqlalchemy import (String, Integer, Boolean, ForeignKey, UUID, CheckConstraint,
                        UniqueConstraint, Index, text, ForeignKeyConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class Account(Base):
    __tablename__ = 'game_accounts'
    id = pk()
    owner_id = mapped_column(ForeignKey('users.id'), nullable=True)
    ownership_revision = mapped_column(Integer, nullable=False, default=1)
    roster_revision = mapped_column(Integer, nullable=False, default=1)
    verified_at = stamp()
    __table_args__ = (CheckConstraint('ownership_revision > 0 AND roster_revision > 0'),)


class Registration(Base):
    __tablename__ = 'game_account_registrations'
    id = pk()
    user_id = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=True)
    lookup_name = mapped_column(String(64), nullable=False)
    label = mapped_column(String(40), nullable=False)
    is_main = mapped_column(Boolean, nullable=False, default=False)
    version = mapped_column(Integer, nullable=False, default=1)
    preview = mapped_column(JSONB, nullable=False)
    fetched_at = stamp()
    created_at = stamp()
    updated_at = stamp()
    deleted_at = stamp(nullable=True)
    __table_args__ = (
        CheckConstraint('version > 0'),
        Index('uq_registration_main', 'user_id', unique=True, postgresql_where=text('is_main AND deleted_at IS NULL')),
        Index('uq_registration_account', 'user_id', 'account_id', unique=True, postgresql_where=text('deleted_at IS NULL AND account_id IS NOT NULL')),
    )


class Character(Base):
    __tablename__ = 'game_characters'
    id = pk()
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False, index=True)
    server_name = mapped_column(String(64), nullable=False)
    character_name = mapped_column(String(64), nullable=False)
    summary = mapped_column(JSONB, nullable=False)
    status = mapped_column(String(16), nullable=False, default='confirmed')
    fetched_at = stamp()
    confirmed_at = stamp()
    power_fetched_at = stamp(nullable=True)
    __table_args__ = (UniqueConstraint('server_name', 'character_name'), UniqueConstraint('account_id', 'id'),
                      CheckConstraint("status IN ('confirmed','suspect','missing')"))


class Configuration(Base):
    __tablename__ = 'character_settings'
    id = pk()
    user_id = mapped_column(ForeignKey('users.id'), nullable=False)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    representative_id = mapped_column(UUID, nullable=True)
    state = mapped_column(String(32), nullable=False, default='unconfigured')
    version = mapped_column(Integer, nullable=False, default=1)
    next_change_at = stamp(nullable=True)
    ended_at = stamp(nullable=True)
    __table_args__ = (
        UniqueConstraint('id', 'account_id'),
        ForeignKeyConstraint(['account_id', 'representative_id'], ['game_characters.account_id', 'game_characters.id']),
        Index('uq_live_configuration', 'user_id', 'account_id', unique=True, postgresql_where=text('ended_at IS NULL')),
        CheckConstraint("state IN ('unconfigured','configured','needs_reconfiguration') AND version > 0"),
    )


class Activity(Base):
    __tablename__ = 'activity_characters'
    settings_id = mapped_column(UUID, primary_key=True)
    character_id = mapped_column(UUID, primary_key=True)
    account_id = mapped_column(UUID, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['settings_id', 'account_id'], ['character_settings.id', 'character_settings.account_id']),
        ForeignKeyConstraint(['account_id', 'character_id'], ['game_characters.account_id', 'game_characters.id']),
    )


class Verification(Base):
    __tablename__ = 'game_account_verifications'
    id = pk()
    actor_id = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    registration_id = mapped_column(ForeignKey('game_account_registrations.id'), nullable=True)
    lookup_name = mapped_column(String(64), nullable=False)
    candidate_id = mapped_column(ForeignKey('game_accounts.id'), nullable=True)
    revision = mapped_column(Integer, nullable=True)
    roster = mapped_column(JSONB, nullable=True)
    baseline = mapped_column(JSONB, nullable=True)
    slots = mapped_column(JSONB, nullable=False)
    status = mapped_column(String(16), nullable=False, default='pending')
    created_at = stamp()
    expires_at = stamp(index=True)
    terminal_at = stamp(nullable=True)
    result = mapped_column(JSONB, nullable=True)
    attempt_count = mapped_column(Integer, nullable=False, default=0)
    last_checked_at = stamp(nullable=True)
    __table_args__ = (CheckConstraint("status IN ('pending','verified','expired','cancelled')"),)


class Audit(Base):
    __tablename__ = 'ownership_audits'
    id = pk()
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    challenge_id = mapped_column(ForeignKey('game_account_verifications.id'), nullable=True, unique=True)
    previous_owner = mapped_column(ForeignKey('users.id'), nullable=True)
    new_owner = mapped_column(ForeignKey('users.id'), nullable=False)
    revision = mapped_column(Integer, nullable=False)
    created_at = stamp(index=True)


class RequestResult(Base):
    __tablename__ = 'game_account_requests'
    id = pk()
    actor_id = mapped_column(ForeignKey('users.id'), nullable=False)
    operation = mapped_column(String(32), nullable=False)
    key = mapped_column(UUID, nullable=False)
    digest = mapped_column(String(64), nullable=False)
    state = mapped_column(String(16), nullable=False, default='running')
    generation = mapped_column(Integer, nullable=False, default=1)
    lease_expires_at = stamp()
    completed_at = stamp(nullable=True)
    status = mapped_column(Integer, nullable=True)
    result = mapped_column(JSONB, nullable=True)
    __table_args__ = (UniqueConstraint('actor_id', 'operation', 'key'),
                      CheckConstraint("state IN ('running','retryable','completed','expired') AND generation > 0"))


class LimitEvent(Base):
    __tablename__ = 'game_account_limit_events'
    id = pk()
    scope = mapped_column(String(128), nullable=False, index=True)
    created_at = stamp(index=True)


class PreviewCache(Base):
    __tablename__ = 'game_account_cache'
    name = mapped_column(String(64), primary_key=True)
    roster = mapped_column(JSONB, nullable=False)
    fetched_at = stamp(index=True)


class FetchLease(Base):
    __tablename__ = 'game_account_fetch_leases'
    name = mapped_column(String(64), primary_key=True)
    generation = mapped_column(Integer, nullable=False, default=1)
    expires_at = stamp(index=True)
    completed = mapped_column(Boolean, nullable=False, default=False)
    roster = mapped_column(JSONB, nullable=True)
    fetched_at = stamp(nullable=True)
