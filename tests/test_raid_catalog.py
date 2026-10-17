from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.raids import service


def test_public_reads_need_no_session_key_database_or_provider(client, monkeypatch):
    from app.core import database
    from app.game_accounts.provider import LostArkProvider

    def forbidden(*args, **kwargs):
        raise AssertionError('Common catalog/cycle must not access member DB or provider')

    monkeypatch.setattr(database, 'session', forbidden)
    monkeypatch.setattr(database, 'engine', forbidden)
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    for path in ('/v1/raid-catalog', '/v1/raid-cycle'):
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.headers['Cache-Control'] == 'no-store'
        assert 'set-cookie' not in response.headers


def test_catalog_product_ids_levels_composition_and_rewards(client):
    body = client.get('/v1/raid-catalog').json()
    assert body['schema_version'] == 2 and body['catalog_version'] == '2026.08.20'
    assert body['updated_at'] == '2026-08-20T00:00:00Z'
    expected = {
        'kazeros_act4': {'normal': '1700', 'hard': '1720'},
        'kazeros_finale': {'normal': '1710', 'hard': '1730'},
        'serca': {'normal': '1710', 'hard': '1730', 'nightmare': '1740'},
        'horizon_cathedral': {'stage1': '1700', 'stage2': '1720', 'stage3': '1750'},
        'belgardin': {'normal': '1750', 'hard': '1770', 'nightmare': '1780'},
    }
    assert {r['raid_id']: {d['difficulty_id']: d['min_item_level'] for d in r['difficulties']}
            for r in body['raids']} == expected
    assert [r['display_order'] for r in body['raids']] == [1, 2, 3, 4, 5]
    for raid in body['raids']:
        count = 1 if raid['raid_id'] in ('serca', 'horizon_cathedral') else 2
        assert raid['party_size'] == 4 * count and raid['party_count'] == count
        assert raid['required_support_count'] == raid['max_dealer_count_per_class'] == count
    assert body['raids'][0]['difficulties'][0]['clear_gold'] == 13500
    assert body['raids'][3]['difficulties'][0]['bound_gold'] == 30000


@pytest.mark.parametrize('path', ['/v1/raid-catalog', '/v1/raid-cycle'])
@pytest.mark.parametrize('suffix,body', [('?user_id=other', None), ('?limit=1&limit=2', None),
                                      ('?cycle_key=2026-10-21', None), ('', '{}')])
def test_reads_reject_client_scope_time_and_body(client, path, suffix, body):
    response = client.request('GET', path + suffix, content=body)
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'INVALID_REQUEST'
    assert response.json()['error']['request_id']
    assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('stamp,key,start', [
    ('2026-10-20T20:59:59.999999+00:00', '2026-10-14', '2026-10-13T21:00:00+00:00'),
    ('2026-10-20T21:00:00+00:00', '2026-10-21', '2026-10-20T21:00:00+00:00'),
    ('2026-10-21T00:00:00+09:00', '2026-10-14', '2026-10-13T21:00:00+00:00'),
    ('2026-10-21T06:00:00+09:00', '2026-10-21', '2026-10-20T21:00:00+00:00'),
    ('2025-12-31T20:59:59+00:00', '2025-12-31', '2025-12-30T21:00:00+00:00'),
    ('2026-01-06T21:00:00+00:00', '2026-01-07', '2026-01-06T21:00:00+00:00'),
    ('2024-02-29T12:00:00+00:00', '2024-02-28', '2024-02-27T21:00:00+00:00'),
])
def test_server_week_boundaries_ignore_midnight_and_client_timezone(stamp, key, start):
    value = service.cycle(datetime.fromisoformat(stamp))
    assert value.cycle_key == key
    assert value.starts_at == datetime.fromisoformat(start)
    assert value.ends_at - value.starts_at == timedelta(days=7)
    assert value.starts_at <= value.server_time < value.ends_at
    assert value.server_time.utcoffset() == timedelta(0)


def test_cycle_endpoint_uses_one_server_clock_and_utc_fields(client, monkeypatch):
    fixed = service.cycle(datetime(2026, 10, 20, 21, tzinfo=timezone.utc))
    monkeypatch.setattr(service, 'cycle', lambda: fixed)
    assert client.get('/v1/raid-cycle').json() == {
        'server_time': '2026-10-20T21:00:00Z', 'cycle_key': '2026-10-21',
        'starts_at': '2026-10-20T21:00:00Z', 'ends_at': '2026-10-27T21:00:00Z',
        'timezone': 'Asia/Seoul',
    }


@pytest.mark.parametrize('raid,diff,version,code', [
    ('unknown', 'normal', '2026.08.20', 'RAID_NOT_FOUND'),
    ('serca', 'stage1', '2026.08.20', 'DIFFICULTY_NOT_FOUND'),
    ('serca', 'normal', 'older', 'CATALOG_VERSION_CONFLICT'),
])
def test_selection_rejects_invalid_pair_and_stale_catalog(raid, diff, version, code):
    with pytest.raises(service.CatalogSelectionError) as error:
        service.difficulty(raid, diff, version)
    assert error.value.code == code


@pytest.mark.parametrize('disable_raid', [True, False])
def test_selection_rejects_inactive_raid_or_difficulty(disable_raid):
    value = service.catalog()
    raid = value.raids[0]
    if disable_raid:
        raid = raid.model_copy(update={'is_active': False})
    else:
        disabled = raid.difficulties[0].model_copy(update={'is_active': False})
        raid = raid.model_copy(update={'difficulties': (disabled, *raid.difficulties[1:])})
    changed = value.model_copy(update={'raids': (raid, *value.raids[1:])})
    with pytest.raises(service.CatalogSelectionError, match='RAID_INACTIVE'):
        service.difficulty(raid.raid_id, 'normal', value.catalog_version, source=changed)
    # An isolated modified catalog cannot mutate the shared published snapshot.
    assert service.difficulty(raid.raid_id, 'normal', value.catalog_version).is_active


@pytest.mark.parametrize('level,eligible', [
    (Decimal('1699.999999999999'), False), (Decimal('1700'), True),
    (Decimal('1700.000000000001'), True), (Decimal('NaN'), False),
    (Decimal('Infinity'), False), (None, False), (1700.0, False),
])
def test_entry_level_preserves_decimal_precision_and_rejects_unknown(level, eligible):
    selected = service.difficulty('kazeros_act4', 'normal', '2026.08.20')
    assert service.meets_item_level(level, selected) is eligible


def test_naive_server_clock_is_rejected():
    with pytest.raises(ValueError, match='Timezone-aware'):
        service.cycle(datetime(2026, 10, 21, 6))
