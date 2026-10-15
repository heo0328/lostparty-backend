"""Display-only power observations. Workers never write business data or grant ownership."""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import timedelta

from sqlalchemy import select, text
from app.core.database import session, now
from app.game_accounts.models import Character, ScopedPowerCache as PowerCache
from app.game_accounts import lifecycle
from app.game_accounts.combat_power import default_collection_target, parse_profile_power
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable
from app.lostark_keys import service as credentials
from app.lostark_keys import rate_limits
from app.game_accounts.support import (authorize, lock, fail, reserve,
                                       commit_result, release, GameError)

TTL = timedelta(minutes=30)
BUDGET_SECONDS = 20
SAFE_REASONS = {'UPSTREAM_UNAVAILABLE', 'UPSTREAM_NOT_CONFIGURED', 'UPSTREAM_RATE_LIMITED',
                'UPSTREAM_INVALID_RESPONSE', 'UPSTREAM_BUSY', 'UPSTREAM_RESPONSE_TOO_LARGE', 'LOSTARK_KEY_REJECTED'}


def scoped(db):
    db.execute(text("SET LOCAL statement_timeout = '500ms'"))
    db.execute(text("SET LOCAL lock_timeout = '500ms'"))


def current_roster(db, uid, rid):
    from app.game_accounts.service import reg, ownership
    r = reg(db, uid, rid)
    account, state = ownership(db, uid, r)
    fingerprint = lifecycle.digest(lifecycle.registration_stamp(db,r))
    if account and state == 'owned':
        rows = [dict(c.summary, power_fetched_at=c.power_fetched_at, summary_fetched_at=c.fetched_at,
                     _scope=lifecycle.power_scope(r,c), _usable=lifecycle.usable(db,c))
                for c in db.scalars(select(Character).where(Character.account_id==account.id,Character.lifecycle_state!='retired'))]
    else:
        rows = [dict(row, power_fetched_at=None, summary_fetched_at=r.fetched_at,
                     _scope=lifecycle.power_scope(r), _usable=True) for row in r.preview]
    return fingerprint, {(row['server_name'],row['character_name']):row for row in rows}


def key_for(uid, pair, scope, version):
    identity = ('canonical',str(scope['character_id']),scope['lifecycle_revision']) if scope['character_id'] else (
        'preview',str(scope['registration_id']),scope['preview_version'],*pair)
    return uid, lifecycle.digest((identity,version))


def overlay(db, uid, row, scope=None):
    candidates=[]
    if scope:
        query=select(PowerCache).where(PowerCache.actor_id==uid)
        if scope['character_id']:
            query=query.where(PowerCache.character_id==scope['character_id'])
        else:
            query=query.where(PowerCache.character_id.is_(None),PowerCache.registration_id==scope['registration_id'],
                              PowerCache.preview_version==scope['preview_version'],PowerCache.server_name==row['server_name'],
                              PowerCache.character_name==row['character_name'])
        candidates=list(db.scalars(query))
    value,fetched=row.get('combat_power'),row.get('power_fetched_at')
    good=max((c for c in candidates if c.fetched_at),key=lambda c:c.fetched_at,default=None)
    if good and (fetched is None or good.fetched_at>=fetched): value,fetched=good.value,good.fetched_at
    current_candidates=[c for c in candidates if c.lifecycle_revision==scope['lifecycle_revision']]
    c=max((c for c in current_candidates if c.checked_at),key=lambda c:c.checked_at,default=None)
    status=c.status if c else 'available' if fetched else 'unknown'
    checked=c.checked_at if c else fetched
    reason=c.reason if c else None
    stale=(fetched is None or now(db)>=fetched+TTL or status in ('unavailable','failed') or
           fetched<row.get('summary_fetched_at',fetched) or row.get('eligible') is False or row.get('_usable') is False)
    return dict(combat_power=value,power_fetched_at=fetched,power_checked_at=checked,
                power_status=status,power_reason=reason,power_stale=stale)


def fetch_power(pair, token, observer=None):
    try:
        raw = LostArkProvider(token, observer=observer).profile(pair[1])
        value = parse_profile_power(raw, *pair)
        return ('available', value, None) if value is not None else ('unavailable', None, 'COMBAT_POWER_UNAVAILABLE')
    except ProviderUnavailable as error:
        reason = error.reason if error.reason in SAFE_REASONS else 'UPSTREAM_UNAVAILABLE'
        return 'failed', None, reason
    except Exception:
        # Never return URL/profile/error repr from a provider exception.
        return 'failed', None, 'UPSTREAM_UNAVAILABLE'


def release_claims(claims):
    if not claims:
        return
    with session() as db, db.begin():
        scoped(db)
        for ident, generation in claims.values():
            c = db.get(PowerCache, ident, with_for_update=True)
            if c and c.generation == generation:
                c.lease_expires_at = None


