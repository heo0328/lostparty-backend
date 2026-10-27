from datetime import date

from app.core.database import session, now
from app.game_accounts import lifecycle
from app.game_accounts.profiles import owned_character
from app.game_accounts.support import authorize, fail, reserve, commit_result, release
from app.raids import service as raids
from app.raid_weekly.models import WeeklyState


def parse_cycle(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or parsed.weekday() != 2:
            raise ValueError()
        return parsed
    except (ValueError, TypeError):
        fail('INVALID_REQUEST', 400)


def scope(db, uid, cid, expected=None):
    account, character = owned_character(db, uid, cid)
    if account.verified_at is None:
        fail('OWNERSHIP_REQUIRED', 403)
    if expected and (account.ownership_revision != expected['expected_ownership_revision'] or
                     character.lifecycle_revision != expected['expected_lifecycle_revision']):
        fail('REVISION_CONFLICT')
    return account, character


def raid_by_id(raid_id):
    raid = next((r for r in raids.catalog().raids if r.raid_id == raid_id), None)
    if raid is None:
        fail('RAID_NOT_FOUND', 404)
    return raid


def entry(db, account, character, raid, key, current_cycle, row, stamp=None):
    sources = []
    if row and row.manual_completed_at is not None:
        sources.append(dict(source='manual', completed_at=row.manual_completed_at,
                            difficulty_id=row.manual_difficulty_id, party_id=None))
    if row and row.party_completed_at is not None:
        sources.append(dict(source='party', completed_at=row.party_completed_at,
                            difficulty_id=row.party_difficulty_id, party_id=row.completed_party_id))
    participation = (dict(party_id=row.active_party_id, difficulty_id=row.active_difficulty_id,
                          joined_at=row.joined_at) if row and row.active_party_id else None)
    from app.raid_rooms.cycles import target
    temporal = 'PLAY_NOT_STARTED' if stamp is not None and key.isoformat()==current_cycle.cycle_key and stamp < target(stamp,key.isoformat()).playable_from else None
    reason = ('CURRENT_CYCLE_REQUIRED' if key.isoformat() != current_cycle.cycle_key else
              temporal or ('RAID_INACTIVE' if not raid.is_active else
              'CHARACTER_UNUSABLE' if not lifecycle.usable(db, character) else
              'PARTICIPATION_CONFIRMATION_REQUIRED' if participation else None))
    return dict(character_id=character.id, raid_id=raid.raid_id, cycle_key=key.isoformat(),
                revision=row.revision if row else 1, ownership_revision=account.ownership_revision,
                lifecycle_revision=character.lifecycle_revision,
                state='completed' if sources else 'participating' if participation else 'incomplete',
                completion_sources=sources, participation=participation,
                can_mark_completed=reason is None,
                can_clear_manual_completion=(temporal is None and key.isoformat() == current_cycle.cycle_key and
                                             bool(row and row.manual_completed_at)),
                mark_blocked_reason=reason)


def get(principal, character_ids, cycle_key=None):
    if len(set(character_ids)) != len(character_ids):
        fail('INVALID_REQUEST', 400)
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        stamp=now(db)
        current_cycle = raids.cycle(stamp)
        key = parse_cycle(cycle_key if cycle_key is not None else current_cycle.cycle_key)
        if key > date.fromisoformat(current_cycle.cycle_key):
            fail('INVALID_REQUEST', 400)
        entries = []
        for cid in character_ids:
            account, character = scope(db, uid, cid)
            for raid in raids.catalog().raids:
                row = db.get(WeeklyState, (uid, cid, raid.raid_id, key))
                entries.append(entry(db, account, character, raid, key, current_cycle, row,stamp))
        return dict(current_cycle=current_cycle, cycle_key=key.isoformat(),
                    catalog_version=raids.catalog().catalog_version, entries=entries)


def require_available_for_participation(db, uid, cid, raid_id, key):
    """Internal only: caller must authorize(write=True) and atomically write slot+occupancy.

    Does not validate ownership/raid eligibility or create a party/participation by itself.
    All future admission writers must share this lock/key; pending is never occupancy.
    """
    row = db.get(WeeklyState, (uid, cid, raid_id, key))
    if row and (row.manual_completed_at is not None or row.party_completed_at is not None):
        fail('WEEKLY_ALREADY_COMPLETED')
    if row and row.active_party_id is not None:
        fail('WEEKLY_ALREADY_PARTICIPATING')
    return row


def put(principal, cid, raid_id, key, data):
    ticket, replay = reserve(principal, 'raid-weekly-manual-completion', key,
                             {'character_id': str(cid), 'raid_id': raid_id, 'body': data})
    if replay:return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            account, character = scope(db, uid, cid, data)
            requested_cycle = parse_cycle(data['expected_cycle_key'])
            stamp=now(db)
            current_cycle = raids.cycle(stamp)
            if requested_cycle.isoformat() != current_cycle.cycle_key:
                fail('CYCLE_CHANGED')
            from app.raid_rooms.cycle_outcomes import playable as require_playable
            require_playable(stamp,requested_cycle.isoformat())
            if data['expected_catalog_version'] != raids.catalog().catalog_version:
                fail('CATALOG_VERSION_CONFLICT')
            raid = raid_by_id(raid_id)
            if data['completed']:
                lifecycle.require_usable(db, character)
                if not raid.is_active:
                    fail('RAID_INACTIVE')
                if data['difficulty_id'] is not None:
                    try:
                        raids.difficulty(raid_id, data['difficulty_id'], data['expected_catalog_version'])
                    except raids.CatalogSelectionError as error:
                        fail(error.code, 404 if error.code.endswith('NOT_FOUND') else 409)
            row = db.get(WeeklyState, (uid, cid, raid_id, requested_cycle))
            if (row.revision if row else 1) != data['expected_revision']:
                fail('REVISION_CONFLICT')
            if data['completed'] and row and row.active_party_id is not None:
                fail('PARTICIPATION_CONFIRMATION_REQUIRED')
            had_manual = bool(row and row.manual_completed_at is not None)
            changed = (had_manual != data['completed'] or
                       (had_manual and row.manual_difficulty_id != data['difficulty_id']))
            if changed:
                stamp = now(db)
                if row is None:
                    row = WeeklyState(user_id=uid, character_id=cid, raid_id=raid_id,
                                      cycle_key=requested_cycle, revision=1)
                    db.add(row)
                row.manual_completed_at = (row.manual_completed_at or stamp) if data['completed'] else None
                row.manual_difficulty_id = data['difficulty_id']
                row.revision += 1
                row.updated_at = stamp
            db.flush()
            # Database clock, not transaction-start time; boundary-crossing writes roll back.
            saved=commit_result(db,ticket,200,entry(db,account,character,raid,requested_cycle,current_cycle,row,stamp))
            db.flush();final_stamp=now(db)
            if raids.cycle(final_stamp).cycle_key!=current_cycle.cycle_key:fail('CYCLE_CHANGED')
            require_playable(final_stamp,requested_cycle.isoformat())
            return saved
    except Exception:
        release(ticket)
        raise
