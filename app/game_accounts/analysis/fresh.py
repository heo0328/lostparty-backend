"""Bounded, actor/scope-fenced in-flight observation sharing. Not a TTL cache."""
import time
import uuid
from datetime import timedelta, datetime, timezone
from sqlalchemy import select, text
from app.core.database import session, now
from app.game_accounts.models.analysis import AnalysisFetch
from app.game_accounts.common.support import lock, fail, GameError
from app.game_accounts.rosters.lifecycle import digest
from app.game_accounts.provider_io import credentials, rate_limits
from app.game_accounts.provider_io.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.analysis.analyzer import analyze, AnalysisUnavailable


def scoped(db):
    db.execute(text("SET LOCAL statement_timeout = '500ms'"))
    db.execute(text("SET LOCAL lock_timeout = '500ms'"))


def collect(principal, target, snapshot, deadline):
    uid = principal[0].id
    scope = digest([str(uid), str(target['character_id']), target['ownership_revision'],
                    target['lifecycle_revision'], target['server_name'], target['character_name'], target['class_name'], snapshot.generation])
    with session() as db, db.begin():
        scoped(db)
        credentials.check(db, principal, snapshot)
        lock(db, 'analysis-fetch:' + scope)
        at = now(db)
        # A request starting AFTER completion must create its own fresh fetch.
        row = db.scalar(select(AnalysisFetch).where(AnalysisFetch.actor_id == uid,
            AnalysisFetch.scope_digest == scope, AnalysisFetch.state == 'running',
            AnalysisFetch.expires_at > at).order_by(AnalysisFetch.expires_at.desc()).limit(1))
        owner = row is None
        if owner:
            row = AnalysisFetch(id=uuid.uuid4(), actor_id=uid, scope_digest=scope,
                generation=1, state='running', expires_at=at+timedelta(seconds=30))
            db.add(row)
        ident, generation = row.id, row.generation
    if not owner:
        while time.monotonic() < deadline:
            with session() as db:
                scoped(db)
                credentials.check(db, principal, snapshot)
                row = db.get(AnalysisFetch, ident)
                if row is None or row.generation != generation or now(db) >= row.expires_at:
                    fail('UPSTREAM_UNAVAILABLE', 503)
                if row.state == 'completed':
                    return row.result
                if row.state == 'failed':
                    saved = row.result
                    raise GameError(saved['code'], saved['status'], saved['retry_after_seconds'],
                                    datetime.fromisoformat(saved['retry_at']) if saved['retry_at'] else None)
            time.sleep(min(.05, max(0, deadline-time.monotonic())))
        fail('UPSTREAM_UNAVAILABLE', 503)
    try:
        if time.monotonic()>=deadline:fail('UPSTREAM_UNAVAILABLE',503)
        credentials.before_call(principal, snapshot)
        if time.monotonic()>=deadline:fail('UPSTREAM_UNAVAILABLE',503)
        raw = LostArkProvider(snapshot.token, observer=rate_limits.observer(snapshot.fingerprint)).armory(target['character_name'])
        role, summary, detail = analyze(raw, server_name=target['server_name'], character_name=target['character_name'],
            class_name=target['class_name'], lifecycle_revision=target['lifecycle_revision'], fetched_at=datetime.now(timezone.utc))
        result = dict(role=role, summary=summary, detail=detail)
        credentials.current(snapshot)
        if time.monotonic() >= deadline:
            fail('UPSTREAM_UNAVAILABLE', 503)
        with session() as db, db.begin():
            scoped(db)
            row = db.get(AnalysisFetch, ident, with_for_update=True)
            if row is None or row.generation != generation or now(db) >= row.expires_at:
                fail('UPSTREAM_UNAVAILABLE', 503)
            row.state, row.result = 'completed', result
        return result
    except (ProviderUnavailable, AnalysisUnavailable, GameError) as exc:
        code = exc.reason if isinstance(exc, ProviderUnavailable) else exc.code if isinstance(exc, GameError) else str(exc)
        status = exc.status if isinstance(exc, GameError) else 503
        retry_after, retry_at = getattr(exc, 'retry_after', None), getattr(exc, 'retry_at', None)
        with session() as db:
            _, blocked_until, _ = rate_limits.state(db, snapshot.fingerprint)
            if blocked_until is not None:
                retry = rate_limits.metadata(db, snapshot.fingerprint, code)
                retry_after, retry_at = retry['retry_after_seconds'], retry['retry_at']
        safe = dict(code=code, status=status, retry_after_seconds=retry_after,
                    retry_at=retry_at.isoformat() if retry_at else None)
        with session() as db, db.begin():
            scoped(db)
            row = db.get(AnalysisFetch, ident, with_for_update=True)
            if row and row.generation == generation and row.state == 'running':
                row.state, row.result = 'failed', safe
        raise GameError(code, status, retry_after, retry_at) from None
