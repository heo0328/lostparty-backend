"""Explicit availability saves only. Reads never copy or create state.

All writes share the game mutation lock, CAS and original-success transaction.
Personal saves never propagate. An explicit room copy may satisfy an initial
unconfirmed automatic plan; confirmed schedules and proposals are untouched.
"""
from copy import deepcopy
from sqlalchemy import select
from app.core.database import session, now
from app.game_accounts.models import Account, Registration
from app.game_accounts.support import authorize, fail, reserve, commit_result, release
from app.raid_rooms.integrated_models import RecruitmentRoom, RecruitmentMembership
from app.raid_rooms.source_models import PersonalAvailability, AvailabilitySubmission


def normalize(intervals):
    """Monday 00:00 origin; split Sunday overflow then merge adjacent coverage."""
    spans = []
    for row in intervals:
        def minute(value):
            h, m = map(int, value.split(':'))
            return h * 60 + m
        start = (row['weekday'] - 1) * 1440 + minute(row['start'])
        end = ((row['weekday'] - 1 + row['end_day_offset']) * 1440 + minute(row['end']))
        spans.append((start, min(end, 10080)))
        if end > 10080:
            spans.append((0, end - 10080))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1]['end_minute']:
            merged[-1]['end_minute'] = max(end, merged[-1]['end_minute'])
        else:
            merged.append(dict(start_minute=start, end_minute=end))
    return merged


def verified(db, uid):
    if db.scalar(select(Registration.id).join(Account, Registration.account_id == Account.id).where(
            Registration.user_id == uid, Registration.deleted_at.is_(None),
            Account.owner_id == uid, Account.verified_at.is_not(None)).limit(1)) is None:
        fail('OWNERSHIP_REQUIRED', 403)


def membership(db, uid, rid, *, write=False):
    room = db.get(RecruitmentRoom, rid)
    member = db.scalar(select(RecruitmentMembership).where(
        RecruitmentMembership.room_id == rid, RecruitmentMembership.user_id == uid,
        RecruitmentMembership.ended_at.is_(None)))
    if room is None or member is None:
        fail('ROOM_NOT_FOUND', 404)
    if write:
        if room.ended_at is not None:
            fail('ROOM_NOT_ACTIVE')
        if room.migration_state != 'ready':
            fail('ROOM_REVIEW_REQUIRED')
    return member


def personal_output(row):
    return dict(exists=row is not None, version=row.revision if row else 1,
        timezone='Asia/Seoul', intervals=deepcopy(row.intervals) if row else [],
        normalized_intervals=deepcopy(row.normalized_intervals) if row else [],
        updated_at=row.saved_at if row else None)


def submission_output(member, row):
    return dict(membership_id=member.id,
        state='ready' if row else 'missing', revision=row.revision if row else 1,
        source_personal_version=row.source_personal_revision if row else None,
        intervals=deepcopy(row.intervals) if row else [],
        normalized_intervals=deepcopy(row.normalized_intervals) if row else [],
        submitted_at=row.submitted_at if row else None)


def get(principal, rid=None):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        from sqlalchemy import text
        db.execute(text('SET TRANSACTION READ ONLY'))
        uid = authorize(db, principal)
        if rid is None:
            # Existing personal data remains accessible after account unlinking.
            return personal_output(db.get(PersonalAvailability, uid))
        member = membership(db, uid, rid)
        return submission_output(member, db.get(AvailabilitySubmission, member.id))


def put(principal, key, data, rid=None):
    operation = 'recruitment-personal-time' if rid is None else 'recruitment-room-time'
    ticket, replay = reserve(principal, operation, key, {'room_id': str(rid) if rid else None, 'body': data})
    if replay and rid is not None:
        from app.raid_rooms.v1_compat import enabled
        if enabled():return replay
    if replay:
        # Current auth and room membership still required; never recheck resource CAS
        # or overwrite a newer submission with this historical success.
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            uid = authorize(db, principal)
            if rid is not None:
                member = membership(db, uid, rid)
                if str(member.id) != replay[1]['membership_id']:
                    fail('REVISION_CONFLICT')
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            if rid is not None:
                from app.raid_rooms.v1_compat import reject_write
                reject_write(db)
            verified(db, uid)
            personal = db.get(PersonalAvailability, uid)
            version = personal.revision if personal else 1
            stamp = now(db)
            if rid is None:
                if version != data['expected_version']:
                    fail('REVISION_CONFLICT')
                if personal is None or personal.intervals != data['intervals']:
                    if version == 2147483647:
                        fail('REVISION_CONFLICT')
                    if personal is None:
                        personal = PersonalAvailability(user_id=uid, timezone='Asia/Seoul')
                        db.add(personal)
                    personal.revision = version + 1
                    personal.intervals = deepcopy(data['intervals'])
                    personal.normalized_intervals = normalize(data['intervals'])
                    personal.saved_at = stamp
                result = personal_output(personal)
            else:
                member = membership(db, uid, rid, write=True)
                row = db.get(AvailabilitySubmission, member.id)
                revision = row.revision if row else 1
                if (version != data['expected_personal_version'] or
                        revision != data['expected_submission_revision'] or
                        member.revision != data['expected_membership_revision']):
                    fail('REVISION_CONFLICT')
                if personal is None:
                    fail('PERSONAL_AVAILABILITY_REQUIRED')
                if row is None or row.source_personal_revision != version:
                    if revision == 2147483647:
                        fail('REVISION_CONFLICT')
                    if row is None:
                        row = AvailabilitySubmission(membership_id=member.id, room_id=rid, user_id=uid)
                        db.add(row)
                    row.revision = revision + 1
                    row.source_personal_revision = version
                    row.intervals = deepcopy(personal.intervals)
                    row.normalized_intervals = deepcopy(personal.normalized_intervals)
                    row.submitted_at = stamp
                    room=db.get(RecruitmentRoom,rid);room.plan_revision+=1;room.revision+=1
                    from app.raid_rooms.core import directory
                    directory(db)
                result = submission_output(member, row)
            db.flush()
            if rid is not None:
                from app.raid_rooms.scheduling import evaluate_initial,ScheduleGroup
                if db.scalar(select(ScheduleGroup.id).where(ScheduleGroup.room_id==rid).limit(1)) is not None:
                    evaluate_initial(db,db.get(RecruitmentRoom,rid),stamp)
            value=commit_result(db, ticket, 200, result)
            db.flush()
            if rid is not None:
                from app.raids.service import cycle
                if cycle(now(db)).cycle_key!=cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
            return value
    except Exception:
        release(ticket)
        raise


# Two-cycle storage never falls back to the legacy global room graph.
from app.raid_rooms.v1_compat import read as _current_read
get=_current_read('availability')(get)
