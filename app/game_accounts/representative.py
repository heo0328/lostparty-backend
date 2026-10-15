"""Stored representative selection only; no provider or credential access."""
import uuid
from sqlalchemy import select
from app.core.database import session
from app.game_accounts.models import Character, Activity
from app.game_accounts import service
from app.game_accounts.support import authorize, fail, reserve, commit_result, release


def owned(db, uid, rid):
    registration = service.reg(db, uid, rid)
    account, state = service.ownership(db, uid, registration)
    if state != 'owned':
        fail('OWNERSHIP_REQUIRED', 403)
    return registration, account


def output(db, uid, registration, account):
    configuration = service.config(db, uid, account.id)
    return dict(registration_id=registration.id, game_account_id=account.id,
                is_main=registration.is_main, registration_version=registration.version,
                settings_version=configuration.version if configuration else 1,
                ownership_revision=account.ownership_revision, roster_revision=account.roster_revision,
                representative_character_id=configuration.representative_id if configuration else None,
                configuration_state=configuration.state if configuration else 'unconfigured',
                next_change_at=None)


def get(principal, rid):
    with session() as db, db.begin():
        # Read all versions and the representative from one consistent snapshot.
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        registration, account = owned(db, uid, rid)
        return output(db, uid, registration, account)


def put(principal, rid, key, data):
    ticket, replay = reserve(principal, 'representative', key, {'target': str(rid), 'body': data})
    if replay:
        with session() as db:
            owned(db, authorize(db, principal), rid)
        return replay
    try:
        with session() as db, db.begin():
            # All game writers use the same transaction lock. No network here.
            uid = authorize(db, principal, write=True)
            registration, account = owned(db, uid, rid)
            if not registration.is_main:
                fail('MAIN_REGISTRATION_CHANGED')
            configuration = service.config(db, uid, account.id)
            if (registration.version != data['expected_registration_version'] or
                    (configuration.version if configuration else 1) != data['expected_settings_version'] or
                    account.ownership_revision != data['expected_ownership_revision'] or
                    account.roster_revision != data['expected_roster_revision']):
                fail('REVISION_CONFLICT')
            selected = set(db.scalars(select(Activity.character_id).where(
                Activity.settings_id == configuration.id))) if configuration else set()
            if not selected:
                fail('SETTINGS_NOT_CONFIGURED')
            character = db.get(Character, uuid.UUID(data['character_id']))
            if character is None or character.account_id != account.id:
                fail('CHARACTER_NOT_FOUND', 404)
            if character.id not in selected:
                fail('CHARACTER_NOT_ACTIVE')
            if character.status != 'confirmed':
                fail('CHARACTER_UNUSABLE')
            if configuration.representative_id != character.id:
                configuration.representative_id = character.id
                configuration.version += 1
                configuration.next_change_at = None
            db.flush()
            return commit_result(db, ticket, 200, output(db, uid, registration, account))
    except Exception:
        release(ticket)
        raise
