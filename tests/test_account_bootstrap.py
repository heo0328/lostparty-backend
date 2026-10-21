import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, date, timedelta
from threading import Event

import pytest
from sqlalchemy import select, text, event, insert, delete, inspect

from app.core.database import session, engine, now
from app.game_accounts import bootstrap
from app.game_accounts.models import (Account, Registration, Character, Configuration, Activity, NameClaim,
    CharacterPersonalPreferences, CharacterRoleSummary, AccountCharacterPresentation, ScopedPowerCache)
from app.raid_weekly.models import WeeklyState
from tests.test_game_accounts import world, register, verify, page, save_data, change, BASE, another_user
from tests.test_role_summaries import put as put_role

URL = '/v2/me/account-bootstrap'
STAMP = datetime(2026, 10, 20, 20, 59, 59, tzinfo=timezone.utc)  # KST Wednesday 05:59:59


@pytest.fixture
def selected(client, world):
    headers, state = world
    r = register(client, headers, main=True)
    verify(client, headers, state, r['registration_id'])
    p = page(client, headers, r['registration_id'])
    assert change(client, headers, 'put', BASE+'/'+r['registration_id']+'/character-settings', save_data(p)).status_code == 200
    r = next(x for x in client.get(BASE, headers=headers).json()['items'] if x['registration_id'] == r['registration_id'])
    return headers, state, r


def fingerprints():
    with engine().connect() as c:
        return {t:c.scalar(text('SELECT md5(COALESCE(string_agg(h,\'\' ORDER BY h),\'\')) FROM '
            '(SELECT md5(to_jsonb(t)::text) h FROM "'+t+'" t) s'))
            for t in inspect(c).get_table_names() if t != 'alembic_version'}


def test_empty_strict_auth_and_no_implicit_rows(client, login):
    auth, _ = login()
    h = {'Authorization':'Bearer '+auth['access_token']}
    assert client.get(URL).status_code == 401
    for suffix in ('?user_id='+str(uuid.uuid4()), '?limit=1', '?cursor=x', '?character_id=x&character_id=y'):
        assert client.get(URL+suffix, headers=h).status_code == 400
    assert client.request('GET', URL, headers=h, content=b'{}').status_code == 400
    before = fingerprints()
    out = client.get(URL, headers=h)
    assert out.status_code == 200 and out.headers['Cache-Control'] == 'no-store'
    assert out.json()['complete'] is True and out.json()['registrations'] == []
    assert out.json()['weekly_states']['entries'] == []
    assert fingerprints() == before


@pytest.mark.parametrize('kind,status', [('disabled', 403), ('revoked', 401)])
def test_current_auth_state_blocks_bootstrap(client, login, kind, status):
    from app.auth.models import User, Session
    auth, _ = login(); h = {'Authorization':'Bearer '+auth['access_token']}
    with session() as db, db.begin():
        if kind == 'disabled':
            db.get(User, uuid.UUID(auth['user']['id'])).status = 'disabled'
        else:
            db.get(Session, uuid.UUID(auth['session']['id'])).revoked_at = now(db)
    assert client.get(URL, headers=h).status_code == status


def test_existing_projections_match_hidden_off_and_readonly(client, selected, monkeypatch):
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as credentials
    from app.raid_weekly import service as weekly
    h, state, r = selected
    ids = [i['character_id'] for i in page(client, h, r['registration_id'])['characters']['items']]
    assert put_role(client, h, ids[0]).status_code == 200
    with session() as db, db.begin():
        uid = db.scalar(select(Registration.user_id).where(Registration.id == uuid.UUID(r['registration_id'])))
        db.add(CharacterPersonalPreferences(user_id=uid, character_id=uuid.UUID(ids[0]), ownership_revision=1,
            version=2, preferred_role='support', visible=False, display_order=0, saved_at=now(db)))
    def forbidden(*a, **kw):
        raise AssertionError('No provider/credentials in bootstrap')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(credentials, 'capture', forbidden)
    monkeypatch.setattr(bootstrap, 'now', lambda db: STAMP)
    monkeypatch.setattr(weekly, 'now', lambda db: STAMP)
    calls = state['calls']
    before = fingerprints()
    out = client.get(URL, headers=h)
    assert out.status_code == 200
    body = out.json(); bundle = body['registrations'][0]
    assert bundle['registration'] == client.get(BASE, headers=h).json()['items'][0]
    assert bundle['characters'] == client.get('/v2/me/game-accounts/'+r['registration_id']+'/characters', headers=h).json()
    assert bundle['representative'] == client.get(BASE+'/'+r['registration_id']+'/representative', headers=h).json()
    assert bundle['presentation'] == client.get('/v2/me/game-accounts/'+r['registration_id']+'/presentation-settings', headers=h).json()
    assert len(bundle['personal_profiles']) == 3
    for profile in bundle['personal_profiles']:
        assert profile == client.get('/v2/me/characters/'+profile['character_id']+'/personal-profile', headers=h).json()
    old = client.get('/v1/me/raid-weekly-states', headers=h, params=[('character_id', i) for i in sorted(ids)]).json()
    assert body['weekly_states'] == old
    assert body['server_now'] == body['weekly_states']['current_cycle']['server_time']
    assert state['calls'] == calls and fingerprints() == before


