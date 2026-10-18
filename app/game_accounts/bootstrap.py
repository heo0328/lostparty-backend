"""One member-owned, read-only snapshot; no provider, command, or cache writes."""
from collections import defaultdict
from datetime import date

from pydantic import ValidationError
from sqlalchemy import select, text, func
from sqlalchemy.dialects.postgresql import distinct_on

from app.core.database import session, now
from app.game_accounts import service, lifecycle, lifecycle_reads, profiles, presentation, representative, activity_policy
from app.game_accounts.models import (Registration, Account, Character, Configuration, Activity, NameClaim,
    CharacterRoleSummary, CharacterPersonalPreferences, AccountCharacterPresentation, ScopedPowerCache)
from app.game_accounts.bootstrap_schemas import AccountBootstrap
from app.game_accounts.support import authorize, fail
from app.raid_weekly.models import WeeklyState
from app.raid_weekly import service as weekly
from app.raids import service as raids

MAX_REGISTRATIONS = 20
MAX_CHARACTERS = 200
MAX_BYTES = 16 * 1024 * 1024


class StoredRows:
    """Only explicitly batch-loaded rows, for existing pure domain projections."""
    def __init__(self, claims, roles, preferences):
        self.rows = {
            NameClaim: {(r.server_name, r.character_name): r for r in claims},
            CharacterRoleSummary: {(r.user_id, r.character_id, r.ownership_revision, r.role): r for r in roles},
            CharacterPersonalPreferences: {(r.user_id, r.character_id, r.ownership_revision): r for r in preferences},
        }

    def get(self, model, key):
        return self.rows[model].get(key)


def current_personal_rows(db, model, uid, ids):
    if not ids:
        return []
    return list(db.scalars(select(model).join(Character, Character.id == model.character_id)
        .join(Account, Account.id == Character.account_id).where(model.user_id == uid,
            model.character_id.in_(ids), model.ownership_revision == Account.ownership_revision)))


