"""Producer-to-HTTP item level evidence; synthetic PostgreSQL/users only."""
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import event, inspect

from app.core.database import session, now
from app.game_accounts.models import Account, Character
from app.groups.admission_core import display as shared_identity
from app.raid_rooms import application_display as display, cycle_lists
from app.raid_rooms.cycle_application_models import CycleApplication
from tests.test_application_composition import (current, candidate, ready, sources, imported, people, worlds,
    room, apply, actor, change_class, context, admission_request, commands)
from tests.test_application_display import client, page
from tests.test_raid_room_migrations import table_digests

KEYS = ('item_level', 'item_level_source', 'item_level_fetched_at')


def legacy(ack):
    with session() as db, db.begin():
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        saved = dict(app.display)
        for key in KEYS:
            saved.pop(key, None)
        app.display = saved
    return saved


def change_level(w, value):
    with session() as db, db.begin():
        char = db.get(Character, uuid.UUID(w['ids'][0]))
        char.summary = {**char.summary, 'item_level': value}


@pytest.mark.parametrize('role', ['dealer', 'support'])
def test_real_post_snapshot_storage_http_growth_and_ack(current, role):
    engine, a, b = current;rid, c, n = room(a)
    if role == 'support':change_class(b, '바드')
    with session() as db, db.begin():
        char = db.get(Character, uuid.UUID(b['ids'][0]))
        char.confirmed_at = now(db) - timedelta(hours=1)
        expected_time = char.confirmed_at
        expected_level = str(char.summary['item_level'])
        assert set(shared_identity(char)) == {'server_name', 'character_name', 'class_name'}
    body = admission_request(context(b, rid, c, 'apply', role)).model_dump(mode='json')
    key = str(uuid.uuid4())
    with client(b) as http:
        path = f'/v2/raid-rooms/{rid}/applications'
        first = http.post(path, json=body, headers={'Idempotency-Key': key})
        assert first.status_code == 201, first.json().get('error')
    ack = first.json()['data']
    with session() as db:
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        saved = deepcopy(app.display)
        assert saved['item_level'] == expected_level and saved['item_level_source'] == 'application_snapshot'
        assert datetime.fromisoformat(saved['item_level_fetched_at'].replace('Z', '+00:00')) == expected_time
        assert app.created_at > expected_time
    change_level(b, '1999.99999999999999999999')
    before = table_digests(engine, set(inspect(engine).get_table_names()))
    with client(a) as http:
        response = http.get(path, params=dict(target_cycle_key=c, reader_profile=display.PROFILE))
        assert response.status_code == 200
        assert response.json()['data']['items'][0]['display'] == saved
    assert table_digests(engine, set(before)) == before
    with client(b) as http:
        replay = http.post(path, json=body, headers={'Idempotency-Key': key})
        assert replay.status_code == 201 and replay.json() == first.json()
    with session() as db:
        assert db.get(CycleApplication, uuid.UUID(ack['application_id'])).display == saved


def test_legacy_current_saved_no_backfill_default_unchanged(current):
    engine, a, b = current;rid, c, n = room(a);ack = apply(b, rid, c)[1]['data'];old = legacy(ack)
    change_level(b, '1750.1234567890123456789')
    before = table_digests(engine, set(inspect(engine).get_table_names()))
    with client(a) as http:
        response = http.get(f'/v2/raid-rooms/{rid}/applications', params=dict(target_cycle_key=c, reader_profile=display.PROFILE))
        assert response.status_code == 200
        item = response.json()['data']['items'][0]
    assert item['display']['item_level'] == '1750.1234567890123456789'
    assert item['display']['item_level_source'] == 'current_saved'
    assert item['display']['item_level_fetched_at'] is not None
    assert {k: v for k, v in item['display'].items() if k not in KEYS} == old
    assert cycle_lists.applications(actor(a['uid']), c, rid=rid)['data']['items'][0]['display'] == old
    assert commands.application(actor(b['uid']), uuid.UUID(ack['application_id']))['data']['display'] == old
    assert table_digests(engine, set(before)) == before
    with session() as db:
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        assert app.display == old and app.revision == 1


@pytest.mark.parametrize('condition', ['ownership', 'owner', 'missing', 'suspect', 'retired', 'no_level'])
def test_legacy_boundaries_unavailable(current, condition):
    _, a, b = current;rid, c, n = room(a);ack = apply(b, rid, c)[1]['data'];legacy(ack)
    with session() as db, db.begin():
        char = db.get(Character, uuid.UUID(b['ids'][0]));account = db.get(Account, char.account_id)
        if condition == 'ownership':account.ownership_revision += 1
        elif condition == 'owner':account.owner_id = a['uid']
        elif condition == 'missing':
            app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
            app.selection = {**app.selection, 'character_id': str(uuid.uuid4())}
        elif condition == 'suspect':char.status = 'suspect'
        elif condition == 'retired':char.lifecycle_state = 'retired'
        else:char.summary = {**char.summary, 'item_level': None}
    item = page(a, rid, c)['data']['items'][0]
    assert {k: item['display'][k] for k in KEYS} == dict(item_level=None, item_level_source='unavailable', item_level_fetched_at=None)


def test_saved_snapshot_survives_ownership_and_unknown_time(current):
    _, a, b = current;rid, c, n = room(a);ack = apply(b, rid, c)[1]['data']
    with session() as db, db.begin():
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        app.display = {**app.display, 'item_level': '1700', 'item_level_fetched_at': None}
        char = db.get(Character, uuid.UUID(b['ids'][0]));db.get(Account, char.account_id).ownership_revision += 1
    item = page(a, rid, c)['data']['items'][0]
    assert item['display']['item_level'] == '1700'
    assert item['display']['item_level_source'] == 'application_snapshot'
    assert item['display']['item_level_fetched_at'] is None
    assert item['display_reason'] == 'APPLICATION_CONTEXT_CHANGED'


def test_level_change_keeps_cursor_scope_and_query_count(current, people):
    engine, a, b = current;rid, c, n = room(a);ack = apply(b, rid, c)[1]['data'];legacy(ack)
    for i in range(2):legacy(apply(people('level-page-'+str(i)), rid, c)[1]['data'])
    queries = []
    def count(*args):queries.append(1)
    event.listen(engine, 'before_cursor_execute', count)
    try:
        first = page(a, rid, c, limit=1);one = len(queries);queries.clear()
        page(a, rid, c, limit=50);assert len(queries) == one
    finally:event.remove(engine, 'before_cursor_execute', count)
    assert first['data']['next_cursor']
    change_level(b, '1900')
    assert page(a, rid, c, limit=1, cursor=first['data']['next_cursor'])['data']['items']


@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '-1', True, 'invalid', '', None])
def test_invalid_level_never_becomes_zero_or_other_value(bad):
    char = SimpleNamespace(summary={'item_level': bad}, confirmed_at=None, status='confirmed', lifecycle_state='active')
    result = display.level_display({}, char, connected=True)
    assert result == dict(item_level=None, item_level_source='unavailable', item_level_fetched_at=None)
    assert display.level_display({'item_level': 'invalid'}, SimpleNamespace(
        summary={'item_level': '1800'}, confirmed_at=None, status='confirmed', lifecycle_state='active'), connected=True)['item_level'] is None