def test_unverified_lost_and_other_member_do_not_receive_profiles(client, selected, monkeypatch, login):
    h, _, r = selected
    other = another_user(login, monkeypatch, client)
    assert client.get(URL, headers=other).json()['registrations'] == []
    with session() as db, db.begin():
        a = db.get(Account, uuid.UUID(r['game_account_id']))
        a.owner_id = None
        a.ownership_revision += 1
    lost = client.get(URL, headers=h).json()['registrations'][0]
    assert lost['registration']['ownership_status'] == 'ownership_lost'
    assert lost['representative'] is None and lost['presentation'] is None
    assert lost['personal_profiles'] == []
    assert all(i['character_id'] is None and i['combat_power'] is None for i in lost['characters']['items'])
    # Explicitly unbind only in isolated fixture to exercise the preview branch.
    with session() as db, db.begin():
        db.get(Registration, uuid.UUID(r['registration_id'])).account_id = None
    preview = client.get(URL, headers=h).json()['registrations'][0]
    assert preview['registration']['ownership_status'] == 'unverified'
    assert preview['personal_profiles'] == []


def test_unconfigured_defaults_deleted_registration_and_missing_data(client, selected):
    h, _, r = selected
    with session() as db, db.begin():
        conf = db.scalar(select(Configuration))
        db.execute(delete(Activity).where(Activity.settings_id == conf.id))
        conf.state, conf.representative_id = 'unconfigured', None
    bundle = client.get(URL, headers=h).json()['registrations'][0]
    assert bundle['registration']['settings']['configuration_state'] == 'unconfigured'
    assert bundle['personal_profiles'] == [] and bundle['representative']['representative_character_id'] is None
    assert bundle['presentation']['visible_count'] == 6
    with session() as db, db.begin():
        db.scalar(select(Character)).summary = {}
    bad = client.get(URL, headers=h)
    assert bad.status_code == 503 and bad.json()['error']['code'] == 'BOOTSTRAP_DATA_UNAVAILABLE'
    with session() as db, db.begin():
        db.get(Registration, uuid.UUID(r['registration_id'])).deleted_at = now(db)
    assert client.get(URL, headers=h).json()['registrations'] == []


@pytest.mark.parametrize('kind', ['suspect', 'conflict', 'retired'])
def test_activity_eligibility_explicit_unavailable(client, selected, kind):
    h, _, _ = selected
    with session() as db, db.begin():
        c = db.scalar(select(Character))
        cid = str(c.id)
        if kind == 'suspect':
            c.lifecycle_state, c.status = 'suspect', 'suspect'
        elif kind == 'conflict':
            db.delete(db.get(NameClaim, (c.server_name, c.character_name)))
        else:
            c.lifecycle_state = 'retired'
    out = client.get(URL, headers=h)
    assert out.status_code == 200
    bundle = out.json()['registrations'][0]
    assert cid in bundle['registration']['settings']['ineligible_character_ids']
    if kind == 'suspect':
        assert any(p['character_id'] == cid for p in bundle['personal_profiles'])
        assert all(e['mark_blocked_reason'] == 'CHARACTER_UNUSABLE' for e in out.json()['weekly_states']['entries'] if e['character_id'] == cid)
    else:
        assert bundle['unavailable_characters'] == [dict(character_id=cid, code='IDENTITY_CONFLICT' if kind == 'conflict' else 'CHARACTER_UNUSABLE')]
        assert not any(p['character_id'] == cid for p in bundle['personal_profiles'])
        assert not any(e['character_id'] == cid for e in out.json()['weekly_states']['entries'])


