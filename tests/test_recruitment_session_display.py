"""Opt-in prejoin display: synthetic restricted PostgreSQL, no live accounts."""
import json
import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import insert, select

from app.core.database import session, now
from app.raid_rooms import command_context as opaque, session_display as display
from app.raid_rooms import cycle_opening as opening, cycle_continuation as continuation
from app.raid_rooms import cycle_wire as wire, cycle_schemas as inputs
from tests.test_recruitment_cycle_planning import (
    planning, consent, lifecycle, candidate, ready, sources, imported, people, worlds,
    scheduled, plan, preflight, request, creation, actor, add_member, cancel_member,
    fingerprints, denied, commands, cycles, next_key, change_body, character,
    service, coordinated, graph,
)
from tests.test_recruitment_cycle_commands import create_room, admission_request
from tests.test_recruitment_cycle_lifecycle import opening_body, continue_body, scoped
from tests.test_recruitment_cycle_times_http import client
from tests.test_recruitment_cycle_outcomes import outcomes
from docs.design.validate_issue13_prejoin_session_display import validate


def admission(w, rid, key, intent='join', include=True, cid=None):
    return commands.get_context(actor(w['uid']), rid, key, uuid.UUID(cid or w['ids'][0]),
                                'dealer', intent, include)


def checked(ctx, kind):
    value = ctx['data']['session_display']
    validate(value)
    assert value['kind'] == kind
    token = opaque.unseal(ctx['data']['context_token'])
    assert token['session_display_version'] == 1
    assert len(ctx['data']['context_token'].encode()) <= 4096
    return value


