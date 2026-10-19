"""Candidate F2 reads: one read-only snapshot, no provider calls or reservations."""
from contextlib import contextmanager
from datetime import date
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from app.core.database import session, now
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Character, CharacterRoleSummary
from app.game_accounts.support import authorize, fail, cursor_encode, cursor_decode, GameError
from app.member_limits.models import MemberUsageHead, MemberUsageLimits
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from app.raid_rooms import core, projections as p, schemas as s, policies, service, runtime
from app.raid_rooms.commands import Selection
from app.raid_rooms.models import Room, Round, Membership, Application, DirectoryHead, MemberHead


@contextmanager
def snapshot(principal, *, public=False):
    if principal is None and not public:
        fail('AUTH_REQUIRED', 401)
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        uid = authorize(db, principal) if principal is not None else None
        yield db, uid, now(db)


def encode(model, data):
    return model.model_validate(data).model_dump(mode='json')


def visible(db, rid):
    room = core.room(db, rid, active=False)
    # Q3 is deliberately not implemented. Group existence must not leak via public reads.
    if room.scope != 'public' or room.group_id is not None:
        fail('ROOM_NOT_FOUND', 404)
    return room, db.get(Round, room.round_id)


def page(items, *, scope, revision, limit, cursor):
    if type(limit) is not int or not 1 <= limit <= 50:
        fail('INVALID_REQUEST', 400)
    start = cursor_decode(cursor, scope, revision) if cursor is not None else 0
    if start > len(items):
        fail('INVALID_REQUEST', 400)
    following = start + limit
    token = cursor_encode(dict(scope=scope, revision=revision, offset=following)) if following < len(items) else None
    return items[start:following], token


def digest(data):
    return lifecycle.digest(jsonable_encoder(data))


def room_list(principal=None, *, scope='public', group_id=None, raid_id=None, difficulty_id=None,
              state='active', limit=20, cursor=None):
    if scope not in ('public', 'group') or state not in ('active', 'ended', 'all') or (
            difficulty_id is not None and raid_id is None) or (scope == 'public' and group_id is not None) or (scope == 'group' and group_id is None):
        fail('INVALID_REQUEST', 400)
    with snapshot(principal, public=True) as (db, uid, stamp):
        if scope == 'group':
            # No group-room adapter until Q3 is settled; no group metadata is returned.
            fail('ROOM_FEATURE_UNSUPPORTED')
        cycle = raids.cycle(stamp).cycle_key
        query = select(Room, Round).join(Round, Room.round_id == Round.id).where(
            Room.scope == 'public', Room.group_id.is_(None), Round.cycle_key == date.fromisoformat(cycle))
        if state != 'all':
            query = query.where(Room.ended_at.is_(None) if state == 'active' else Room.ended_at.is_not(None))
        if raid_id is not None:
            query = query.where(Round.raid_id == raid_id)
        if difficulty_id is not None:
            query = query.where(Round.difficulty_id == difficulty_id)
        rows = list(db.execute(query.order_by(Room.created_at.desc(), Room.id.desc())))
        items = [p.summary(db, room, round, stamp) for room, round in rows]
        head = db.get(DirectoryHead, 1)
        if head is None:
            fail('SERVICE_UNAVAILABLE', 503)
        binding = jsonable_encoder(['raid-room-list', str(uid) if uid else None,
                                    scope, group_id, raid_id, difficulty_id, state, limit])
        items, token = page(items, scope=binding, revision=digest([cycle, head.revision, items]), limit=limit, cursor=cursor)
        return encode(s.RoomPage, dict(items=items, directory_revision=head.revision, next_cursor=token))


def room_summary(rid, principal=None):
    with snapshot(principal, public=True) as (db, uid, stamp):
        room, round = visible(db, rid)
        return encode(s.RoomSummary, p.summary(db, room, round, stamp))


def room_detail(principal, rid):
    with snapshot(principal) as (db, uid, stamp):
        room, round = visible(db, rid)
        mine = core.member(db, room, uid)
        if room.ended_at is not None:
            fail('ROOM_NOT_ACTIVE')
        return encode(s.RoomDetail, p.detail(db, room, round, mine, stamp))


def management(principal, rid):
    with snapshot(principal) as (db, uid, stamp):
        room, round = visible(db, rid)
        mine = core.member(db, room, uid)
        if room.ended_at is not None:
            fail('ROOM_NOT_ACTIVE')
        return encode(s.RoomManagement, p.management(db, room, round, mine, stamp))


def memberships(principal, *, state='current', limit=20, cursor=None):
    if state not in ('current', 'ended', 'all'):
        fail('INVALID_REQUEST', 400)
    with snapshot(principal) as (db, uid, stamp):
        rows = list(db.scalars(select(Membership).where(Membership.user_id == uid)
                              .order_by(Membership.joined_at.desc(), Membership.id.desc())))
        items, contexts = [], []
        for m in rows:
            room, round = db.get(Room, m.room_id), db.get(Round, m.round_id)
            # No Q3 group disclosure, even in a mixed personal page.
            if room.scope != 'public' or room.group_id is not None:
                continue
            ended = m.ended_at is not None
            if state != 'all' and (state == 'ended') != ended:
                continue
            items.append(dict(room_id=room.id, round_id=round.id, membership_id=m.id, revision=m.revision,
                character_id=m.character_id, selected_role=m.selected_role, party_no=m.party_no,
                joined_at=m.joined_at, ended_at=m.ended_at,
                end_reason=('room_ended' if room.ended_at == m.ended_at else 'left') if ended else None,
                relation='ended' if ended else 'current', round_cycle_key=round.cycle_key,
                round_phase=p.phase(room, round, stamp), access_state='history_only' if ended else 'full',
                group_id=room.group_id))
            contexts.append([room.revision, round.revision, core.policy_snapshot(db, room)])
        head = db.get(MemberHead, uid)
        version = head.membership_revision if head else 1
        items, token = page(items, scope=['room-memberships', str(uid), state, limit],
            revision=digest([raids.cycle(stamp).cycle_key, version, items, contexts]), limit=limit, cursor=cursor)
        return encode(s.MembershipPage, dict(items=items, membership_head=version, next_cursor=token))


