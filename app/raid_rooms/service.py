"""F1 internal services; every admission requires an explicit reviewed policy.

No routes, default allow-policy, provider I/O or production activation here.
"""
import uuid
from datetime import date, timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func
from app.auth.models import User
from app.core.database import session, now
from app.game_accounts.support import authorize, fail, reserve, release, commit_result, GameError
from app.raids import service as raids
from app.groups import admission_core as groups
from app.raid_rooms import core
from app.raid_rooms.commands import Selection
from app.raid_rooms.models import Room, Round, Membership, Application


def require_policy(policy):
    if not callable(policy):
        raise TypeError('An explicit admission policy is required; no production default')


def execute(principal, operation, key, payload, run, replay_check):
    ticket, replay = reserve(principal, 'room-core-'+operation, key, payload)
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            replay_check(db, authorize(db, principal), replay[1])
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            status, body, guard = run(db, uid)
            result = commit_result(db, ticket, status, body)
            db.flush()
            if guard:
                guard(now(db))
            return result
    except Exception:
        release(ticket)
        raise


def check_member_ack(db, uid, body):
    mid = body.get('actor_membership_id', body.get('membership_id'))
    m = db.get(Membership, uuid.UUID(mid)) if mid else None
    if m is None or m.user_id != uid or (str(m.room_id) != body.get('room_id') or str(m.round_id) != body.get('round_id')):
        fail('ROOM_MEMBERSHIP_REQUIRED', 403)


def check_application_ack(db, uid, body, *, applicant):
    row = db.get(Application, uuid.UUID(body['application_id']))
    if row is None or str(row.room_id) != body['room_id'] or (applicant and row.user_id != uid):
        fail('ROOM_APPLICATION_NOT_FOUND', 404)
    # For a rejection reserve() binds the original actor/operation/body; no current private state returned.


def guard(round, expires_at=None):
    def final(stamp):
        if raids.cycle(stamp).cycle_key != round.cycle_key.isoformat():
            fail('CYCLE_CHANGED')
        if stamp >= round.ends_at:
            fail('SCHEDULE_CONFLICT')
        if expires_at is not None and stamp >= expires_at:
            fail('APPLICATION_NOT_PENDING')
    return final


def ack(room, round, actor, target, stamp, application=None):
    return dict(room_id=room.id, round_id=round.id, actor_membership_id=actor.id,
        affected_membership_id=target.id, room_revision=room.revision, round_revision=round.revision,
        members_revision=room.members_revision, actor_membership_revision=actor.revision,
        affected_membership_revision=target.revision, application_id=application.id if application else None,
        application_revision=application.revision if application else None, executed_at=stamp)


def create(principal, key, command, *, policy):
    require_policy(policy)
    def run(db, uid):
        stamp = now(db)
        cycle = raids.cycle(stamp)
        if command.scope != 'public' or command.group_id is not None:
            fail('ROOM_FEATURE_UNSUPPORTED')
        if command.expected_cycle_key != cycle.cycle_key:
            fail('CYCLE_CHANGED')
        start, end = command.schedule.starts_at, command.schedule.ends_at
        if start is None or end is None or start >= end or start < cycle.starts_at or end > cycle.ends_at:
            fail('SCHEDULE_REVIEW_REQUIRED')
        if end <= stamp:
            fail('SCHEDULE_CONFLICT')
        try:
            raids.difficulty(command.raid_id, command.difficulty_id, command.expected_catalog_version)
        except raids.CatalogSelectionError as error:
            fail(error.code)
        raid = next(r for r in raids.catalog().raids if r.raid_id == command.raid_id)
        rid, round_id = uuid.uuid4(), uuid.uuid4()
        room = Room(id=rid, round_id=round_id, leader_membership_id=uuid.uuid4(), title=command.title,
            scope='public', group_id=None, creation_scope='public', creation_group_id=None,
            admission_mode=command.admission_mode, revision=1, members_revision=1,
            applications_revision=1, created_at=stamp)
        round = Round(id=round_id, room_id=rid, raid_id=command.raid_id,
            difficulty_id=command.difficulty_id, catalog_version=command.expected_catalog_version,
            cycle_key=date.fromisoformat(cycle.cycle_key), party_count=raid.party_count,
            revision=1, starts_at=start, ends_at=end, created_at=stamp)
        character, build = core.selection(db, uid, command.selection, round, increasing=True)
        policy(db, uid, room, round, command.selection, character)
        db.add(room); db.flush()
        db.add(round); db.flush()
        membership = core.occupy(db, uid, room, round, command.selection, character, build, stamp)
        room.leader_membership_id = membership.id
        return 201, ack(room, round, membership, membership, stamp), guard(round)
    return execute(principal, 'create', key, jsonable_encoder(command), run, check_member_ack)


