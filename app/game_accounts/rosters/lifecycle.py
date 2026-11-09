"""Internal identity/evidence boundary. Live adapters currently issue no BindingEvidence."""
import hashlib
import json
from dataclasses import dataclass
from sqlalchemy import select, delete
from app.core.database import now
from app.game_accounts.models import (Account, Registration, Character, NameClaim, Configuration,
                                     Activity, CharacterRetirement, CharacterHistoryHead, ScopedPowerCache,
                                     CharacterRoleSummary, CharacterPersonalPreferences)
from app.game_accounts.support import fail


@dataclass(frozen=True)
class BindingEvidence:
    account_id: str
    snapshot: tuple
    continuity_ids: tuple[str, ...] = ()
    complete: bool = False


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def character_stamp(db, character):
    claim = db.get(NameClaim, (character.server_name, character.character_name))
    return (str(character.id), character.lifecycle_revision, character.lifecycle_state, character.status,
            str(claim.character_id) if claim else None, claim.revision if claim else None)


def account_stamp(db, account):
    characters = db.scalars(select(Character).where(Character.account_id == account.id).order_by(Character.id))
    return (str(account.id), str(account.owner_id), account.ownership_revision, account.roster_revision,
            tuple(character_stamp(db, c) for c in characters))


def registration_stamp(db, registration):
    account = db.get(Account, registration.account_id) if registration.account_id else None
    return (str(registration.id), registration.version, registration.is_main,
            account_stamp(db, account) if account else None)


def evidence(db, account, *, continuity_ids=(), complete=False):
    """For validated internal adapters/tests only; never derive this from names or HTTP input."""
    return BindingEvidence(str(account.id), account_stamp(db, account), tuple(map(str, continuity_ids)), complete)


def validate_binding(db, account, proof):
    if type(proof) is not BindingEvidence or proof.account_id != str(account.id):
        fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
    if proof.snapshot != account_stamp(db, account):
        fail('REVISION_CONFLICT')


def usable(db, character):
    if character.lifecycle_state != 'active' or character.status != 'confirmed':
        return False
    claim = db.get(NameClaim, (character.server_name, character.character_name))
    return claim is not None and claim.character_id == character.id


def require_usable(db, character):
    if not usable(db, character):
        fail('CHARACTER_UNUSABLE')


def power_scope(registration, character=None):
    return dict(character_id=character.id if character else None,
                lifecycle_revision=character.lifecycle_revision if character else None,
                registration_id=registration.id, preview_version=None if character else registration.version)


def retire(db, account, character, proof):
    """No live/public caller. Requires a fresh complete internal evidence snapshot."""
    validate_binding(db, account, proof)
    if not proof.complete:
        fail('ROSTER_EVIDENCE_PENDING')
    if character.account_id != account.id or account.owner_id is None:
        fail('IDENTITY_CONFLICT')
    if character.lifecycle_state == 'retired':
        return
    claim = db.get(NameClaim, (character.server_name, character.character_name))
    if not claim or claim.character_id != character.id:
        fail('IDENTITY_CONFLICT')
    head = db.get(CharacterHistoryHead, account.owner_id)
    if head is None:
        head = CharacterHistoryHead(user_id=account.owner_id, revision=1)
        db.add(head); db.flush()
    head.revision += 1
    current = now(db)
    good = db.scalar(select(ScopedPowerCache).where(
        ScopedPowerCache.actor_id == account.owner_id, ScopedPowerCache.character_id == character.id,
        ScopedPowerCache.fetched_at.is_not(None)).order_by(ScopedPowerCache.fetched_at.desc()).limit(1))
    db.add(CharacterRetirement(character_id=character.id, user_id=account.owner_id, account_id=account.id,
        server_name=character.server_name, character_name=character.character_name,
        class_name=character.summary['class_name'], combat_power=good.value if good else character.summary.get('combat_power'),
        item_level=character.summary.get('item_level'), power_fetched_at=good.fetched_at if good else character.power_fetched_at,
        item_level_fetched_at=character.confirmed_at if character.summary.get('item_level') is not None else None,
        retired_at=current, lifecycle_revision=character.lifecycle_revision+1, history_revision=head.revision))
    for conf in db.scalars(select(Configuration).where(Configuration.account_id == account.id, Configuration.ended_at.is_(None))):
        selected = db.get(Activity, (conf.id, character.id))
        if selected or conf.representative_id == character.id:
            if selected: db.delete(selected)
            if conf.representative_id == character.id: conf.representative_id = None
            conf.state = 'needs_reconfiguration'; conf.version += 1
    # Only the retiring canonical UUID; preserve account presentation and all other IDs.
    # This internal transaction still has no live/public caller.
    for model in (CharacterRoleSummary, CharacterPersonalPreferences):
        db.execute(delete(model).where(model.character_id == character.id))
    db.delete(claim)
    character.lifecycle_state, character.status = 'retired', 'missing'
    character.lifecycle_revision += 1
    character.summary, character.power_fetched_at = {}, None
    # Tombstone ID and FK references remain. Older leases can never match this revision.
    account.roster_revision += 1
    for registration in db.scalars(select(Registration).where(Registration.account_id == account.id, Registration.deleted_at.is_(None))):
        registration.version += 1
    db.flush()
