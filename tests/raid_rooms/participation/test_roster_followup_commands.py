"""Mixed completed history/current selection through real isolated commands."""
import uuid
from datetime import date, timedelta
import pytest
from sqlalchemy import select, inspect, delete
from app.game_accounts.support import GameError
from app.core.database import session, now
from app.raid_rooms.schedules import beta_schedule
from app.raid_rooms.participation import cycle_lifecycle as life, cycle_character, cycle_leadership
from app.raid_rooms.reads import cycle_member_reads
from app.raid_rooms.participation import membership_actions
from app.raid_rooms.admissions import cycle_continuation
from app.raid_rooms import roster_participation as rp
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentAssignment as Assignment
from app.raid_rooms.source_models import TimeReservation
from tests.raid_rooms.participation.test_roster_public_contract import presence_db, policy_db, group_beta, beta, current, candidate, ready, sources, imported, people, worlds, bundle, change, complete, actor, P, Q, client, observe
from tests.raid_rooms.admissions.test_beta_recruitment import beta_join
from tests.raid_rooms.schedules.test_recruitment_cycle_times import save_personal, submit, confirm
from tests.raid_rooms.participation.test_membership_actions import body as departure_body
from tests.raid_rooms.participation.test_recruitment_cycle_lifecycle import continue_body, cancel_member
from tests.raid_rooms.common.test_raid_room_migrations import table_digests


def row_for(db, rid, key):
    return db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid,
        RoomCycle.cycle_key == date.fromisoformat(key)))


def mixed(w, rid, key):
    complete(w, rid, key, index=0)
    cycle_character.execute(actor(w['uid']), rid, uuid.uuid4(), change(w, rid, key))
    with session() as db:
        row = row_for(db, rid, key)
        cm = life.actual_member(db, row, w['uid'])
        active, preserved = rp.split(db, row, cm)
        assert len(active) == len(preserved) == 1
        assert active[0].character_id == uuid.UUID(w['ids'][1])
        assert preserved[0].character_id == uuid.UUID(w['ids'][0])
        return cm.id, life.assignment_snapshot(preserved[0])


def assert_preserved(snapshot):
    with session() as db:
        assert life.assignment_snapshot(db.get(Assignment, snapshot['id'])) == snapshot


def test_mixed_schedule_submit_confirm_preserves_history_and_other_week(presence_db):
    _, a, _ = presence_db
    rid, c, n = bundle(a)
    opposite = cycle_member_reads.plan(actor(a['uid']), rid, n)['data']['my_assignments']
    with rp.using(P):
        cmid, preserved = mixed(a, rid, c)
        with session() as db, db.begin():
            row = row_for(db, rid, c)
            saved = beta_schedule.get(db, row)
            beta_schedule.reconcile(db, db.get(Room, rid), row,
                saved.base_starts_at - timedelta(minutes=20))
        save_personal(a)
        assert submit(a, rid, c)[0] == 200
        assert confirm(a, rid, c)[0] == 200
        with session() as db:
            reservations = list(db.scalars(select(TimeReservation).where(
                TimeReservation.user_id == a['uid'], TimeReservation.released_at.is_(None))))
            active, _ = rp.split(db, row_for(db, rid, c), db.get(life.CycleMember, cmid))
            current = [r for r in reservations if r.assignment_id in {a.id for a in active}]
            assert len(current) == 1
            assert db.get(Assignment, current[0].assignment_id).character_id == uuid.UUID(a['ids'][1])
    assert_preserved(preserved)
    assert cycle_member_reads.plan(actor(a['uid']), rid, n)['data']['my_assignments'] == opposite


