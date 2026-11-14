"""Read-only account-wide reservations; no ownership/activity requalification."""
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import load_only
from app.raids import service as raids
from app.game_accounts.common.support import fail
from app.raid_rooms.admissions.admission_service import snapshot
from app.raid_rooms.common.readiness import require_cycle_worker
from app.raid_rooms.models.source_models import TimeReservation as Reservation, SessionParticipation
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment, RecruitmentItem as Item, RecruitmentRound as Round
from app.raid_rooms.models.cycle_models import CycleRound, RoomCycle
from app.raid_rooms.schemas.personal_reservations import ReservationPage, ReservationItem
from app.raid_rooms.schedules import reservation_cursor

MAX_ROWS = 10000
MAX_BYTES = 1048576
POLICY = 'personal-reservations-1'

def utc(value):
    if value.tzinfo is None or value.utcoffset() is None: fail('RESERVATION_DATA_UNAVAILABLE', 503)
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def calendar_key(stamp):
    local = stamp.astimezone(raids.KST).date()
    return local - timedelta(days=(local.weekday() - 2) % 7)

def window(stamp, key):
    try:
        parsed = date.fromisoformat(key)
        if parsed.isoformat() != key or parsed.weekday() != 2: raise ValueError()
    except (TypeError, ValueError): fail('INVALID_REQUEST', 400)
    current = calendar_key(stamp)
    if parsed not in (current, current + timedelta(days=7)):
        fail('CALENDAR_WEEK_UNAVAILABLE', 409)
    start = datetime.combine(parsed, time(), raids.KST).astimezone(timezone.utc)
    return current, start, start + timedelta(days=7)

def label(value, length):
    if value is None: return None
    if not isinstance(value, str) or len(value) > length: fail('RESERVATION_DATA_UNAVAILABLE', 503)
    return value if value.strip() else None

def query(uid, start, end):
    # Outer joins make broken mandatory references detectable, rather than an
    # apparently complete page which silently omitted an owned reservation.
    return (select(Reservation, Assignment, Item, Round, SessionParticipation, CycleRound, RoomCycle).select_from(Reservation)
        .outerjoin(Assignment, Assignment.id == Reservation.assignment_id)
        .outerjoin(Item, Item.id == Reservation.item_id)
        .outerjoin(Round, Round.id == Reservation.round_id)
        .outerjoin(SessionParticipation, SessionParticipation.id == Reservation.participation_id)
        .outerjoin(CycleRound, CycleRound.round_id == Reservation.round_id)
        .outerjoin(RoomCycle, RoomCycle.id == CycleRound.cycle_id)
        .where(Reservation.user_id == uid, Reservation.released_at.is_(None),
               Reservation.starts_at < end, Reservation.ends_at > start)
        .options(load_only(Reservation.id, Reservation.user_id, Reservation.room_id, Reservation.membership_id,
            Reservation.session_id, Reservation.segment_id, Reservation.assignment_id, Reservation.item_id,
            Reservation.round_id, Reservation.participation_id, Reservation.starts_at, Reservation.ends_at, Reservation.schedule_revision),
            load_only(Assignment.id, Assignment.user_id, Assignment.room_id, Assignment.membership_id, Assignment.item_id,
                Assignment.round_id, Assignment.character_id, Assignment.display),
            load_only(Item.id, Item.room_id, Item.raid_id),
            load_only(Round.id, Round.room_id, Round.item_id, Round.cycle_key, Round.difficulty_id),
            load_only(SessionParticipation.id, SessionParticipation.user_id, SessionParticipation.room_id,
                SessionParticipation.membership_id, SessionParticipation.session_id),
            load_only(CycleRound.round_id, CycleRound.room_id, CycleRound.item_id, CycleRound.cycle_key),
            load_only(RoomCycle.id, RoomCycle.room_id, RoomCycle.cycle_key))
        .order_by(Reservation.starts_at, Reservation.id).limit(MAX_ROWS + 1))

