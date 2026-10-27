import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth.models import Session, User
from app.core.database import session, now
from app.game_accounts.models import Account, Character, Registration, RequestResult
from app.game_accounts.support import GameError, authorize, fail
from app.raid_weekly import service
from app.raid_weekly.models import WeeklyState
from tests.test_game_accounts import world, another_user, change, page
from tests.test_role_summaries import owned

URL = '/v1/me/raid-weekly-states'
STAMP = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
CYCLE = '2026-10-14'


@pytest.fixture(autouse=True)
def weekly_clock(monkeypatch):
    monkeypatch.setattr(service, 'now', lambda db: STAMP)


def path(cid, raid='serca'):
    return f'/v1/me/characters/{cid}/raid-weekly-states/{raid}/manual-completion'


def body(**changes):
    result = dict(completed=True, difficulty_id='normal', expected_cycle_key=CYCLE,
                  expected_catalog_version='2026.08.20', expected_revision=1,
                  expected_ownership_revision=1, expected_lifecycle_revision=1)
    result.update(changes)
    return result


def put(client, headers, cid, data=None, key=None, raid='serca'):
    return change(client, headers, 'put', path(cid, raid), body() if data is None else data, key)


def get(client, headers, cid, **kwargs):
    return client.get(URL, headers=headers, params={'character_id': str(cid), **kwargs})


def one(client, headers, cid, raid='serca', **kwargs):
    response = get(client, headers, cid, **kwargs)
    assert response.status_code == 200, response.text
    return next(e for e in response.json()['entries'] if e['raid_id'] == raid)


def principal(cid):
    with session() as db:
        account = db.get(Account, db.get(Character, uuid.UUID(str(cid))).account_id)
        return (db.get(User, account.owner_id),
                db.scalar(select(Session).where(Session.user_id == account.owner_id)))


def seed(cid, **values):
    actor = principal(cid)[0].id
    with session() as db, db.begin():
        row = WeeklyState(user_id=actor, character_id=uuid.UUID(str(cid)), raid_id='serca',
                          cycle_key=date.fromisoformat(CYCLE), revision=2, updated_at=STAMP, **values)
        db.add(row)


def test_read_defaults_are_db_only_and_do_not_write_or_change_settings(client, owned, monkeypatch):
    h, registration, cid = owned
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as keys
    def forbidden(*args, **kwargs): raise AssertionError('Weekly API must not call provider or decrypt key')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(keys, 'capture', forbidden)
    before = page(client, h, registration['registration_id'])
    with session() as db:
        commands = db.scalar(select(func.count()).select_from(RequestResult))
    out = get(client, h, cid)
    assert out.status_code == 200 and out.headers['Cache-Control'] == 'no-store'
    assert len(out.json()['entries']) == 5 and out.json()['cycle_key'] == CYCLE
    assert all(e['state'] == 'incomplete' and e['revision'] == 1 and e['can_mark_completed']
               for e in out.json()['entries'])
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyState)) == 0
        assert db.scalar(select(func.count()).select_from(RequestResult)) == commands
    assert put(client, h, cid, body(completed=False, difficulty_id=None)).json()['revision'] == 1
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyState)) == 0
    assert put(client, h, cid).status_code == 200
    assert page(client, h, registration['registration_id']) == before


def test_manual_completion_correction_noop_difficulty_and_historical_ack(client, owned):
    h, _, cid = owned
    key = uuid.uuid4()
    first = put(client, h, cid, key=key)
    assert first.status_code == 200 and first.json()['revision'] == 2
    assert first.json()['completion_sources'][0]['source'] == 'manual'
    assert put(client, h, cid, body(expected_revision=2)).json() == first.json()
    # Normal/hard are one ledger row, not separate weekly rights.
    hard = put(client, h, cid, body(expected_revision=2, difficulty_id='hard'))
    assert hard.status_code == 200 and hard.json()['revision'] == 3
    assert one(client, h, cid)['completion_sources'][0]['difficulty_id'] == 'hard'
    assert one(client, h, cid, 'kazeros_act4')['state'] == 'incomplete'
    assert put(client, h, cid, key=key).json() == first.json()
    assert put(client, h, cid, body(difficulty_id='hard'), key=key).json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert put(client, h, cid, body(expected_revision=2)).json()['error']['code'] == 'REVISION_CONFLICT'
    cleared = put(client, h, cid, body(completed=False, difficulty_id=None, expected_revision=3))
    assert cleared.status_code == 200 and cleared.json()['revision'] == 4
    assert cleared.json()['state'] == 'incomplete' and not cleared.json()['completion_sources']
    assert put(client, h, cid, key=key).json() == first.json()
    assert one(client, h, cid)['revision'] == 4
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyState)) == 1