def test_mixed_departure_failure_rolls_back_history_leases_and_leadership(presence_db, monkeypatch):
    engine, a, b = presence_db
    rid, c, n = bundle(a)
    beta_join(b, rid, c)
    with rp.using(P):
        _, preserved = mixed(a, rid, c)
        ctx = membership_actions.get(actor(a['uid']), rid, c)
        request = departure_body(ctx, 'leave_target')
        tables = set(inspect(engine).get_table_names()) - {'game_account_requests'}
        before = table_digests(engine, tables)
        original = membership_actions.cleanup
        def fail_after_cleanup(*args, **kwargs):
            original(*args, **kwargs)
            raise GameError('SYNTHETIC_ROLLBACK')
        with monkeypatch.context() as patch:
            patch.setattr(membership_actions, 'cleanup', fail_after_cleanup)
            with pytest.raises(GameError, match='SYNTHETIC_ROLLBACK'):
                membership_actions.execute(actor(a['uid']), rid, uuid.uuid4(), request)
        assert table_digests(engine, tables) == before
        assert membership_actions.execute(actor(a['uid']), rid, uuid.uuid4(), request)[0] == 200
    assert_preserved(preserved)


def test_completed_mixed_history_has_authority_but_no_current_selection(presence_db):
    from app.raid_rooms import cycle_schemas
    _, a, b = presence_db
    rid, c, n = bundle(a)
    beta_join(b, rid, c)
    with rp.using(P):
        _, preserved = mixed(a, rid, c)
        complete(a, rid, c, index=1)
        with session() as db:
            source = life.source(db, a['uid'], db.get(Room, rid), now(db))
            assert source[1].state == 'completed'
            assert source[3] is None and source[6] is None
            assert life.qualify(db, db.get(Room, rid), source[0], source[1])[0] is None
        ctx = cycle_leadership.get_transfer(actor(a['uid']), rid, c)
        assert ctx['data']['permission']['allowed']
        candidate = next(v for v in ctx['data']['candidates'] if v['character_id'] == b['ids'][0])
        request = cycle_schemas.Transfer.model_validate(dict(
            expected_cycle_key=ctx['scope']['current_cycle_key'], target_cycle_key=c,
            expected_target_revision=ctx['scope']['target_revision'], context_token=ctx['data']['context_token'],
            expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
            candidate_cycle_member_id=candidate['cycle_member_id'], expected_candidate_revision=candidate['revision']))
        assert cycle_leadership.transfer(actor(a['uid']), rid, uuid.uuid4(), request)[0] == 200
    assert_preserved(preserved)


@pytest.mark.parametrize('mixed_leaves', [False, True])
def test_mixed_actual_departure_and_succession_are_target_only(presence_db, mixed_leaves):
    _, a, b = presence_db
    rid, c, n = bundle(a)
    beta_join(b, rid, c)
    beta_join(b, rid, n)
    subject = a if mixed_leaves else b
    opposite = cycle_member_reads.plan(actor(a['uid']), rid, n)['data']['my_assignments']
    with rp.using(P):
        cmid, preserved = mixed(subject, rid, c)
        ctx = membership_actions.get(actor(a['uid']), rid, c)
        option = ctx['data']['options']['leave_target']
        assert option['permission']['allowed']
        command = uuid.uuid4()
        request = departure_body(ctx, 'leave_target')
        result = membership_actions.execute(actor(a['uid']), rid, command, request)
        assert result[0] == 200
        assert membership_actions.execute(actor(a['uid']), rid, command, request) == result
        with session() as db:
            row = row_for(db, rid, c)
            successor = db.get(life.CycleMember, db.get(CycleGeneration, (row.id, row.generation)).leader_cycle_member_id)
            assert successor.user_id == b['uid']
            assert life.actual_member(db, row, a['uid']) is None
            if not mixed_leaves:
                assert successor.id == cmid
                assert life.qualify(db, db.get(Room, rid), row, successor)[0].character_id == uuid.UUID(b['ids'][1])
    assert_preserved(preserved)
    assert cycle_member_reads.plan(actor(b['uid']), rid, n)['data']['my_assignments'][0]['character_id'] == b['ids'][0]
    assert cycle_member_reads.plan(actor(a['uid']), rid, n)['data']['my_assignments'] == opposite


