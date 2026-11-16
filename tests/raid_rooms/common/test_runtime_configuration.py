"""One current runtime, isolated schema guards, and complete worker shutdown."""
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


def test_current_factories_have_independent_caches_and_one_contract():
    current,other=main.create_app(),main.create_app()
    expected=json.loads(Path('openapi/openapi.yaml').read_text())
    assert current.openapi()==other.openapi()==main.app.openapi()==expected
    assert not hasattr(main,'create_legacy_app') and not hasattr(main,'create_two_cycle_app')
    current.openapi_schema=None
    assert current.openapi()==expected
    marker=lambda:None
    current.dependency_overrides[marker]=marker
    assert marker not in other.dependency_overrides
    current.openapi()['info']['title']='isolated cache mutation'
    assert other.openapi()==expected


def test_current_workers_start_and_cancel_on_failure(monkeypatch):
    started,stopped,guards=[],[],[]
    async def worker(name):
        started.append(name)
        try:await asyncio.Event().wait()
        finally:stopped.append(name)
    monkeypatch.setattr(database,'session',lambda:nullcontext(object()))
    monkeypatch.setattr(readiness,'require_two_cycle_active',lambda db:guards.append('current'))
    monkeypatch.setattr(main,'run',lambda:worker('auth'))
    monkeypatch.setattr(main,'run_ownership_worker',lambda:worker('ownership'))
    def recruitment(processor):
        assert processor is cycle_worker.process_due
        return worker('recruitment')
    monkeypatch.setattr(main,'run_recruitment_worker',recruitment)
    async def execute():
        with pytest.raises(RuntimeError,match='test failure'):
            async with main.create_app().router.lifespan_context(main.create_app()):
                await asyncio.sleep(0)
                assert sorted(started)==['auth','ownership','recruitment']
                raise RuntimeError('test failure')
        assert sorted(stopped)==sorted(started)
    asyncio.run(execute());assert guards==['current']


@pytest.mark.parametrize('revision',[None,'0023_recruitment_resume','0032_beta_recruitment','0036_roster_presence','0037_server_analysis'])
def test_current_runtime_rejects_other_schemas_without_mutation(monkeypatch,revision):
    with isolated_app_database() as (engine,role,upgrade):
        if revision:upgrade(revision)
        monkeypatch.setattr(database,'engine',lambda:engine)
        tables=set(inspect(engine).get_table_names());before=table_digests(engine,tables)
        if revision=='0037_server_analysis':
            with TestClient(main.create_app()) as http:assert http.get('/docs').status_code==404
        else:
            with pytest.raises(Exception):
                with TestClient(main.create_app()):pass
        assert set(inspect(engine).get_table_names())==tables
        assert table_digests(engine,tables)==before
