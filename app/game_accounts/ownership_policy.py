"""Current-owner decisions; never transfer authority from a name alone."""
from sqlalchemy import select
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Registration, Character, NameClaim
from app.game_accounts.support import fail


def owned(account, uid):
    return account is not None and account.owner_id == uid and account.verified_at is not None


def reject_linked(db, uid, registration):
    if registration and owned(db.get(Account, registration.account_id) if registration.account_id else None, uid):
        fail('ALREADY_VERIFIED')


def observed_account(db, uid, rows):
    """A fresh roster must resolve all existing claims to one current account.

    At least one non-retired canonical anchor and this member's persisted
    registration link are required. Unknown/new names do not create authority.
    """
    accounts = set()
    for row in rows:
        pair = row['server_name'], row['character_name']
        claim = db.get(NameClaim, pair)
        if claim is None:
            continue
        character = db.get(Character, claim.character_id)
        if (character is None or character.lifecycle_state == 'retired'
                or (character.server_name, character.character_name) != pair):
            return None
        accounts.add(character.account_id)
    if len(accounts) != 1:
        return None
    account = db.get(Account, next(iter(accounts)))
    if not owned(account, uid):
        return None
    history = db.scalar(select(Registration.id).where(
        Registration.user_id == uid, Registration.account_id == account.id).limit(1))
    return account if history else None


def reject_observed(db, uid, rows):
    if observed_account(db, uid, rows):
        fail('ALREADY_VERIFIED')


def links_stamp(db, uid):
    """Fence account/claim and historical-registration changes across I/O."""
    rows = db.scalars(select(Registration).where(Registration.user_id == uid,
        Registration.account_id.is_not(None)).order_by(Registration.id)).all()
    accounts = {}
    for r in rows:
        if r.account_id not in accounts:
            a = db.get(Account, r.account_id)
            accounts[r.account_id] = (a.verified_at, lifecycle.account_stamp(db, a))
    return lifecycle.digest([(r.id, r.account_id, r.version, r.deleted_at,
                              accounts[r.account_id]) for r in rows])


def restore(db, uid, rows):
    account = observed_account(db, uid, rows)
    if account and db.scalar(select(Registration.id).where(
            Registration.user_id == uid, Registration.account_id == account.id,
            Registration.deleted_at.is_(None)).limit(1)):
        fail('REGISTRATION_EXISTS')
    return account
