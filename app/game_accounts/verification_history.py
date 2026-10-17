"""Internal history only. Observed name claims never grant ownership."""
import uuid
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import session, now
from app.core.errors import AuthError
from app.game_accounts import verification_context
from app.game_accounts.models import VerificationExecution, Verification, Registration, NameClaim, Character, Account
from app.game_accounts.support import authorize

OPERATIONS = frozenset(('start', 'confirm', 'cancel'))


def owners(db, account_ids):
    rows = db.scalars(select(Account).where(Account.id.in_(account_ids)).order_by(Account.id))
    return [dict(account_id=str(a.id), owner_id=str(a.owner_id) if a.owner_id else None,
                 ownership_revision=a.ownership_revision) for a in rows]


def begin(principal, ticket, operation, payload, rid):
    with session() as db, db.begin():
        uid = authorize(db, principal)
        target = rid
        name = None
        challenge_id = None
        initial = None
        if operation == 'start':
            if payload['source'] == 'direct_input':
                name = payload['character_name']
            else:
                target = uuid.UUID(payload['registration_id'])
                r = db.get(Registration, target)
                if r and r.user_id == uid and not r.deleted_at:
                    name = payload.get('target_character', {}).get('character_name', r.lookup_name)
                    initial = dict(source='stored_registration',
                        context=verification_context.capture(name, r.preview),
                        conflicting_accounts=owners(db, [r.account_id]) if r.account_id else [])
        else:
            v = db.get(Verification, rid)
            if v and v.actor_id == uid:
                challenge_id, name = v.id, v.lookup_name
                initial = dict(source='stored_challenge',
                    context=(v.identity_snapshot or {}).get('proof_context'),
                    conflicting_accounts=owners(db, [v.candidate_id]) if v.candidate_id else [])
        db.add(VerificationExecution(command_id=ticket[0], generation=ticket[1],
            actor_id=uid, operation=operation, requested_target=target,
            challenge_id=challenge_id, lookup_name=name, target_snapshot=initial, started_at=now(db)))


def observed(principal, ticket, obs):
    """Capture conflicting owners before apply can reject or mutate ownership."""
    with session() as db, db.begin():
        authorize(db, principal, write=True)
        event = db.get(VerificationExecution, ticket)
        context = verification_context.capture(event.lookup_name, obs.roster)
        if context is None:
            return
        accounts = set()
        for row in obs.roster:
            claim = db.get(NameClaim, (row['server_name'], row['character_name']))
            character = db.get(Character, claim.character_id) if claim else None
            if character:
                accounts.add(character.account_id)
        event.target_snapshot = dict(source='provider_observation', context=context, observed_at=obs.fetched_at.isoformat(),
            # These are name conflicts, not a canonical binding or authority.
            conflicting_accounts=owners(db, accounts) if accounts else [])


def complete(db, ticket, status, body):
    event = db.get(VerificationExecution, ticket)
    if event is None:
        return
    event.state, event.finished_at, event.http_status = 'completed', now(db), status
    if status >= 400:
        event.outcome_code = body['error']['code']
    elif event.operation == 'cancel':
        event.outcome_code = 'CANCEL_ACKNOWLEDGED'
    else:
        event.challenge_id = uuid.UUID(str(body['challenge_id']))
        event.outcome_code = body.get('result_code') or body['status'].upper()


def failed(ticket, error):
    with session() as db, db.begin():
        event = db.get(VerificationExecution, ticket)
        if event and event.state == 'running':
            event.state, event.finished_at = 'failed', now(db)
            # Never persist exception text, provider payloads or credentials.
            if isinstance(error, AuthError):
                event.outcome_code, event.http_status = error.code, error.status
            elif isinstance(error, SQLAlchemyError):
                event.outcome_code, event.http_status = 'SERVICE_UNAVAILABLE', 503
            else:
                event.outcome_code, event.http_status = 'INTERNAL_ERROR', 500
