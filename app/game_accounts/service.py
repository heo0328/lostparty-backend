import uuid
import time
from datetime import timedelta
from sqlalchemy import select, delete
from app.core.database import session, now
from app.game_accounts import observations
from app.game_accounts.models import (Account, Registration, Character, Configuration, Activity,
                                     Verification, Audit, PreviewCache, FetchLease)
from app.game_accounts.support import authorize, fail, quota, reserve, commit_result, release, cursor_encode, cursor_decode
from app.game_accounts.provider import ProviderUnavailable
from app.game_accounts.equipment import EquipmentItem, required_slots, compare_equipment, EquipmentIncomplete


def lookup(name, proof=False, cached=False):
    # Equipment proof is always fetched independently; summaries can share an
    # already running fresh request without holding DB locks over the network.
    if cached:
        with session() as db:
            c = db.get(PreviewCache, name)
            if c and now(db) < c.fetched_at+timedelta(minutes=30):
                return observations.Observation(c.roster, c.fetched_at)
    owner, generation = True, None
    if not proof:
        from app.game_accounts.support import lock
        with session() as db, db.begin():
            lock(db, 'fetch:'+name)
            lease = db.get(FetchLease, name)
            current = now(db)
            if lease and not lease.completed and current < lease.expires_at:
                owner, generation = False, lease.generation
            else:
                if lease is None:
                    lease = FetchLease(name=name, generation=1, expires_at=current+timedelta(seconds=30))
                    db.add(lease)
                else:
                    lease.generation += 1
                    lease.expires_at = current+timedelta(seconds=30)
                    lease.completed, lease.roster, lease.fetched_at = False, None, None
                generation = lease.generation
    if not owner:
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            with session() as db:
                lease = db.get(FetchLease, name)
                if lease is None or lease.generation != generation:
                    fail('UPSTREAM_UNAVAILABLE',503)
                if lease.completed:
                    if lease.roster is None:
                        fail('UPSTREAM_UNAVAILABLE',503)
                    return observations.Observation(lease.roster,lease.fetched_at)
            time.sleep(0.05)
        fail('UPSTREAM_UNAVAILABLE',503)
    try:
        quota('provider-global', 80)
        if proof:
            quota('provider-global', 80)
        result = observations.fetch(name, proof)
        if not proof:
            with session() as db, db.begin():
                from app.game_accounts.support import lock
                lock(db, 'fetch:'+name)
                lease = db.get(FetchLease, name)
                if lease.generation != generation or now(db) >= lease.expires_at:
                    fail('UPSTREAM_UNAVAILABLE',503)
                lease.completed, lease.roster, lease.fetched_at = True, result.roster, result.fetched_at
                c = db.get(PreviewCache,name)
                if c:
                    c.roster,c.fetched_at = result.roster,result.fetched_at
                else:
                    db.add(PreviewCache(name=name,roster=result.roster,fetched_at=result.fetched_at))
        return result
    except Exception as error:
        if not proof:
            with session() as db, db.begin():
                from app.game_accounts.support import lock
                lock(db, 'fetch:'+name)
                lease = db.get(FetchLease,name)
                if lease and lease.generation == generation:
                    lease.completed,lease.roster = True,None
        if isinstance(error,ProviderUnavailable):
            fail('UPSTREAM_UNAVAILABLE',503)
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
    return dict(configuration_state=c.state if c else 'unconfigured', activity_character_ids=chosen,
                representative_character_id=c.representative_id if c else None, settings_version=c.version if c else 1,
                ownership_revision=a.ownership_revision if a else None, next_change_at=c.next_change_at if c else None,
                selection_complete=True, ineligible_character_ids=[i for i in chosen if i not in eligible])


def reg_out(db, uid, r):
    a, state = ownership(db, uid, r)
    count = len(list(db.scalars(select(Character.id).where(Character.account_id == a.id)))) if a else len(r.preview)
    conf = config(db,uid,a.id) if a and state=='owned' else None
    rep = db.get(Character,conf.representative_id) if conf and conf.representative_id else None
    representative = None
    if rep:
        from app.game_accounts.power_service import overlay
        representative = dict(rep.summary)
        representative['combat_power'] = overlay(db, uid, dict(rep.summary, power_fetched_at=rep.power_fetched_at))['combat_power']
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
    obs = lookup(data.character_name, cached=True)
    return dict(characters=obs.roster, server_fetched_at=obs.fetched_at, expires_at=obs.fetched_at+timedelta(minutes=30))


