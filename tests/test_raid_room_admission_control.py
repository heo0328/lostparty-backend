"""Candidate HTTP controls: pause new admissions, retain replay/read/recovery."""
import uuid

import pytest
from sqlalchemy import select, func

from app.core.database import session
from app.raid_rooms import runtime, usage
from app.raid_rooms.models import Room, Application
from tests.test_raid_room_foundation import people, worlds
from tests.test_raid_room_http import (
    http, post, err, create, create_body, detail, context, membership, decision,
)


@pytest.mark.parametrize('setting', [None, 'false', '0', 'invalid-test-config'])
def test_default_paused_create_fails_without_new_room_and_can_retry(http, people, monkeypatch, setting):
    a = people('a')
    body, key = create_body(a), uuid.uuid4()
    if setting is None:
        monkeypatch.delenv(runtime.SETTING, raising=False)
    else:
        monkeypatch.setenv(runtime.SETTING, setting)
    err(post(http, a, 'raid-rooms', body, key), 503, 'SERVICE_UNAVAILABLE')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Room)) == 0
        assert usage.count(db, a['uid']) == 0
    monkeypatch.setenv(runtime.SETTING, 'true')
    first = post(http, a, 'raid-rooms', body, key)
    assert first.status_code == 201, first.text
    monkeypatch.setenv(runtime.SETTING, 'false')
    replay = post(http, a, 'raid-rooms', body, key)
    assert replay.status_code == 201 and replay.json() == first.json()
    assert http.get('/v1/raid-rooms/'+first.json()['room_id']).status_code == 200


def test_pause_join_context_retry_replay_transfer_leave_end_and_usage(http, people, monkeypatch):
    a, b = people('a'), people('b')
    rid = create(http, a)
    body, key = context(http, b, rid), uuid.uuid4()
    monkeypatch.setenv(runtime.SETTING, 'false')
    result = http.get('/v1/raid-rooms/'+rid+'/admission-context', headers=b['headers'],
                      params=dict(character_id=b['ids'][0], selected_role='dealer', party_no=1, intent='join'))
    assert result.status_code == 200
    assert result.json()['eligibility'] == {'allowed': False, 'reason': 'SERVICE_UNAVAILABLE'}
    err(post(http, b, f'raid-rooms/{rid}/join', body, key), 503, 'SERVICE_UNAVAILABLE')
    with session() as db:
        assert usage.count(db, b['uid']) == 0
    monkeypatch.setenv(runtime.SETTING, 'true')
    joined = post(http, b, f'raid-rooms/{rid}/join', body, key)
    assert joined.status_code == 200, joined.text
    monkeypatch.setenv(runtime.SETTING, 'false')
    assert post(http, b, f'raid-rooms/{rid}/join', body, key).json() == joined.json()
    with session() as db:
        assert usage.limits_snapshot(db, b['uid'])['usage']['raid_rooms']['used'] == 1
    target = next(m for m in detail(http, a, rid)['members'] if not m['is_me'])
    assert post(http, a, f'raid-rooms/{rid}/leadership-transfer', membership(http, a, rid, target=target)).status_code == 200
    assert post(http, a, f'raid-rooms/{rid}/leave', membership(http, a, rid)).status_code == 200
    assert post(http, b, f'raid-rooms/{rid}/end', membership(http, b, rid)).status_code == 200
    with session() as db:
        assert usage.count(db, a['uid']) == usage.count(db, b['uid']) == 0


def test_paused_apply_and_approve_but_reject_withdraw_and_replay_survive(http, people, monkeypatch):
    a, b, c, d = [people(x) for x in 'abcd']
    rid = create(http, a, mode='leader_only')
    body, key = context(http, d, rid, intent='apply'), uuid.uuid4()
    aids = []
    for w in (b, c):
        result = post(http, w, f'raid-rooms/{rid}/applications', context(http, w, rid, intent='apply'))
        assert result.status_code == 201
        aids.append(result.json()['application_id'])
    cmd, approval_key = decision(http, a, rid, aids[0]), uuid.uuid4()
    monkeypatch.setenv(runtime.SETTING, 'false')
    err(post(http, d, f'raid-rooms/{rid}/applications', body, key), 503, 'SERVICE_UNAVAILABLE')
    err(post(http, a, f'raid-room-applications/{aids[0]}/approve', cmd, approval_key), 503, 'SERVICE_UNAVAILABLE')
    private = detail(http, a, rid)
    assert private['permissions']['approve'] == {'allowed': False, 'reason': 'SERVICE_UNAVAILABLE'}
    assert private['permissions']['reject']['allowed']
    application = http.get('/v1/raid-room-applications/'+aids[0], headers=a['headers']).json()
    assert application['permissions']['approve'] == {'allowed': False, 'reason': 'SERVICE_UNAVAILABLE'}
    assert application['permissions']['reject']['allowed']
    with session() as db:
        assert db.get(Application, uuid.UUID(aids[0])).state == 'pending'
        assert usage.count(db, b['uid']) == 0
    withdrawn = post(http, c, f'raid-room-applications/{aids[1]}/withdraw', {'expected_application_revision': 1})
    assert withdrawn.status_code == 200
    monkeypatch.setenv(runtime.SETTING, 'true')
    approved = post(http, a, f'raid-room-applications/{aids[0]}/approve', cmd, approval_key)
    assert approved.status_code == 200, approved.text
    new = post(http, d, f'raid-rooms/{rid}/applications', context(http, d, rid, intent='apply'), key)
    # Same key with a refreshed context is a different request body; use a fresh key.
    assert new.status_code == 409
    new = post(http, d, f'raid-rooms/{rid}/applications', context(http, d, rid, intent='apply'))
    assert new.status_code == 201
    monkeypatch.setenv(runtime.SETTING, 'false')
    assert post(http, a, f'raid-room-applications/{aids[0]}/approve', cmd, approval_key).json() == approved.json()
    aid = new.json()['application_id']
    assert post(http, a, f'raid-room-applications/{aid}/reject', decision(http, a, rid, aid)).status_code == 200
    assert http.get('/v1/raid-rooms/'+rid).json()['member_count'] == 2


def test_pause_does_not_change_candidate_contract_or_expose_main_routes(http, monkeypatch):
    before = http.app.openapi()
    monkeypatch.setenv(runtime.SETTING, 'false')
    http.app.openapi_schema = None
    assert http.app.openapi() == before
    from app.main import app
    assert all(getattr(route.endpoint,'__module__','')!='app.raid_rooms.router' for route in app.routes)
