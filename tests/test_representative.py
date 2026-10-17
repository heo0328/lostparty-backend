import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select, func
from app.auth.models import User, Session
from app.core.database import session, now
from app.game_accounts import representative as service
from app.game_accounts.models import Account, Registration, Character, Configuration, Activity, RequestResult, NameClaim
from app.game_accounts.support import GameError
from tests.test_game_accounts import PrivateHeaders, change, BASE


@pytest.fixture
def selection(login):
    auth, _ = login()
    headers = PrivateHeaders(Authorization='Bearer ' + auth['access_token'])
    with session() as db, db.begin():
        uid = db.scalar(select(User.id))
        current = now(db)
        account = Account(owner_id=uid, verified_at=current)
        db.add(account); db.flush()
        registration = Registration(user_id=uid, account_id=account.id, lookup_name='sample-0',
                                    label='', is_main=True, preview=[], fetched_at=current,
                                    created_at=current, updated_at=current)
        db.add(registration)
        characters = [Character(account_id=account.id, server_name='sample-server', character_name=f'sample-{i}',
                                summary=dict(server_name='sample-server', character_name=f'sample-{i}',
                                             class_name='sample-class', character_level=60,
                                             item_level='1700', combat_power=None),
                                fetched_at=current, confirmed_at=current) for i in range(3)]
        db.add_all(characters); db.flush()
        db.add_all([NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id) for c in characters])
        configuration = Configuration(user_id=uid, account_id=account.id, representative_id=characters[0].id,
                                      state='configured', next_change_at=current+timedelta(minutes=5))
        db.add(configuration); db.flush()
        db.add_all([Activity(settings_id=configuration.id, account_id=account.id, character_id=c.id)
                    for c in characters[:2]])
        return dict(headers=headers, rid=str(registration.id), aid=account.id, cid=configuration.id,
                    ids=[str(c.id) for c in characters], uid=uid)


def url(w):
    return BASE+'/'+w['rid']+'/representative'


def get(client, w):
    return client.get(url(w), headers=w['headers'])


def body(w, target=None):
    return dict(character_id=target or w['ids'][1], expected_registration_version=1,
                expected_settings_version=1, expected_ownership_revision=1, expected_roster_revision=1)


def put(client, w, data=None, key=None):
    return change(client, w['headers'], 'put', url(w), body(w) if data is None else data, key)


def error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()['error']['code'] == code
    assert response.headers['Cache-Control'] == 'no-store'


def test_read_only_change_noop_replay_and_no_provider(client, selection, monkeypatch):
    w = selection
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as credentials
    def forbidden(*args, **kwargs): raise AssertionError('No provider or credential access')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(credentials, 'capture', forbidden)
    before = get(client, w)
    assert before.status_code == 200 and len(before.json()) == 10
    assert before.json()['next_change_at'] is None
    with session() as db:
        assert db.get(Configuration, w['cid']).next_change_at is not None  # GET never cleans rows.
    key = uuid.uuid4()
    changed = put(client, w, key=key)
    assert changed.status_code == 200 and changed.json()['settings_version'] == 2
    assert changed.json()['representative_character_id'] == w['ids'][1]
    assert changed.json()['next_change_at'] is None
    assert put(client, w, key=key).json() == changed.json()
    data = body(w); data['expected_settings_version'] = 2
    assert put(client, w, data).json() == changed.json()  # no-op
    error(put(client, w), 409, 'REVISION_CONFLICT')  # stale even same target
    error(put(client, w, body(w, w['ids'][0]), key), 409, 'IDEMPOTENCY_CONFLICT')
    data['character_id'] = w['ids'][0]
    assert put(client, w, data).json()['settings_version'] == 3  # immediate second change
    assert put(client, w, key=key).json() == changed.json()  # historical success never reapplied
    assert get(client, w).json()['representative_character_id'] == w['ids'][0]
    with session() as db:
        c = db.get(Configuration, w['cid'])
        assert c.state == 'configured'
        assert set(db.scalars(select(Activity.character_id).where(Activity.settings_id == c.id))) == {uuid.UUID(i) for i in w['ids'][:2]}
        assert db.get(Registration, uuid.UUID(w['rid'])).version == 1
        assert db.get(Account, w['aid']).roster_revision == 1


@pytest.mark.parametrize('field', ['expected_registration_version', 'expected_settings_version',
                                   'expected_ownership_revision', 'expected_roster_revision'])
def test_all_revision_conflicts(client, selection, field):
    data = body(selection); data[field] = 2
    error(put(client, selection, data), 409, 'REVISION_CONFLICT')


@pytest.mark.parametrize('state,code', [('suspect', 'CHARACTER_UNUSABLE'), ('missing', 'CHARACTER_UNUSABLE'),
                                      ('inactive', 'CHARACTER_NOT_ACTIVE'), ('foreign', 'CHARACTER_NOT_FOUND')])
