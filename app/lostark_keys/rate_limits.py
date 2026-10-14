"""Token-scoped control state only; never writes character/cache/request results."""
from datetime import datetime, timedelta, timezone
from math import ceil
from sqlalchemy import select, delete
from app.core.database import session, now
from app.game_accounts.models import LimitEvent
from app.game_accounts.support import lock, GameError
from app.lostark_keys.models import ProviderLimit


def integer(value, maximum):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 16:
        return None
    result = int(value)
    return result if result <= maximum else None


def observation(status, headers, observed_at):
    # requests headers are case-insensitive; also support plain test dictionaries.
    values = {k.lower(): v for k, v in headers.items() if k.lower() in (
        'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset')}
    limit = integer(values.get('x-ratelimit-limit'), 1000000)
    remaining = integer(values.get('x-ratelimit-remaining'), 1000000)
    if status != 429 and not (status == 200 and remaining == 0):
        return None
    reset = integer(values.get('x-ratelimit-reset'), 253402300799)
    if reset is not None:
        deadline = datetime.fromtimestamp(reset, timezone.utc)
        if observed_at < deadline <= observed_at + timedelta(seconds=300):
            return deadline
    return observed_at + timedelta(seconds=60)


def record(fingerprint, deadline):
    # This independent transaction survives rejected/timed-out business results.
    with session() as db, db.begin():
        lock(db, 'quota:lostark-token:' + fingerprint)
        row = db.get(ProviderLimit, fingerprint)
        if row is None:
            db.add(ProviderLimit(fingerprint=fingerprint, blocked_until=deadline))
        elif deadline > row.blocked_until:
            row.blocked_until = deadline


def observer(fingerprint):
    def observe(status, headers):
        deadline = observation(status, headers, datetime.now(timezone.utc))
        if deadline is not None:
            record(fingerprint, deadline)
    return observe


def state(db, fingerprint):
    current = now(db)
    row = db.get(ProviderLimit, fingerprint, populate_existing=True)
    upstream = row.blocked_until if row and row.blocked_until > current else None
    scope = 'lostark-token:' + fingerprint
    events = list(db.scalars(select(LimitEvent.created_at).where(
        LimitEvent.scope == scope, LimitEvent.created_at > current-timedelta(seconds=60)
    ).order_by(LimitEvent.created_at)))
    local = events[-80] + timedelta(seconds=60) if len(events) >= 80 else None
    deadlines = [d for d in (upstream, local) if d is not None]
    return current, max(deadlines) if deadlines else None, upstream is not None


def metadata(db, fingerprint, reason):
    current, deadline, _ = state(db, fingerprint)
    if deadline is None:
        # Historical failed cache may outlive a short observed deadline. Do not
        # extend provider state: expose an immediately eligible absolute time.
        deadline = current
    return {'retry_after_seconds': max(1, ceil((deadline-current).total_seconds())),
            'retry_at': deadline}


def reject_wait(db, fingerprint):
    current, deadline, upstream = state(db, fingerprint)
    if deadline is not None:
        raise GameError('UPSTREAM_RATE_LIMITED' if upstream else 'RATE_LIMITED',
                        503 if upstream else 429,
                        max(1, ceil((deadline-current).total_seconds())), deadline)


def acquire(fingerprint):
    with session() as db, db.begin():
        scope = 'lostark-token:' + fingerprint
        lock(db, 'quota:' + scope)
        current, deadline, upstream = state(db, fingerprint)
        if deadline is not None:
            raise GameError('UPSTREAM_RATE_LIMITED' if upstream else 'RATE_LIMITED',
                            503 if upstream else 429,
                            max(1, ceil((deadline-current).total_seconds())), deadline)
        db.execute(delete(LimitEvent).where(LimitEvent.scope==scope,
                   LimitEvent.created_at<=current-timedelta(seconds=60)))
        db.add(LimitEvent(scope=scope, created_at=current))
