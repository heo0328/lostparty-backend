"""Current-app representative policy, with read-only projections and write repair."""
from contextvars import ContextVar
from decimal import Decimal, InvalidOperation, localcontext
from sqlalchemy import select, tuple_
from app.game_accounts.models.models import Character, NameClaim, Activity, Configuration, Registration, ScopedPowerCache

current_policy = ContextVar('account_representative_policy2', default=False)


def number(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 128:
        return None
    try:
        with localcontext() as ctx:
            ctx.prec = 128
            value = Decimal(raw)
            if not value.is_finite() or value < 0:
                return None
            if value == 0:
                return '0'
            if not -128 <= value.adjusted() <= 63:
                return None
            value = format(value.normalize(), 'f')
            return value if len(value) <= 64 else None
    except (InvalidOperation, ValueError):
        return None


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z') if value is not None else None


def observations(db, uid, characters):
    """One snapshot; successful observations retained across TTL/failed checks."""
    claims = {(c.server_name, c.character_name): c.character_id for c in db.scalars(
        select(NameClaim).where(tuple_(NameClaim.server_name, NameClaim.character_name).in_(
            [(c.server_name, c.character_name) for c in characters])))} if characters else {}
    caches = {}
    if characters:
        for row in db.scalars(select(ScopedPowerCache).where(
                ScopedPowerCache.actor_id == uid,
                ScopedPowerCache.character_id.in_([c.id for c in characters]),
                ScopedPowerCache.fetched_at.is_not(None)).order_by(
                    ScopedPowerCache.fetched_at.desc(), ScopedPowerCache.scope_key)):
            if number(row.value) is not None:
                caches.setdefault((row.character_id, row.lifecycle_revision), row)
    result = []
    for c in characters:
        reason = ('CHARACTER_UNUSABLE' if c.lifecycle_state != 'active' or c.status != 'confirmed'
                  else 'IDENTITY_CONFLICT' if claims.get((c.server_name, c.character_name)) != c.id else None)
        level = number(c.summary.get('item_level'))
        power, observed = number(c.summary.get('combat_power')), c.power_fetched_at
        if observed is None or power is None:
            power, observed = None, None
        cached = caches.get((c.id, c.lifecycle_revision))
        if cached and (observed is None or cached.fetched_at >= observed):
            power, observed = number(cached.value), cached.fetched_at
        result.append(dict(character_id=str(c.id), character_name=c.character_name,
            item_level=level, combat_power=power, item_level_observed_at=stamp(c.fetched_at) if level is not None else None,
            combat_power_observed_at=stamp(observed), usable=reason is None, blocked_reason=reason))
    return result


def selection_key(row):
    def desc(value):
        return value is None, Decimal(value).copy_negate() if value is not None else 0
    return (*desc(row['item_level']), *desc(row['combat_power']),
            row['character_name'].encode('utf-16-be'), row['character_id'])


def choose(rows, selected, existing=None, *, transition=False):
    selected = set(map(str, selected))
    candidates = [r for r in rows if r['usable'] and r['character_id'] in selected]
    if not transition and existing is not None and str(existing) in {r['character_id'] for r in candidates}:
        return str(existing)
    return min(candidates, key=selection_key)['character_id'] if candidates else None


def projected(registration, configuration, selected, eligible):
    rep = configuration.representative_id if configuration else None
    return rep if registration.is_main and rep in set(selected) and rep in set(eligible) else None


def effective(db, registration, configuration):
    if configuration is None or not registration.is_main or configuration.representative_id is None:
        return None
    rep = db.get(Character, configuration.representative_id)
    if rep is None or rep.account_id != configuration.account_id:
        return None
    selected = db.get(Activity, (configuration.id, rep.id))
    from app.game_accounts.rosters.lifecycle import usable
    return rep.id if selected and usable(db, rep) else None


def repair(db, uid, registration, *, transition=False):
    """Caller holds game mutation lock; never writes activities/ranks/groups."""
    from uuid import UUID
    if not registration.is_main or not registration.account_id:
        return
    from app.game_accounts.models.models import Account
    account = db.get(Account, registration.account_id)
    if account is None or account.owner_id != uid:
        return
    conf = db.scalar(select(Configuration).where(Configuration.user_id == uid,
        Configuration.account_id == account.id, Configuration.ended_at.is_(None)))
    if conf is None:
        return
    chosen = list(db.scalars(select(Activity.character_id).where(Activity.settings_id == conf.id)))
    characters = list(db.scalars(select(Character).where(Character.account_id == account.id,
        Character.lifecycle_state != 'retired')))
    rows = observations(db, uid, characters)
    rep = choose(rows, chosen, conf.representative_id, transition=transition)
    valid = {r['character_id'] for r in rows if r['usable']}
    state = conf.state
    if chosen:
        state = 'configured' if set(map(str, chosen)) <= valid and rep else 'needs_reconfiguration'
    elif conf.state != 'unconfigured':
        state = 'needs_reconfiguration'
    target = UUID(rep) if rep else None
    if target != conf.representative_id or state != conf.state:
        conf.representative_id, conf.state = target, state
        conf.version += 1
        conf.next_change_at = None


def repair_account(db, account):
    if not current_policy.get():
        return
    for registration in db.scalars(select(Registration).where(Registration.account_id == account.id,
            Registration.user_id == account.owner_id, Registration.deleted_at.is_(None), Registration.is_main.is_(True))):
        repair(db, account.owner_id, registration)
