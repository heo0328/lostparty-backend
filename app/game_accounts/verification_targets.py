"""Explicit registration targets and current ownership, never name-based transfer."""
from sqlalchemy import select
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Character, NameClaim
from app.game_accounts.support import fail


def normalize(payload):
    # Preserve the exact legacy normalized shape, including its old null fields.
    result = dict(payload)
    for key in ('target_character', 'expected_registration_version'):
        if result.get(key) is None:
            result.pop(key, None)
    return result


def selected(db, uid, registration, data):
    target = data.get('target_character')
    if target is None:
        return registration.lookup_name
    if registration.version != data['expected_registration_version']:
        fail('REVISION_CONFLICT')
    pair = target['server_name'], target['character_name']
    account = db.get(Account, registration.account_id) if registration.account_id else None
    if account and account.owner_id == uid:
        rows = db.scalars(select(Character).where(Character.account_id == account.id,
                                                  Character.lifecycle_state != 'retired'))
        match = next((c for c in rows if (c.server_name, c.character_name) == pair), None)
        if match is None:
            fail('CHARACTER_NOT_FOUND', 404)
        claim = db.get(NameClaim, pair)
        if claim is None or claim.character_id != match.id:
            fail('IDENTITY_CONFLICT')
    elif pair not in {(row['server_name'], row['character_name']) for row in registration.preview}:
        fail('CHARACTER_NOT_FOUND', 404)
    return target['character_name']


def claims(db, rows):
    values, accounts = [], {}
    for row in rows:
        pair = row['server_name'], row['character_name']
        claim = db.get(NameClaim, pair)
        character = db.get(Character, claim.character_id) if claim else None
        if character:
            if character.account_id not in accounts:
                account = db.get(Account, character.account_id)
                accounts[character.account_id] = lifecycle.digest(lifecycle.account_stamp(db, account))
            value = (str(claim.character_id), claim.revision, accounts[character.account_id])
        else:
            value = None
        values.append((pair, value))
    return lifecycle.digest(sorted(values))


def owned_candidate(db, uid, registration, context, rows):
    if registration is None or registration.account_id is None:
        return None
    account = db.get(Account, registration.account_id)
    if account.owner_id != uid:
        return None
    claim = db.get(NameClaim, tuple(context['target']))
    character = db.get(Character, claim.character_id) if claim else None
    if character is None or character.account_id != account.id or character.lifecycle_state == 'retired':
        fail('IDENTITY_CONFLICT')
    for row in rows:
        current = db.get(NameClaim, (row['server_name'], row['character_name']))
        c = db.get(Character, current.character_id) if current else None
        if current and (c is None or c.account_id != account.id):
            fail('IDENTITY_CONFLICT')
    return account
