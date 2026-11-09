from app.game_accounts.models.roster_presence import RosterTransition

"""Owned-roster observations, not proof of deletion, rename or transfer.

Only reconcile of a validated owned observation records these transitions. The
revision chain permits an existing seat to survive *only* this cause; it is not
a general lifecycle/ownership bypass. Callers own the mutation lock/transaction.
"""

from sqlalchemy import select
from sqlalchemy import text

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
