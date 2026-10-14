import base64
import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from math import ceil
from sqlalchemy import select, text, delete
from fastapi.encoders import jsonable_encoder
from app.auth.models import User, Session
from app.auth.service import active
from app.core.database import session, now
from app.core.errors import AuthError
from app.core.config import settings
from app.game_accounts.models import RequestResult, LimitEvent


class GameError(AuthError):
    def __init__(self, code, status=409, retry_after=None):
        super().__init__(code, status)
        self.retry_after = retry_after


def fail(code, status=409):
    raise GameError(code, status)


def lock(db, scope):
    value = int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], 'big', signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': value})


def authorize(db, principal, write=False):
    uid, sid = principal[0].id, principal[1].id
    if write:
        # Initial deployment deliberately serializes game mutations. No network
        # call is performed under this lock; auth locks never acquire it.
        lock(db, 'game-mutations-v1')
    query = select(User).where(User.id == uid)
    if write:
        query = query.with_for_update()
    u = db.scalar(query)
    query = select(Session).where(Session.id == sid)
    if write:
        query = query.with_for_update()
    s = db.scalar(query)
    if u is None or s is None or s.user_id != uid:
        fail('SESSION_REVOKED', 401)
    active(u, s, now(db))
    return uid


def quota(scope, maximum, seconds=60):
    with session() as db, db.begin():
        lock(db, 'quota:' + scope)
        current = now(db)
        db.execute(delete(LimitEvent).where(LimitEvent.scope == scope, LimitEvent.created_at <= current-timedelta(seconds=seconds)))
        events = list(db.scalars(select(LimitEvent.created_at).where(LimitEvent.scope == scope).order_by(LimitEvent.created_at)))
        if len(events) >= maximum:
            wait = max(1, ceil((events[-maximum]+timedelta(seconds=seconds)-current).total_seconds()))
            raise GameError('RATE_LIMITED', 429, wait)
        db.add(LimitEvent(scope=scope, created_at=current))


def reserve(principal, operation, key, payload):
    digest = hashlib.sha256(json.dumps(jsonable_encoder(payload), sort_keys=True, separators=(',',':')).encode()).hexdigest()
    with session() as db, db.begin():
        uid = authorize(db, principal)
        lock(db, f'dedup:{uid}:{operation}:{key}')
        r = db.scalar(select(RequestResult).where(RequestResult.actor_id == uid, RequestResult.operation == operation, RequestResult.key == key).with_for_update())
        current = now(db)
        if r:
            if not hmac.compare_digest(r.digest, digest):
                fail('IDEMPOTENCY_CONFLICT')
            if r.completed_at:
                if current >= r.completed_at + timedelta(hours=24):
                    fail('IDEMPOTENCY_EXPIRED')
                return None, (r.status, r.result)
            if r.state == 'running' and current < r.lease_expires_at:
                raise GameError('REQUEST_IN_PROGRESS', 409, 2)
            r.generation += 1
            r.state = 'running'
            r.lease_expires_at = current + timedelta(seconds=30)
        else:
            r = RequestResult(actor_id=uid, operation=operation, key=key, digest=digest,
                              lease_expires_at=current+timedelta(seconds=30))
            db.add(r)
            db.flush()
        return (r.id, r.generation), None


def commit_result(db, ticket, status, result):
    r = db.scalar(select(RequestResult).where(RequestResult.id == ticket[0]).with_for_update())
    if r is None or r.generation != ticket[1] or r.state != 'running' or now(db) >= r.lease_expires_at:
        raise GameError('REQUEST_IN_PROGRESS', 409, 2)
    r.state, r.completed_at, r.status, r.result = 'completed', now(db), status, jsonable_encoder(result)
    return status, r.result


def release(ticket):
    if ticket:
        with session() as db, db.begin():
            r = db.scalar(select(RequestResult).where(RequestResult.id == ticket[0]).with_for_update())
            if r and r.generation == ticket[1] and r.state == 'running':
                r.state = 'retryable'


def cursor_encode(data):
    raw = json.dumps(data, sort_keys=True, separators=(',',':')).encode()
    signature = hmac.new(settings.recovery_key(), b'game-cursor-v1:' + raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw+signature).decode().rstrip('=')


def cursor_decode(value, scope, revision):
    try:
        if len(value) > 2048:
            raise ValueError()
        raw = base64.b64decode(value+'='*((-len(value))%4), altchars=b'-_', validate=True)
        data, signature = raw[:-32], raw[-32:]
        expected = hmac.new(settings.recovery_key(), b'game-cursor-v1:'+data, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        result = json.loads(data)
        if result['scope'] != scope or type(result['offset']) is not int or result['offset'] < 0:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        fail('INVALID_REQUEST', 400)
    if result['revision'] != revision:
        fail('CURSOR_STALE')
    return result['offset']