def refresh(principal, rid, key, payload):
    deadline = time.monotonic() + BUDGET_SECONDS
    ticket, replay = reserve(principal, 'power', key, {'target': str(rid), 'body': payload})
    if replay:
        from app.game_accounts.service import replay_access
        replay_access(principal, 'power', rid)
        return replay
    claims, outcomes, ready = {}, {}, []
    try:
        with session() as db:
            current_roster(db, authorize(db, principal), rid)
        snapshot = credentials.capture(principal)
        pairs = list(dict.fromkeys((v['server_name'], v['character_name']) for v in payload['characters']))
        with session() as db, db.begin():
            scoped(db)
            uid = authorize(db, principal, write=True)
            credentials.check(db, principal, snapshot)
            fingerprint, roster = current_roster(db, uid, rid)
            if any(pair not in roster for pair in pairs):
                fail('CHARACTER_OUT_OF_SCOPE', 400)
            for pair in pairs:
                row = roster[pair]
                if not row['_usable']: fail('CHARACTER_UNUSABLE')
                if not default_collection_target(row.get('item_level')):
                    outcomes[pair] = ('skipped', 'ITEM_LEVEL_UNAVAILABLE' if row.get('item_level') is None else 'ITEM_LEVEL_BELOW_DEFAULT')
                    continue
                ident = key_for(uid, pair, row['_scope'], snapshot.version)
                c = db.get(PowerCache, ident)
                current = now(db)
                cached = c and c.credential_version == snapshot.version and c.checked_at and c.checked_at >= row['summary_fetched_at'] and current < c.checked_at + (timedelta(seconds=10) if c.status == 'failed' else TTL)
                if cached and c.reason == 'UPSTREAM_RATE_LIMITED':
                    _, blocked_until, _ = rate_limits.state(db, snapshot.fingerprint)
                    cached = blocked_until is not None
                if cached:
                    outcomes[pair] = ('cached' if c.status == 'available' else c.status, c.reason)
                    continue
                if c and c.credential_version == snapshot.version and c.lease_expires_at and current < c.lease_expires_at:
                    outcomes[pair] = ('deferred', 'FETCH_IN_PROGRESS')
                    continue
                if not c:
                    c = PowerCache(actor_id=uid, scope_key=ident[1], **row['_scope'], credential_version=snapshot.version,
                                   server_name=pair[0], character_name=pair[1],
                                   generation=0, status='unknown', value=row.get('combat_power'),
                                   fetched_at=row.get('power_fetched_at'))
                    db.add(c)
                if c.credential_version != snapshot.version:
                    c.checked_at, c.status, c.reason = None, 'unknown', None
                c.credential_version = snapshot.version
                c.generation += 1
                c.lease_expires_at = current + timedelta(seconds=30)
                claims[pair] = ident, c.generation
                ready.append(pair)
        pool = ThreadPoolExecutor(max_workers=2)
        pending, observed = {}, {}
        try:
            # One second is reserved for fenced DB commit. No sleep/quota waiting.
            while ready or pending:
                while ready and len(pending) < 2 and time.monotonic() < deadline - 1:
                    pair = ready.pop(0)
                    try:
                        with session() as db:
                            uid_now=authorize(db,principal)
                            actual,_=current_roster(db,uid_now,rid)
                            if actual!=fingerprint: fail('REVISION_CONFLICT')
                        credentials.before_call(principal, snapshot)
                    except GameError as error:
                        if error.code not in ('RATE_LIMITED', 'UPSTREAM_RATE_LIMITED'):
                            raise
                        outcomes[pair] = ('deferred', error.code)
                        for rest in ready:
                            outcomes[rest] = ('deferred', error.code)
                        ready.clear()
                        break
                    pending[pool.submit(fetch_power, pair, snapshot.token, rate_limits.observer(snapshot.fingerprint))] = pair
                remaining = deadline - 1 - time.monotonic()
                if remaining <= 0 or not pending:
                    break
                done, _ = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                if not done:
                    break
                for future in done:
                    pair = pending.pop(future)
                    observed[pair] = future.result()
                    reason = observed[pair][2]
                    if reason in ('LOSTARK_KEY_REJECTED', 'UPSTREAM_RATE_LIMITED'):
                        for rest in ready:
                            outcomes[rest] = ('deferred', reason)
                        ready.clear()
            for pair in ready:
                outcomes[pair] = ('deferred', 'TIME_BUDGET_EXCEEDED')
            for future, pair in pending.items():
                future.cancel()
                outcomes[pair] = ('deferred', 'TIME_BUDGET_EXCEEDED')
        finally:
            # In-flight requests may finish transport cleanup after response;
            # their pure return values are discarded, never applied later.
            pool.shutdown(wait=False, cancel_futures=True)
        with session() as db, db.begin():
            scoped(db)
            authorize(db, principal, write=True)
            credentials.check(db, principal, snapshot)
            actual, roster_now = current_roster(db, uid, rid)
            if actual != fingerprint:
                fail('REVISION_CONFLICT')
            current = now(db)
            for pair, (ident, generation) in claims.items():
                c = db.get(PowerCache, ident, with_for_update=True)
                if not c or c.generation != generation or not c.lease_expires_at or current >= c.lease_expires_at:
                    raise GameError('REQUEST_IN_PROGRESS', 409, 2)
                if pair in observed:
                    state, value, reason = observed[pair]
                    c.status, c.reason, c.checked_at = state, reason, current
                    if state == 'available':
                        c.value, c.fetched_at = value, current
                    outcomes[pair] = ('updated' if state == 'available' else state, reason)
                c.lease_expires_at = None
            db.flush()
            items = []
            for pair in pairs:
                data = overlay(db, uid, roster_now[pair], roster_now[pair]['_scope'])
                state, reason = outcomes[pair]
                retry = rate_limits.metadata(db, snapshot.fingerprint, reason) if reason in ('RATE_LIMITED', 'UPSTREAM_RATE_LIMITED') else {'retry_after_seconds': None, 'retry_at': None}
                items.append(dict(server_name=pair[0], character_name=pair[1], **data,
                                  status=state, reason=reason, **retry))
            result = commit_result(db, ticket, 200, dict(items=items))
        claims.clear()
        return result
    except Exception:
        release_claims(claims)
        release(ticket)
        raise
