"""Opt-in display readers against disposable PostgreSQL and synthetic principals."""
import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import event, inspect, select

from app.core.database import session, now
from app.game_accounts.models import Account, Character, CharacterRoleSummary
from app.raid_rooms import application_display as display, cycle_lists, cycle_member_reads
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_application_models import CycleApplication
from tests.test_application_composition import (current, candidate, ready, sources, imported, people, worlds,
    room, apply, approve, actor, denied, change_class)
from tests.test_admission_eligibility import minimum
from tests.test_recruitment_participation import write_power
from tests.test_recruitment_cycle_http import client as base_client
from tests.test_raid_room_migrations import table_digests

SCHEMA = json.loads(Path('docs/features/recruitment/participation/examples/application-display-v1.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def client(w):
    from app.main import no_store
    value = base_client(w)
    value.app.middleware('http')(no_store)
    return value


def page(w, rid, key, **kw):
    value = cycle_lists.applications(actor(w['uid']), key, rid=rid, reader_profile=display.PROFILE, **kw)
    VALIDATOR.validate(value)
    return value


def detail(w, rid, key):
    value = cycle_member_reads.detail(actor(w['uid']), rid, key, reader_profile=display.PROFILE)
    VALIDATOR.validate(value)
    return value


def test_profile_default_and_readonly(current):
    engine, a, b = current; rid, c, n = room(a); apply(b, rid, c)
    before = table_digests(engine, set(inspect(engine).get_table_names()))
    default = cycle_lists.applications(actor(a['uid']), c, rid=rid)
    extended = page(a, rid, c)
    item = extended['data']['items'][0]
    for field in ('comparison', 'analysis', 'display_reason'):
        assert field in item
        item.pop(field)
    assert item == default['data']['items'][0]
    original = cycle_member_reads.detail(actor(b['uid']), rid, c)
    expanded = detail(b, rid, c)
    assert expanded['data'].pop('my_application')['state'] == 'pending'
    # Timestamps are observations, not response-identity promises.
    assert set(expanded['data']) == set(original['data'])
    assert table_digests(engine, set(before)) == before
    denied('ROOM_LEADER_REQUIRED', page, b, rid, c)
    denied('INVALID_REQUEST', cycle_lists.applications, actor(b['uid']), c, reader_profile=display.PROFILE)


def test_role_success_current_error_missing_and_minimum(current):
    _, a, b = current; rid, c, n = room(a); change_class(b, '바드')
    apply(b, rid, c, 'support'); minimum(rid, c, '100', '100')
    write_power(b, 'dealer', '999', '2026-10-10T00:00:00Z')
    item = page(a, rid, c)['data']['items'][0]
    assert item['comparison']['actual'] is None and item['comparison']['state'] == 'missing'
    write_power(b, 'support', '100.0000000000000000000001', '2026-10-11T00:00:00Z')
    write_power(b, 'support', None, None, 3)
    with session() as db, db.begin():
        head = db.get(CharacterRoleSummary, (b['uid'], uuid.UUID(b['ids'][0]), 1, 'support'))
        head.summary = {**head.summary, 'integrity_status': 'error', 'issues': [dict(code='SOURCE_UNAVAILABLE', severity='error')]}
    item = page(a, rid, c)['data']['items'][0]
    assert item['selected_role'] == 'support' and item['display_reason'] is None
    assert item['comparison']['actual'] == '100.0000000000000000000001'
    assert item['comparison']['state'] == 'meets'
    assert item['comparison']['success_summary_version'] == 2
    assert item['analysis']['integrity_status'] == 'error'
    assert item['analysis']['version'] == item['comparison']['current_summary_version'] == 3
    assert item['analysis']['issues'] == item['comparison']['current_issues']
    minimum(rid, c, None, None)
    assert page(a, rid, c)['data']['items'][0]['comparison']['state'] == 'unrestricted'


def test_ownership_change_no_cross_owner_leak(current):
    _, a, b = current; rid, c, n = room(a); apply(b, rid, c)
    with session() as db, db.begin():
        character = db.get(Character, uuid.UUID(b['ids'][0]));account = db.get(Account, character.account_id)
        account.ownership_revision += 1
    item = page(a, rid, c)['data']['items'][0]
    assert item['display_reason'] == 'APPLICATION_CONTEXT_CHANGED'
    assert item['comparison'] is None and item['analysis'] is None


def test_malformed_analysis_is_failure_not_empty(current):
    _, a, b = current; rid, c, n = room(a); apply(b, rid, c)
    write_power(b, 'dealer', '100', '2026-10-10T00:00:00Z')
    with session() as db, db.begin():
        head = db.scalar(select(CharacterRoleSummary).where(CharacterRoleSummary.user_id == b['uid'],
            CharacterRoleSummary.character_id == uuid.UUID(b['ids'][0]), CharacterRoleSummary.role == 'dealer'))
        head.summary = {**head.summary, 'integrity_status': 'invalid'}
    denied('SERVICE_UNAVAILABLE', page, a, rid, c)


@pytest.mark.parametrize('state', ['pending', 'expired', 'withdrawn', 'accepted', 'rejected', 'cancelled'])
def test_own_effective_states_and_other_actor_cycle(current, state):
    _, a, b = current; rid, c, n = room(a); ack = apply(b, rid, c)[1]['data']
    with session() as db, db.begin():
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        if state == 'expired':
            stamp = now(db)
            app.created_at = stamp - timedelta(hours=1)
            app.expires_at = stamp - timedelta(seconds=1)
        elif state != 'pending':
            app.state, app.ended_at = state, now(db)
    assert detail(b, rid, c)['data']['my_application']['state'] == state
    assert detail(b, rid, n)['data']['my_application'] is None
    assert detail(a, rid, c)['data']['my_application'] is None
    if state == 'accepted':assert detail(b, rid, c)['data']['my_target_role'] == 'none'


def test_expiry_equality_no_write(current):
    _, a, b = current; rid, c, n = room(a); ack = apply(b, rid, c)[1]['data']
    with session() as db, db.begin():
        app = db.get(CycleApplication, uuid.UUID(ack['application_id']))
        target = db.get(RoomCycle, app.cycle_id)
        from app.raid_rooms.integrated_models import RecruitmentRoom
        result = display.own_application(db, b['uid'], db.get(RecruitmentRoom, rid), target, app.expires_at)
        assert result['state'] == 'expired' and app.state == 'pending' and app.ended_at is None


def test_pages_profile_binding_analysis_refresh_and_bulk(current, people):
    engine, a, b = current; rid, c, n = room(a); apply(b, rid, c)
    count = []
    def record(*args):count.append(1)
    event.listen(engine, 'before_cursor_execute', record)
    try:
        page(a, rid, c); one = len(count)
        event.remove(engine, 'before_cursor_execute', record)
        for i in range(3):apply(people('display-'+str(i)), rid, c)
        event.listen(engine, 'before_cursor_execute', record);count.clear()
        first = page(a, rid, c, limit=1);assert len(count) == one
        count.clear();full = page(a, rid, c, limit=50);assert len(count) == one
    finally:event.remove(engine, 'before_cursor_execute', record)
    cursor = first['data']['next_cursor'];assert cursor
    denied('INVALID_REQUEST', cycle_lists.applications, actor(a['uid']), c, rid=rid, limit=1, cursor=cursor)
    denied('INVALID_REQUEST', page, a, rid, n, limit=1, cursor=cursor)
    denied('INVALID_REQUEST', page, a, rid, c, limit=1, cursor=cursor[:-3]+'xxx')
    write_power(b, 'dealer', '100', '2026-10-10T00:00:00Z')
    rest = page(a, rid, c, limit=1, cursor=cursor)  # analysis does not stale membership pagination
    seen = [first['data']['items'][0]['application_id']]
    while True:
        seen.extend(v['application_id'] for v in rest['data']['items'])
        cursor = rest['data']['next_cursor']
        if cursor is None:break
        rest = page(a, rid, c, limit=1, cursor=cursor)
    assert seen == [v['application_id'] for v in full['data']['items']]
    cursor = page(a, rid, c, limit=1)['data']['next_cursor']
    with session() as db, db.begin():
        app = db.get(CycleApplication, uuid.UUID(full['data']['items'][0]['application_id']))
        app.state, app.ended_at = 'withdrawn', now(db);app.revision += 1
    denied('CURSOR_STALE', page, a, rid, c, limit=1, cursor=cursor)


def test_http_profiles_and_closed_contract(current):
    _, a, b = current; rid, c, n = room(a); apply(b, rid, c)
    for w, suffix in [(a,'applications'), (b,'detail')]:
        with client(w) as http:
            path=f'/v2/raid-rooms/{rid}/{suffix}'
            response=http.get(path,params=dict(target_cycle_key=c,reader_profile=display.PROFILE))
            assert response.status_code == 200, response.json().get('error')
            VALIDATOR.validate(response.json());assert 'no-store' in response.headers['cache-control']
            basic=http.get(path,params=dict(target_cycle_key=c));assert basic.status_code==200
            if suffix=='detail':assert 'my_application' not in basic.json()['data']
            else:assert 'comparison' not in basic.json()['data']['items'][0]
            assert http.get(path,params=dict(target_cycle_key=c,reader_profile='invalid')).status_code==400
            assert http.get(path,params=[('target_cycle_key',c),('reader_profile',display.PROFILE),('reader_profile',display.PROFILE)]).status_code==400
            assert http.request('GET',path,params=dict(target_cycle_key=c,reader_profile=display.PROFILE),json={}).status_code==400
    with client(b) as http:
        assert http.get(f'/v2/raid-rooms/{rid}/applications',params=dict(target_cycle_key=c,reader_profile=display.PROFILE)).status_code==403
        assert http.get(f'/v2/raid-rooms/{rid}/detail',params=dict(target_cycle_key=c,reader_profile=display.PROFILE,membership_id=str(uuid.uuid4()))).status_code==400
        assert http.get('/v2/me/raid-room-applications',params=dict(target_cycle_key=c,reader_profile=display.PROFILE)).status_code==400


def test_missing_head_source_and_database_failure_are_distinct(current, monkeypatch):
    from sqlalchemy import delete
    from sqlalchemy.exc import OperationalError
    _, a, b = current; rid, c, n = room(a); ack = apply(b, rid, c)[1]['data']
    with session() as db, db.begin():
        db.execute(delete(CharacterRoleSummary).where(CharacterRoleSummary.user_id == b['uid']))
    item = page(a, rid, c)['data']['items'][0]
    assert item['analysis'] is None and item['display_reason'] is None
    assert item['comparison']['actual'] is None
    with session() as db, db.begin():
        app=db.get(CycleApplication,uuid.UUID(ack['application_id']))
        app.selection={**app.selection,'character_id':str(uuid.uuid4())}
    item = page(a, rid, c)['data']['items'][0]
    assert item['display_reason']=='CHARACTER_DATA_UNAVAILABLE' and item['comparison'] is None
    def failed(*args):raise OperationalError('synthetic', {}, Exception('synthetic'))
    monkeypatch.setattr(display,'projections',failed)
    with client(a) as http:
        response=http.get(f'/v2/raid-rooms/{rid}/applications',params=dict(target_cycle_key=c,reader_profile=display.PROFILE))
        assert response.status_code==503 and response.json()['error']['code']=='SERVICE_UNAVAILABLE'


def test_latest_history_pending_precedence_and_generation_filter(current):
    from types import SimpleNamespace
    _, a, b = current; rid, c, n = room(a); first = apply(b, rid, c)[1]['data']
    with session() as db,db.begin():
        old=db.get(CycleApplication,uuid.UUID(first['application_id']))
        old.state,old.ended_at='withdrawn',now(db)
    second=apply(b,rid,c)[1]['data']
    with session() as db,db.begin():
        old=db.get(CycleApplication,uuid.UUID(first['application_id']))
        # Artificial later terminal history must not win over a valid pending.
        old.created_at=now(db)+timedelta(seconds=1)
        target=SimpleNamespace(id=old.cycle_id,generation=old.generation+1)
        assert display.own_application(db,b['uid'],SimpleNamespace(id=rid),target,now(db)) is None
    assert detail(b,rid,c)['data']['my_application']['application_id']==second['application_id']


def test_actual_bearer_approval_and_revocation(current):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth.models import Session
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    _,a,b=current;rid,c,n=room(a);ack=apply(b,rid,c)[1]['data']
    app=FastAPI();register(app);app.include_router(router);app.middleware('http')(no_store)
    query=dict(target_cycle_key=c,reader_profile=display.PROFILE);route=f'/v2/raid-rooms/{rid}/applications'
    with TestClient(app,raise_server_exceptions=False) as http:
        for headers in ({},{'Authorization':'Bearer invalid'}):
            response=http.get(route,params=query,headers=headers)
            assert response.status_code==401 and response.headers['cache-control']=='no-store'
        response=http.get(route,params=query,headers=a['headers']);assert response.status_code==200
        VALIDATOR.validate(response.json())
        assert http.get(route,params=query,headers=b['headers']).status_code==403
        approve(a,ack,rid,c)
        response=http.get(f'/v2/raid-rooms/{rid}/detail',params=query,headers=b['headers'])
        assert response.status_code==200,response.json().get('error')
        assert response.json()['data']['my_application']['state']=='accepted'
        assert response.json()['data']['my_target_role']=='member'
        with session() as db,db.begin():
            db.scalar(select(Session).where(Session.user_id==a['uid'])).revoked_at=now(db)
        assert http.get(route,params=query,headers=a['headers']).status_code==401


def test_profile_size_limit_does_not_change_default(current, monkeypatch):
    _,a,b=current;rid,c,n=room(a);apply(b,rid,c)
    monkeypatch.setattr(display,'MAX_RESPONSE_BYTES',64)
    for w,suffix in [(a,'applications'),(b,'detail')]:
        with client(w) as http:
            path=f'/v2/raid-rooms/{rid}/{suffix}'
            response=http.get(path,params=dict(target_cycle_key=c,reader_profile=display.PROFILE))
            assert response.status_code==413 and response.json()['error']['code']=='RESPONSE_TOO_LARGE'
            assert response.headers['cache-control']=='no-store'
            assert http.get(path,params=dict(target_cycle_key=c)).status_code==200
