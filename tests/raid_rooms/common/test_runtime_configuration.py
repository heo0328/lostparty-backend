"""Runtime selection, independent apps and guarded starts on disposable DBs."""
import asyncio
import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app import main
from app.core import database
from app.raid_rooms.common import readiness, cycle_worker
from tests.raid_rooms.common.test_raid_room_migrations import isolated_app_database, table_digests


def test_factories_are_independent_and_both_contracts_unchanged():
    current = main.create_app()
    other = main.create_app()
    legacy = main.create_legacy_app()
    expected = json.loads(Path('openapi/openapi.yaml').read_text())
    old = json.loads(Path('openapi/legacy.openapi.yaml').read_text())
    assert current.openapi() == main.app.openapi() == main.create_two_cycle_app().openapi() == expected
    assert legacy.openapi() == old
    # A second call must reuse the decorated cache rather than decorating it
    # again (which would recursively add Participation_/RosterIssues_ variants).
    for _ in range(3):
        assert current.openapi() == expected
        assert main.app.openapi() == expected
        assert legacy.openapi() == old
    current.openapi_schema = None
    assert current.openapi() == expected
    marker = lambda: None
    current.dependency_overrides[marker] = marker
    assert marker not in other.dependency_overrides and marker not in legacy.dependency_overrides
    current.openapi()['info']['title'] = 'isolated cache mutation'
    assert other.openapi() == expected and legacy.openapi() == old


@pytest.mark.parametrize('legacy', [False, True])
def test_only_selected_worker_starts_and_all_tasks_cancel_on_error(monkeypatch, legacy):
    started, stopped, guards = [], [], []

    async def worker(name):
        started.append(name)
        try:
            await asyncio.Event().wait()
        finally:
            stopped.append(name)

    monkeypatch.setattr(database, 'session', lambda: nullcontext(object()))
    monkeypatch.setattr(readiness, 'require_active', lambda db: guards.append('legacy'))
    monkeypatch.setattr(readiness, 'require_two_cycle_active', lambda db: guards.append('current'))
    monkeypatch.setattr(main, 'run', lambda: worker('auth'))
    monkeypatch.setattr(main, 'run_ownership_worker', lambda: worker('ownership'))

    def recruitment(*args):
        assert args == (() if legacy else (cycle_worker.process_due,))
        return worker('recruitment')

    monkeypatch.setattr(main, 'run_recruitment_worker', recruitment)

    async def execute():
        application = main.create_legacy_app() if legacy else main.create_app()
        with pytest.raises(RuntimeError, match='test failure'):
            async with application.router.lifespan_context(application):
                await asyncio.sleep(0)
                assert sorted(started) == ['auth', 'ownership', 'recruitment']
                raise RuntimeError('test failure')
        assert sorted(stopped) == sorted(started)

    asyncio.run(execute())
    assert guards == ['legacy' if legacy else 'current']


@pytest.mark.parametrize('revision', [
    None, '0023_recruitment_resume', '0024_recruitment_cycles', '0036_roster_presence',
])
def test_explicit_new_install_and_supported_schema_guard(monkeypatch, revision):
    with isolated_app_database() as (engine, role, upgrade):
        if revision:
            upgrade(revision)
        monkeypatch.setattr(database, 'engine', lambda: engine)
        tables = set(inspect(engine).get_table_names())
        before = table_digests(engine, tables)
        for factory, supported in [
            (main.create_app, revision == '0036_roster_presence'),
            (main.create_legacy_app, revision == '0023_recruitment_resume'),
        ]:
            if supported:
                with TestClient(factory()) as http:
                    assert http.get('/docs').status_code == 404
            else:
                with pytest.raises(Exception):
                    with TestClient(factory()):
                        pass
            assert set(inspect(engine).get_table_names()) == tables
            assert table_digests(engine, tables) == before
