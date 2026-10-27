"""Direct HTTP reference checks for #26, against disposable PostgreSQL only."""
import json
import runpy
import uuid
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.core.database import session, now
from app.raid_rooms.cycle_application_models import CycleApplication
from tests.test_application_display import client
from tests.test_application_composition import (current, candidate, ready, sources, imported, people, worlds,
    room, apply, approve)
from tests.test_raid_room_migrations import table_digests

CHECKS = runpy.run_path('docs/features/recruitment/participation/tools/validate-application-display.py')
REFERENCES = CHECKS['validate_detail_references']
VALIDATOR = CHECKS['VALIDATOR']


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items() if k not in ('server_now', 'server_time', 'evaluated_at')}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def response_pair(engine, viewer, rid, key):
    before = table_digests(engine, set(inspect(engine).get_table_names()))
    with client(viewer) as http:
        path = f'/v2/raid-rooms/{rid}/detail'
        expanded = http.get(path, params=dict(target_cycle_key=key, reader_profile='application-display-1'))
        basic = http.get(path, params=dict(target_cycle_key=key))
    assert expanded.status_code == basic.status_code == 200, expanded.json().get('error')
    value = expanded.json()
    VALIDATOR.validate(value)
    REFERENCES(value)
    REFERENCES(basic.json())
    common = deepcopy(value)
    common['data'].pop('my_application')
    assert normalize(common) == normalize(basic.json())
    assert table_digests(engine, set(before)) == before
    assert expanded.headers['cache-control'] == 'no-store'
    return value


@pytest.mark.parametrize('state', ['none', 'pending', 'expired', 'withdrawn', 'rejected',
                                 'cancelled', 'accepted_history', 'accepted_participating'])
def test_detail_states_reference_complete_http(current, state):
    engine, a, b = current
    rid, c, n = room(a)
    if state != 'none':
        ack = apply(b, rid, c)[1]['data']
        if state == 'accepted_participating':
            approve(a, ack, rid, c)
        elif state not in ('pending',):
            with session() as db, db.begin():
                app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
                stamp = now(db)
                if state == 'expired':
                    app.created_at, app.expires_at = stamp - timedelta(hours=1), stamp - timedelta(seconds=1)
                else:
                    app.state, app.ended_at = ('accepted' if state == 'accepted_history' else state), stamp
    value = response_pair(engine, b, rid, c)
    own = value['data']['my_application']
    if state == 'none':
        assert own is None
    else:
        assert own['state'] == ('accepted' if state.startswith('accepted') else state)
    assert value['data']['my_target_role'] == ('member' if state == 'accepted_participating' else 'none')


@pytest.mark.parametrize('variant', ['eight_next', 'bundle_current'])
def test_eight_and_bundle_http_references(current, variant):
    engine, a, b = current
    rid, c, n = room(a, eight=variant == 'eight_next', bundle=variant == 'bundle_current')
    key = n if variant == 'eight_next' else c
    approve(a, apply(b, rid, key)[1]['data'], rid, key)
    value = response_pair(engine, b, rid, key)
    assert len(value['data']['room']['items']) == (2 if variant == 'bundle_current' else 1)
    if variant == 'eight_next':
        assert value['data']['room']['app_capacity'] == 8
        assert {s['party_no'] for s in value['data']['formation_slots']} == {1, 2}


def test_completed_history_http_keeps_references(current):
    from tests.test_recruitment_cycle_times import scheduled
    from tests.test_recruitment_cycle_outcomes import complete
    engine, a, b = current
    rid, c, n = scheduled(a)
    complete(a, rid, c)
    value = response_pair(engine, a, rid, c)
    assert value['data']['formation_history']


def test_authored_historical_round_can_differ_from_current():
    examples = json.loads(Path('docs/features/recruitment/participation/examples/application-display-v1.examples.json').read_text())
    value = deepcopy(next(c['response'] for c in examples['examples'] if c['name'] == 'detail_pending'))
    member = value['data']['members'][0]
    old = deepcopy(member['assignments'][0])
    old.update(assignment_id='00000000-0000-0000-0000-000000000090',
               round_id='00000000-0000-0000-0000-000000000091', state='completed')
    member['assignments'].append(old)
    value['data']['formation_history'].append(dict(target_cycle_key=value['scope']['target_cycle_key'],
        round_id=old['round_id'], party_no=old['party_no'], slot_no=old['slot_no'],
        assignment_id=old['assignment_id'], status='completed', is_leader=True))
    VALIDATOR.validate(value)
    REFERENCES(value)