def test_target_eligibility(client, selection, state, code):
    w = selection; data = body(w)
    if state in ('suspect', 'missing'):
        with session() as db, db.begin(): db.get(Character, uuid.UUID(w['ids'][1])).status = state
    elif state == 'inactive': data['character_id'] = w['ids'][2]
    else: data['character_id'] = str(uuid.uuid4())
    error(put(client, w, data), 404 if state == 'foreign' else 409, code)
    assert get(client, w).json()['settings_version'] == 1


def test_old_representative_unusable_reconfiguration_preserved(client, selection):
    w = selection
    with session() as db, db.begin():
        db.get(Character, uuid.UUID(w['ids'][0])).status = 'suspect'
        db.get(Configuration, w['cid']).state = 'needs_reconfiguration'
    result = put(client, w)
    assert result.status_code == 200
    assert result.json()['configuration_state'] == 'needs_reconfiguration'


def test_unset_configuration_read_only_and_no_auto_selection(client, selection):
    w = selection
    with session() as db, db.begin():
        db.query(Activity).delete()
        db.delete(db.get(Configuration, w['cid']))
    result = get(client, w)
    assert result.json()['representative_character_id'] is None
    assert result.json()['configuration_state'] == 'unconfigured'
    error(put(client, w), 409, 'SETTINGS_NOT_CONFIGURED')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Configuration)) == 0


@pytest.mark.parametrize('state,status,code', [('deleted',404,'REGISTRATION_NOT_FOUND'),
                                             ('foreign',404,'REGISTRATION_NOT_FOUND'),
                                             ('lost',403,'OWNERSHIP_REQUIRED'),
                                             ('preview',403,'OWNERSHIP_REQUIRED')])
def test_read_write_replay_access(client, selection, state, status, code):
    w = selection; key = uuid.uuid4()
    assert put(client, w, key=key).status_code == 200
    with session() as db, db.begin():
        r = db.get(Registration, uuid.UUID(w['rid']))
        if state == 'deleted': r.deleted_at = now(db)
        elif state == 'foreign':
            other = User(status='active', created_at=now(db), updated_at=now(db), last_login_at=now(db))
            db.add(other); db.flush(); r.user_id = other.id
        elif state == 'lost': db.get(Account, w['aid']).owner_id = None
        else: r.account_id = None
    error(get(client, w), status, code)
    error(put(client, w, key=key), status, code)
    error(put(client, w), status, code)


def test_main_switch_aba_and_historical_replay(client, selection):
    w = selection; key = uuid.uuid4()
    original = put(client, w, key=key)
    assert original.status_code == 200
    path = BASE+'/'+w['rid']
    assert change(client, w['headers'], 'patch', path, {'is_main': False, 'expected_version': 1}).status_code == 200
    assert get(client, w).json()['is_main'] is False
    error(put(client, w), 409, 'MAIN_REGISTRATION_CHANGED')
    assert put(client, w, key=key).json() == original.json()  # historical is_main=true
    assert change(client, w['headers'], 'patch', path, {'is_main': True, 'expected_version': 2}).status_code == 200
    data = body(w, w['ids'][0]); data['expected_settings_version'] = 2
    error(put(client, w, data), 409, 'REVISION_CONFLICT')  # ABA registration version
    data['expected_registration_version'] = 3
    assert put(client, w, data).status_code == 200


@pytest.mark.parametrize('state,status', [('revoked',401), ('expired',401), ('disabled',403)])
def test_session_checked_for_read_write_replay(client, selection, state, status):
    w = selection; key = uuid.uuid4()
    assert put(client, w, key=key).status_code == 200
    with session() as db, db.begin():
        if state == 'disabled': db.get(User, w['uid']).status = 'disabled'
        else:
            row = db.scalar(select(Session))
            if state == 'revoked': row.revoked_at = now(db)
            else: row.idle_expires_at = now(db)-timedelta(seconds=1)
    assert get(client, w).status_code == status
    assert put(client, w, key=key).status_code == status
    assert put(client, w).status_code == status


@pytest.mark.parametrize('field,value', [('character_id',None), ('character_id','bad'),
    ('expected_settings_version',True), ('expected_settings_version','1'),
    ('expected_roster_revision',0), ('expected_ownership_revision',None),
    ('expected_registration_version',1.0), ('user_id','untrusted')])
def test_strict_inputs(client, selection, field, value):
    data = body(selection); data[field] = value
    error(put(client, selection, data), 400, 'INVALID_REQUEST')