def registrations(principal, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        uid = authorize(db, principal)
        rows = list(db.scalars(select(Registration).where(Registration.user_id == uid, Registration.deleted_at.is_(None)).order_by(Registration.created_at, Registration.id)))
        revision = [(str(r.id), r.version) for r in rows]
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
        offset = cursor_decode(cursor, scope, revision) if cursor else 0
        if a and state == 'owned':
            rows = list(db.scalars(select(Character).where(Character.account_id == a.id).order_by(Character.server_name, Character.character_name, Character.id)))
            items = [dict(**c.summary, character_id=c.id, roster_status=c.status, summary_fetched_at=c.fetched_at,
                          last_confirmed_at=c.confirmed_at, requires_refresh=c.status != 'confirmed', eligible=c.status == 'confirmed', power_stale=c.power_fetched_at is None or c.power_fetched_at<c.fetched_at, power_fetched_at=c.power_fetched_at) for c in rows]
        else:
            items = [dict(**v, character_id=None, roster_status='preview', summary_fetched_at=r.fetched_at,
                          last_confirmed_at=None, requires_refresh=True, eligible=False, power_stale=True, power_fetched_at=None) for v in r.preview]
        from app.game_accounts.power_service import overlay
        for item in items:
            item.update(overlay(db, uid, item))
        following = offset+limit
        return dict(characters=dict(items=items[offset:following], next_cursor=cursor_encode(dict(scope=scope,revision=revision,offset=following)) if following<len(items) else None),
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
            if operation == 'settings' and ownership(db, uid, r)[1] != 'owned':
                fail('OWNERSHIP_REQUIRED',403)


def mutate(principal, operation, key, payload, rid=None):
    ticket, replay = reserve(principal, operation, key, {'target':str(rid) if rid else None, 'body':payload})
    if replay:
        replay_access(principal, operation, rid)
        return replay
    try:
        obs = None
        baseline_revision = None
        if operation == 'register':
            obs = lookup(payload['lookup_character_name'])
        elif operation in ('refresh','start','confirm'):
            with session() as db:
                uid = authorize(db, principal)
                if operation == 'refresh':
                    r = reg(db, uid, rid)
                    name, baseline_revision = r.lookup_name, r.version
                elif operation == 'start':
                    if payload['source'] == 'registration':
                        r = reg(db, uid, uuid.UUID(payload['registration_id']))
                        name, baseline_revision = r.lookup_name, r.version
                    else:
                        name = payload['character_name']
                else:
                    v = db.get(Verification, rid)
                    if not v or v.actor_id != uid:
                        fail('VERIFICATION_NOT_FOUND',404)
                    retained(v,now(db))
                    name = v.lookup_name
                    # Terminal/expired challenges never call the provider.
                    if v.status != 'pending' or now(db) >= v.expires_at:
                        name = None
            if operation == 'refresh':
                quota('manual:'+str(principal[0].id)+':'+str(rid),1,10)
            elif operation == 'start':
                quota('start:'+str(principal[0].id),3)
            elif name:
                quota('confirm-user:'+str(principal[0].id),12)
                quota('confirm:'+str(rid),1,5)
            if name:
                obs = lookup(name, proof=operation != 'refresh')
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            status, result = apply(db, uid, operation, payload, rid, obs, baseline_revision)
            return commit_result(db, ticket, status, result)
    except Exception:
        release(ticket)
        raise


def reconcile(db, a, obs):
    existing = { (c.server_name,c.character_name):c for c in db.scalars(select(Character).where(Character.account_id==a.id)) }
    if len(set(existing) | keys(obs.roster)) > 200:
        fail('CHARACTER_LIMIT', 400)
    additions, suspects = 0, 0
    for row in obs.roster:
        k = row['server_name'],row['character_name']
        c = existing.pop(k,None)
        if c:
            summary = dict(row)
            if summary.get('combat_power') is not None:
                c.power_fetched_at=obs.fetched_at
            if summary.get('combat_power') is None:
                summary['combat_power'] = c.summary.get('combat_power')
            c.summary, c.status, c.fetched_at, c.confirmed_at = summary,'confirmed',obs.fetched_at,obs.fetched_at
        else:
            other = db.scalar(select(Character).where(Character.server_name==k[0],Character.character_name==k[1]))
            if other:
                fail('IDENTITY_CONFLICT')
            c = Character(account_id=a.id, server_name=k[0], character_name=k[1], summary=row,
                          fetched_at=obs.fetched_at, confirmed_at=obs.fetched_at, power_fetched_at=obs.fetched_at if row.get('combat_power') is not None else None)
            db.add(c)
            additions += 1
    for c in existing.values():
        c.status = 'missing' if obs.disappearance_validated else 'suspect'
        c.fetched_at = obs.fetched_at
        suspects += 1
    a.roster_revision += 1
    db.flush()
    bad = {c.id for c in db.scalars(select(Character).where(Character.account_id==a.id,Character.status!='confirmed'))}
    for conf in db.scalars(select(Configuration).where(Configuration.account_id==a.id,Configuration.ended_at.is_(None))):
        selected = set(db.scalars(select(Activity.character_id).where(Activity.settings_id==conf.id)))
        if selected & bad and conf.state != 'needs_reconfiguration':
            conf.state = 'needs_reconfiguration'
            conf.version += 1
    return additions, suspects


def retained(v, current):
    terminal = v.terminal_at or (v.expires_at if current >= v.expires_at else None)
    if terminal and current >= terminal+timedelta(hours=24):
        fail('VERIFICATION_NOT_FOUND',404)


def verification_out(v, current, code=None):
    status = 'expired' if v.status=='pending' and current>=v.expires_at else v.status
    result = v.result or {}
    return dict(challenge_id=v.id,status=status,required_slots=v.slots,expires_at=v.expires_at,
                remaining_seconds=max(0,int((v.expires_at-current).total_seconds())) if status=='pending' else 0,
                result_code=code, result_reference=result.get('result_reference'),registration_id=result.get('registration_id') or v.registration_id)


def verification(principal, vid):
    with session() as db:
        uid = authorize(db,principal)
        v = db.get(Verification,vid)
        if not v or v.actor_id != uid:
            fail('VERIFICATION_NOT_FOUND',404)
        current=now(db)
        retained(v,current)
        return verification_out(v,current)


def apply(db, uid, op, data, rid, obs, baseline_revision):
    current = now(db)
    if op == 'register':
        r = create_registration(db,uid,data['lookup_character_name'],data['label'],data['is_main'],obs)
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
                added,suspects=reconcile(db,a,obs)
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
        valid=set(db.scalars(select(Character.id).where(Character.account_id==a.id,Character.status=='confirmed')))
        if not set(selected)<=valid:
            fail('CHARACTER_NOT_FOUND',404)
        previous=set(db.scalars(select(Activity.character_id).where(Activity.settings_id==c.id)))
        if c.representative_id and c.representative_id!=representative:
            if c.next_change_at and current<c.next_change_at:
                fail('REPRESENTATIVE_COOLDOWN')
            c.next_change_at=current+timedelta(minutes=5)
        if previous!=set(selected) or c.representative_id!=representative or c.state!='configured':
            db.execute(delete(Activity).where(Activity.settings_id==c.id))
            db.add_all([Activity(settings_id=c.id,account_id=a.id,character_id=i) for i in selected])
            c.representative_id,c.state=representative,'configured'
            c.version+=1
        db.flush()
        return 200,settings_out(db,uid,r)
    if op=='start':
        r=reg(db,uid,uuid.UUID(data['registration_id'])) if data['source']=='registration' else existing_registration(db,uid,obs.roster)
        if data['source']=='registration' and r.version!=baseline_revision:
            fail('REVISION_CONFLICT')
        try:
            slots=required_slots(obs.equipment or {})
        except EquipmentIncomplete:
            fail('EQUIPMENT_INCOMPLETE',400)
        candidate=canonical_candidate(db,obs.roster)
        v=Verification(actor_id=uid,registration_id=r.id if r else None,lookup_name=r.lookup_name if data['source']=='registration' else data['character_name'],
                       candidate_id=candidate.id if candidate else None,revision=candidate.ownership_revision if candidate else None,
                       roster=obs.roster,baseline={k:dict(name=e.name,grade=e.grade) for k,e in obs.equipment.items()},
                       slots=list(slots),created_at=current,expires_at=current+timedelta(minutes=10))
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
    v.attempt_count+=1; v.last_checked_at=current
    baseline={k:EquipmentItem(**e) for k,e in v.baseline.items()}
    if obs is None or obs.equipment is None:
        fail('UPSTREAM_UNAVAILABLE',503)
    code=compare_equipment(baseline,tuple(v.slots),obs.equipment)
    if code!='EQUIPMENT_MATCHED':
        return 200,verification_out(v,current,code)
    if not obs.proof_validated:
        return 200,verification_out(v,current,'PROVIDER_EVIDENCE_PENDING')
    candidate=canonical_candidate(db,obs.roster)
    if (candidate.id if candidate else None)!=v.candidate_id or (candidate.ownership_revision if candidate else None)!=v.revision:
        fail('REVISION_CONFLICT')
    if v.registration_id:
        source_registration=reg(db,uid,v.registration_id)
        if source_registration.account_id and (candidate is None or candidate.id!=source_registration.account_id):
            fail('IDENTITY_CONFLICT')
    if candidate:
        current_keys={(c.server_name,c.character_name) for c in db.scalars(select(Character).where(Character.account_id==candidate.id))}
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
    reconcile(db,a,obs)
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


def canonical_candidate(db, rows):
    observed=keys(rows)
    ids=set()
    # At most 200 keys; identity is observed, never inferred by name alone.
    for server,name in observed:
        aid=db.scalar(select(Character.account_id).where(Character.server_name==server,Character.character_name==name))
        if aid:
            ids.add(aid)
    if len(ids)>1:
        fail('IDENTITY_CONFLICT')
    return db.get(Account,next(iter(ids))) if ids else None
