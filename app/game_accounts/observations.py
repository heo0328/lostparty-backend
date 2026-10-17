"""Typed provider boundary. Live schema proof is deliberately not implied."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from time import monotonic
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.equipment import parse_equipment, InvalidSnapshot
from app.game_accounts.lifecycle import BindingEvidence
from app.game_accounts import equipment_proof, verification_context
from app.game_accounts.owned_refresh import OwnedObservation


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
    owned_observation: OwnedObservation | None = None


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
    if verification_context.resolve_input(name, rows) is None:
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
    return sorted(rows, key=lambda r: (r['server_name'], r['character_name']))


def fetch(name, proof=False, *, token, before_armory=None, observer=None, on_roster=None):
    started = monotonic()
    stage = 'provider_init'
    timings = {}
    stage_started = started

    def enter(next_stage):
        nonlocal stage, stage_started
        current = monotonic()
        timings[stage] = round((current - stage_started) * 1000, 3)
        stage, stage_started = next_stage, current

    try:
        provider = LostArkProvider(token, observer=observer)
        enter('siblings_transport')
        raw_roster = provider.siblings(name)
        enter('siblings_schema')
        rows = roster(raw_roster, name)
        canonical_name = verification_context.resolve_input(name, rows)
        gear = None
        if proof:
            enter('before_armory')
            if on_roster is not None:
                on_roster(rows)
            if before_armory is not None:
                before_armory()
            enter('armory_transport')
            raw = provider.armory(canonical_name)
            enter('armory_profile')
            profile = raw.get('ArmoryProfile') if isinstance(raw, dict) else None
            matching = next(r for r in rows if r['character_name'] == canonical_name)
            if not isinstance(profile, dict) or profile.get('CharacterName') != canonical_name or profile.get('ServerName') != matching['server_name']:
                raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
            matching['combat_power'] = number(profile.get('CombatPower'))
            enter('armory_equipment')
            try:
                gear = parse_equipment(raw.get('ArmoryEquipment'))
            except InvalidSnapshot:
                raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE') from None
        enter('equipment_receipt')
        collected_at = datetime.now(timezone.utc)
        receipt = equipment_proof.collect(canonical_name, rows, gear, collected_at) if proof else None
        return Observation(rows, collected_at, gear, equipment_evidence=receipt)
    except ProviderUnavailable as error:
        current = monotonic()
        timings[stage] = round((current - stage_started) * 1000, 3)
        error.diagnostic_stage = stage
        error.diagnostic_elapsed_ms = round((current - started) * 1000, 3)
        error.diagnostic_timings = timings
        if stage in ('siblings_schema', 'armory_profile', 'armory_equipment'):
            error.http_status = 200
        raise
