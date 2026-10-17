import uuid
import time
from contextlib import nullcontext
from datetime import timedelta
from sqlalchemy import select, delete
from app.core.database import session, now
from app.game_accounts import observations, provider_diagnostics, ownership_policy
from app.lostark_keys import service as credentials
from app.lostark_keys import rate_limits
from app.game_accounts.models import ScopedRosterCache as MemberPreview, ScopedRosterLease as MemberFetch
from app.game_accounts import lifecycle, activity_policy, verification_context, verification_history, equipment_proof, owned_refresh, verification_targets
from app.game_accounts.models import (Account, Registration, Character, Configuration, Activity,
                                     Verification, Audit, PreviewCache, FetchLease, NameClaim)
from app.game_accounts.support import authorize, fail, quota, reserve, commit_result, release, cursor_encode, cursor_decode, GameError
from app.game_accounts.provider import ProviderUnavailable
from app.game_accounts.equipment import EquipmentItem, required_slots, compare_equipment, EquipmentIncomplete


def lookup(principal, snapshot, name, proof=False, cached=False, *, context='direct', guard=None, on_roster=None):
    context_key = lifecycle.digest(context)
    identity = snapshot.user_id, snapshot.version, context_key, name
    scope = f'fetch:{snapshot.user_id}:{snapshot.version}:{context_key}:{name}'
    def check_context(db):
        if guard:
            rid, expected = guard
            r = reg(db, principal[0].id, rid)
            if lifecycle.digest(lifecycle.registration_stamp(db, r)) != expected:
                fail('REVISION_CONFLICT')
    owner, generation = True, None
    with session() as db, db.begin():
        authorize(db, principal, write=True)
        credentials.check(db, principal, snapshot)
        check_context(db)
        if cached:
            c = db.get(MemberPreview, identity)
            if c and now(db) < c.fetched_at + timedelta(minutes=30):
                return observations.Observation(c.roster, c.fetched_at)
        if not proof:
            from app.game_accounts.support import lock
            lock(db, scope)
            lease = db.get(MemberFetch, identity)
            current = now(db)
            if lease and not lease.completed and current < lease.expires_at:
                owner, generation = False, lease.generation
            else:
                if lease is None:
                    lease = MemberFetch(user_id=snapshot.user_id, credential_version=snapshot.version, scope_key=context_key,
                                        name=name, generation=1, expires_at=current+timedelta(seconds=30))
                    db.add(lease)
                else:
                    lease.generation += 1
                    lease.expires_at = current+timedelta(seconds=30)
                    lease.completed, lease.roster, lease.fetched_at = False, None, None
                generation = lease.generation
    if not owner:
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            with session() as db, db.begin():
                authorize(db, principal, write=True)
                credentials.check(db, principal, snapshot)
                check_context(db)
                lease = db.get(MemberFetch, identity)
                if lease is None or lease.generation != generation:
                    fail('UPSTREAM_UNAVAILABLE',503)
                if lease.completed:
                    if lease.roster is None:
                        rate_limits.reject_wait(db, snapshot.fingerprint)
                        fail('UPSTREAM_UNAVAILABLE',503)
                    return observations.Observation(lease.roster,lease.fetched_at)
            time.sleep(0.05)
        fail('UPSTREAM_UNAVAILABLE',503)
    def before_call():
        credentials.before_call(principal,snapshot)
        if guard:
            with session() as db:
                authorize(db,principal)
                check_context(db)
    try:
        before_call()
        options = dict(token=snapshot.token, before_armory=before_call,
                       observer=rate_limits.observer(snapshot.fingerprint))
        if on_roster is not None:
            options['on_roster'] = on_roster
        result = observations.fetch(name, proof, **options)
        with session() as db, db.begin():
            authorize(db, principal, write=True)
            credentials.check(db, principal, snapshot)
            check_context(db)
            if not proof:
                from app.game_accounts.support import lock
                lock(db, scope)
                lease = db.get(MemberFetch, identity)
                if lease.generation != generation or now(db) >= lease.expires_at:
                    fail('UPSTREAM_UNAVAILABLE',503)
                lease.completed, lease.roster, lease.fetched_at = True, result.roster, result.fetched_at
                c = db.get(MemberPreview, identity)
                if c:
                    c.roster,c.fetched_at = result.roster,result.fetched_at
                else:
                    db.add(MemberPreview(user_id=snapshot.user_id, credential_version=snapshot.version, scope_key=context_key,
                                         name=name, roster=result.roster, fetched_at=result.fetched_at))
        return result
    except Exception as error:
        if not proof:
            with session() as db, db.begin():
                from app.game_accounts.support import lock
                lock(db, scope)
                lease = db.get(MemberFetch, identity)
                if lease and lease.generation == generation:
                    lease.completed,lease.roster = True,None
        # A changed key takes precedence over provider failure, without applying it.
        with session() as db, db.begin():
            authorize(db, principal, write=True)
            credentials.check(db, principal, snapshot)
        if isinstance(error, ProviderUnavailable):
            request_id = provider_diagnostics.record(error)
            if error.reason == 'UPSTREAM_RATE_LIMITED':
                with session() as db:
                    retry = rate_limits.metadata(db, snapshot.fingerprint, error.reason)
                rejected = GameError(error.reason, 503, retry['retry_after_seconds'], retry['retry_at'])
                rejected.request_id = request_id
                raise rejected
            rejected = GameError(error.reason if error.reason in ('LOSTARK_KEY_REJECTED', 'UPSTREAM_RATE_LIMITED') else 'UPSTREAM_UNAVAILABLE',
                                 409 if error.reason == 'LOSTARK_KEY_REJECTED' else 503)
            rejected.provider_not_found = error.http_status == 404
            rejected.request_id = request_id
            raise rejected
        raise


