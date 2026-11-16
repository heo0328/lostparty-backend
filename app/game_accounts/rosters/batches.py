"""Bounded read-only snapshot of current personal profiles."""

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy import text

from app.core.database import session
from app.core.database import now
from app.game_accounts.character_profiles import profiles
from app.game_accounts.rosters.bootstrap import StoredRows
from app.game_accounts.rosters.bootstrap import current_personal_rows
from app.game_accounts.models.models import Account
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import Registration
from app.game_accounts.models.models import NameClaim
from app.game_accounts.models.models import CharacterRoleSummary
from app.game_accounts.models.models import CharacterPersonalPreferences
from app.game_accounts.schemas.profile_schemas import PersonalProfileOut
from app.game_accounts.common.support import fail


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