def snapshot(db, uid, stamp):
    registrations = list(db.scalars(select(Registration).where(Registration.user_id == uid,
        Registration.deleted_at.is_(None)).order_by(Registration.created_at, Registration.id)
        .limit(MAX_REGISTRATIONS + 1)))
    if len(registrations) > MAX_REGISTRATIONS:
        fail('BOOTSTRAP_LIMIT_EXCEEDED')
    aids = {r.account_id for r in registrations if r.account_id}
    accounts = {a.id: a for a in db.scalars(select(Account).where(Account.id.in_(aids)))} if aids else {}
    owned = {a.id for a in accounts.values() if a.owner_id == uid}
    chars = list(db.scalars(select(Character).where(Character.account_id.in_(owned),
        Character.lifecycle_state != 'retired').order_by(Character.server_name, Character.character_name, Character.id)
        .limit(MAX_REGISTRATIONS * MAX_CHARACTERS + 1))) if owned else []
    by_account = defaultdict(list)
    for c in chars:
        by_account[c.account_id].append(c)
    if any(len(v) > MAX_CHARACTERS for v in by_account.values()) or any(len(r.preview) > MAX_CHARACTERS for r in registrations):
        fail('BOOTSTRAP_LIMIT_EXCEEDED')
    foreign_counts = dict(db.execute(select(Character.account_id, func.count()).where(
        Character.account_id.in_(aids - owned), Character.lifecycle_state != 'retired').group_by(Character.account_id)).all()) if aids - owned else {}
    configurations = list(db.scalars(select(Configuration).where(Configuration.user_id == uid,
        Configuration.account_id.in_(owned), Configuration.ended_at.is_(None)))) if owned else []
    configs = {c.account_id: c for c in configurations}
    activities = list(db.scalars(select(Activity).where(Activity.settings_id.in_([c.id for c in configurations]))
        .order_by(Activity.character_id).limit(MAX_REGISTRATIONS * MAX_CHARACTERS + 1))) if configurations else []
    chosen = defaultdict(list)
    for a in activities:
        chosen[a.settings_id].append(a.character_id)
    if len(activities) > MAX_REGISTRATIONS * MAX_CHARACTERS or any(len(v) > MAX_CHARACTERS for v in chosen.values()):
        fail('BOOTSTRAP_LIMIT_EXCEEDED')
    ids = [c.id for c in chars]
    claims = list(db.scalars(select(NameClaim).where(NameClaim.character_id.in_(ids)))) if ids else []
    # At most two cache rows per character, preserving overlay's latest-good and
    # current-lifecycle latest-check semantics without loading historical caches.
    power = defaultdict(list)
    if ids:
        base = select(ScopedPowerCache).where(ScopedPowerCache.actor_id == uid, ScopedPowerCache.character_id.in_(ids))
        good = base.where(ScopedPowerCache.fetched_at.is_not(None)).ext(distinct_on(ScopedPowerCache.character_id)).order_by(
            ScopedPowerCache.character_id, ScopedPowerCache.fetched_at.desc(), ScopedPowerCache.scope_key)
        checked = base.join(Character, Character.id == ScopedPowerCache.character_id).where(
            ScopedPowerCache.lifecycle_revision == Character.lifecycle_revision, ScopedPowerCache.checked_at.is_not(None)
        ).ext(distinct_on(ScopedPowerCache.character_id)).order_by(ScopedPowerCache.character_id,
            ScopedPowerCache.checked_at.desc(), ScopedPowerCache.scope_key)
        for row in [*db.scalars(good), *db.scalars(checked)]:
            power[row.character_id].append(row)
    selected_ids = {a.character_id for a in activities} & set(ids)
    roles = current_personal_rows(db, CharacterRoleSummary, uid, selected_ids)
    prefs = current_personal_rows(db, CharacterPersonalPreferences, uid, selected_ids)
    stored = StoredRows(claims, roles, prefs)
    displays = {r.game_account_id: r for r in db.scalars(select(AccountCharacterPresentation)
        .join(Account, Account.id == AccountCharacterPresentation.game_account_id).where(
            AccountCharacterPresentation.user_id == uid, Account.id.in_(owned),
            AccountCharacterPresentation.ownership_revision == Account.ownership_revision))} if owned else {}
    cycle = raids.cycle(stamp)
    key = date.fromisoformat(cycle.cycle_key)
    weekly_rows = {(r.character_id, r.raid_id): r for r in db.scalars(select(WeeklyState).where(
        WeeklyState.user_id == uid, WeeklyState.character_id.in_(selected_ids), WeeklyState.cycle_key == key))} if selected_ids else {}
    catalog = raids.catalog()
    bundles, entries = [], []
    for r in registrations:
        a = accounts.get(r.account_id)
        state = 'unverified' if a is None else 'owned' if a.owner_id == uid else 'ownership_lost'
        configuration = configs.get(a.id) if a and state == 'owned' else None
        active_ids = chosen[configuration.id] if configuration else []
        current = by_account[a.id] if a and state == 'owned' else []
        eligible = {c.id for c in current if activity_policy.eligible(stored, c)}
        settings = service.settings_value(a, configuration, active_ids, eligible)
        items = [lifecycle_reads.current_item(stored, uid, r, c, candidates=power[c.id], at=stamp) for c in current] if state == 'owned' else [
            lifecycle_reads.preview_item(stored, uid, r, row) for row in r.preview]
        rep = next((c for c in current if configuration and c.id == configuration.representative_id), None)
        rep_summary = dict(rep.summary, combat_power=next(i['combat_power'] for i in items if i['character_id'] == rep.id)) if rep else None
        registration = dict(registration_id=r.id, label=r.label, is_main=r.is_main, version=r.version,
            game_account_id=a.id if a else None, verification_status='verified' if a else 'unverified',
            ownership_status=state, ownership_revision=a.ownership_revision if a else None,
            roster_revision=a.roster_revision if a else None, settings=settings, representative_summary=rep_summary,
            character_count=len(current) if state == 'owned' else foreign_counts.get(a.id, 0) if a else len(r.preview),
            server_fetched_at=r.fetched_at)
        character_list = dict(registration_id=r.id, game_account_id=a.id if a else None, is_main=r.is_main,
            registration_version=r.version, ownership_status=state, ownership_revision=a.ownership_revision if a else None,
            roster_revision=a.roster_revision if a else r.version, settings=settings, items=items,
            next_cursor=None, server_fetched_at=r.fetched_at)
        personal, unavailable = [], []
        current_by_id = {c.id: c for c in current}
        for cid in active_ids:
            c = current_by_id.get(cid)
            claim = stored.get(NameClaim, (c.server_name, c.character_name)) if c else None
            reason = 'CHARACTER_UNUSABLE' if c is None else 'IDENTITY_CONFLICT' if not claim or claim.character_id != cid else None
            if reason:
                unavailable.append(dict(character_id=cid, code=reason))
                continue
            personal.append(profiles.output(stored, uid, a, c))
            # The existing 50-ID limit is a V1 request limit. Project all current
            # activities from this same snapshot, never call separate HTTP batches.
            entries.extend(weekly.entry(stored, a, c, raid, key, cycle, weekly_rows.get((cid, raid.raid_id))) for raid in catalog.raids)
        bundles.append(dict(registration=registration, characters=character_list,
            representative=representative.value(r, a, configuration) if state == 'owned' else None,
            presentation=presentation.output(r, a, displays.get(a.id)) if state == 'owned' else None,
            personal_profiles=personal, unavailable_characters=unavailable))
    return dict(server_now=stamp, complete=True, registrations=bundles,
        weekly_states=dict(current_cycle=cycle, cycle_key=cycle.cycle_key, catalog_version=catalog.catalog_version, entries=entries))


def get(principal):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        stamp = now(db)
        uid = authorize(db, principal)
        try:
            result = AccountBootstrap.model_validate(snapshot(db, uid, stamp))
        except ValidationError:
            fail('BOOTSTRAP_DATA_UNAVAILABLE', 503)
        payload = result.model_dump_json().encode('utf-8')
        if len(payload) > MAX_BYTES:
            fail('BOOTSTRAP_RESPONSE_TOO_LARGE')
        return payload