@pytest.mark.parametrize('kind', ['ownership', 'settings'])
def test_repeatable_snapshot_across_concurrent_commit(client, selected, kind):
    h, _, r = selected
    entered, resume = Event(), Event()
    blocked = [False]
    def pause(conn, cursor, statement, parameters, context, many):
        if not blocked[0] and 'FROM game_account_registrations' in statement:
            blocked[0] = True
            entered.set()
            assert resume.wait(10)
    event.listen(engine(), 'after_cursor_execute', pause)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(client.get, URL, headers=h)
            assert entered.wait(10)
            try:
                with session() as db, db.begin():
                    a = db.get(Account, uuid.UUID(r['game_account_id']))
                    conf = db.scalar(select(Configuration))
                    conf.version += 1
                    if kind == 'ownership':
                        a.owner_id, a.ownership_revision = None, 2
                        conf.ended_at = now(db)
                    else:
                        db.execute(delete(Activity).where(Activity.settings_id == conf.id))
                        conf.representative_id, conf.state = None, 'unconfigured'
            finally:
                resume.set()
            response = pending.result(timeout=10)
    finally:
        resume.set()
        event.remove(engine(), 'after_cursor_execute', pause)
    assert response.status_code == 200
    before = response.json()['registrations'][0]
    assert before['registration']['ownership_status'] == 'owned'
    assert len(before['personal_profiles']) == 3
    after = client.get(URL, headers=h).json()['registrations'][0]
    assert after['personal_profiles'] == []
    assert after['registration']['ownership_status'] == ('ownership_lost' if kind == 'ownership' else 'owned')


def test_cycle_boundary_and_weekly_evidence(client, selected, monkeypatch):
    h, _, _ = selected
    clock = [STAMP]
    monkeypatch.setattr(bootstrap, 'now', lambda db: clock[0])
    with session() as db, db.begin():
        c = db.scalar(select(Character))
        uid = db.scalar(select(Registration.user_id))
        db.add(WeeklyState(user_id=uid, character_id=c.id, raid_id='serca', cycle_key=date(2026, 10, 14),
            revision=2, active_party_id=uuid.uuid4(), active_difficulty_id='normal', joined_at=STAMP, updated_at=STAMP))
    original = bootstrap.profiles.output
    def crossing(*args):
        clock[0] = STAMP.replace(hour=21, minute=0, second=0)
        return original(*args)
    monkeypatch.setattr(bootstrap.profiles, 'output', crossing)
    old = client.get(URL, headers=h).json()['weekly_states']
    assert old['cycle_key'] == '2026-10-14'
    assert any(e['participation'] and e['mark_blocked_reason'] == 'PARTICIPATION_CONFIRMATION_REQUIRED' for e in old['entries'])
    new = client.get(URL, headers=h).json()['weekly_states']
    assert new['cycle_key'] == '2026-10-21' and all(e['state'] == 'incomplete' for e in new['entries'])


def seed(uid, account_count, character_count):
    with session() as db, db.begin():
        stamp = now(db)
        accounts, registrations, chars, claims, configs, activities = [], [], [], [], [], []
        for i in range(account_count):
            aid, rid, sid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            accounts.append(dict(id=aid, owner_id=uid, ownership_revision=1, roster_revision=1, verified_at=stamp))
            registrations.append(dict(id=rid, user_id=uid, account_id=aid, lookup_name=f'load-{i}-0', label='', is_main=i == 0,
                version=1, preview=[], fetched_at=stamp, created_at=stamp, updated_at=stamp))
            configs.append(dict(id=sid, user_id=uid, account_id=aid, state='configured', version=2))
            for j in range(character_count):
                cid = uuid.uuid4(); name = f'load-{i}-{j}'
                summary = dict(server_name='load-server', character_name=name, class_name='sample-class',
                    character_level=60, item_level='1700', combat_power=None)
                chars.append(dict(id=cid, account_id=aid, server_name='load-server', character_name=name,
                    summary=summary, status='confirmed', fetched_at=stamp, confirmed_at=stamp,
                    lifecycle_state='active', lifecycle_revision=1))
                claims.append(dict(server_name='load-server', character_name=name, character_id=cid, revision=1))
                activities.append(dict(settings_id=sid, character_id=cid, account_id=aid))
        for model, rows in ((Account, accounts), (Registration, registrations), (Character, chars),
                            (NameClaim, claims), (Configuration, configs), (Activity, activities)):
            db.execute(insert(model), rows)