def test_body_query_missing_fields_keys_and_guest(client, selection):
    w = selection
    for data in ({}, {k:v for k,v in body(w).items() if k != 'expected_registration_version'}):
        error(put(client, w, data), 400, 'INVALID_REQUEST')
    for query in ('?x=1', '?x=1&x=2', '?limit=1'):
        error(client.get(url(w)+query, headers=w['headers']), 400, 'INVALID_REQUEST')
        error(change(client, w['headers'], 'put', url(w)+query, body(w)), 400, 'INVALID_REQUEST')
    error(client.request('GET', url(w), headers=w['headers'], json={}),400,'INVALID_REQUEST')
    error(client.put(url(w), headers=w['headers'], json=body(w)),400,'INVALID_REQUEST')
    error(put(client, w, key=uuid.uuid1()),400,'INVALID_REQUEST')
    assert client.get(url(w)).status_code == 401
    assert change(client, {}, 'put', url(w), body(w)).status_code == 401
    assert get(client, w).json()['settings_version'] == 1


def test_shared_version_concurrency_with_full_settings(client, selection):
    w = selection
    data = dict(activity_character_ids=w['ids'][:2], representative_character_id=w['ids'][1],
                expected_settings_version=1, expected_ownership_revision=1, expected_roster_revision=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(put, client, w)
        b = pool.submit(change, client, w['headers'], 'put', BASE+'/'+w['rid']+'/character-settings', data)
        results = [a.result(), b.result()]
    assert sorted(r.status_code for r in results) == [200,409]
    assert get(client, w).json()['settings_version'] == 2


def test_fencing_rollback_retry_inprogress_expiry(client, selection, monkeypatch):
    w = selection; key = uuid.uuid4(); original = service.commit_result
    def expire(*args): raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(service, 'commit_result', expire)
    failed = put(client, w, key=key)
    error(failed,409,'REQUEST_IN_PROGRESS'); assert failed.headers['Retry-After'] == '2'
    assert get(client, w).json()['settings_version'] == 1
    with session() as db, db.begin():
        row = db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.state = 'running'; row.lease_expires_at = now(db)+timedelta(seconds=30)
    error(put(client,w,key=key),409,'REQUEST_IN_PROGRESS')
    with session() as db, db.begin():
        row = db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.lease_expires_at = now(db)-timedelta(seconds=1)
    monkeypatch.setattr(service,'commit_result',original)
    assert put(client,w,key=key).status_code == 200
    with session() as db, db.begin():
        row = db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.completed_at = now(db)-timedelta(hours=24)
    error(put(client,w,key=key),409,'IDEMPOTENCY_EXPIRED')


def test_database_failure_is_sanitized(client, selection, monkeypatch):
    from sqlalchemy.exc import OperationalError
    def unavailable(*args): raise OperationalError('private SQL',{},Exception('private database details'))
    monkeypatch.setattr(service,'output',unavailable)
    response = get(client, selection)
    error(response,503,'SERVICE_UNAVAILABLE')
    assert 'private' not in response.text


def test_old_settings_replay_timer_is_null_without_rewriting_history(client, selection):
    w = selection; key = uuid.uuid4()
    data = dict(activity_character_ids=w['ids'][:2], representative_character_id=w['ids'][1],
                expected_settings_version=1, expected_ownership_revision=1, expected_roster_revision=1)
    path = BASE+'/'+w['rid']+'/character-settings'
    first = change(client,w['headers'],'put',path,data,key)
    assert first.status_code == 200
    legacy_timer = '2099-01-01T00:00:00Z'
    with session() as db, db.begin():
        row = db.scalar(select(RequestResult).where(RequestResult.key==key))
        row.result = dict(row.result, next_change_at=legacy_timer)
    replay = change(client,w['headers'],'put',path,data,key)
    assert replay.status_code == 200 and replay.json()['next_change_at'] is None
    assert replay.json()['settings_version'] == first.json()['settings_version']
    with session() as db:
        row = db.scalar(select(RequestResult).where(RequestResult.key==key))
        assert row.result['next_change_at'] == legacy_timer


def test_two_representative_commands_have_one_winner(client, selection):
    w = selection
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: put(client,w), range(2)))
    assert sorted(r.status_code for r in results) == [200,409]
    assert get(client,w).json()['settings_version'] == 2


def test_empty_activity_does_not_auto_add_target(client, selection):
    w=selection
    with session() as db, db.begin(): db.query(Activity).delete()
    error(put(client,w),409,'SETTINGS_NOT_CONFIGURED')
    assert get(client,w).json()['settings_version']==1


def test_foreign_account_character_not_found(client, selection):
    w=selection
    with session() as db, db.begin():
        other=Account(owner_id=w['uid'],verified_at=now(db))
        db.add(other); db.flush()
        c=db.get(Character,uuid.UUID(w['ids'][2])); c.account_id=other.id
    error(put(client,w,body(w,w['ids'][2])),404,'CHARACTER_NOT_FOUND')
