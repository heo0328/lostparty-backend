"""Typed provider boundary. Live schema proof is deliberately not implied."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.equipment import parse_equipment, InvalidSnapshot
from app.game_accounts.lifecycle import BindingEvidence
from app.game_accounts import equipment_proof


@dataclass(frozen=True)
class Observation:
    roster: list[dict]
    fetched_at: datetime
    equipment: dict | None = None
    # Legacy trusted test-adapter marker; live uses server equipment receipts.
    proof_validated: bool = False
    disappearance_validated: bool = False
    binding: BindingEvidence | None = None
    equipment_evidence: equipment_proof.ServerEquipmentObservation | None = None


def number(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
    try:
        result = Decimal(value.replace(',', ''))
        if not result.is_finite() or result < 0:
            raise ValueError()
        return str(result)
    except (InvalidOperation, ValueError):
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE') from None


def roster(raw, name):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 200:
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
    rows, keys = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
        fields = [item.get(k) for k in ('ServerName', 'CharacterName', 'CharacterClassName')]
        level = item.get('CharacterLevel')
        if any(not isinstance(v, str) or not v.strip() or len(v) > 64 for v in fields) or type(level) is not int or not 0 <= level <= 1000:
            raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
        key = tuple(fields[:2])
        if key in keys:
            raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
        keys.add(key)
        rows.append(dict(server_name=fields[0], character_name=fields[1], class_name=fields[2],
                         character_level=level, item_level=number(item.get('ItemAvgLevel')), combat_power=None))
    if sum(r['character_name'] == name for r in rows) != 1:
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
    return sorted(rows, key=lambda r: (r['server_name'], r['character_name']))


def fetch(name, proof=False, *, token, before_armory=None, observer=None):
    provider = LostArkProvider(token, observer=observer)
    rows = roster(provider.siblings(name), name)
    gear = None
    if proof:
        if before_armory is not None:
            before_armory()
        raw = provider.armory(name)
        profile = raw.get('ArmoryProfile') if isinstance(raw, dict) else None
        matching = next(r for r in rows if r['character_name'] == name)
        if not isinstance(profile, dict) or profile.get('CharacterName') != name or profile.get('ServerName') != matching['server_name']:
            raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
        matching['combat_power'] = number(profile.get('CombatPower'))
        try:
            gear = parse_equipment(raw.get('ArmoryEquipment'))
        except InvalidSnapshot:
            raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE') from None
    collected_at = datetime.now(timezone.utc)
    receipt = equipment_proof.collect(name, rows, gear, collected_at) if proof else None
    return Observation(rows, collected_at, gear, equipment_evidence=receipt)
