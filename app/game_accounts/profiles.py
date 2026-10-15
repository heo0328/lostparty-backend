"""Member-owned analysis storage, independent of provider power/activity."""
from sqlalchemy import select
from app.core.database import session, now
from app.game_accounts.models import Account, Character, Registration, NameClaim, CharacterRoleSummary
from app.game_accounts.support import authorize, fail, reserve, commit_result, release


def owned_character(db, uid, cid, *, write=False):
    character = db.get(Character, cid)
    if character is None:
        fail('CHARACTER_NOT_FOUND', 404)
    registration = db.scalar(select(Registration.id).where(
        Registration.user_id == uid, Registration.account_id == character.account_id,
        Registration.deleted_at.is_(None)))
    if registration is None:
        fail('CHARACTER_NOT_FOUND', 404)
    account = db.get(Account, character.account_id)
    if account.owner_id != uid:
        fail('OWNERSHIP_REQUIRED', 403)
    if character.lifecycle_state == 'retired' or (write and (
            character.lifecycle_state != 'active' or character.status != 'confirmed')):
        fail('CHARACTER_UNUSABLE')
    claim = db.get(NameClaim, (character.server_name, character.character_name))
    if claim is None or claim.character_id != character.id:
        fail('IDENTITY_CONFLICT')
    return account, character


def stored(row):
    return dict(version=row.version if row else 1, summary=row.summary if row else None,
                saved_at=row.saved_at if row else None)


def get(principal, cid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        account, character = owned_character(db, uid, cid)
        roles = {role: stored(db.get(CharacterRoleSummary, (uid, cid, account.ownership_revision, role)))
                 for role in ('dealer', 'support')}
        return dict(character_id=cid, game_account_id=account.id,
                    ownership_revision=account.ownership_revision,
                    lifecycle_revision=character.lifecycle_revision, lifecycle_state=character.lifecycle_state,
                    **roles, preferences=dict(version=1, preferred_role=None, visible=True,
                                              display_order=None, saved_at=None))


def put(principal, cid, role, key, data):
    ticket, replay = reserve(principal, 'role-summary', key,
                             {'target': str(cid), 'role': role, 'body': data})
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            account, character = owned_character(db, authorize(db, principal), cid)
            if (account.ownership_revision != data['expected_ownership_revision'] or
                    character.lifecycle_revision != data['expected_lifecycle_revision']):
                fail('REVISION_CONFLICT')
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            account, character = owned_character(db, uid, cid, write=True)
            if (account.ownership_revision != data['expected_ownership_revision'] or
                    character.lifecycle_revision != data['expected_lifecycle_revision']):
                fail('REVISION_CONFLICT')
            row = db.get(CharacterRoleSummary, (uid, cid, account.ownership_revision, role))
            if (row.version if row else 1) != data['expected_version']:
                fail('REVISION_CONFLICT')
            if row is None:
                row = CharacterRoleSummary(user_id=uid, character_id=cid,
                                           ownership_revision=account.ownership_revision, role=role,
                                           version=2, summary=data['summary'], saved_at=now(db))
                db.add(row)
            elif row.summary != data['summary']:
                row.summary = data['summary']
                row.version += 1
                row.saved_at = now(db)
            db.flush()
            result = dict(character_id=cid, role=role, ownership_revision=account.ownership_revision,
                          lifecycle_revision=character.lifecycle_revision, **stored(row))
            return commit_result(db, ticket, 200, result)
    except Exception:
        release(ticket)
        raise