def test_unknown_difficulty_is_nullable_and_does_not_add_entry_level_policy(client, owned):
    h, _, cid = owned
    with session() as db, db.begin():
        character = db.get(Character, uuid.UUID(cid))
        character.summary = dict(character.summary, item_level=None)
    result = put(client, h, cid, body(difficulty_id=None))
    assert result.status_code == 200 and result.json()['completion_sources'][0]['difficulty_id'] is None


@pytest.mark.parametrize('field', list(body()))
def test_every_required_field(client, owned, field):
    h, _, cid = owned
    data = body(); del data[field]
    assert put(client, h, cid, data).status_code == 400


@pytest.mark.parametrize('changes', [
    {'completed': 1}, {'completed': 'true'}, {'expected_revision': True}, {'expected_revision': '1'},
    {'expected_revision': 0}, {'difficulty_id': ''}, {'completed': False},
    {'expected_cycle_key': '2026-10-15'}, {'expected_cycle_key': '2026-99-99'},
    {'user_id': str(uuid.uuid4())}, {'party_id': str(uuid.uuid4())}, {'completion_source': 'party'},
])
def test_strict_input_cannot_forge_actor_sources_or_dates(client, owned, changes):
    h, _, cid = owned
    assert put(client, h, cid, body(**changes)).status_code == 400
    assert one(client, h, cid)['revision'] == 1


@pytest.mark.parametrize('query', [
    [], [('character_id', 'invalid')], [('character_id', str(uuid.uuid4())), ('actor_id', 'other')],
    [('character_id', str(uuid.uuid4()))] * 51,
])
def test_bad_query_shape(client, owned, query):
    h, _, _ = owned
    assert client.get(URL, headers=h, params=query).status_code == 400


def test_query_duplicates_future_dates_get_body_and_put_query(client, owned):
    h, _, cid = owned
    assert client.get(URL, headers=h, params=[('character_id', cid)] * 2).status_code == 400
    assert client.get(URL, headers=h, params=[('character_id', cid), ('cycle_key', CYCLE), ('cycle_key', CYCLE)]).status_code == 400
    for key in ('2026-10-15', '2026-99-99', '2026-10-21'):
        assert get(client, h, cid, cycle_key=key).status_code == 400
    assert client.request('GET', URL, headers=h, params={'character_id': cid}, content='{}').status_code == 400
    assert change(client, h, 'put', path(cid) + '?user_id=other', body()).status_code == 400
    assert client.put(path(cid), headers=h, json=body()).status_code == 400
    assert put(client, h, cid, key=uuid.uuid1()).status_code == 400


@pytest.mark.parametrize('changes,raid,code', [
    ({'expected_revision': 2}, 'serca', 'REVISION_CONFLICT'),
    ({'expected_ownership_revision': 2}, 'serca', 'REVISION_CONFLICT'),
    ({'expected_lifecycle_revision': 2}, 'serca', 'REVISION_CONFLICT'),
    ({'expected_catalog_version': 'old'}, 'serca', 'CATALOG_VERSION_CONFLICT'),
    ({'expected_cycle_key': '2026-10-07'}, 'serca', 'CYCLE_CHANGED'),
    ({'difficulty_id': 'stage1'}, 'serca', 'DIFFICULTY_NOT_FOUND'),
    ({}, 'absent', 'RAID_NOT_FOUND'),
])
def test_stale_revision_and_wrong_pair_never_write(client, owned, changes, raid, code):
    h, _, cid = owned
    response = put(client, h, cid, body(**changes), raid=raid)
    assert response.json()['error']['code'] == code
    assert one(client, h, cid)['revision'] == 1


