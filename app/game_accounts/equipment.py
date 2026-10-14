"""Compare server-fetched equipment only; this verdict does not grant ownership."""
from dataclasses import dataclass
from secrets import SystemRandom
from typing import Mapping

SLOTS = ('무기', '투구', '어깨', '상의', '하의', '장갑')
# Provider Types must be checked against sanitized live fixtures before wiring APIs.
OTHER_TYPES = frozenset(('목걸이', '귀걸이', '반지', '어빌리티 스톤', '팔찌'))


class InvalidSnapshot(ValueError):
    def __init__(self):
        super().__init__('INVALID_EQUIPMENT_SNAPSHOT')


class EquipmentIncomplete(ValueError):
    def __init__(self):
        super().__init__('EQUIPMENT_INCOMPLETE')


@dataclass(frozen=True)
class EquipmentItem:
    name: str
    grade: str


def parse_equipment(raw: object) -> dict[str, EquipmentItem]:
    """Never interpret null, malformed entries or unknown Types as unequipped."""
    if not isinstance(raw, list) or not raw or len(raw) > 32:
        raise InvalidSnapshot()
    result = {}
    for item in raw:
        if not isinstance(item, dict):
            raise InvalidSnapshot()
        kind = item.get('Type')
        if not isinstance(kind, str) or kind not in (*SLOTS, *OTHER_TYPES):
            raise InvalidSnapshot()
        if kind in OTHER_TYPES:
            continue
        name, grade = item.get('Name'), item.get('Grade')
        if (kind in result or not isinstance(name, str) or not name.strip()
                or len(name) > 512 or not isinstance(grade, str)
                or not grade.strip() or len(grade) > 64):
            raise InvalidSnapshot()
        result[kind] = EquipmentItem(name, grade)
    return result


def required_slots(baseline: Mapping[str, EquipmentItem]) -> tuple[str, ...]:
    if set(baseline) != set(SLOTS) or any(not isinstance(v, EquipmentItem) for v in baseline.values()):
        raise EquipmentIncomplete()
    rng = SystemRandom()
    return tuple(rng.sample(SLOTS, rng.randint(1, 3)))


def compare_equipment(baseline: Mapping[str, EquipmentItem], required: tuple[str, ...],
                      observed: Mapping[str, EquipmentItem]) -> str:
    if (set(baseline) != set(SLOTS) or not 1 <= len(required) <= 3
            or len(set(required)) != len(required) or not set(required) <= set(SLOTS)
            or not set(observed) <= set(SLOTS)
            or any(not isinstance(v, EquipmentItem) for v in (*baseline.values(), *observed.values()))):
        raise InvalidSnapshot()
    # A partial upstream response can remove unrequested slots too. Fail closed.
    if any(observed.get(slot) != baseline[slot] for slot in SLOTS if slot not in required):
        return 'NON_REQUIRED_EQUIPMENT_CHANGED'
    if any(slot in observed for slot in required):
        return 'REQUIRED_EQUIPMENT_PRESENT'
    return 'EQUIPMENT_MATCHED'
