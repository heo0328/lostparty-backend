"""Typed provider boundary. Live schema proof is deliberately not implied."""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.equipment import parse_equipment, InvalidSnapshot


@dataclass(frozen=True)
class Observation:
    roster: list[dict]
    fetched_at: datetime
    equipment: dict | None = None
    # Only an injected test adapter can currently provide validated proof.
    proof_validated: bool = False
    disappearance_validated: bool = False


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


def fetch(name, proof=False):
    provider = LostArkProvider(os.getenv('LOSTARK_API_TOKEN', ''))
    rows = roster(provider.siblings(name), name)
    gear = None
    if proof:
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
    return Observation(rows, datetime.now(timezone.utc), gear)
