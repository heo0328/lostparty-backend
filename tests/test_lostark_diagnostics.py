import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.game_accounts import diagnostics
from app.game_accounts.provider import ProviderUnavailable


def sample():
    return dict(ServerName='private-server', CharacterName='private-character',
                CharacterClassName='private-class', CharacterLevel=60, ItemAvgLevel='1,700.25')


def test_probe_success_contains_shape_only():
    row=sample()
    provider=SimpleNamespace(siblings=Mock(return_value=[row,dict(row,CharacterName='private-alt',ItemAvgLevel=None)]))
    code, report=diagnostics.check_summary(provider,'private-character')
    assert code==0 and report['status']=='passed'
    assert report['character_count']==2 and report['null_item_levels']==1
    assert report['field_types']['ItemAvgLevel']=={'null':1,'string':1}
    assert report['ownership_proof'] is False and report['roster_completeness_proven'] is False
    serialized=json.dumps(report)
    assert all(value not in serialized for value in ('private-character','private-alt','private-server','private-class','1,700.25'))
    provider.siblings.assert_called_once_with('private-character')


@pytest.mark.parametrize('raw', [None, [], [sample(),sample()],
    [dict(sample(),ItemAvgLevel='NaN')], [dict(sample(),CharacterLevel=True)],
    [dict(sample(),CharacterName='not-input')], [sample()]*201])
def test_probe_invalid_data_never_becomes_success_or_leaks(raw):
    provider=SimpleNamespace(siblings=Mock(return_value=raw))
    code, report=diagnostics.check_summary(provider,'private-character')
    assert code==1 and report['reason']=='UPSTREAM_INVALID_RESPONSE'
    assert 'private-' not in json.dumps(report)
    provider.siblings.assert_called_once()


def test_probe_failure_hides_untrusted_exception_message():
    provider=SimpleNamespace(siblings=Mock(side_effect=ProviderUnavailable('private-secret-url')))
    code, report=diagnostics.check_summary(provider,'private-character')
    assert code==1 and report['reason']=='UPSTREAM_UNAVAILABLE'
    assert 'private-' not in json.dumps(report)


def test_missing_key_never_prompts_or_calls_provider(monkeypatch,capsys):
    monkeypatch.setenv('LOSTARK_API_TOKEN','must-not-be-used')
    monkeypatch.setattr(diagnostics.sys.stdin,'isatty',lambda:False)
    provider=Mock();prompt=Mock()
    monkeypatch.setattr(diagnostics,'LostArkProvider',provider)
    monkeypatch.setattr(diagnostics.getpass,'getpass',prompt)
    assert diagnostics.main()==2
    assert json.loads(capsys.readouterr().out)['reason']=='INTERACTIVE_TERMINAL_REQUIRED'
    provider.assert_not_called();prompt.assert_not_called()


def test_non_tty_never_echoes_input_or_calls_provider(monkeypatch,capsys):
    monkeypatch.setenv('LOSTARK_API_TOKEN','test-only-placeholder')
    monkeypatch.setattr(diagnostics.sys.stdin,'isatty',lambda:False)
    provider=Mock();prompt=Mock()
    monkeypatch.setattr(diagnostics,'LostArkProvider',provider)
    monkeypatch.setattr(diagnostics.getpass,'getpass',prompt)
    assert diagnostics.main()==2
    assert json.loads(capsys.readouterr().out)['reason']=='INTERACTIVE_TERMINAL_REQUIRED'
    provider.assert_not_called();prompt.assert_not_called()


def test_cli_swallows_traceback_with_private_context(monkeypatch,capsys):
    monkeypatch.setenv('LOSTARK_API_TOKEN','test-only-placeholder')
    monkeypatch.setattr(diagnostics.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(diagnostics.sys.stderr,'isatty',lambda:True)
    monkeypatch.setattr(diagnostics.getpass,'getpass',lambda _: 'private-character')
    monkeypatch.setattr(diagnostics,'LostArkProvider',Mock(side_effect=RuntimeError('private-secret-url')))
    assert diagnostics.main()==1
    captured=capsys.readouterr()
    assert 'private-' not in captured.out+captured.err
    assert json.loads(captured.out)['reason']=='CHECK_UNAVAILABLE'