def get(principal, rid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        room = core.room(db, rid)
        core.supported(room)
        mine = core.member(db, room, uid)
        round = db.get(Round, room.round_id)
        rows = list(db.scalars(select(Membership).where(Membership.room_id == rid,
                         Membership.ended_at.is_(None)).order_by(Membership.party_no, Membership.slot_no)))
        return jsonable_encoder(dict(room_id=rid, round_id=round.id, revision=room.revision,
            round_revision=round.revision, members_revision=room.members_revision,
            my_membership_id=mine.id, my_membership_revision=mine.revision,
            leader_membership_id=room.leader_membership_id,
            phase='current' if raids.cycle(now(db)).cycle_key == round.cycle_key.isoformat() else 'cycle_closed',
            policy_snapshot=core.policy_snapshot(db, room), issues=core.issues(db, room),
            members=[dict(membership_id=m.id, revision=m.revision, character_id=m.character_id,
                selected_role=m.selected_role, party_no=m.party_no, slot_no=m.slot_no,
                display=m.display, joined_at=m.joined_at) for m in rows]))


def admit(principal, rid, key, command, *, policy, applying=False):
    require_policy(policy)
    def run(db, uid):
        room = core.room(db, rid)
        core.supported(room)
        round, cycle = core.current(db, room, command.expected_cycle_key, command.expected_catalog_version)
        core.cas(room, round, command)
        core.require_policy_snapshot(db, room, command.expected_policy_snapshot)
        if room.admission_mode != ('leader_only' if applying else 'direct_join'):
            fail('ROOM_FEATURE_UNSUPPORTED')
        if db.scalar(select(Membership.id).where(Membership.room_id == rid,
                Membership.user_id == uid, Membership.ended_at.is_(None))):
            fail('ROOM_MEMBER_EXISTS')
        character, build = core.selection(db, uid, command.selection, round, increasing=not applying)
        policy(db, uid, room, round, command.selection, character)
        stamp = now(db)
        if applying:
            pending = db.scalar(select(Application).where(Application.room_id == rid,
                Application.user_id == uid, Application.state == 'pending'))
            if pending is not None:
                if application_state(db, pending, stamp) == 'pending':
                    fail('ROOM_APPLICATION_EXISTS')
                finish_application(db, room, pending, 'expired', pending.expires_at)
                db.flush()
            value = Application(room_id=rid, round_id=round.id, user_id=uid,
                selection=jsonable_encoder(command.selection), display=groups.display(character),
                state='pending', revision=1, created_at=stamp, expires_at=min(stamp+timedelta(hours=24), cycle.ends_at))
            db.add(value); db.flush()
            room.applications_revision += 1
            core.touch_user(db, uid, application=True)
            return 201, application_ack(value, stamp), guard(round, value.expires_at)
        membership = core.occupy(db, uid, room, round, command.selection, character, build, stamp)
        room.revision += 1
        room.members_revision += 1
        round.revision += 1
        return 200, ack(room, round, membership, membership, stamp), guard(round)
    replay_check = (lambda db, uid, body: check_application_ack(db, uid, body, applicant=True)) if applying else check_member_ack
    return execute(principal, 'apply' if applying else 'join', key,
        dict(room_id=str(rid), body=jsonable_encoder(command)), run, replay_check)


def application_state(db, row, stamp):
    if row.state != 'pending':
        return row.state
    if stamp >= row.expires_at:
        return 'expired'
    room = db.get(Room, row.room_id)
    if room.ended_at is not None or db.scalar(select(Membership.id).where(
            Membership.room_id == room.id, Membership.user_id == row.user_id, Membership.ended_at.is_(None))):
        return 'cancelled'
    return 'pending'


def application_ack(row, stamp):
    return dict(room_id=row.room_id, application_id=row.id, application_revision=row.revision,
                state=row.state, executed_at=stamp)


def finish_application(db, room, row, state, stamp):
    row.state, row.ended_at = state, stamp
    row.revision += 1
    room.applications_revision += 1
    core.touch_user(db, row.user_id, application=True)


def application(principal, aid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        row = db.get(Application, aid)
        if row is None:
            fail('ROOM_APPLICATION_NOT_FOUND', 404)
        room = core.room(db, row.room_id, active=False)
        core.supported(room)
        if row.user_id != uid:
            core.leader(db, room, uid)
        stamp = now(db)
        state = application_state(db, row, stamp)
        ended = row.ended_at
        if state == 'expired' and ended is None:
            ended = row.expires_at
        elif state == 'cancelled' and ended is None:
            ended = room.ended_at
        return jsonable_encoder(dict(application_id=aid, room_id=row.room_id, revision=row.revision,
            state=state, expires_at=row.expires_at, ended_at=ended, display=row.display))


def decide(principal, aid, key, command, *, approve=False, policy=None):
    if approve:
        require_policy(policy)
    def run(db, uid):
        row = db.get(Application, aid)
        if row is None:
            fail('ROOM_APPLICATION_NOT_FOUND', 404)
        room = core.room(db, row.room_id)
        core.supported(room)
        actor = core.leader(db, room, uid)
        round, _ = core.current(db, room, command.expected_cycle_key)
        core.cas(room, round, command)
        if row.revision != command.expected_application_revision:
            fail('REVISION_CONFLICT')
        stamp = now(db)
        if application_state(db, row, stamp) != 'pending':
            fail('APPLICATION_NOT_PENDING')
        if approve:
            core.require_policy_snapshot(db, room, command.expected_policy_snapshot)
            data = Selection.model_validate(row.selection)
            try:
                character, build = core.selection(db, row.user_id, data, round, increasing=True)
            except GameError as error:
                if error.code in ('REVISION_CONFLICT', 'POLICY_CONTEXT_CHANGED'):
                    fail('APPLICATION_CONTEXT_CHANGED')
                raise
            policy(db, row.user_id, room, round, data, character)
            membership = core.occupy(db, row.user_id, room, round, data, character, build, stamp)
            room.revision += 1
            room.members_revision += 1
            round.revision += 1
            finish_application(db, room, row, 'accepted', stamp)
            body = ack(room, round, actor, membership, stamp, row)
        else:
            finish_application(db, room, row, 'rejected', stamp)
            body = application_ack(row, stamp)
        return 200, body, guard(round, row.expires_at)
    return execute(principal, 'approve' if approve else 'reject', key,
        dict(application_id=str(aid), body=jsonable_encoder(command)), run,
        check_member_ack if approve else lambda db, uid, body: check_application_ack(db, uid, body, applicant=False))


def withdraw(principal, aid, key, command):
    def run(db, uid):
        row = db.get(Application, aid)
        if row is None or row.user_id != uid:
            fail('ROOM_APPLICATION_NOT_FOUND', 404)
        room = core.room(db, row.room_id, active=False)
        if row.revision != command.expected_application_revision:
            fail('REVISION_CONFLICT')
        stamp = now(db)
        state = application_state(db, row, stamp)
        if state != 'pending':
            fail('APPLICATION_NOT_PENDING')
        finish_application(db, room, row, 'withdrawn', stamp)
        def final(current):
            if current >= row.expires_at:
                fail('APPLICATION_NOT_PENDING')
        return 200, application_ack(row, stamp), final
    return execute(principal, 'withdraw', key, dict(application_id=str(aid), body=jsonable_encoder(command)),
        run, lambda db, uid, body: check_application_ack(db, uid, body, applicant=True))


def recover(principal, rid, key, command, operation):
    if operation not in ('leave', 'transfer', 'end'):
        raise ValueError('Unsupported recovery operation')
    def run(db, uid):
        room = core.room(db, rid)
        # Group recovery disclosure is Q3, and has no enabled internal adapter in F1.
        core.supported(room)
        membership = core.member(db, room, uid)
        round = db.get(Round, room.round_id)
        core.cas(room, round, command, membership)
        stamp = now(db)
        if operation == 'transfer':
            if membership.id != room.leader_membership_id:
                fail('ROOM_LEADER_REQUIRED', 403)
            if command.target_membership_id == membership.id:
                fail('ROOM_TRANSFER_TARGET_INVALID')
            target = db.get(Membership, command.target_membership_id)
            if target is None or target.room_id != rid or target.ended_at is not None:
                fail('ROOM_TARGET_UNAVAILABLE')
            user = db.scalar(select(User).where(User.id == target.user_id).with_for_update())
            if user is None or user.status != 'active':
                fail('ROOM_TARGET_UNAVAILABLE')
            if target.revision != command.expected_target_membership_revision:
                fail('REVISION_CONFLICT')
            room.leader_membership_id = target.id
            membership.revision += 1
            target.revision += 1
            room.revision += 1
            room.members_revision += 1
            core.directory(db)
            return 200, ack(room, round, membership, target, stamp), None
        if operation == 'leave' and membership.id == room.leader_membership_id:
            fail('ROOM_LEADER_TRANSFER_REQUIRED')
        if operation == 'end':
            if membership.id != room.leader_membership_id:
                fail('ROOM_LEADER_REQUIRED', 403)
            count = db.scalar(select(func.count()).select_from(Membership).where(
                Membership.room_id == rid, Membership.ended_at.is_(None)))
            if count != 1:
                fail('ROOM_LAST_MEMBER_REQUIRED')
            room.ended_at = round.ended_at = stamp
            room.applications_revision += 1
        core.end_membership(db, room, round, membership, stamp)
        room.revision += 1
        room.members_revision += 1
        round.revision += 1
        body = dict(room_id=rid, round_id=round.id, membership_id=membership.id,
                    membership_revision=membership.revision, ended_at=stamp)
        if operation == 'end':
            body.update(room_revision=room.revision, round_revision=round.revision)
        return 200, body, None
    return execute(principal, operation, key, dict(room_id=str(rid), body=jsonable_encoder(command)), run, check_member_ack)