def test_three_gets_opt_in_strict_and_legacy_shape_readonly(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    add_member(b, rid, c)
    routes = [
        (f'/v2/raid-rooms/{rid}/admission-context', b,
         dict(target_cycle_key=n, character_id=b['ids'][0], selected_role='dealer', intent='join'),
         wire.OutputContract3GetV2RaidRoomsRoomIdAdmissionContext, 'existing'),
        (f'/v2/me/raid-rooms/{rid}/continuation-context', b,
         dict(target_cycle_key=n, action='join'), wire.ContinuationContext, 'existing'),
        (f'/v2/me/raid-rooms/{rid}/opening-context', a,
         dict(target_cycle_key=n, intent='open'), wire.OpeningContext, 'none'),
    ]
    before = fingerprints(engine)
    for path, w, query, legacy, kind in routes:
        with client(w) as http:
            for extra in ({}, {'include_session_display': 'false'}):
                result = http.get(path, params=query | extra)
                assert result.status_code == 200, result.json().get('error')
                value = result.json()
                legacy.model_validate(value)
                assert 'session_display' not in value['data']
                assert 'session_display_version' not in opaque.unseal(value['data']['context_token'])
            result = http.get(path, params=query | {'include_session_display': 'true'})
            assert result.status_code == 200, result.json().get('error')
            checked(result.json(), kind)
            assert result.headers['cache-control'] == 'no-store'
            for bad in ('', 'null', '1', '0', 'TRUE', 'yes'):
                assert http.get(path, params=query | {'include_session_display': bad}).status_code == 400
            repeated = list(query.items()) + [('include_session_display', 'true'), ('include_session_display', 'false')]
            assert http.get(path, params=repeated).status_code == 400
    assert fingerprints(engine) == before


def test_actual_choices_times_digest_stable_and_original_ack(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a, alternatives=2)
    ctx = admission(b, rid, n)
    actual = checked(ctx, 'existing')
    assert len(actual['sessions']) == 2 and actual['previews'] == []
    assert actual['target_cycle_key'] == n and actual['target_generation'] == 1
    for sess, choice in zip(actual['sessions'], ctx['data']['session_choices']):
        assert {k: sess[k] for k in choice} == choice
        assert sess['state'] in ('unconfirmed', 'confirmed') and sess['starts_at'] and sess['ends_at']
    assert checked(admission(b, rid, n), 'existing')['display_revision'] == actual['display_revision']
    body = admission_request(ctx, target_session_ids=[s['session_id'] for s in actual['sessions']])
    command = uuid.uuid4()
    ack = commands.admit(actor(b['uid']), rid, command, body)
    with session() as db, db.begin():
        sess = db.get(graph.Session, uuid.UUID(actual['sessions'][0]['session_id']))
        sess.ends_at += timedelta(minutes=5)
        sess.schedule_revision += 1
    before = fingerprints(engine)
    assert commands.admit(actor(b['uid']), rid, command, body) == ack
    assert fingerprints(engine) == before


@pytest.mark.parametrize('change', ['ends_at', 'revision', 'schedule_revision', 'state', 'head'])
def test_admission_rejects_changed_display_without_target_revision_change(planning, change):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    ctx = admission(b, rid, n)
    sess_id = uuid.UUID(checked(ctx, 'existing')['sessions'][0]['session_id'])
    with session() as db, db.begin():
        sess = db.get(graph.Session, sess_id)
        if change == 'ends_at': sess.ends_at += timedelta(minutes=5)
        elif change in ('revision', 'schedule_revision'): setattr(sess, change, getattr(sess, change) + 1)
        elif change == 'state': sess.state = 'unconfirmed' if sess.state == 'confirmed' else 'confirmed'
        else:
            binding = db.get(graph.SessionBinding, sess_id)
            db.get(graph.ScheduleHead, binding.group_id).active = False
    before = fingerprints(engine)
    denied('SELECTION_CONTEXT_CHANGED', commands.admit, actor(b['uid']), rid, uuid.uuid4(), admission_request(ctx))
    assert fingerprints(engine) == before


def test_old_unmarked_token_keeps_original_calculation(planning):
    _, a, b = planning
    rid, c, n = scheduled(a)
    ctx = admission(b, rid, n, include=False)
    assert 'session_display_version' not in opaque.unseal(ctx['data']['context_token'])
    with session() as db, db.begin():
        row = db.scalar(select(graph.Session).where(graph.Session.id == uuid.UUID(ctx['data']['session_choices'][0]['session_id'])))
        row.ends_at += timedelta(minutes=5)
    assert commands.admit(actor(b['uid']), rid, uuid.uuid4(), admission_request(ctx))[0] == 200


def test_continuation_actual_and_decline_none_with_original_bodies(planning):
    _, a, b = planning
    rid, c, n = scheduled(a)
    add_member(b, rid, c)
    ctx = continuation.get(actor(b['uid']), rid, n, include_session_display=True)
    actual = checked(ctx, 'existing')
    assert len(actual['sessions']) == 1 and ctx['data']['target_session_ids'] == []
    decline = continuation.get(actor(b['uid']), rid, n, action='decline', include_session_display=True)
    checked(decline, 'none')
    assert continuation.execute(actor(b['uid']), rid, uuid.uuid4(), continue_body(ctx))[0] == 200


def test_continuation_and_character_bind_display_changes(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    add_member(b, rid, c)
    ctx = continuation.get(actor(b['uid']), rid, n, include_session_display=True)
    replacement = admission(a, rid, n, 'change_character', cid=a['ids'][1])
    change = change_body(replacement, plan(a, rid, n))
    with session() as db, db.begin():
        sess = db.get(graph.Session, uuid.UUID(ctx['data']['session_display']['sessions'][0]['session_id']))
        sess.ends_at += timedelta(minutes=5)
    before = fingerprints(engine)
    denied('TARGET_CONTEXT_STALE', continuation.execute, actor(b['uid']), rid, uuid.uuid4(), continue_body(ctx))
    denied('TARGET_CONTEXT_STALE', character.execute, actor(a['uid']), rid, uuid.uuid4(), change)
    assert fingerprints(engine) == before


@pytest.mark.parametrize('mode,occurrence,count,scope,materialization', [
    ('manual', 'each', 2, 'selected_weekdays', 'on_open'),
    ('manual', 'one_of', 1, 'selected_weekdays', 'on_open'),
    ('manual', 'one_of', 2, 'selected_weekdays', 'after_group_selection'),
    ('coordinated', 'one_of', 1, 'selected_weekdays', 'after_coordination'),
    ('coordinated', 'one_of', 0, 'any_current_cycle', 'after_coordination'),
    ('unscheduled', 'one_of', 1, 'selected_weekdays', 'not_scheduled'),
])
def test_opening_preview_materialization_readonly_and_target_dates(planning, mode, occurrence, count, scope, materialization):
    engine, a, b = planning
    room = create_room(a, combined=False, bundle=True)
    rid = uuid.UUID(room['room_id']); c = room['created_cycles'][0]['target_cycle_key']; n = next_key()
    item_ids = [v['item_id'] for v in plan(a, rid, c)['data']['game_items']]
    groups = coordinated(a, rid, c, planning_mode=mode, occurrence_mode=occurrence, day_scope=scope,
        auto_confirm_additional_members=1 if mode == 'coordinated' else None,
        alternatives=[dict(client_alternative_key=f'preview-{i}', existing_session_id=None,
            expected_session_revision=None, weekday=3, starts_local='00:05' if mode == 'manual' else None,
            leader_latest_start_local='05:00' if mode == 'coordinated' else None,
            item_ids=item_ids) for i in range(count)])
    service.edit(actor(a['uid']), rid, uuid.uuid4(), groups)
    before = fingerprints(engine)
    ctx = opening.get(actor(a['uid']), rid, n, 'open', include_session_display=True)
    preview = checked(ctx, 'opening_preview')
    assert preview['room_cycle_id'] == ctx['data']['prospective_room_cycle_id']
    assert preview['target_generation'] == ctx['data']['prospective_generation']
    assert preview['plan_revision'] is None and preview['sessions'] == []
    assert len(preview['previews']) == 1
    alternatives = preview['previews'][0]['alternatives']
    assert len(alternatives) == count
    for alt in alternatives:
        assert alt['session_id'] is None and alt['materialization'] == materialization
        if mode == 'manual':
            expected = graph.local_start(n, 3, '00:05')
            assert datetime.fromisoformat(alt['starts_at'].replace('Z', '+00:00')) == expected
            assert alt['time_state'] == 'bounded'
        else: assert alt['time_state'] == 'undetermined'
    assert fingerprints(engine) == before
    body = opening_body(ctx); command = uuid.uuid4()
    result = opening.execute(actor(a['uid']), rid, command, body)
    view = plan(a, rid, n)['data']
    assert len(view['sessions']) == (count if materialization == 'on_open' else 0)
    assert all(p['confirmation_state'] == 'confirmation_pending' for p in view['my_participations'])
    assert opening.execute(actor(a['uid']), rid, command, body) == result


def test_preview_source_revision_and_settings_stale_reopen_and_noop(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    old_ids = {v['session_id'] for v in checked(admission(b, rid, n), 'existing')['sessions']}
    cancel_member(a, rid, n)
    ctx = opening.get(actor(a['uid']), rid, n, 'reopen', include_session_display=True)
    preview = checked(ctx, 'opening_preview')
    assert preview['target_generation'] == 2
    with session() as db, db.begin():
        source = db.scalar(select(commands.RoomCycle).where(commands.RoomCycle.room_id == rid, commands.RoomCycle.cycle_key == date.fromisoformat(c)))
        group = graph.groups(db, source)[0]
        group.revision += 1
    before = fingerprints(engine)
    denied('TARGET_CONTEXT_STALE', opening.execute, actor(a['uid']), rid, uuid.uuid4(), opening_body(ctx, 'reopen'))
    assert fingerprints(engine) == before
    fresh = opening.get(actor(a['uid']), rid, n, 'reopen', include_session_display=True)
    opening.execute(actor(a['uid']), rid, uuid.uuid4(), opening_body(fresh, 'reopen'))
    actual = checked(admission(b, rid, n), 'existing')
    assert actual['target_generation'] == 2
    assert old_ids.isdisjoint(v['session_id'] for v in actual['sessions'])
    noop = opening.get(actor(a['uid']), rid, n, 'open', include_session_display=True)
    checked(noop, 'none')
    assert opening.execute(actor(a['uid']), rid, uuid.uuid4(), opening_body(noop))[1]['data']['outcome'] == 'noop'


def test_full_utf8_response_cap_returns_413_no_truncation(planning, monkeypatch):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    path = f'/v2/raid-rooms/{rid}/admission-context'
    query = dict(target_cycle_key=n, character_id=b['ids'][0], selected_role='dealer', intent='join')
    with client(b) as http:
        result = http.get(path, params=query | {'include_session_display': 'true'})
        assert result.status_code == 200
        size = len(result.content)
        monkeypatch.setattr(display, 'MAX_RESPONSE_BYTES', size)
        assert http.get(path, params=query | {'include_session_display': 'true'}).status_code == 200
        monkeypatch.setattr(display, 'MAX_RESPONSE_BYTES', size - 1)
        before = fingerprints(engine)
        response = http.get(path, params=query | {'include_session_display': 'true'})
        assert response.status_code == 413 and response.json()['error']['code'] == 'RESPONSE_TOO_LARGE'
        assert response.headers['cache-control'] == 'no-store'
        assert fingerprints(engine) == before
        assert http.get(path, params=query).status_code == 200


def test_real_authentication_required_and_private_plan_stays_private(planning):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    _, a, b = planning
    rid, c, n = scheduled(a)
    app = FastAPI(); register(app); app.include_router(router); app.middleware('http')(no_store)
    path = f'/v2/raid-rooms/{rid}/admission-context'
    query = dict(target_cycle_key=n, character_id=b['ids'][0], selected_role='dealer', intent='join', include_session_display='true')
    with TestClient(app) as http:
        assert http.get(path, params=query).status_code == 401
        assert http.get(path, params=query, headers={'Authorization': 'Bearer invalid'}).status_code == 401
        response = http.get(path, params=query, headers=b['headers'])
        assert response.status_code == 200, response.json().get('error')
        checked(response.json(), 'existing')
        assert http.get(f'/v2/me/raid-rooms/{rid}/plan', params={'target_cycle_key': n}, headers=b['headers']).status_code == 403
        for suffix in ('opening-context', 'continuation-context'):
            extra = dict(intent='open') if suffix == 'opening-context' else dict(action='join')
            assert http.get(f'/v2/me/raid-rooms/{rid}/{suffix}', params=dict(target_cycle_key=n, include_session_display='true', **extra), headers=b['headers']).status_code == 403
        from app.auth.models import Session
        with session() as db, db.begin():
            db.scalar(select(Session).where(Session.user_id == b['uid'])).revoked_at = now(db)
        assert http.get(path, params=query, headers=b['headers']).status_code == 401


def test_empty_preview_and_application_keep_original_body(planning):
    _, a, b = planning
    room = create_room(a, combined=False, mode='leader_only')
    rid = uuid.UUID(room['room_id']); c = room['created_cycles'][0]['target_cycle_key']
    ctx = admission(b, rid, c, 'apply')
    assert checked(ctx, 'existing')['sessions'] == []
    assert commands.admit(actor(b['uid']), rid, uuid.uuid4(), admission_request(ctx), applying=True)[0] == 201
    ctx = opening.get(actor(a['uid']), rid, next_key(), 'open', include_session_display=True)
    assert checked(ctx, 'opening_preview')['previews'] == []


def test_nullable_actual_times_and_missing_preview_duration(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    with session() as db, db.begin():
        row = db.scalar(select(commands.RoomCycle).where(commands.RoomCycle.room_id == rid, commands.RoomCycle.cycle_key == date.fromisoformat(n)))
        sess = graph.sessions(db, row)[0]
        sess.state = 'unconfirmed'; sess.starts_at = sess.ends_at = None
        source = db.scalar(select(commands.RoomCycle).where(commands.RoomCycle.room_id == rid, commands.RoomCycle.cycle_key == date.fromisoformat(c)))
        source.settings_snapshot = source.settings_snapshot | dict(items=[v | dict(duration_minutes=None) for v in source.settings_snapshot['items']])
    actual = checked(admission(b, rid, n), 'existing')['sessions'][0]
    assert actual['starts_at'] is actual['ends_at'] is actual['join_deadline'] is None
    cancel_member(a, rid, n)
    before = fingerprints(engine)
    ctx = opening.get(actor(a['uid']), rid, n, 'reopen', include_session_display=True)
    preview = checked(ctx, 'opening_preview')
    assert all(v['time_state'] == 'start_only' and v['ends_at'] is None
               for g in preview['previews'] for v in g['alternatives'])
    assert fingerprints(engine) == before


def test_real_one_mib_preview_limit_with_large_stored_intent(planning):
    from app.raid_rooms.source_models import ScheduleAlternative
    engine, a, b = planning
    ctx = preflight(a, bundle=True)
    group = dict(client_group_key='large-preview', existing_group_id=None, expected_group_revision=None,
        occurrence_mode='one_of', planning_mode='manual', required=True,
        auto_confirm_additional_members=None, day_scope='selected_weekdays', alternatives=[
            dict(client_alternative_key=f'initial-{i}', existing_session_id=None, expected_session_revision=None,
                weekday=3, starts_local='00:05', leader_latest_start_local=None,
                item_order=[v['raid_id'] for v in ctx['data']['targets']]) for i in range(2)])
    room = creation.create(actor(a['uid']), uuid.uuid4(), request(ctx, schedule_groups=[group]))[1]['data']
    rid = uuid.UUID(room['room_id']); n = next_key()
    with session() as db, db.begin():
        source = db.get(commands.RoomCycle, uuid.UUID(room['created_cycles'][0]['room_cycle_id']))
        stored = graph.groups(db, source)[0]
        order = [str(item.id) for item, _ in graph.admission.rounds(db, source)]
        db.execute(insert(ScheduleAlternative), [dict(id=uuid.uuid4(), room_id=rid, group_id=stored.id,
            client_key=f'large-{i}', weekday=3, start_minute=5, latest_start_minute=None,
            item_order=order, session_id=None) for i in range(5000)])
    before = fingerprints(engine)
    with commands.base.snapshot(actor(a['uid'])) as (db, uid, stamp):
        value, *_ = opening.prepare(db, uid, rid, n, 'open', None, None, stamp, include_session_display=True)
        assert len(value['data']['session_display']['previews'][0]['alternatives']) == 5002
        assert len(value['data']['context_token'].encode()) <= 4096
        from fastapi.encoders import jsonable_encoder
        assert len(json.dumps(jsonable_encoder(value), ensure_ascii=False, separators=(',', ':')).encode()) > 1024 * 1024
    path = f'/v2/me/raid-rooms/{rid}/opening-context'
    with client(a) as http:
        query = dict(target_cycle_key=n, intent='open')
        response = http.get(path, params=query | dict(include_session_display='true'))
        assert response.status_code == 413 and response.json()['error']['code'] == 'RESPONSE_TOO_LARGE'
        assert http.get(path, params=query).status_code == 200
    assert fingerprints(engine) == before


def test_opt_in_character_success_original_ack_and_explicit_decline(planning):
    engine, a, b = planning
    rid, c, n = scheduled(a)
    ctx = admission(a, rid, n, 'change_character', cid=a['ids'][1])
    checked(ctx, 'existing')
    body = change_body(ctx, plan(a, rid, n)); command = uuid.uuid4()
    result = character.execute(actor(a['uid']), rid, command, body)
    before = fingerprints(engine)
    assert character.execute(actor(a['uid']), rid, command, body) == result
    assert fingerprints(engine) == before
    add_member(b, rid, c)
    ctx = continuation.get(actor(b['uid']), rid, n, action='decline', include_session_display=True)
    checked(ctx, 'none')
    body = wire.ScopedCommand.model_validate(scoped(ctx)); command = uuid.uuid4()
    result = continuation.execute(actor(b['uid']), rid, command, body, decline=True)
    assert continuation.execute(actor(b['uid']), rid, command, body, decline=True) == result


def test_current_db29_contexts_continuation_and_reopening(outcomes):
    _, a, b = outcomes
    rid, c, n = scheduled(a)
    add_member(b, rid, c)
    checked(admission(b, rid, n), 'existing')
    ctx = continuation.get(actor(b['uid']), rid, n, include_session_display=True)
    checked(ctx, 'existing')
    continuation.execute(actor(b['uid']), rid, uuid.uuid4(), continue_body(ctx))
    replacement = admission(b, rid, n, 'change_character', cid=b['ids'][1])
    checked(replacement, 'existing')
    character.execute(actor(b['uid']), rid, uuid.uuid4(), change_body(replacement, plan(b, rid, n)))
    checked(opening.get(actor(a['uid']), rid, n, 'open', include_session_display=True), 'none')
    cancel_member(b, rid, n); cancel_member(a, rid, n)
    ctx = opening.get(actor(a['uid']), rid, n, 'reopen', include_session_display=True)
    checked(ctx, 'opening_preview')
    assert opening.execute(actor(a['uid']), rid, uuid.uuid4(), opening_body(ctx, 'reopen'))[0] == 200
    assert checked(admission(b, rid, n), 'existing')['target_generation'] == 2