def test_batch_all_or_nothing_other_actor_and_session_authority(client, owned, login, monkeypatch):
    h, _, cid = owned
    assert get(client, {}, cid).status_code == 401
    assert put(client, {}, cid).status_code == 401
    other = another_user(login, monkeypatch, client)
    assert get(client, other, cid).status_code == 404
    assert put(client, other, cid).status_code == 404
    mixed = client.get(URL, headers=h, params=[('character_id', cid), ('character_id', str(uuid.uuid4()))])
    assert mixed.status_code == 404 and 'entries' not in mixed.json()
    assert one(client, h, cid)['revision'] == 1


@pytest.mark.parametrize('state,status', [('revoked', 401), ('disabled', 403), ('ownership_lost', 403)])
def test_current_auth_and_original_ack_before_resource_revalidation(client, owned, state, status):
    h, _, cid = owned; key = uuid.uuid4()
    first=put(client,h,cid,key=key)
    assert first.status_code == 200
    actor = principal(cid)[0].id
    with session() as db, db.begin():
        if state == 'revoked':
            db.scalar(select(Session).where(Session.user_id == actor)).revoked_at = now(db)
        elif state == 'disabled':
            db.get(User, actor).status = 'disabled'
        else:
            db.get(Account, db.get(Character, uuid.UUID(cid)).account_id).owner_id = None
    assert get(client, h, cid).status_code == status
    replay=put(client,h,cid,key=key)
    if state=='ownership_lost':
        assert replay.status_code==200 and replay.json()==first.json()
        assert put(client,h,cid,key=uuid.uuid4()).status_code==status
    else:assert replay.status_code==status


def test_suspect_blocks_new_completion_but_allows_own_manual_correction(client, owned):
    h, _, cid = owned
    assert put(client, h, cid).status_code == 200
    with session() as db, db.begin():
        character = db.get(Character, uuid.UUID(cid))
        character.lifecycle_state = character.status = 'suspect'; character.lifecycle_revision = 2
    out = one(client, h, cid)
    assert out['mark_blocked_reason'] == 'CHARACTER_UNUSABLE' and out['can_clear_manual_completion']
    assert put(client, h, cid, body(expected_revision=2, expected_lifecycle_revision=2)).json()['error']['code'] == 'CHARACTER_UNUSABLE'
    cleared = put(client, h, cid, body(completed=False, difficulty_id=None, expected_revision=2, expected_lifecycle_revision=2))
    assert cleared.status_code == 200 and cleared.json()['state'] == 'incomplete'


def test_manual_correction_preserves_party_completion_and_never_recreates_membership(client, owned):
    h, _, cid = owned; party_id = uuid.uuid4()
    seed(cid, manual_completed_at=STAMP, manual_difficulty_id='normal',
         party_completed_at=STAMP, party_difficulty_id='hard', completed_party_id=party_id)
    result = put(client, h, cid, body(completed=False, difficulty_id=None, expected_revision=2))
    assert result.status_code == 200 and result.json()['state'] == 'completed'
    assert result.json()['completion_sources'] == [dict(source='party', completed_at='2026-10-16T12:00:00Z',
                                                     difficulty_id='hard', party_id=str(party_id))]
    with session() as db:
        with pytest.raises(GameError, match='WEEKLY_ALREADY_COMPLETED'):
            service.require_available_for_participation(db, principal(cid)[0].id, uuid.UUID(cid), 'serca', date.fromisoformat(CYCLE))


def test_occupied_completion_needs_confirmation_and_correction_preserves_occupancy(client, owned):
    h, _, cid = owned; party_id = uuid.uuid4()
    seed(cid, active_party_id=party_id, active_difficulty_id='normal', joined_at=STAMP)
    before = one(client, h, cid)
    assert before['state'] == 'participating' and before['mark_blocked_reason'] == 'PARTICIPATION_CONFIRMATION_REQUIRED'
    blocked = put(client, h, cid, body(expected_revision=2))
    assert blocked.status_code == 409 and blocked.json()['error']['code'] == 'PARTICIPATION_CONFIRMATION_REQUIRED'
    result = put(client, h, cid, body(completed=False, difficulty_id=None, expected_revision=2))
    assert result.status_code == 200 and result.json() == before