def reg(db, uid, rid):
    r = db.get(Registration, rid)
    if not r or r.user_id != uid or r.deleted_at:
        fail('REGISTRATION_NOT_FOUND', 404)
    return r


def ownership(db, uid, r):
    a = db.get(Account, r.account_id) if r.account_id else None
    return a, ('unverified' if a is None else 'owned' if a.owner_id == uid else 'ownership_lost')


def config(db, uid, aid):
    return db.scalar(select(Configuration).where(Configuration.user_id == uid, Configuration.account_id == aid, Configuration.ended_at.is_(None)))


def settings_out(db, uid, r):
    a, status = ownership(db, uid, r)
    c = config(db, uid, a.id) if a and status == 'owned' else None
    chosen = list(db.scalars(select(Activity.character_id).where(Activity.settings_id == c.id).order_by(Activity.character_id))) if c else []
    eligible = set(db.scalars(select(Character.id).where(Character.account_id == a.id, Character.status == 'confirmed'))) if c else set()
    eligible = {i for i in eligible if activity_policy.eligible(db, db.get(Character, i))}
    return dict(configuration_state=c.state if c else 'unconfigured', activity_character_ids=chosen,
                representative_character_id=c.representative_id if c else None, settings_version=c.version if c else 1,
                ownership_revision=a.ownership_revision if a else None, next_change_at=None,
                selection_complete=True, ineligible_character_ids=[i for i in chosen if i not in eligible])


def reg_out(db, uid, r):
    a, state = ownership(db, uid, r)
    count = len(list(db.scalars(select(Character.id).where(Character.account_id == a.id, Character.lifecycle_state != 'retired')))) if a else len(r.preview)
    conf = config(db,uid,a.id) if a and state=='owned' else None
    rep = db.get(Character,conf.representative_id) if conf and conf.representative_id else None
    representative = None
    if rep and rep.lifecycle_state != 'retired':
        from app.game_accounts.power_service import overlay
        representative = dict(rep.summary)
        representative['combat_power'] = overlay(db, uid, dict(rep.summary, power_fetched_at=rep.power_fetched_at), lifecycle.power_scope(r, rep))['combat_power']
    return dict(registration_id=r.id, label=r.label, is_main=r.is_main, version=r.version,
                game_account_id=a.id if a else None, verification_status='verified' if a else 'unverified',
                ownership_status=state, ownership_revision=a.ownership_revision if a else None,
                roster_revision=a.roster_revision if a else None, settings=settings_out(db, uid, r),
                representative_summary=representative, character_count=count, server_fetched_at=r.fetched_at)


def make_main(db, uid, r):
    for other in db.scalars(select(Registration).where(Registration.user_id == uid, Registration.is_main.is_(True), Registration.deleted_at.is_(None), Registration.id != r.id)):
        other.is_main = False
        other.version += 1
        other.updated_at = now(db)
    db.flush()
    r.is_main = True


def keys(rows):
    return {(r['server_name'], r['character_name']) for r in rows}


def existing_registration(db, uid, rows):
    for r in db.scalars(select(Registration).where(Registration.user_id == uid, Registration.deleted_at.is_(None))):
        if keys(r.preview) & keys(rows):
            return r
    return None


