"""Apply API roster observations to an already owned registration.

Internal authorization scope is deliberately separate from identity/transfer
BindingEvidence. API address continuity follows the agreed observation policy.
"""
from dataclasses import dataclass, replace
from sqlalchemy import select
from app.game_accounts import lifecycle, verification_context
from app.game_accounts.models import Account, Character, NameClaim
from app.game_accounts.support import fail, GameError

MAX_LOOKUPS = 3


@dataclass(frozen=True)
class OwnedScope:
    registration_id: object
    account_id: object
    actor_id: object
    stamp: str
    anchors: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class OwnedObservation:
    scope: OwnedScope
    target: tuple[str, str]


def capture(db, uid, registration):
    account = db.get(Account, registration.account_id) if registration.account_id else None
    if account is None or account.owner_id != uid:
        return None
    rows = db.scalars(select(Character).where(Character.account_id == account.id).order_by(
        Character.server_name, Character.character_name, Character.id))
    anchors = tuple((c.server_name, c.character_name) for c in rows if lifecycle.usable(db, c))
    return OwnedScope(registration.id, account.id, uid,
                      lifecycle.digest(lifecycle.registration_stamp(db, registration)), anchors)


def validate(db, uid, registration, observation):
    scoped = observation.owned_observation
    if type(scoped) is not OwnedObservation or type(scoped.scope) is not OwnedScope:
        fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
    scope = scoped.scope
    account = db.get(Account, scope.account_id)
    if (scope.actor_id != uid or scope.registration_id != registration.id
            or registration.account_id != scope.account_id or account is None or account.owner_id != uid
            or lifecycle.digest(lifecycle.registration_stamp(db, registration)) != scope.stamp):
        fail('REVISION_CONFLICT')
    context = verification_context.capture(scoped.target[1], observation.roster)
    if context is None:
        fail('UPSTREAM_INVALID_RESPONSE', 503)
    if tuple(context['target']) != scoped.target or scoped.target not in scope.anchors:
        fail('IDENTITY_CONFLICT')
    for row in observation.roster:
        claim = db.get(NameClaim, (row['server_name'], row['character_name']))
        character = db.get(Character, claim.character_id) if claim else None
        if claim and (character is None or character.account_id != account.id):
            fail('IDENTITY_CONFLICT')
    return account


def fetch(principal, snapshot, preferred_name, scope, *, context, guard):
    from app.game_accounts import service
    preferred = [pair for pair in scope.anchors if pair[1] == preferred_name]
    candidates = preferred + [pair for pair in scope.anchors if pair not in preferred]
    if not candidates:
        fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
    for index, target in enumerate(candidates[:MAX_LOOKUPS]):
        try:
            observation = service.lookup(principal, snapshot, target[1], context=context, guard=guard)
            return replace(observation, owned_observation=OwnedObservation(scope, target))
        except GameError as error:
            # No automatic retry on timeout, malformed data, key or quota errors.
            if not getattr(error, 'provider_not_found', False) or index == min(len(candidates), MAX_LOOKUPS)-1:
                raise
