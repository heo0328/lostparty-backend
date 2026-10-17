"""Presentation count belongs to a member/account ownership lifetime."""
from app.core.database import session, now
from app.game_accounts import representative
from app.game_accounts.models import AccountCharacterPresentation
from app.game_accounts.support import authorize, fail, reserve, commit_result, release


def output(registration, account, row):
    return dict(registration_id=registration.id, game_account_id=account.id,
                registration_version=registration.version, ownership_revision=account.ownership_revision,
                version=row.version if row else 1, visible_count=row.visible_count if row else 6,
                saved_at=row.saved_at if row else None)


def get(principal, rid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        registration, account = representative.owned(db, uid, rid)
        row = db.get(AccountCharacterPresentation, (uid, account.id, account.ownership_revision))
        return output(registration, account, row)


def put(principal, rid, key, data):
    ticket, replay = reserve(principal, 'account-presentation', key, {'target': str(rid), 'body': data})
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            _, account = representative.owned(db, authorize(db, principal), rid)
            if account.ownership_revision != data['expected_ownership_revision']:
                fail('REVISION_CONFLICT')
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            registration, account = representative.owned(db, uid, rid)
            row = db.get(AccountCharacterPresentation, (uid, account.id, account.ownership_revision))
            if (registration.version != data['expected_registration_version'] or
                    account.ownership_revision != data['expected_ownership_revision'] or
                    (row.version if row else 1) != data['expected_version']):
                fail('REVISION_CONFLICT')
            if (row.visible_count if row else 6) != data['visible_count']:
                saved_at = now(db)
                if row is None:
                    row = AccountCharacterPresentation(user_id=uid, game_account_id=account.id,
                                                       ownership_revision=account.ownership_revision, version=1)
                    db.add(row)
                row.visible_count = data['visible_count']
                row.version += 1
                row.saved_at = saved_at
            db.flush()
            return commit_result(db, ticket, 200, output(registration, account, row))
    except Exception:
        release(ticket)
        raise