def create_registration(db, uid, name, label, main, obs):
    name = verification_context.resolve_input(name, obs.roster)
    if name is None:
        fail('UPSTREAM_INVALID_RESPONSE',503)
    if existing_registration(db, uid, obs.roster):
        fail('REGISTRATION_EXISTS')
    rows = list(db.scalars(select(Registration.id).where(Registration.user_id == uid, Registration.deleted_at.is_(None))))
    if len(rows) >= 20:
        fail('REGISTRATION_LIMIT', 400)
    current = now(db)
    r = Registration(user_id=uid, lookup_name=name, label=label, is_main=False, preview=obs.roster,
                     fetched_at=obs.fetched_at, created_at=current, updated_at=current)
    db.add(r)
    db.flush()
    if main:
        make_main(db, uid, r)
    return r


def preview(principal, data):
    quota('preview:'+str(principal[0].id), 30)
    snapshot = credentials.capture(principal)
    obs = lookup(principal, snapshot, data.character_name, cached=True)
    return dict(characters=[dict(row, combat_power=None) for row in obs.roster],
                server_fetched_at=obs.fetched_at, expires_at=obs.fetched_at+timedelta(minutes=30))


def registrations(principal, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        uid = authorize(db, principal)
        rows = list(db.scalars(select(Registration).where(Registration.user_id == uid, Registration.deleted_at.is_(None)).order_by(Registration.created_at, Registration.id)))
        revision = [(str(r.id), lifecycle.digest(lifecycle.registration_stamp(db,r)), settings_out(db,uid,r)['settings_version']) for r in rows]
        # JSON cursor converts tuples to arrays.
        revision = [list(v) for v in revision]
        scope = 'registrations:'+str(uid)
        offset = cursor_decode(cursor, scope, revision) if cursor else 0
        following = offset+limit
        return dict(items=[reg_out(db, uid, r) for r in rows[offset:following]],
                    next_cursor=cursor_encode(dict(scope=scope, revision=revision, offset=following)) if following < len(rows) else None)


def characters(principal, rid, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        uid = authorize(db, principal)
        r = reg(db, uid, rid)
        a, state = ownership(db, uid, r)
        scope = 'characters:'+str(uid)+':'+str(rid)
        revision = a.roster_revision if a else r.version
        cursor_revision = lifecycle.digest((lifecycle.registration_stamp(db,r),settings_out(db,uid,r)['settings_version']))
        offset = cursor_decode(cursor, scope, cursor_revision) if cursor else 0
        if a and state == 'owned':
            rows = list(db.scalars(select(Character).where(Character.account_id == a.id, Character.lifecycle_state != 'retired').order_by(Character.server_name, Character.character_name, Character.id)))
            scopes = [lifecycle.power_scope(r,c) for c in rows]
            items = [dict(**c.summary, character_id=c.id, roster_status=c.status, summary_fetched_at=c.fetched_at,
                          last_confirmed_at=c.confirmed_at, requires_refresh=c.status != 'confirmed', eligible=lifecycle.usable(db,c), power_stale=c.power_fetched_at is None or c.power_fetched_at<c.fetched_at, power_fetched_at=c.power_fetched_at) for c in rows]
        else:
            scopes = [lifecycle.power_scope(r) for _ in r.preview]
            items = [dict(**v, character_id=None, roster_status='preview', summary_fetched_at=r.fetched_at,
                          last_confirmed_at=None, requires_refresh=True, eligible=False, power_stale=True, power_fetched_at=None) for v in r.preview]
        from app.game_accounts.power_service import overlay
        for item, cache_scope in zip(items, scopes):
            item.update(overlay(db, uid, item, cache_scope))
        following = offset+limit
        return dict(characters=dict(items=items[offset:following], next_cursor=cursor_encode(dict(scope=scope,revision=cursor_revision,offset=following)) if following<len(items) else None),
                    settings=settings_out(db, uid, r), ownership_status=state, roster_revision=revision, server_fetched_at=r.fetched_at)


def replay_access(principal, operation, rid):
    if rid is None or operation == 'delete':
        return
    with session() as db:
        uid = authorize(db, principal)
        if operation in ('confirm', 'cancel'):
            v = db.get(Verification, rid)
            if not v or v.actor_id != uid:
                fail('VERIFICATION_NOT_FOUND',404)
            retained(v,now(db))
        else:
            r = reg(db, uid, rid)
            owned = ownership(db, uid, r)[1] == 'owned'
            if operation == 'settings' and not owned:
                fail('OWNERSHIP_REQUIRED',403)
            return owned


def mutate(principal, operation, key, payload, rid=None):
    if operation == 'start':
        payload = verification_targets.normalize(payload)
    ticket, replay = reserve(principal, operation, key, {'target':str(rid) if rid else None, 'body':payload})
    if replay:
        owned = replay_access(principal, operation, rid)
        if not owned and operation in ('patch', 'refresh'):
            result = dict(replay[1])
            if operation == 'refresh':
                result['registration'] = dict(result['registration'], representative_summary=None)
            else:
                result['representative_summary'] = None
            return replay[0], result
        if operation == 'settings':
            # Old saved successes can predate cooldown removal. Do not rewrite
            # their state or version; only retire the obsolete timer in the DTO.
            return replay[0], dict(replay[1], next_change_at=None)
        return replay
    try:
        if operation in verification_history.OPERATIONS:
            verification_history.begin(principal, ticket, operation, payload, rid)
        obs = None
        snapshot = None
        baseline_revision = None
        guard = None
        owned_scope = None
        registration_links = None
        context = operation + ":" + str(key)
        if operation == 'register':
            with session() as db:
                registration_links = ownership_policy.links_stamp(db, authorize(db, principal))
            snapshot = credentials.capture(principal)
            obs = lookup(principal, snapshot, payload['lookup_character_name'], context=context)
        elif operation in ('refresh','start','confirm'):
            with session() as db:
                uid = authorize(db, principal)
                if operation == 'refresh':
                    r = reg(db, uid, rid)
                    name, baseline_revision = r.lookup_name, r.version
                elif operation == 'start':
                    if payload['source'] == 'registration':
                        r = reg(db, uid, uuid.UUID(payload['registration_id']))
                        ownership_policy.reject_linked(db, uid, r)
                        name, baseline_revision = verification_targets.selected(db, uid, r, payload), r.version
                    else:
                        name = payload['character_name']
                else:
                    v = db.get(Verification, rid)
                    if not v or v.actor_id != uid:
                        fail('VERIFICATION_NOT_FOUND',404)
                    retained(v,now(db))
                    name = v.lookup_name
                    if v.status == 'pending' and now(db) < v.expires_at and v.registration_id:
                        ownership_policy.reject_linked(db, uid, reg(db, uid, v.registration_id))
                    # Terminal/expired challenges never call the provider.
                    if v.status != 'pending' or now(db) >= v.expires_at:
                        name = None
            with session() as db:
                if operation in ('refresh', 'start') and (operation == 'refresh' or payload['source'] == 'registration'):
                    target = rid if operation == 'refresh' else uuid.UUID(payload['registration_id'])
                    r = reg(db, authorize(db,principal), target)
                    guard = (target, lifecycle.digest(lifecycle.registration_stamp(db,r)))
                    if operation == 'refresh':
                        owned_scope = owned_refresh.capture(db, principal[0].id, r)
                elif operation == 'confirm':
                    v = db.get(Verification,rid)
                    if v and v.registration_id:
                        r = reg(db,authorize(db,principal),v.registration_id)
                        guard = (r.id,lifecycle.digest(lifecycle.registration_stamp(db,r)))
                if guard:
                    context = list(map(str,guard))
            if operation == 'refresh':
                quota('manual:'+str(principal[0].id)+':'+str(rid),1,10)
            elif operation == 'start':
                quota('start:'+str(principal[0].id),3)
            elif name:
                quota('confirm-user:'+str(principal[0].id),12)
                quota('confirm:'+str(rid),1,5)
            if name:
                snapshot = credentials.capture(principal)
                if operation=='confirm':
                    with session() as db:
                        v=db.get(Verification,rid)
                        if v.identity_snapshot is None: fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
                        if v.identity_snapshot.get('credential_version')!=snapshot.version: fail('LOSTARK_KEY_CHANGED')
                if owned_scope is not None:
                    obs = owned_refresh.fetch(principal, snapshot, name, owned_scope, context=context, guard=guard)
                else:
                    def check_roster(rows):
                        with session() as db:
                            uid = authorize(db, principal)
                            credentials.check(db, principal, snapshot)
                            if guard and lifecycle.digest(lifecycle.registration_stamp(db, reg(db,uid,guard[0]))) != guard[1]:
                                fail('REVISION_CONFLICT')
                            ownership_policy.reject_observed(db, uid, rows)
                    obs = lookup(principal, snapshot, name, proof=operation != 'refresh', context=context,
                                 guard=guard, on_roster=check_roster if operation in ('start', 'confirm') else None)
                if operation in verification_history.OPERATIONS:
                    verification_history.observed(principal, ticket, obs)
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            if snapshot is not None:
                credentials.check(db, principal, snapshot)
            if registration_links is not None and registration_links != ownership_policy.links_stamp(db, uid):
                fail('REVISION_CONFLICT')
            if guard and lifecycle.digest(lifecycle.registration_stamp(db, reg(db,uid,guard[0]))) != guard[1]:
                fail('REVISION_CONFLICT')
            confirmation_was_pending = (operation == 'confirm' and
                (challenge := db.get(Verification, rid)) is not None and challenge.status == 'pending')
            with (db.begin_nested() if operation == 'confirm' else nullcontext()) as attempt:
                status, result = apply(db, uid, operation, payload, rid, obs, baseline_revision, snapshot.version if snapshot else None)
                if operation == 'confirm':
                    db.flush()
                expired = (confirmation_was_pending and obs is not None and status == 200
                           and (result.get('status') == 'verified' or result.get('result_code') == 'ACCOUNT_BINDING_EVIDENCE_PENDING')
                           and now(db) >= db.get(Verification, rid).expires_at)
                if expired:
                    # Undo *all* ownership/registration/character/audit writes.
                    attempt.rollback()
            if expired:
                v = db.get(Verification, rid)
                v.status, v.terminal_at = 'expired', now(db)
                v.attempt_count += 1
                v.last_checked_at = v.terminal_at
                status, result = 409, {'error': dict(code='VERIFICATION_EXPIRED', message='Challenge is terminal', request_id=str(uuid.uuid4()))}
            response = commit_result(db, ticket, status, result)
            if operation in verification_history.OPERATIONS:
                verification_history.complete(db, ticket, *response)
            return response
    except Exception as error:
        if operation in verification_history.OPERATIONS:
            verification_history.failed(ticket, error)
        release(ticket)
        raise


def reconcile(db, a, obs, *, fresh=False, owned=False):
    if not fresh and not owned:
        lifecycle.validate_binding(db,a,obs.binding)
    existing = {(c.server_name,c.character_name):c for c in db.scalars(select(Character).where(
        Character.account_id==a.id,Character.lifecycle_state!='retired'))}
    if len(set(existing) | keys(obs.roster)) > 200:
        fail('CHARACTER_LIMIT',400)
    additions, suspects = 0, 0
    for row in obs.roster:
        k = row['server_name'],row['character_name']
        c = existing.pop(k,None)
        if c:
            claim=db.get(NameClaim,k)
            if not claim or claim.character_id!=c.id: fail('IDENTITY_CONFLICT')
            if not lifecycle.usable(db,c):
                if not owned and (not obs.binding or str(c.id) not in obs.binding.continuity_ids):
                    suspects+=1
                    continue
                c.lifecycle_revision+=1
            summary=dict(row)
            if summary.get('combat_power') is not None: c.power_fetched_at=obs.fetched_at
            else: summary['combat_power']=c.summary.get('combat_power')
            c.summary,c.status,c.lifecycle_state=summary,'confirmed','active'
            c.fetched_at,c.confirmed_at=obs.fetched_at,obs.fetched_at
        else:
            if db.get(NameClaim,k): fail('IDENTITY_CONFLICT')
            c=Character(account_id=a.id,server_name=k[0],character_name=k[1],summary=row,
                        fetched_at=obs.fetched_at,confirmed_at=obs.fetched_at,
                        power_fetched_at=obs.fetched_at if row.get('combat_power') is not None else None)
            db.add(c); db.flush()
            db.add(NameClaim(server_name=k[0],character_name=k[1],character_id=c.id))
            additions+=1
    for c in existing.values():
        # Absence is suspect only. No live retirement/claim release path here.
        if c.status=='confirmed' and c.lifecycle_state=='active': c.lifecycle_revision+=1
        c.status,c.lifecycle_state,c.fetched_at='suspect','suspect',obs.fetched_at
        suspects+=1
    a.roster_revision+=1
    db.flush()
    bad={c.id for c in db.scalars(select(Character).where(Character.account_id==a.id)) if not activity_policy.eligible(db,c)}
    for conf in db.scalars(select(Configuration).where(Configuration.account_id==a.id,Configuration.ended_at.is_(None))):
        selected=set(db.scalars(select(Activity.character_id).where(Activity.settings_id==conf.id)))
        if selected & bad and conf.state!='needs_reconfiguration':
            conf.state='needs_reconfiguration'; conf.version+=1
    return additions,suspects


def retained(v, current):
    terminal = v.terminal_at or (v.expires_at if current >= v.expires_at else None)
    if terminal and current >= terminal+timedelta(hours=24):
        fail('VERIFICATION_NOT_FOUND',404)


def verification_out(v, current, code=None):
    status = 'expired' if v.status=='pending' and current>=v.expires_at else v.status
    result = v.result or {}
    persisted_code = result.get('pending_code') if status=='pending' else None
    return dict(challenge_id=v.id,status=status,required_slots=v.slots,expires_at=v.expires_at,
                remaining_seconds=max(0,int((v.expires_at-current).total_seconds())) if status=='pending' else 0,
                result_code=code if code is not None else persisted_code, result_reference=result.get('result_reference'),registration_id=result.get('registration_id') or v.registration_id)


def verification(principal, vid):
    with session() as db:
        uid = authorize(db,principal)
        v = db.get(Verification,vid)
        if not v or v.actor_id != uid:
            fail('VERIFICATION_NOT_FOUND',404)
        current=now(db)
        retained(v,current)
        return verification_out(v,current)


def apply(db, uid, op, data, rid, obs, baseline_revision, credential_version=None):
    current = now(db)
    if op == 'register':
        restored = ownership_policy.restore(db, uid, obs.roster)
        r = create_registration(db,uid,data['lookup_character_name'],data['label'],data['is_main'],obs)
        if restored:
            r.account_id = restored.id
            if config(db, uid, restored.id) is None:
                db.add(Configuration(user_id=uid, account_id=restored.id))
            db.flush()
        return 201,reg_out(db,uid,r)
    if op in ('patch','delete','refresh','settings'):
        r = reg(db,uid,rid)
        if op in ('patch','delete') and r.version != data['expected_version']:
            fail('REVISION_CONFLICT')
        if op == 'patch':
            if data.get('is_main'):
                make_main(db,uid,r)
            elif 'is_main' in data:
                r.is_main=False
            if 'label' in data:
                r.label=data['label']
            r.version += 1
            r.updated_at=current
            return 200,reg_out(db,uid,r)
        if op == 'delete':
            r.deleted_at,r.is_main=current,False
            r.version += 1
            if r.account_id:
                c = config(db,uid,r.account_id)
                if c:
                    c.ended_at=current
            return 204,None
        a,state=ownership(db,uid,r)
        if op == 'refresh':
            if r.version != baseline_revision:
                fail('REVISION_CONFLICT')
            # Refresh never silently attaches or transfers a canonical account.
            added,suspects=0,0
            if a and state=='owned':
                owned_refresh.validate(db, uid, r, obs)
                added,suspects=reconcile(db,a,obs,owned=True)
                r.lookup_name = obs.owned_observation.target[1]
            r.preview,r.fetched_at=obs.roster,obs.fetched_at
            r.version+=1
            return 200,dict(registration=reg_out(db,uid,r),added_count=added,suspect_count=suspects,requires_refresh=bool(suspects))
        if state!='owned':
            fail('OWNERSHIP_REQUIRED',403)
        c=config(db,uid,a.id)
        if c is None:
            c=Configuration(user_id=uid,account_id=a.id)
            db.add(c); db.flush()
        if (c.version!=data['expected_settings_version'] or a.ownership_revision!=data['expected_ownership_revision'] or a.roster_revision!=data['expected_roster_revision']):
            fail('REVISION_CONFLICT')
        selected=[uuid.UUID(i) for i in data['activity_character_ids']]
        representative=uuid.UUID(data['representative_character_id']) if data['representative_character_id'] else None
        if not selected:
            fail('EMPTY_ACTIVITY_SELECTION',400)
        if len(set(selected))!=len(selected):
            fail('INVALID_REQUEST',400)
        if representative not in selected:
            fail('REPRESENTATIVE_REQUIRED',400)
        valid={c.id for c in db.scalars(select(Character).where(Character.account_id==a.id)) if lifecycle.usable(db,c)}
        if not set(selected)<=valid:
            fail('CHARACTER_NOT_FOUND',404)
        for character_id in selected:
            activity_policy.require_eligible(db, db.get(Character, character_id))
        previous=set(db.scalars(select(Activity.character_id).where(Activity.settings_id==c.id)))
        c.next_change_at=None
        if previous!=set(selected) or c.representative_id!=representative or c.state!='configured':
            db.execute(delete(Activity).where(Activity.settings_id==c.id))
            db.add_all([Activity(settings_id=c.id,account_id=a.id,character_id=i) for i in selected])
            c.representative_id,c.state=representative,'configured'
            c.version+=1
        db.flush()
        return 200,settings_out(db,uid,r)
    if op=='start':
        r=reg(db,uid,uuid.UUID(data['registration_id'])) if data['source']=='registration' else existing_registration(db,uid,obs.roster)
        if data['source']=='registration':
            ownership_policy.reject_linked(db, uid, r)
        ownership_policy.reject_observed(db, uid, obs.roster)
        if data['source']=='registration' and r.version!=baseline_revision:
            fail('REVISION_CONFLICT')
        try:
            slots=required_slots(obs.equipment or {})
        except EquipmentIncomplete:
            fail('EQUIPMENT_INCOMPLETE',400)
        lookup_name=verification_targets.selected(db,uid,r,data) if data['source']=='registration' else data['character_name']
        lookup_name=verification_context.resolve_input(lookup_name,obs.roster)
        proof_context=verification_context.capture(lookup_name,obs.roster)
        if proof_context is None:
            fail('UPSTREAM_INVALID_RESPONSE',503)
        target=data.get('target_character')
        if target and proof_context['target'] != [target['server_name'],target['character_name']]:
            fail('IDENTITY_CONFLICT')
        mode='legacy'
        if obs.binding is not None:
            candidate=canonical_candidate(db,obs.roster,obs.binding)
        else:
            candidate=verification_targets.owned_candidate(db,uid,r,proof_context,obs.roster) if data['source']=='registration' else None
            if candidate:
                mode='owned_registration'
            else:
                mode='pending' if any(db.get(NameClaim,k) for k in keys(obs.roster)) or (r and r.account_id) else 'fresh'
        v=Verification(actor_id=uid,registration_id=r.id if r else None,lookup_name=lookup_name,
                       candidate_id=candidate.id if candidate else None,revision=candidate.ownership_revision if candidate else None,
                       roster=obs.roster,baseline={k:dict(name=e.name,grade=e.grade) for k,e in obs.equipment.items()},
                       slots=list(slots),identity_snapshot={'registration':lifecycle.digest(lifecycle.registration_stamp(db,r)) if r else None,
                           'account':lifecycle.digest(lifecycle.account_stamp(db,candidate)) if candidate else None,
                           'credential_version':credential_version,'proof_context':proof_context,
                           'binding_mode':mode,'claim_snapshot':verification_targets.claims(db,obs.roster),
                           'server_equipment_baseline':equipment_proof.baseline(obs,lookup_name,current)},
                       created_at=current,expires_at=current+timedelta(minutes=10))
        db.add(v); db.flush()
        return 201,verification_out(v,current)
    v=db.get(Verification,rid)
    if not v or v.actor_id!=uid:
        fail('VERIFICATION_NOT_FOUND',404)
    retained(v,current)
    if v.status=='pending' and current>=v.expires_at:
        v.status,v.terminal_at='expired',current
    if op=='cancel':
        if v.status=='pending':
            v.status,v.terminal_at='cancelled',current
        return 204,None
    if v.status=='verified':
        return 200,verification_out(v,current)
    if v.status!='pending':
        # Terminal outcome commits together with dedup and cannot run proof.
        return 409,{'error':dict(code='VERIFICATION_'+v.status.upper(),message='Challenge is terminal',request_id=str(uuid.uuid4()))}
    if obs is not None:
        ownership_policy.reject_observed(db, uid, obs.roster)
    if v.identity_snapshot is None:
        fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
    if v.identity_snapshot.get('credential_version') != credential_version:
        fail('LOSTARK_KEY_CHANGED')
    source = reg(db,uid,v.registration_id) if v.registration_id else None
    if source and v.identity_snapshot['registration'] != lifecycle.digest(lifecycle.registration_stamp(db,source)):
        fail('REVISION_CONFLICT')
    if v.candidate_id:
        candidate=db.get(Account,v.candidate_id)
        if candidate is None or v.identity_snapshot['account']!=lifecycle.digest(lifecycle.account_stamp(db,candidate)):
            fail('REVISION_CONFLICT')
    v.attempt_count+=1; v.last_checked_at=current
    baseline={k:EquipmentItem(**e) for k,e in v.baseline.items()}
    if obs is None or obs.equipment is None:
        fail('UPSTREAM_UNAVAILABLE',503)
    code=compare_equipment(baseline,tuple(v.slots),obs.equipment)
    if code!='EQUIPMENT_MATCHED':
        return 200,verification_out(v,current,code)
    pending=verification_context.pending_code(v.identity_snapshot,v.lookup_name,obs.roster)
    if pending:
        return 200,verification_out(v,current,pending)
    if not equipment_proof.validated(v,obs,current):
        return 200,verification_out(v,current,'PROVIDER_EVIDENCE_PENDING')
    mode=v.identity_snapshot.get('binding_mode','legacy')
    saved_claims=v.identity_snapshot.get('claim_snapshot')
    if saved_claims is not None and saved_claims != verification_targets.claims(db,obs.roster):
        fail('REVISION_CONFLICT')
    if mode=='pending':
        v.result={'pending_code':'ACCOUNT_BINDING_EVIDENCE_PENDING'}
        v.identity_snapshot=dict(v.identity_snapshot,equipment_control_verified_at=current.isoformat())
        return 200,verification_out(v,current,'ACCOUNT_BINDING_EVIDENCE_PENDING')
    if mode=='owned_registration':
        candidate=verification_targets.owned_candidate(db,uid,source,v.identity_snapshot['proof_context'],obs.roster)
        if candidate is None: fail('REVISION_CONFLICT')
    else:
        candidate=canonical_candidate(db,obs.roster,obs.binding)
    if (candidate.id if candidate else None)!=v.candidate_id or (candidate.ownership_revision if candidate else None)!=v.revision:
        fail('REVISION_CONFLICT')
    if v.registration_id:
        source_registration=reg(db,uid,v.registration_id)
        if source_registration.account_id and (candidate is None or candidate.id!=source_registration.account_id):
            fail('IDENTITY_CONFLICT')
    if candidate and mode!='owned_registration':
        current_keys={(c.server_name,c.character_name) for c in db.scalars(select(Character).where(Character.account_id==candidate.id,Character.lifecycle_state!='retired'))}
        if not current_keys<=keys(obs.roster) and not obs.disappearance_validated:
            return 200,verification_out(v,current,'ROSTER_EVIDENCE_PENDING')
    r=reg(db,uid,v.registration_id) if v.registration_id else existing_registration(db,uid,obs.roster)
    if r is None:
        r=create_registration(db,uid,v.lookup_name,v.lookup_name[:40],False,obs)
    a=candidate
    if a is None:
        a=Account(owner_id=uid,verified_at=current)
        db.add(a); db.flush()
    previous=a.owner_id if candidate else None
    if candidate and previous!=uid:
        a.owner_id=uid; a.ownership_revision+=1
        for old in db.scalars(select(Configuration).where(Configuration.account_id==a.id,Configuration.ended_at.is_(None))):
            old.ended_at=current
    duplicate=db.scalar(select(Registration).where(Registration.user_id==uid,Registration.account_id==a.id,Registration.deleted_at.is_(None),Registration.id!=r.id))
    if duplicate:
        fail('REGISTRATION_EXISTS')
    if candidate and previous!=uid:
        from dataclasses import replace
        obs=replace(obs,binding=lifecycle.evidence(db,a,continuity_ids=obs.binding.continuity_ids,complete=obs.binding.complete))
    reconcile(db,a,obs,fresh=candidate is None,owned=mode=='owned_registration')
    a.verified_at=current
    r.account_id,r.preview,r.fetched_at=a.id,obs.roster,obs.fetched_at
    r.version+=1
    if config(db,uid,a.id) is None:
        db.add(Configuration(user_id=uid,account_id=a.id))
    audit=Audit(account_id=a.id,challenge_id=v.id,previous_owner=previous,new_owner=uid,revision=a.ownership_revision,created_at=current)
    db.add(audit); db.flush()
    v.status,v.terminal_at='verified',current
    v.registration_id=r.id
    v.result=dict(result_reference=str(audit.id),registration_id=str(r.id))
    return 200,verification_out(v,current)


def canonical_candidate(db, rows, evidence=None):
    # Names identify conflicts, never authority or account continuity.
    claims=[db.get(NameClaim,(row['server_name'],row['character_name'])) for row in rows]
    if evidence is None:
        if any(claims): fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
        return None
    if type(evidence) is not lifecycle.BindingEvidence: fail('ACCOUNT_BINDING_EVIDENCE_PENDING')
    account=db.get(Account,uuid.UUID(evidence.account_id))
    if account is None: fail('IDENTITY_CONFLICT')
    lifecycle.validate_binding(db,account,evidence)
    for claim in claims:
        if claim and db.get(Character,claim.character_id).account_id!=account.id:
            fail('IDENTITY_CONFLICT')
    return account