def test_maximum_scope_payload_and_query_count(client, login, capsys):
    auth, _ = login(); h = {'Authorization':'Bearer '+auth['access_token']}
    seed(uuid.UUID(auth['user']['id']), 20, 200)
    statements = []
    def collect(conn, cursor, sql, parameters, context, many):
        statements.append(sql)
    event.listen(engine(), 'before_cursor_execute', collect)
    try:
        started = time.perf_counter()
        response = client.get(URL, headers=h)
        elapsed = time.perf_counter()-started
    finally:
        event.remove(engine(), 'before_cursor_execute', collect)
    assert response.status_code == 200
    body = response.json()
    assert len(body['registrations']) == 20
    assert sum(len(r['characters']['items']) for r in body['registrations']) == 4000
    assert sum(len(r['personal_profiles']) for r in body['registrations']) == 4000
    from app.raids.service import catalog
    assert len(body['weekly_states']['entries']) == 4000 * len(catalog().raids)
    assert len(response.content) <= bootstrap.MAX_BYTES
    assert len(statements) <= 22
    assert not any(s.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for s in statements)
    with capsys.disabled():
        print(f'BOOTSTRAP_MAX registrations=20 characters=4000 bytes={len(response.content)} statements={len(statements)} seconds={elapsed:.3f}')


@pytest.mark.parametrize('accounts,characters', [(21, 1), (1, 201)])
def test_limits_are_errors_not_truncated_success(client, login, accounts, characters):
    auth, _ = login(); h = {'Authorization':'Bearer '+auth['access_token']}
    seed(uuid.UUID(auth['user']['id']), accounts, characters)
    response = client.get(URL, headers=h)
    assert response.status_code == 409 and response.json()['error']['code'] == 'BOOTSTRAP_LIMIT_EXCEEDED'


def test_payload_limit_is_explicit_error(client, selected, monkeypatch):
    h, _, _ = selected
    monkeypatch.setattr(bootstrap, 'MAX_BYTES', 100)
    response = client.get(URL, headers=h)
    assert response.status_code == 409 and response.json()['error']['code'] == 'BOOTSTRAP_RESPONSE_TOO_LARGE'


def test_batch_power_matches_stored_latest_good_and_current_check(client, selected):
    h, _, r = selected
    with session() as db, db.begin():
        registration = db.get(Registration, uuid.UUID(r['registration_id']))
        c = db.scalar(select(Character))
        c.lifecycle_revision = 2
        stamp = now(db)
        for scope, revision, value, fetched, checked, status in [
            ('old-good', 1, '12345', stamp-timedelta(minutes=2), stamp-timedelta(minutes=2), 'available'),
            ('new-failed', 2, None, None, stamp-timedelta(minutes=1), 'failed'),
        ]:
            db.add(ScopedPowerCache(actor_id=registration.user_id, scope_key=scope, character_id=c.id,
                lifecycle_revision=revision, registration_id=registration.id, preview_version=None,
                credential_version=1, server_name=c.server_name, character_name=c.character_name,
                value=value, fetched_at=fetched, checked_at=checked, status=status,
                reason='UPSTREAM_UNAVAILABLE' if status == 'failed' else None, generation=1))
    out = client.get(URL, headers=h)
    assert out.status_code == 200
    bundle = out.json()['registrations'][0]
    current = client.get('/v2/me/game-accounts/'+r['registration_id']+'/characters', headers=h).json()
    assert bundle['characters'] == current
    assert bundle['registration'] == client.get(BASE, headers=h).json()['items'][0]
    row = next(i for i in bundle['characters']['items'] if i['power_status'] == 'failed')
    assert row['combat_power'] == '12345' and row['power_stale'] is True
