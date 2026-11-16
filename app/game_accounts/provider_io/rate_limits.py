"""Token-scoped control state only; never writes character/cache/request results."""
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from math import ceil
from email.utils import parsedate_to_datetime
from sqlalchemy import select
from sqlalchemy import delete
from app.core.database import session
from app.core.database import now
from app.game_accounts.models.models import LimitEvent
from app.game_accounts.common.support import lock
from app.game_accounts.common.support import GameError
from app.game_accounts.models.provider_limits import ProviderLimit


def integer(value, maximum):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 16:
        return None
    result = int(value)
    return result if result <= maximum else None


def retry_deadline(value, at):
    seconds=integer(value,300)
    if seconds is not None:
        return at+timedelta(seconds=seconds) if seconds else None
    if not isinstance(value,str) or len(value)>128:return None
    try:
        deadline=parsedate_to_datetime(value)
        if deadline.tzinfo is not None and at<deadline<=at+timedelta(seconds=300):return deadline
    except (ValueError,TypeError,OverflowError):
        pass
    return None


def observation(status, headers, observed_at):
    # Header values are only parsed into a bounded deadline; never persisted raw.
    values = {k.lower(): v for k, v in headers.items() if k.lower() in (
        'x-ratelimit-remaining', 'x-ratelimit-reset', 'retry-after')}
    remaining = integer(values.get('x-ratelimit-remaining'), 1000000)
    retry=retry_deadline(values.get('retry-after'),observed_at)
    if status in (401,403,415):
        return max(observed_at+timedelta(seconds=60),retry or observed_at)
    if status is None or status in (500,502,503,504):
        return max(observed_at+timedelta(seconds=30),retry or observed_at)
    if status != 429 and not (status == 200 and remaining == 0):
        return None
    reset = integer(values.get('x-ratelimit-reset'), 253402300799)
    if reset is not None:
        deadline = datetime.fromtimestamp(reset, timezone.utc)
        if observed_at < deadline <= observed_at + timedelta(seconds=300):
            return max(deadline,retry or observed_at)
    return max(observed_at+timedelta(seconds=60),retry or observed_at)


def record(fingerprint, deadline, code='UPSTREAM_RATE_LIMITED', upstream_status=None):
    # This independent transaction survives rejected/timed-out business results.
    with session() as db, db.begin():
        lock(db, 'quota:lostark-token:' + fingerprint)
        row = db.get(ProviderLimit, fingerprint)
        if row is None:
            db.add(ProviderLimit(fingerprint=fingerprint, blocked_until=deadline, blocked_code=code, upstream_status=upstream_status))
        elif deadline > row.blocked_until:
            row.blocked_until = deadline
            row.blocked_code = code
            row.upstream_status = upstream_status


def observer(fingerprint):
    def observe(status, headers):
        deadline = observation(status, headers, datetime.now(timezone.utc))
        if deadline is not None:
            code = ('LOSTARK_KEY_REJECTED' if status in (401,403) else
                    'UPSTREAM_RATE_LIMITED' if status in (200,429) else 'UPSTREAM_UNAVAILABLE')
            record(fingerprint, deadline, code, status)
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
    return current, max(deadlines) if deadlines else None, (row.blocked_code if upstream else None)


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
        raise GameError(upstream or 'RATE_LIMITED',
                        503 if upstream else 429,
                        max(1, ceil((deadline-current).total_seconds())), deadline)


def acquire(fingerprint):
    with session() as db, db.begin():
        scope = 'lostark-token:' + fingerprint
        lock(db, 'quota:' + scope)
        current, deadline, upstream = state(db, fingerprint)
        if deadline is not None:
            raise GameError(upstream or 'RATE_LIMITED',
                            503 if upstream else 429,
                            max(1, ceil((deadline-current).total_seconds())), deadline)
        db.execute(delete(LimitEvent).where(LimitEvent.scope==scope,
                   LimitEvent.created_at<=current-timedelta(seconds=60)))
        db.add(LimitEvent(scope=scope, created_at=current))