def test_mixed_continuation_uses_current_active_character_and_preserves_p(presence_db):
    _, a, b = presence_db
    rid, c, n = bundle(a)
    beta_join(b, rid, c)
    with rp.using(P):
        _, preserved = mixed(b, rid, c)
        ctx = cycle_continuation.get(actor(b['uid']), rid, n)
        assert ctx['data']['permission']['allowed']
        assert ctx['data']['selection']['character_id'] == b['ids'][1]
        request = continue_body(ctx)
        command = uuid.uuid4()
        result = cycle_continuation.execute(actor(b['uid']), rid, command, request)
        assert result[0] == 200
        assert cycle_continuation.execute(actor(b['uid']), rid, command, request) == result
        assigned = cycle_member_reads.plan(actor(b['uid']), rid, n)['data']['my_assignments']
        assert len(assigned) == 2
        assert all(v['character_id'] == b['ids'][1] for v in assigned)
    assert_preserved(preserved)


@pytest.mark.parametrize('kind', ['opening', 'continuation', 'reopening'])
def test_completed_source_requires_explicit_new_selection_through_http(presence_db, kind):
    _, a, b = presence_db
    is_opening = kind != 'continuation'
    if kind == 'opening':
        rid, c = bundle(a, continuation=False)
        w = a
    elif kind == 'reopening':
        rid, c, next_key = bundle(a)
        w = a
        with rp.using(P):
            cancel_member(a, rid, next_key)
    else:
        rid, c, _ = bundle(a)
        w = b
    beta_join(b, rid, c)
    n = (date.fromisoformat(c) + timedelta(days=7)).isoformat()
    with rp.using(P):
        cmid, preserved = mixed(w, rid, c)
        complete(w, rid, c, index=1)
    with session() as db:
        saved = beta_schedule.get(db, row_for(db, rid, c))
        next_base = saved.base_starts_at + timedelta(days=7)
        originals = [life.assignment_snapshot(v) for v in life.assignments(
            db, row_for(db, rid, c), db.get(life.CycleMember, cmid))]
    query = Q | P | dict(target_cycle_key=n)
    if is_opening:
        query |= dict(intent='reopen' if kind == 'reopening' else 'open',
            base_starts_at=next_base.isoformat(), early_coordination_enabled='false')
    context_path = f'/v2/me/raid-rooms/{rid}/' + ('opening-context' if is_opening else 'continuation-context')
    command_path = f'/v2/raid-rooms/{rid}/' + ('recruitment-openings' if is_opening else 'continuation-participations')
    def command_body(value, selection=None):
        d, s = value['data'], value['scope']
        body = dict(expected_cycle_key=s['current_cycle_key'], target_cycle_key=n,
            expected_target_revision=s['target_revision'], context_token=d['context_token'],
            selection=selection or d['selection'], target_items=d['targets'], target_session_ids=d['target_session_ids'])
        if is_opening:
            body |= dict(intent='reopen' if d['opening_effect'] == 'reopen_and_join' else 'open',
                beta_schedule=d['beta_schedule_config'])
        return body
    with client(w) as http:
        if kind == 'reopening':
            wrong = http.get(context_path, params=query | dict(intent='open'))
            assert wrong.status_code == 200, wrong.text
            assert wrong.json()['data']['permission']['reason'] == 'TARGET_REOPEN_REQUIRED'
        blocked = http.get(context_path, params=query)
        assert blocked.status_code == 200, blocked.text
        empty = blocked.json()
        assert empty['data']['selection'] is None
        assert empty['data']['permission'] == dict(allowed=False, reason='CHARACTER_SELECTION_REQUIRED', next_change_at=None)
        explicit = http.get(context_path, params=query | dict(character_id=w['ids'][1], selected_role='dealer'))
        assert explicit.status_code == 200, explicit.text
        chosen = explicit.json()
        assert chosen['data']['permission']['allowed'], chosen
        # A valid character copied into an unselected context cannot bypass it.
        tampered = command_body(empty, chosen['data']['selection'])
        tampered['target_items'] = chosen['data']['targets']
        denied = http.post(command_path, params=Q | P,
            json=tampered, headers={'Idempotency-Key':str(uuid.uuid4())})
        assert denied.status_code == 409, denied.text
        assert denied.json()['error']['code'] == 'CHARACTER_SELECTION_REQUIRED'
        with session() as db:
            next_row = row_for(db, rid, n)
            assert next_row is None if kind == 'opening' else life.actual_member(db, next_row, w['uid']) is None
        # Source history still authorizes the actor, but cannot replace a new
        # destination character's current activity requirement or stale CAS.
        from app.game_accounts.models import Activity
        with session() as db, db.begin():
            activity = db.scalar(select(Activity).where(Activity.character_id == uuid.UUID(w['ids'][1])))
            activity_values = {column.name:getattr(activity, column.name) for column in Activity.__table__.columns}
            db.execute(delete(Activity).where(Activity.character_id == uuid.UUID(w['ids'][1])))
        invalid = http.get(context_path, params=query | dict(character_id=w['ids'][1], selected_role='dealer'))
        assert invalid.status_code == 200, invalid.text
        assert invalid.json()['data']['selection'] is None
        assert invalid.json()['data']['permission']['reason'] == 'ACTIVITY_SELECTION_REQUIRED'
        stale = http.post(command_path, params=Q | P, json=command_body(chosen),
            headers={'Idempotency-Key':str(uuid.uuid4())})
        assert stale.status_code == 409, stale.text
        assert stale.json()['error']['code'] == 'TARGET_CONTEXT_STALE'
        with session() as db, db.begin():
            db.add(Activity(**activity_values))
            next_row = row_for(db, rid, n)
            assert next_row is None if kind == 'opening' else life.actual_member(db, next_row, w['uid']) is None
        chosen_response = http.get(context_path, params=query | dict(character_id=w['ids'][1], selected_role='dealer'))
        assert chosen_response.status_code == 200, chosen_response.text
        chosen = chosen_response.json()
        assert chosen['data']['permission']['allowed']
        command = uuid.uuid4()
        body = command_body(chosen)
        result = http.post(command_path, params=Q | P, json=body, headers={'Idempotency-Key':str(command)})
        assert result.status_code == 200, result.text
        replay = http.post(command_path, params=Q, json=body, headers={'Idempotency-Key':str(command)})
        assert replay.status_code == 200 and replay.json() == result.json(), replay.text
        existing_query = query | dict(intent='open') if is_opening else query
        again = http.get(context_path, params=existing_query)
        assert again.status_code == 200, again.text
        if kind == 'continuation':
            assert again.json()['data']['permission']['reason'] == 'ROOM_MEMBER_EXISTS'
        else:
            assert again.json()['data']['opening_effect'] == 'already_open'
            assert again.json()['data']['permission']['allowed']
            # Missing existing N still keeps its own seat; an opening noop
            # must not turn into a fresh eligibility check on a completed C.
            observe(dict(w, ids=[w['ids'][1], w['ids'][0]]))
            existing = http.get(context_path, params=existing_query)
            assert existing.status_code == 200, existing.text
            assert existing.json()['data']['selection']['character_id'] == w['ids'][1]
            assert existing.json()['data']['permission']['allowed']
            noop = http.post(command_path, params=Q | P, json=command_body(existing.json()),
                headers={'Idempotency-Key':str(uuid.uuid4())})
            assert noop.status_code == 200, noop.text
            assert noop.json()['data']['outcome'] == 'noop'
        with session() as db:
            row = row_for(db, rid, n)
            cm = life.actual_member(db, row, w['uid'])
            assert all(v.character_id == uuid.UUID(w['ids'][1]) for v in life.assignments(db, row, cm))
    with session() as db:
        assert [life.assignment_snapshot(v) for v in life.assignments(
            db, row_for(db, rid, c), db.get(life.CycleMember, cmid))] == originals
    assert_preserved(preserved)