def project(record, catalog):
    r, a, item, rd, part, cr, cycle = record
    if any(x is None for x in (a, item, rd, part, cr, cycle)):
        fail('RESERVATION_DATA_UNAVAILABLE', 503)
    if not (r.user_id == a.user_id == part.user_id and r.room_id == a.room_id == item.room_id == rd.room_id == part.room_id == cr.room_id == cycle.room_id
            and r.membership_id == a.membership_id == part.membership_id
            and r.session_id == part.session_id and r.item_id == a.item_id == rd.item_id == cr.item_id
            and r.round_id == a.round_id == cr.round_id and rd.cycle_key == cr.cycle_key == cycle.cycle_key
            and r.starts_at < r.ends_at):
        fail('RESERVATION_DATA_UNAVAILABLE', 503)
    display = a.display
    if not isinstance(display, dict): fail('RESERVATION_DATA_UNAVAILABLE', 503)
    raid = catalog.get(item.raid_id)
    return dict(reservation_id=str(r.id), session_id=str(r.session_id), segment_id=str(r.segment_id), room_id=str(r.room_id),
        cycle_key=cycle.cycle_key.isoformat(), starts_at=utc(r.starts_at), ends_at=utc(r.ends_at), schedule_revision=r.schedule_revision,
        raid=dict(raid_id=item.raid_id, difficulty_id=rd.difficulty_id, display_name=label(raid.display_name if raid else None, 128)),
        character=dict(character_id=str(a.character_id), display=dict(name=label(display.get('character_name'),128),
            server_name=label(display.get('server_name'),64), class_name=label(display.get('class_name'),64))))

def page(principal, key, limit=100, cursor=None):
    if type(limit) is not int or not 1 <= limit <= 200: fail('INVALID_REQUEST', 400)
    with snapshot(principal) as (db, uid, stamp):
        # Full DDL/privilege readiness is checked at current-app startup.
        # Per read, retain the supported-head guard without hundreds of catalog introspections.
        require_cycle_worker(db)
        current, start, end = window(stamp, key)
        catalog = {raid.raid_id: raid for raid in raids.catalog().raids}
        records = list(db.execute(query(uid, start, end)))
        if len(records) > MAX_ROWS: fail('RESERVATION_QUERY_LIMIT_EXCEEDED', 503)
        try: items = [ReservationItem.model_validate(project(row, catalog)).model_dump() for row in records]
        except ValidationError: fail('RESERVATION_DATA_UNAVAILABLE', 503)
        scope = [POLICY, str(uid), key, current.isoformat()]
        revision = hashlib.sha256(json.dumps([scope, items], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        binding = [*scope, str(principal[1].id), limit]
        expires = int(stamp.timestamp()) + 600
        last = None
        if cursor: last, expires = reservation_cursor.decode(cursor, binding, revision, stamp)
        # Compare instants, not ISO strings (fractional seconds are variable).
        remaining = [i for i in items if last is None or (datetime.fromisoformat(i['starts_at'].replace('Z','+00:00')), i['reservation_id']) >
                     (datetime.fromisoformat(last[0].replace('Z','+00:00')),last[1])]
        selected = remaining[:limit]
        token = reservation_cursor.encode(binding, revision, [selected[-1]['starts_at'],selected[-1]['reservation_id']],expires) if len(remaining)>limit else None
        value = dict(scope=dict(server_now=utc(stamp), current_cycle_key=raids.cycle(stamp).cycle_key,
            current_calendar_week_key=current.isoformat(), calendar_week_key=key, timezone='Asia/Seoul',
            window_start=utc(start), window_end=utc(end), policy_version=POLICY),
            data=dict(items=selected, result_revision=revision, next_cursor=token, evaluated_at=utc(stamp)))
        try: result = ReservationPage.model_validate(value).model_dump()
        except ValidationError: fail('RESERVATION_DATA_UNAVAILABLE', 503)
        if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())>MAX_BYTES:
            fail('RESPONSE_TOO_LARGE', 413)
        return result
