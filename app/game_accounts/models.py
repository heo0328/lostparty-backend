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
    lifecycle_state = mapped_column(String(16), nullable=False, default='active')
    lifecycle_revision = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint('id', 'server_name', 'character_name', name='uq_character_identity_address'),
                      CheckConstraint("lifecycle_state IN ('active','suspect','retired') AND lifecycle_revision > 0", name='ck_character_lifecycle'), UniqueConstraint('account_id', 'id'),
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
    identity_snapshot = mapped_column(JSONB, nullable=True)
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


class PowerCache(Base):
    __tablename__ = 'character_power_cache'
    actor_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    server_name = mapped_column(String(64), primary_key=True)
    character_name = mapped_column(String(64), primary_key=True)
    value = mapped_column(String(64), nullable=True)
    fetched_at = stamp(nullable=True)
    checked_at = stamp(nullable=True)
    status = mapped_column(String(16), nullable=False, default='unknown')
    reason = mapped_column(String(40), nullable=True)
    generation = mapped_column(Integer, nullable=False, default=0)
    lease_expires_at = stamp(nullable=True)
    credential_version = mapped_column(Integer, nullable=True)
    __table_args__ = (CheckConstraint("status IN ('unknown','available','unavailable','failed') AND generation >= 0"),)


class NameClaim(Base):
    __tablename__ = 'character_name_claims'
    server_name = mapped_column(String(64), primary_key=True)
    character_name = mapped_column(String(64), primary_key=True)
    character_id = mapped_column(UUID, nullable=False, unique=True)
    revision = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        ForeignKeyConstraint(['character_id', 'server_name', 'character_name'],
                             ['game_characters.id', 'game_characters.server_name', 'game_characters.character_name']),
        CheckConstraint('revision > 0'),
    )


class CharacterHistoryHead(Base):
    __tablename__ = 'character_history_heads'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    revision = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (CheckConstraint('revision > 0'),)


class CharacterRetirement(Base):
    __tablename__ = 'character_retirements'
    id = pk()
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False, unique=True)
    user_id = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    server_name = mapped_column(String(64), nullable=False)
    character_name = mapped_column(String(64), nullable=False)
    class_name = mapped_column(String(64), nullable=False)
    combat_power = mapped_column(String(64), nullable=True)
    item_level = mapped_column(String(64), nullable=True)
    power_fetched_at = stamp(nullable=True)
    item_level_fetched_at = stamp(nullable=True)
    retired_at = stamp()
    lifecycle_revision = mapped_column(Integer, nullable=False)
    history_revision = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint('lifecycle_revision > 0 AND history_revision > 0'),)


class ScopedPowerCache(Base):
    __tablename__ = 'scoped_character_power_cache'
    actor_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    scope_key = mapped_column(String(64), primary_key=True)
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=True)
    lifecycle_revision = mapped_column(Integer, nullable=True)
    registration_id = mapped_column(ForeignKey('game_account_registrations.id'), nullable=False)
    preview_version = mapped_column(Integer, nullable=True)
    credential_version = mapped_column(Integer, nullable=False)
    server_name = mapped_column(String(64), nullable=False)
    character_name = mapped_column(String(64), nullable=False)
    value = mapped_column(String(64), nullable=True)
    fetched_at = stamp(nullable=True)
    checked_at = stamp(nullable=True)
    status = mapped_column(String(16), nullable=False, default='unknown')
    reason = mapped_column(String(40), nullable=True)
    generation = mapped_column(Integer, nullable=False, default=0)
    lease_expires_at = stamp(nullable=True)
    __table_args__ = (CheckConstraint("status IN ('unknown','available','unavailable','failed') AND generation >= 0"),
                     CheckConstraint('credential_version > 0'),
                     CheckConstraint('(character_id IS NOT NULL AND lifecycle_revision IS NOT NULL AND lifecycle_revision > 0 AND preview_version IS NULL) OR '
                                     '(character_id IS NULL AND lifecycle_revision IS NULL AND preview_version IS NOT NULL AND preview_version > 0)'))


class ScopedRosterCache(Base):
    __tablename__ = 'scoped_roster_cache'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    credential_version = mapped_column(Integer, primary_key=True)
    scope_key = mapped_column(String(64), primary_key=True)
    name = mapped_column(String(64), primary_key=True)
    roster = mapped_column(JSONB, nullable=False)
    fetched_at = stamp(index=True)


class ScopedRosterLease(Base):
    __tablename__ = 'scoped_roster_leases'
    user_id = mapped_column(ForeignKey('users.id'), primary_key=True)
    credential_version = mapped_column(Integer, primary_key=True)
    scope_key = mapped_column(String(64), primary_key=True)
    name = mapped_column(String(64), primary_key=True)
    generation = mapped_column(Integer, nullable=False, default=1)
    expires_at = stamp(index=True)
    completed = mapped_column(Boolean, nullable=False, default=False)
    roster = mapped_column(JSONB, nullable=True)
    fetched_at = stamp(nullable=True)
