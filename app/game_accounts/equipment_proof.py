"""Accept the established removal challenge using server-collected observations.

This proves present equipment control under the product's observation policy,
not provider completeness, permanent identity or account continuity.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from app.game_accounts import verification_context
from app.game_accounts.equipment import EquipmentItem, SLOTS


def equipment_digest(equipment):
    if (not isinstance(equipment, dict) or not set(equipment) <= set(SLOTS)
            or any(type(item) is not EquipmentItem for item in equipment.values())):
        return None
    values = {slot: [item.name, item.grade] for slot, item in equipment.items()}
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class ServerEquipmentObservation:
    context: dict
    equipment_digest: str
    fetched_at: datetime


def collect(name, roster, equipment, fetched_at):
    """Called only after the server transport/parser have validated the response."""
    context = verification_context.capture(name, roster)
    digest = equipment_digest(equipment)
    if context is None or digest is None:
        return None
    return ServerEquipmentObservation(context, digest, fetched_at)


def attests(obs, name):
    receipt = obs.equipment_evidence
    return (type(receipt) is ServerEquipmentObservation
            and isinstance(receipt.fetched_at, datetime)
            and receipt.context == verification_context.capture(name, obs.roster)
            and receipt.equipment_digest == equipment_digest(obs.equipment)
            and receipt.fetched_at == obs.fetched_at
            and receipt.fetched_at.tzinfo is not None)


def baseline(obs, name, current):
    if not attests(obs, name) or obs.fetched_at > current:
        return None
    receipt = obs.equipment_evidence
    return dict(method='server-equipment-removal-v1', context=receipt.context,
                equipment_digest=receipt.equipment_digest, fetched_at=receipt.fetched_at.isoformat())


def validated(challenge, obs, current):
    # Existing trusted injected adapters remain available for isolated tests.
    # Live fetch never sets this legacy marker and always supplies a receipt.
    if obs.equipment_evidence is None:
        return obs.proof_validated is True
    saved = (challenge.identity_snapshot or {}).get('server_equipment_baseline')
    if not isinstance(saved, dict) or saved.get('method') != 'server-equipment-removal-v1':
        return False
    if not attests(obs, challenge.lookup_name):
        return False
    try:
        collected = datetime.fromisoformat(saved['fetched_at'])
        original = {slot: EquipmentItem(**item) for slot, item in challenge.baseline.items()}
        return (saved['context'] == obs.equipment_evidence.context
                and saved['equipment_digest'] == equipment_digest(original)
                and collected <= challenge.created_at <= obs.fetched_at <= current < challenge.expires_at
                and collected < obs.fetched_at)
    except (KeyError, TypeError, ValueError):
        return False
