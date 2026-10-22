"""Read-only group candidates and full-set validation before room pagination.

No provider calls, persistent tokens or personal-roster permission shortcuts.
Every query is scoped to the current group's members and runs in one snapshot.
"""
import hashlib
import hmac
import json
import re
from decimal import Decimal
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.auth.models import User
from app.core.config import settings
from app.game_accounts.models import Account, Registration, Configuration, Activity, Character, NameClaim
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.support import fail, cursor_encode, cursor_decode
from app.raid_rooms.queries import snapshot
from app.raid_rooms.search import filter_context
from app.raid_rooms.candidate_schemas import CandidatePage

MAX_RESPONSE_BYTES = 1024 * 1024


def mac(value):
    raw = json.dumps(jsonable_encoder(value), sort_keys=True, separators=(',', ':')).encode()
    return hmac.new(settings.recovery_key(), b'group-character-candidates-v1\0' + raw, hashlib.sha256).hexdigest()


def number(value):
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
        return None
    return value


def power(row, lifecycle):
    empty = dict(value=None, source='unavailable', trust=None, observed_at=None, saved_at=None,
                 power_revision=None, integrity_status=None)
    if row is None or row.source_summary.get('observed_lifecycle_revision') != lifecycle:
        return empty
    integrity = row.source_summary.get('integrity_status')
    if number(row.combat_power) is None or integrity not in ('clean', 'review', 'error', 'unavailable'):
        return empty
    return dict(value=row.combat_power, source='stored_role_success', trust='client_submitted',
                observed_at=row.observed_at, saved_at=row.source_saved_at,
                power_revision=row.power_revision, integrity_status=integrity)


def load(db, uid, sid, gid, stamp, context=None):
    """Return the full current candidate graph; page slicing happens afterwards."""
    ctx, mapping = context if context is not None else filter_context(db, uid, [gid], stamp)
    subjects = list(mapping.values())
    active = set(db.scalars(select(User.id).where(User.id.in_(subjects), User.status == 'active')))
    rows = list(db.execute(select(Registration, Account, Configuration, Character, NameClaim.revision)
        .join(Account, Account.id == Registration.account_id)
        .join(Configuration, (Configuration.account_id == Account.id) & (Configuration.user_id == Registration.user_id))
        .join(Activity, Activity.settings_id == Configuration.id)
        .join(Character, (Character.id == Activity.character_id) & (Character.account_id == Account.id))
        .join(NameClaim, (NameClaim.server_name == Character.server_name) &
              (NameClaim.character_name == Character.character_name) & (NameClaim.character_id == Character.id))
        .where(Registration.user_id.in_(active), Registration.deleted_at.is_(None),
            Account.owner_id == Registration.user_id, Account.verified_at.is_not(None),
            Configuration.ended_at.is_(None), Character.status == 'confirmed', Character.lifecycle_state == 'active')
        .order_by(Registration.user_id, Character.id))) if active else []
    ids = [c.id for _, _, _, c, _ in rows]
    successes = {(v.user_id, v.character_id, v.ownership_revision, v.role): v for v in db.scalars(
        select(RolePowerSuccess).where(RolePowerSuccess.user_id.in_(active), RolePowerSuccess.character_id.in_(ids)))} if ids else {}
    characters = {u: {} for u in active}
    evidence = []
    for reg, account, config, char, claim_revision in rows:
        level = number(char.summary.get('item_level'))
        characters[reg.user_id][char.id] = dict(character_id=char.id, server_name=char.server_name,
            character_name=char.character_name, class_name=char.summary.get('class_name'), role_family=None,
            item_level=level, item_level_source='stored_character_summary' if level is not None else 'unavailable',
            summary_fetched_at=char.fetched_at, ownership_revision=account.ownership_revision,
            lifecycle_revision=char.lifecycle_revision, ownership_state='owned', activity_state='selected', lifecycle_state='active',
            **{role: power(successes.get((reg.user_id, char.id, account.ownership_revision, role)), char.lifecycle_revision)
               for role in ('dealer', 'support')})
        evidence.append([reg.id, reg.version, account.id, account.ownership_revision, account.roster_revision,
                         config.id, config.version, char.id, char.lifecycle_revision, claim_revision])
    members = []
    for member in ctx['members']:
        subject = mapping[member['member_ref']]
        if subject not in active:
            continue
        values = list(characters[subject].values())
        values.sort(key=lambda c: (c['item_level'] is None, Decimal(c['item_level'] or '0').copy_negate(), str(c['character_id'])))
        members.append(dict(member_ref=member['member_ref'], alias=member['aliases'][0], display=member['display'], characters=values))
    members.sort(key=lambda m: str(m['alias']['group_membership_id']))
    token = mac(['snapshot', uid, sid, gid, ctx['scope_digest'], members, evidence])
    return ctx, members, token


def validate_search(db, uid, sid, gids, context, token, conditions, stamp):
    if len(gids) != 1:
        fail('INVALID_REQUEST', 400)
    _, members, current = load(db, uid, sid, gids[0], stamp, context)
    if not hmac.compare_digest(token, current):
        fail('GROUP_CHARACTER_CANDIDATES_STALE')
    candidates = {m['member_ref']: {c['character_id'] for c in m['characters']} for m in members}
    for condition in conditions:
        allowed = candidates.get(condition.member_ref)
        if (allowed is None or len(set(condition.character_ids)) != len(condition.character_ids)
                or not set(condition.character_ids) <= allowed):
            fail('INVALID_REQUEST', 400)


def get(principal, gid, context_token, limit=50, cursor=None):
    with snapshot(principal) as (db, uid, stamp):
        context = filter_context(db, uid, [gid], stamp)
        if not hmac.compare_digest(context[0]['filter_context_token'], context_token):
            fail('FILTER_CONTEXT_STALE')
        ctx, members, token = load(db, uid, principal[1].id, gid, stamp, context)
        binding = mac(['cursor', uid, principal[1].id, gid, ctx['scope_digest'], limit])
        offset = cursor_decode(cursor, binding, token) if cursor else 0
        logical = [(m, char) for m in members for char in (m['characters'] or [None])]
        if offset > len(logical):
            fail('INVALID_REQUEST', 400)
        selected = logical[offset:offset + limit]
        chunks = []
        for index, (member, char) in enumerate(selected, offset):
            ref = member['member_ref']
            if not chunks or chunks[-1]['member_ref'] != ref:
                chunks.append({k: member[k] for k in ('member_ref', 'alias', 'display')} | dict(
                    continues_from_previous=index > 0 and logical[index-1][0]['member_ref'] == ref,
                    continues_on_next=False, characters=[]))
            if char is not None:
                chunks[-1]['characters'].append(char)
            chunks[-1]['continues_on_next'] = index+1 < len(logical) and logical[index+1][0]['member_ref'] == ref
        following = offset + len(selected)
        next_cursor = cursor_encode(dict(scope=binding, revision=token, offset=following)) if following < len(logical) else None
        result = CandidatePage.model_validate(dict(group_id=gid, filter_context_token=ctx['filter_context_token'],
            scope_digest=ctx['scope_digest'], candidate_token=token, evaluated_at=stamp, groups=chunks,
            next_cursor=next_cursor)).model_dump(mode='json')
        if len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_RESPONSE_BYTES:
            fail('RESPONSE_TOO_LARGE', 413)
        return result