def test_new_week_and_historical_replay_do_not_write_or_revive_old_occupancy(client, owned, monkeypatch):
    h, _, cid = owned; key = uuid.uuid4()
    first = put(client, h, cid, key=key).json()
    monkeypatch.setattr(service, 'now', lambda db: STAMP + timedelta(days=7))
    assert one(client, h, cid)['state'] == 'incomplete'
    past = one(client, h, cid, cycle_key=CYCLE)
    assert past['state'] == 'completed' and past['mark_blocked_reason'] == 'CURRENT_CYCLE_REQUIRED'
    assert not past['can_clear_manual_completion']
    assert put(client, h, cid).json()['error']['code'] == 'CYCLE_CHANGED'
    assert put(client, h, cid, key=key).json() == first
    assert put(client, h, cid, body(expected_cycle_key='2026-10-21')).status_code == 200
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyState)) == 2


def test_boundary_crossing_and_failed_result_commit_roll_back_ledger(client, owned, monkeypatch):
    h, _, cid = owned
    before = datetime(2026, 10, 20, 20, 59, 59, tzinfo=timezone.utc)
    after = before + timedelta(seconds=1)
    stamps = iter([before, before, after])
    monkeypatch.setattr(service, 'now', lambda db: next(stamps))
    assert put(client, h, cid).json()['error']['code'] == 'CYCLE_CHANGED'
    monkeypatch.setattr(service, 'now', lambda db: STAMP)
    assert one(client, h, cid)['revision'] == 1
    original = service.commit_result
    monkeypatch.setattr(service, 'commit_result', lambda *args: fail('SERVICE_UNAVAILABLE', 503))
    key = uuid.uuid4()
    assert put(client, h, cid, key=key).status_code == 503
    assert one(client, h, cid)['revision'] == 1
    monkeypatch.setattr(service, 'commit_result', original)
    assert put(client, h, cid, key=key).status_code == 200


def test_concurrent_normal_hard_completions_share_one_cas(client, owned):
    h, _, cid = owned
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda d: put(client, h, cid, body(difficulty_id=d)), ['normal', 'hard']))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert one(client, h, cid)['revision'] == 2


def test_completion_races_simulated_admission_under_same_transaction_lock(client, owned):
    h, _, cid = owned; actor = principal(cid); gate = Barrier(2)
    def complete():
        gate.wait()
        return put(client, h, cid).status_code
    def admit():
        gate.wait()
        try:
            with session() as db, db.begin():
                uid = authorize(db, actor, write=True)
                service.scope(db, uid, uuid.UUID(cid))
                row = service.require_available_for_participation(db, uid, uuid.UUID(cid), 'serca', date.fromisoformat(CYCLE))
                if row is None:
                    row = WeeklyState(user_id=uid, character_id=uuid.UUID(cid), raid_id='serca', cycle_key=date.fromisoformat(CYCLE), revision=1)
                    db.add(row)
                row.active_party_id = uuid.uuid4(); row.active_difficulty_id = 'hard'; row.joined_at = STAMP
                row.revision += 1; row.updated_at = STAMP
            return 200
        except GameError:
            return 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(complete), pool.submit(admit)
        assert sorted([a.result(), b.result()]) == [200, 409]
    assert one(client, h, cid)['state'] in ('completed', 'participating')


@pytest.mark.parametrize('values', [
    {'revision': 0}, {'cycle_key': date(2026, 10, 15)}, {'active_party_id': uuid.uuid4()},
    {'manual_difficulty_id': 'normal'}, {'party_completed_at': STAMP},
    {'manual_completed_at': STAMP, 'active_party_id': uuid.uuid4(), 'active_difficulty_id': 'normal', 'joined_at': STAMP},
])
def test_postgres_rejects_inconsistent_ledger(values, client, owned):
    _, _, cid = owned; uid = principal(cid)[0].id
    fields = dict(user_id=uid, character_id=uuid.UUID(cid), raid_id='serca', cycle_key=date.fromisoformat(CYCLE), revision=1, updated_at=STAMP)
    fields.update(values)
    with pytest.raises(IntegrityError):
        with session() as db, db.begin():
            db.add(WeeklyState(**fields)); db.flush()
