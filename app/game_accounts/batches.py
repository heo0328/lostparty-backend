"""Bounded snapshot read and independent, replay-compatible summary commands."""
import logging
from time import monotonic

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import session, now
from app.core.errors import AuthError
from app.core.observability import emit, category
from app.game_accounts import profiles
from app.game_accounts.bootstrap import StoredRows, current_personal_rows
from app.game_accounts.models import (Account, Character, Registration, NameClaim,
                                     CharacterRoleSummary, CharacterPersonalPreferences)
from app.game_accounts.profile_schemas import PersonalProfileOut, RoleSummaryIn
from app.game_accounts.support import fail

BUDGET_SECONDS = 20


def error(code, request_id, retry_after=None):
    return dict(code=code, message=code, request_id=request_id, retry_after_seconds=retry_after)


def get(principal, ids, request_id):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        stamp = now(db)
        uid = profiles.authorize(db, principal)
        chars = list(db.scalars(select(Character).where(Character.id.in_(ids))))
        aids = {c.account_id for c in chars}
        registrations = set(db.scalars(select(Registration.account_id).where(
            Registration.user_id == uid, Registration.deleted_at.is_(None),
            Registration.account_id.in_(aids))))
        accounts = {a.id: a for a in db.scalars(select(Account).where(Account.id.in_(aids)))}
        # Only load personal data for current, registered owners. Never historical owners.
        safe_ids = {c.id for c in chars if c.account_id in registrations
                    and accounts[c.account_id].owner_id == uid}
        claims = list(db.scalars(select(NameClaim).where(NameClaim.character_id.in_(safe_ids))))
        stored = StoredRows(claims,
            current_personal_rows(db, CharacterRoleSummary, uid, safe_ids),
            current_personal_rows(db, CharacterPersonalPreferences, uid, safe_ids))
        by_id = {c.id: c for c in chars}
        items = []
        for cid in ids:
            c = by_id.get(cid)
            a = accounts.get(c.account_id) if c else None
            claim = stored.get(NameClaim, (c.server_name, c.character_name)) if c else None
            if c is None or c.account_id not in registrations:
                status, code = 404, 'CHARACTER_NOT_FOUND'
            elif a.owner_id != uid:
                status, code = 403, 'OWNERSHIP_REQUIRED'
            elif c.lifecycle_state == 'retired':
                status, code = 409, 'CHARACTER_UNUSABLE'
            elif claim is None or claim.character_id != cid:
                status, code = 409, 'IDENTITY_CONFLICT'
            else:
                status, code = 200, None
            profile = None
            if code is None:
                try:
                    profile = PersonalProfileOut.model_validate(profiles.output(stored, uid, a, c))
                except ValidationError:
                    fail('PERSONAL_PROFILES_DATA_UNAVAILABLE', 503)
            items.append(dict(character_id=cid, status=status, profile=profile,
                              error=error(code, request_id) if code else None))
        return dict(evaluated_at=stamp, items=items)


def put(principal, data, request_id):
    started = monotonic()
    # Global preflight, before even creating a command reservation.
    with session() as db, db.begin():
        profiles.authorize(db, principal)
    stopped = False
    items = []
    for command in data.items:
        result = None
        detail = None
        if stopped or monotonic() - started >= BUDGET_SECONDS:
            status, detail = 503, error('BATCH_NOT_PROCESSED', request_id)
            stopped = True
        elif command.role not in ('dealer', 'support'):
            status, detail = 400, error('INVALID_ROLE', request_id)
        else:
            # Same model/encoder as single PUT: no batch metadata in the fingerprint.
            body = jsonable_encoder(RoleSummaryIn.model_validate(command.model_dump(
                exclude={'character_id', 'role', 'command_id'})))
            try:
                status, result = profiles.put(principal, command.character_id,
                                             command.role, command.command_id, body)
            except AuthError as exc:
                status = exc.status
                detail = error(exc.code, request_id, getattr(exc, 'retry_after', None))
                stopped = status == 401 or exc.code == 'ACCOUNT_DISABLED' or status >= 500
            except SQLAlchemyError as exc:
                emit('database_error', level=logging.ERROR, category=category(exc))
                status, detail = 503, error('SERVICE_UNAVAILABLE', request_id)
                stopped = True
        items.append(dict(character_id=command.character_id, role=command.role,
            command_id=command.command_id, status=status, result=result, error=detail))
    return dict(items=items)
