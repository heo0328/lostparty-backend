import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.game_accounts import ownership_diagnostics as d
from app.game_accounts.equipment import SLOTS
from app.game_accounts.provider import ProviderUnavailable


def snapshot(missing=()):
    return {'ArmoryProfile': {'CharacterName': 'private-name', 'ServerName': 'private-server'},
            'ArmoryEquipment': [dict(Type=slot, Name='private-item', Grade='private-grade')
                                for slot in SLOTS if slot not in missing]}


def probe(monkeypatch, stages):
    monkeypatch.setattr(d, 'required_slots', lambda gear: ('무기',))
    provider = SimpleNamespace(armory=Mock(side_effect=stages))
    return d.EquipmentProbe(provider, 'private-name'), provider


def test_three_observations_no_identity_or_equipment_payload_leak(monkeypatch):
    p, provider = probe(monkeypatch, [snapshot(), snapshot(('무기',)), snapshot()])
    reports = [p.baseline(), p.changed(), p.restored()]
    assert reports[-1]['status'] == 'ready_for_review'
    assert reports[-1]['provider_calls'] == 3
    text = json.dumps(reports)
    assert 'private-' not in text
    for report in reports:
        assert report['ownership_proof'] is report['canonical_binding'] is report['retirement_proof'] is False
    assert provider.armory.call_count == 3
    with pytest.raises(d.ObservationRejected): p.restored()
    assert provider.armory.call_count == 3


@pytest.mark.parametrize('missing,expected', [((), 'REQUIRED_EQUIPMENT_PRESENT'),
    (('무기','장갑'), 'NON_REQUIRED_EQUIPMENT_CHANGED')])
def test_unchanged_or_extra_missing_never_ready(monkeypatch, missing, expected):
    p,_=probe(monkeypatch,[snapshot(),snapshot(missing),snapshot()]);p.baseline()
    assert p.changed()['comparison']==expected
    assert p.restored()['status']=='not_ready'


@pytest.mark.parametrize('stage', ['baseline','changed','restored'])
def test_null_equipment_is_failure_not_unequipped(monkeypatch, stage):
    bad=snapshot();bad['ArmoryEquipment']=None
    stages=[snapshot(),snapshot(('무기',)),snapshot()]
    stages[['baseline','changed','restored'].index(stage)]=bad
    p,_=probe(monkeypatch,stages)
    with pytest.raises(d.ObservationRejected,match='EQUIPMENT_INVALID'):
        for method in ['baseline','changed','restored']:getattr(p,method)()


def test_profile_changed_or_unknown_type_rejected(monkeypatch):
    for mutate,reason in [(lambda s:s['ArmoryProfile'].update(ServerName='other'),'PROFILE_MISMATCH'),
                          (lambda s:s['ArmoryEquipment'][0].update(Type='private-unknown'),'EQUIPMENT_INVALID')]:
        bad=snapshot(('무기',));mutate(bad)
        p,_=probe(monkeypatch,[snapshot(),bad]);p.baseline()
        with pytest.raises(d.ObservationRejected,match=reason):p.changed()


def test_deadline_no_provider_call_and_no_repeat(monkeypatch):
    clock=[0];p,provider=probe(monkeypatch,[snapshot()]);p._clock=lambda:clock[0];p.baseline();clock[0]=600
    with pytest.raises(d.ObservationRejected,match='OBSERVATION_EXPIRED'):p.changed()
    assert provider.armory.call_count==1


def test_restoration_difference_no_ready(monkeypatch):
    changed=snapshot();changed['ArmoryEquipment'][0]['Name']='new-private-item'
    p,_=probe(monkeypatch,[snapshot(),snapshot(('무기',)),changed]);p.baseline();p.changed()
    assert p.restored()['status']=='not_ready'


def test_incomplete_baseline_and_invalid_sequence(monkeypatch):
    p,provider=probe(monkeypatch,[snapshot(('무기',))])
    with pytest.raises(d.ObservationRejected,match='INVALID_STAGE'):p.changed()
    assert provider.armory.call_count==0
    with pytest.raises(d.ObservationRejected,match='BASELINE_INCOMPLETE'):p.baseline()


def test_non_tty_no_prompt_or_api(monkeypatch,capsys):
    monkeypatch.setattr(d.sys.stdin,'isatty',lambda:False)
    prompt=Mock();provider=Mock();monkeypatch.setattr(d.getpass,'getpass',prompt);monkeypatch.setattr(d,'LostArkProvider',provider)
    assert d.main()==2
    prompt.assert_not_called();provider.assert_not_called()
    assert json.loads(capsys.readouterr().out)['reason']=='INTERACTIVE_TERMINAL_REQUIRED'


def test_hidden_input_failure_stops_before_echo_or_api(monkeypatch,capsys):
    import warnings
    monkeypatch.setattr(d.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(d.sys.stderr,'isatty',lambda:True)
    def broken_terminal(*args):
        warnings.warn('cannot hide input', d.getpass.GetPassWarning)
        pytest.fail('must stop before getpass fallback reads input')
    provider=Mock()
    monkeypatch.setattr(d.getpass,'getpass',broken_terminal)
    monkeypatch.setattr(d,'LostArkProvider',provider)
    assert d.main()==1
    provider.assert_not_called()
    assert json.loads(capsys.readouterr().out)['reason']=='CHECK_UNAVAILABLE'


@pytest.mark.parametrize('error,reason',[(ProviderUnavailable('private-token-url'),'CHECK_UNAVAILABLE'),
    (ProviderUnavailable('UPSTREAM_RATE_LIMITED'),'UPSTREAM_RATE_LIMITED'),(RuntimeError('private-secret'),'CHECK_UNAVAILABLE')])
def test_cli_errors_sanitized_without_retry(monkeypatch,capsys,error,reason):
    monkeypatch.setattr(d.sys.stdin,'isatty',lambda:True);monkeypatch.setattr(d.sys.stderr,'isatty',lambda:True)
    monkeypatch.setattr(d.getpass,'getpass',lambda *a:'private-secret')
    monkeypatch.setattr('builtins.input',lambda *a:'')
    provider=SimpleNamespace(armory=Mock(side_effect=error));monkeypatch.setattr(d,'LostArkProvider',lambda *a:provider)
    assert d.main()==1
    output=capsys.readouterr().out
    assert json.loads(output)['reason']==reason and 'private' not in output
    assert provider.armory.call_count==1
