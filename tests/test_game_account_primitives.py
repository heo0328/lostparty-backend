from itertools import combinations
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from app.game_accounts.equipment import (
    SLOTS, EquipmentIncomplete, InvalidSnapshot, compare_equipment,
    parse_equipment, required_slots,
)
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable, MAX_BODY_BYTES


def gear():
    return [dict(Type=s, Name=f'item-{s}', Grade='고대', Tooltip='ignored') for s in SLOTS]


def test_every_removal_combination_and_unrequested_change():
    baseline = parse_equipment(gear())
    for count in (1, 2, 3):
        for chosen in combinations(SLOTS, count):
            observed = parse_equipment([g for g in gear() if g['Type'] not in chosen])
            assert compare_equipment(baseline, chosen, observed) == 'EQUIPMENT_MATCHED'
            assert compare_equipment(baseline, chosen, baseline) == 'REQUIRED_EQUIPMENT_PRESENT'
            untouched = next(s for s in SLOTS if s not in chosen)
            observed.pop(untouched)
            assert compare_equipment(baseline, chosen, observed) == 'NON_REQUIRED_EQUIPMENT_CHANGED'


@pytest.mark.parametrize('raw', [None, {}, [], [None], [dict(Type='신규부위')],
    [dict(Type='무기', Name=None, Grade='고대')], gear() + [gear()[0]]])
def test_invalid_snapshot_is_not_unequipped(raw):
    with pytest.raises(InvalidSnapshot):
        parse_equipment(raw)


def test_baseline_complete_and_secure_selection():
    baseline = parse_equipment(gear())
    for _ in range(30):
        chosen = required_slots(baseline)
        assert 1 <= len(chosen) <= 3 and len(set(chosen)) == len(chosen)
        assert set(chosen) <= set(SLOTS)
    baseline.pop('무기')
    with pytest.raises(EquipmentIncomplete):
        required_slots(baseline)


@pytest.mark.parametrize('field', ['Name', 'Grade'])
def test_nonrequired_baseline_change_blocks_match(field):
    raw = gear()[1:]
    raw[0][field] = 'changed'
    assert compare_equipment(parse_equipment(gear()), ('무기',), parse_equipment(raw)) == 'NON_REQUIRED_EQUIPMENT_CHANGED'


def test_tooltip_and_accessories_do_not_affect_proof():
    raw = gear()[1:]
    for item in raw:
        item['Tooltip'] = 'new durability'
    raw += [dict(Type='반지', Name='different')]
    assert compare_equipment(parse_equipment(gear()), ('무기',), parse_equipment(raw)) == 'EQUIPMENT_MATCHED'


@pytest.mark.parametrize('chosen', [(), ('무기', '무기'), ('other',), SLOTS])
def test_invalid_required_slots(chosen):
    with pytest.raises(InvalidSnapshot):
        compare_equipment(parse_equipment(gear()), chosen, {})


def transport(status=200, body=b'[{"ServerName":"sample"}]', media='application/json'):
    response = Mock()
    response.status_code = status
    response.headers = {'Content-Type': media}
    response.iter_content.return_value = [body]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return SimpleNamespace(get=Mock(return_value=response)), response


def test_transport_boundaries_and_path_encoding():
    wire, response = transport()
    provider = LostArkProvider('test-only', wire)
    assert provider.siblings('한글/이름?') == [{'ServerName': 'sample'}]
    args, kwargs = wire.get.call_args
    assert args[0].startswith('https://developer-lostark.game.onstove.com/characters/')
    assert '%2F' in args[0] and '%3F' in args[0]
    assert kwargs['timeout'] == (3, 5) and kwargs['allow_redirects'] is False
    assert kwargs['stream'] is True
    assert wire.get.call_count == 1
    response.__exit__.assert_called_once()
    provider.armory('sample')
    assert wire.get.call_args.args[0].endswith('/armories/characters/sample')


@pytest.mark.parametrize('status', [301, 401, 403, 404, 429, 500, 503])
def test_upstream_failures_not_empty_roster(status):
    wire, response = transport(status=status)
    with pytest.raises(ProviderUnavailable) as error:
        LostArkProvider('test-only', wire).siblings('sample')
    assert error.value.reason == ('LOSTARK_KEY_REJECTED' if status in (401,403) else 'UPSTREAM_RATE_LIMITED' if status == 429 else 'UPSTREAM_UNAVAILABLE')
    response.iter_content.assert_not_called()
    assert wire.get.call_count == 1


@pytest.mark.parametrize('body,media', [
    (b'null', 'application/json'), (b'[]', 'application/json'),
    (b'{}', 'application/json'), (b'"text"', 'application/json'),
    (b'<html>maintenance</html>', 'text/html'), (b'{bad', 'application/json'),
    (b'x' * (MAX_BODY_BYTES + 1), 'application/json'),
])
def test_invalid_or_oversized_responses(body, media):
    wire, _ = transport(body=body, media=media)
    with pytest.raises(ProviderUnavailable):
        LostArkProvider('test-only', wire).armory('sample')


def test_timeout_exception_is_sanitized_and_capacity_released():
    wire, _ = transport()
    wire.get.side_effect = requests.Timeout('secret URL and token')
    for _ in range(3):
        with pytest.raises(ProviderUnavailable) as error:
            LostArkProvider('test-only', wire).siblings('sample')
        assert str(error.value) == 'UPSTREAM_UNAVAILABLE'


def test_global_concurrency_bound(monkeypatch):
    from app.game_accounts import provider as module
    from threading import BoundedSemaphore
    gate = BoundedSemaphore(1)
    gate.acquire()
    monkeypatch.setattr(module, '_capacity', gate)
    wire, _ = transport()
    with pytest.raises(ProviderUnavailable, match='UPSTREAM_BUSY'):
        LostArkProvider('test-only', wire).siblings('sample')
    wire.get.assert_not_called()


@pytest.mark.parametrize('token', ['', None, 'x\ny', 'x\ry'])
def test_missing_or_invalid_key_does_not_call_provider(token):
    with pytest.raises(ProviderUnavailable, match='UPSTREAM_NOT_CONFIGURED'):
        LostArkProvider(token)
