"""Server secret boundaries use only disposable synthetic test files."""
from pathlib import Path
import pytest
from app.core.config import settings
from app.game_accounts.provider_io import credentials
from app.game_accounts.common.support import GameError


def test_snapshot_is_redacted_and_generation_rotates(tmp_path,monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(credentials,'settings',SimpleNamespace(secret_dir=str(tmp_path)))
    (tmp_path/'lostark-fingerprint.key').write_bytes(b'x'*32)
    token='synthetic.first.token'
    (tmp_path/'lostark-api-token').write_text(token)
    first=credentials.capture()
    assert token not in repr(first) and first.generation not in repr(first)
    assert credentials.capture()==first
    (tmp_path/'lostark-api-token').write_text('synthetic.second.token')
    assert credentials.capture().generation!=first.generation
    with pytest.raises(GameError,match='SERVER_KEY_CHANGED'):credentials.current(first)


@pytest.mark.parametrize('value',[None,'','bad\nheader','x'*16385,'비ASCII'])
def test_missing_or_invalid_server_configuration_is_safe(tmp_path,monkeypatch,value):
    from types import SimpleNamespace
    monkeypatch.setattr(credentials,'settings',SimpleNamespace(secret_dir=str(tmp_path)))
    (tmp_path/'lostark-fingerprint.key').write_bytes(b'x'*32)
    if value is not None:(tmp_path/'lostark-api-token').write_text(value)
    with pytest.raises(GameError) as caught:credentials.capture()
    assert caught.value.code=='UPSTREAM_NOT_CONFIGURED' and caught.value.status==503
    assert not value or value not in str(caught.value)
