from app.core.database import session, now
from app.game_accounts.support import authorize, fail, reserve, commit_result, release
from app.member_settings.models import MemberSettings


def output(row):
    return {'nice_group_auto_refresh_enabled': row.nice_group_auto_refresh_enabled if row else False,
            'version': row.version if row else 1}


def get(principal):
    with session() as db, db.begin():
        uid = authorize(db, principal)
        return output(db.get(MemberSettings, uid))


def put(principal, key, data):
    ticket, replay = reserve(principal, 'member-settings', key,
                             {'target': '/v1/me/settings', 'body': data})
    if replay:
        # reserve authenticates the current member/session, even for replay.
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            row = db.get(MemberSettings, uid)
            current = output(row)
            if current['version'] != data['expected_version']:
                fail('REVISION_CONFLICT')
            if row is None:
                row = MemberSettings(user_id=uid, nice_group_auto_refresh_enabled=False,
                                     version=1, updated_at=now(db))
                db.add(row)
            if row.nice_group_auto_refresh_enabled != data['nice_group_auto_refresh_enabled']:
                row.nice_group_auto_refresh_enabled = data['nice_group_auto_refresh_enabled']
                row.version += 1
                row.updated_at = now(db)
            db.flush()
            return commit_result(db, ticket, 200, output(row))
    except Exception:
        release(ticket)
        raise
