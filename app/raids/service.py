"""No DB, credentials or provider calls: packaged product data and UTC clock only."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from app.raids.schemas import RaidCatalog, RaidCycle, RaidDifficulty

KST = ZoneInfo('Asia/Seoul')


@lru_cache(maxsize=1)
def catalog() -> RaidCatalog:
    value = RaidCatalog.model_validate_json(Path(__file__).with_name('catalog.json').read_text())
    # Fail closed on invalid packaged data, including duplicate IDs/ambiguous composition.
    if len({raid.raid_id for raid in value.raids}) != len(value.raids):
        raise ValueError('Duplicate raid ID')
    for raid in value.raids:
        if (raid.party_size != 4 * raid.party_count or
                raid.required_support_count != raid.party_count or
                raid.max_dealer_count_per_class != raid.party_count):
            raise ValueError('Invalid raid composition')
        if len({d.difficulty_id for d in raid.difficulties}) != len(raid.difficulties):
            raise ValueError('Duplicate difficulty ID')
    return value


def cycle(at: datetime | None = None) -> RaidCycle:
    stamp = at if at is not None else datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Timezone-aware server time required')
    stamp = stamp.astimezone(timezone.utc)
    local = stamp.astimezone(KST)
    wednesday = local.date() - timedelta(days=(local.weekday() - 2) % 7)
    start = datetime.combine(wednesday, time(6), KST)
    if local < start:
        start -= timedelta(days=7)
    return RaidCycle(server_time=stamp, cycle_key=start.date().isoformat(),
                     starts_at=start.astimezone(timezone.utc),
                     ends_at=(start + timedelta(days=7)).astimezone(timezone.utc),
                     timezone='Asia/Seoul')


class CatalogSelectionError(ValueError):
    """Internal rejection; future commands own the HTTP mapping and transaction."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def difficulty(raid_id: str, difficulty_id: str, expected_catalog_version: str,
               *, source: RaidCatalog | None = None) -> RaidDifficulty:
    value = source if source is not None else catalog()
    if expected_catalog_version != value.catalog_version:
        raise CatalogSelectionError('CATALOG_VERSION_CONFLICT')
    raid = next((r for r in value.raids if r.raid_id == raid_id), None)
    if raid is None:
        raise CatalogSelectionError('RAID_NOT_FOUND')
    selected = next((d for d in raid.difficulties if d.difficulty_id == difficulty_id), None)
    if selected is None:
        raise CatalogSelectionError('DIFFICULTY_NOT_FOUND')
    if not raid.is_active or not selected.is_active:
        raise CatalogSelectionError('RAID_INACTIVE')
    return selected


def meets_item_level(item_level: Decimal | None, selected: RaidDifficulty) -> bool:
    # Unknown/non-finite values never acquire eligibility. Do not truncate to UI integers.
    return (isinstance(item_level, Decimal) and item_level.is_finite() and
            item_level >= Decimal(selected.min_item_level))