def application(principal, aid):
    with snapshot(principal) as (db, uid, stamp):
        row = db.get(Application, aid)
        if row is None:
            fail('ROOM_APPLICATION_NOT_FOUND', 404)
        room, round = visible(db, row.room_id)
        if row.user_id != uid:
            # A former leader or unrelated participant gets no application existence information.
            mine = db.scalar(select(Membership).where(Membership.room_id == room.id, Membership.user_id == uid,
                             Membership.ended_at.is_(None)))
            if mine is None or mine.id != room.leader_membership_id or room.ended_at is not None:
                fail('ROOM_APPLICATION_NOT_FOUND', 404)
        return encode(s.Application, p.application(db, room, round, row, uid, stamp))


def applications(principal, *, room_id=None, state='pending', limit=20, cursor=None):
    if state not in ('pending', 'ended', 'all'):
        fail('INVALID_REQUEST', 400)
    with snapshot(principal) as (db, uid, stamp):
        query = select(Application)
        if room_id is None:
            query = query.where(Application.user_id == uid)
            head = db.get(MemberHead, uid)
            version = head.application_revision if head else 1
        else:
            room, _ = visible(db, room_id)
            if room.ended_at is not None:
                fail('ROOM_NOT_ACTIVE')
            core.leader(db, room, uid)  # Authorization precedes cursor validation.
            query = query.where(Application.room_id == room_id)
            version = room.applications_revision
        items, contexts = [], []
        for row in db.scalars(query.order_by(Application.created_at.desc(), Application.id.desc())):
            room, round = db.get(Room, row.room_id), db.get(Round, row.round_id)
            if room.scope != 'public' or room.group_id is not None:
                continue
            value = p.application(db, room, round, row, uid, stamp)
            if state != 'all' and (state == 'pending') != (value['state'] == 'pending'):
                continue
            items.append(value)
            contexts.append([room.revision, round.revision, room.members_revision, core.policy_snapshot(db, room)])
        items, token = page(items, scope=['room-applications', str(uid), str(room_id), state, limit],
                           revision=digest([raids.cycle(stamp).cycle_key, version, items, contexts]), limit=limit, cursor=cursor)
        return encode(s.ApplicationPage, dict(items=items, applications_revision=version, next_cursor=token))


def admission_context(principal, rid, *, character_id, selected_role, party_no, intent):
    if selected_role not in ('dealer', 'support') or type(party_no) is not int or party_no not in (1, 2) or intent not in ('apply', 'join'):
        fail('INVALID_REQUEST', 400)
    with snapshot(principal) as (db, uid, stamp):
        room, round = visible(db, rid)
        c = db.get(Character, character_id)
        reg = p.registration(db, uid, c)
        a = db.get(Account, c.account_id) if c else None
        if reg is None or a is None or a.owner_id != uid:
            fail('CHARACTER_NOT_FOUND', 404)
        role = db.get(CharacterRoleSummary, (uid, c.id, a.ownership_revision, selected_role))
        weekly = db.get(WeeklyState, (uid, c.id, round.raid_id, round.cycle_key))
        limits, usage = db.get(MemberUsageLimits, uid), db.get(MemberUsageHead, uid)
        selection = Selection(registration_id=reg.id, character_id=c.id, selected_role=selected_role,
            party_no=party_no, expected_registration_version=reg.version,
            expected_ownership_revision=a.ownership_revision, expected_roster_revision=a.roster_revision,
            expected_lifecycle_revision=c.lifecycle_revision, expected_role_summary_version=role.version if role else 1,
            expected_weekly_revision=weekly.revision if weekly else 1,
            expected_limits_revision=limits.revision if limits else 1, expected_usage_revision=usage.revision if usage else 1)
        reason = p.progress_reason(db, room, round, stamp)
        if reason is None:
            try:
                if room.admission_mode != ('leader_only' if intent == 'apply' else 'direct_join'):
                    fail('ROOM_FEATURE_UNSUPPORTED')
                if db.scalar(select(Membership.id).where(Membership.room_id == rid, Membership.user_id == uid,
                             Membership.ended_at.is_(None))) is not None:
                    fail('ROOM_MEMBER_EXISTS')
                if intent == 'apply':
                    pending = db.scalar(select(Application).where(Application.room_id == rid, Application.user_id == uid,
                                        Application.state == 'pending'))
                    if pending and service.application_state(db, pending, stamp) == 'pending':
                        fail('ROOM_APPLICATION_EXISTS')
                character, _ = core.selection(db, uid, selection, round, increasing=intent == 'join', lock=False)
                policies.public_finite(db, uid, room, round, selection, character)
                if intent == 'join':
                    core.require_no_time_overlap(db, uid, round)
                    core.slot(db, uid, room, round, selection, character)
            except GameError as error:
                reason = error.code
        reason = reason or runtime.admission_reason()
        return encode(s.AdmissionContext, dict(room_id=room.id, round_id=round.id,
            room_revision=room.revision, round_revision=round.revision, members_revision=room.members_revision,
            policy_snapshot=core.policy_snapshot(db, room), catalog_version=round.catalog_version,
            cycle_key=round.cycle_key, selection=selection, eligibility=p.permission(reason), evaluated_at=stamp))
