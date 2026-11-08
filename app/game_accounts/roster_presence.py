"""Owned-roster observations, not proof of deletion, rename or transfer.

Only reconcile of a validated owned observation records these transitions. The
revision chain permits an existing seat to survive *only* this cause; it is not
a general lifecycle/ownership bypass. Callers own the mutation lock/transaction.
"""
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.auth.models import Base, pk, stamp


class RosterTransition(Base):
    __tablename__ = 'character_roster_transitions'
    id = pk()
    character_id = mapped_column(ForeignKey('game_characters.id'), nullable=False, index=True)
    account_id = mapped_column(ForeignKey('game_accounts.id'), nullable=False)
    owner_id = mapped_column(ForeignKey('users.id'), nullable=False)
    ownership_revision = mapped_column(Integer, nullable=False)
    from_revision = mapped_column(Integer, nullable=False)
    to_revision = mapped_column(Integer, nullable=False)
    state = mapped_column(String(16), nullable=False)
    source_usable = mapped_column(Boolean, nullable=False)
    observed_at = stamp()
    __table_args__ = (
        UniqueConstraint('character_id', 'ownership_revision', 'to_revision'),
        CheckConstraint("state IN ('missing','present') AND from_revision>0 AND to_revision>=from_revision AND ownership_revision>0"),
    )


class RosterRoomRecovery(Base):
    __tablename__ = 'roster_participation_recoveries'
    id = pk()
    cycle_id = mapped_column(ForeignKey('recruitment_room_cycles.id'), nullable=False)
    generation = mapped_column(Integer, nullable=False)
    evidence = mapped_column(JSONB, nullable=False)
    observed_at = stamp()
    __table_args__ = (
        ForeignKeyConstraint(['cycle_id', 'generation'],
            ['recruitment_cycle_generations.cycle_id', 'recruitment_cycle_generations.generation']),
        CheckConstraint("generation>0 AND jsonb_typeof(evidence)='object'"),
    )


def enabled(db):
    # Cache per Session, never globally across isolated databases/schema versions.
    if 'roster_presence_enabled' not in db.info:
        db.info['roster_presence_enabled'] = db.scalar(text(
            "SELECT to_regclass('public.character_roster_transitions')")) is not None
    return db.info['roster_presence_enabled']


def latest(db, account, character):
    if not enabled(db):
        return None
    return db.scalar(select(RosterTransition).where(
        RosterTransition.character_id == character.id,
        RosterTransition.account_id == account.id,
        RosterTransition.owner_id == account.owner_id,
        RosterTransition.ownership_revision == account.ownership_revision,
    ).order_by(RosterTransition.to_revision.desc()).limit(1))


def record(db, account, character, previous_revision, source_usable, state, observed_at):
    if not enabled(db):
        return
    prior = latest(db, account, character)
    if prior is not None and prior.to_revision == character.lifecycle_revision:
        return
    db.add(RosterTransition(character_id=character.id, account_id=account.id,
        owner_id=account.owner_id, ownership_revision=account.ownership_revision,
        from_revision=previous_revision, to_revision=character.lifecycle_revision,
        state=state, source_usable=source_usable, observed_at=observed_at))
    db.flush()


def missing(db, account, character):
    if character.lifecycle_state != 'suspect' or character.status != 'suspect':
        return None
    value = latest(db, account, character)
    if value is None or value.state != 'missing' or value.to_revision != character.lifecycle_revision:
        return None
    return value


def retained_revision(db, account, character, original_revision):
    """Prove every intervening revision was an owned-roster miss/reappearance."""
    if not enabled(db) or original_revision >= character.lifecycle_revision:
        return False
    rows = list(db.scalars(select(RosterTransition).where(
        RosterTransition.character_id == character.id,
        RosterTransition.account_id == account.id,
        RosterTransition.owner_id == account.owner_id,
        RosterTransition.ownership_revision == account.ownership_revision,
        RosterTransition.to_revision > original_revision,
        RosterTransition.to_revision <= character.lifecycle_revision,
    ).order_by(RosterTransition.to_revision)))
    cursor = original_revision
    expected = 'missing'
    for value in rows:
        if (value.from_revision != cursor or value.to_revision != cursor + 1
                or value.state != expected or (expected == 'missing' and not value.source_usable)):
            return False
        cursor = value.to_revision
        expected = 'present' if expected == 'missing' else 'missing'
    if cursor != character.lifecycle_revision:
        return False
    return (missing(db, account, character) is not None if rows[-1].state == 'missing'
            else character.status == 'confirmed' and character.lifecycle_state == 'active')
