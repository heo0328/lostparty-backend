"""Short atomic commands around uncached provider I/O. No network under mutation locks."""
import uuid
from datetime import timedelta
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts import service as accounts,verification_context,equipment_proof,lifecycle
from app.game_accounts.equipment import EquipmentItem,required_slots,compare_equipment,EquipmentIncomplete
from app.game_accounts.models import Account,Registration,Configuration,Audit,Character
from app.game_accounts.support import authorize,fail,reserve,release,commit_result,quota
from app.lostark_keys import service as credentials
from app.ownership_disputes import core,reads
from app.ownership_disputes.models import Proof,Dispute,AccountHead


def preview(principal,data):
    original=accounts.preview(principal,data)
    with session() as db,db.begin():
        uid=authorize(db,principal);current=now(db)
        return dict(preview=original,ownership_context=core.context(db,uid,original['characters'],data.character_name,current),server_now=current)


def start_target(db,uid,data,did=None):
    r=None;d=None;c=None
    if did:
        d=core.visible_dispute(db,uid,did)
        core.cas(d,data['expected_dispute_version'])
        a=db.get(Account,d.account_id)
        if uid!=d.owner_id:fail('DISPUTE_ACTION_FORBIDDEN',403)
        if d.state!='defending' or a.owner_id!=uid or a.ownership_revision!=d.ownership_revision:fail('REVISION_CONFLICT')
        if now(db)>=core.defense_until(db,d):fail('DEFENSE_WINDOW_CLOSED')
        selection=data['selection'];r=core.registration(db,uid,selection['registration_id'])
        c=db.get(Character,uuid.UUID(selection['character_id']))
        if c is None or c.account_id!=d.account_id or r.account_id!=d.account_id:fail('CHARACTER_NOT_FOUND',404)
        lifecycle.require_usable(db,c)
        expected=(selection['expected_registration_version'],selection['expected_ownership_revision'],selection['expected_roster_revision'],selection['expected_lifecycle_revision'])
        if expected!=(r.version,a.ownership_revision,a.roster_revision,c.lifecycle_revision):fail('REVISION_CONFLICT')
        name=c.character_name
    elif data['source']=='registration':
        r=core.registration(db,uid,data['registration_id'])
        from app.game_accounts import ownership_policy,verification_targets
        ownership_policy.reject_linked(db,uid,r)
        name=verification_targets.selected(db,uid,r,data)
    else:name=data['character_name']
    return name,r,d,c


def mutate(principal,operation,key,data,rid=None):
    ticket,replay=reserve(principal,'ownership-v2-'+operation,key,dict(target=str(rid) if rid else None,body=data))
    if replay:
        with session() as db:
            uid=authorize(db,principal)
            if operation in ('confirm','proof_cancel'):core.owned_proof(db,uid,rid)
            if operation in ('defense','dispute_cancel','settle'):core.visible_dispute(db,uid,rid)
        return replay
    try:
        if operation in ('start','defense'):
            return start(principal,operation,data,rid,ticket)
        obs=snapshot=None
        if operation=='confirm':
            with session() as db:
                uid=authorize(db,principal);p=core.owned_proof(db,uid,rid);core.cas(p,data['expected_version'])
                needs=p.status=='pending' and now(db)<p.expires_at and core.scope_error(db,p) is None
                name=p.lookup_name
            if needs:
                quota('v2-confirm:'+str(rid),1,5);quota('v2-confirm-user:'+str(uid),12)
                snapshot=credentials.capture(principal)
                obs=accounts.lookup(principal,snapshot,name,proof=True,context=['ownership-v2-confirm',str(rid),str(ticket)])
        with session() as db,db.begin():
            uid=authorize(db,principal,write=True);current=now(db)
            if operation in ('confirm','proof_cancel'):
                p=core.owned_proof(db,uid,rid);core.cas(p,data['expected_version'])
                if operation=='proof_cancel':
                    if p.status!='pending':fail('VERIFICATION_TERMINAL')
                    core.finish_proof(db,p,'expired' if current>=p.expires_at else 'cancelled','none',
                                      'VERIFICATION_EXPIRED' if current>=p.expires_at else 'VERIFICATION_CANCELLED',p.expires_at if current>=p.expires_at else current)
                elif p.status=='pending':
                    if current>=p.expires_at:core.finish_proof(db,p,'expired','none','VERIFICATION_EXPIRED',p.expires_at)
                    else:
                        err=core.scope_error(db,p,obs.roster if obs else None)
                        if snapshot and snapshot.version!=p.identity_snapshot['credential_version']:err='LOSTARK_KEY_CHANGED'
                        if err:core.finish_proof(db,p,'invalidated','blocked',err,current)
                        elif obs is None:fail('UPSTREAM_UNAVAILABLE',503)
                        else:
                            credentials.check(db,principal,snapshot)
                            # Roll all proof/ownership/dispute writes back if final work crosses the deadline.
                            crossed=False
                            with db.begin_nested() as attempt:
                                confirm(db,uid,p,obs,current)
                                db.flush()
                                crossed=p.status=='passed' and now(db)>=p.expires_at
                                if crossed:attempt.rollback()
                            if crossed:
                                p=db.get(Proof,rid)
                                core.finish_proof(db,p,'expired','none','VERIFICATION_EXPIRED',p.expires_at)
                body=reads.proof_out(db,p,now(db))
            else:
                d=core.visible_dispute(db,uid,rid);core.cas(d,data['expected_version'])
                if operation=='dispute_cancel':
                    if uid!=d.challenger_id:fail('DISPUTE_ACTION_FORBIDDEN',403)
                    if not (d.state=='review_required' or (d.state=='defending' and current<d.deadline)):
                        fail('DISPUTE_TERMINAL' if d.state not in core.ACTIVE else 'DEFENSE_WINDOW_CLOSED')
                    core.finish_dispute(db,d,'cancelled','CHALLENGER_CANCELLED',current)
                elif operation=='settle':
                    if d.state!='defending':fail('DISPUTE_TERMINAL')
                    if current<d.deadline:fail('DISPUTE_NOT_DUE')
                    if not d.lease_until or d.lease_until<=current:
                        d.next_retry_at=current
                    # Scheduling changes feed/version; it is never the ownership success ACK.
                    d.version+=1;core.touch_dispute(db,d,'SETTLEMENT_REQUESTED')
                body=reads.dispute_out(db,uid,d,now(db))
            return commit_result(db,ticket,200,body)
    except Exception:
        release(ticket);raise


def start(principal,operation,data,rid,ticket):
    with session() as db:
        uid=authorize(db,principal);name,r,d,c=start_target(db,uid,data,rid if operation=='defense' else None)
        guard=(r.id,r.version) if r else None
        generations={h.account_id:h.generation for h in db.scalars(select(AccountHead))}
    quota('v2-start:'+str(uid),3)
    snapshot=credentials.capture(principal)
    def roster_guard(rows):
        # Current ownership/capacity must be checked before an unnecessary Armory call.
        with session() as db:
            actor=authorize(db,principal)
            credentials.check(db,principal,snapshot)
            if operation=='start':
                ctx=core.context(db,actor,rows,name,now(db))
                if not ctx['can_start_claim']:
                    fail(ctx['blocked_reason'] if ctx['blocked_reason']!='IDENTITY_UNRESOLVED' else 'IDENTITY_CONFLICT')
            else:
                _,_,parent,chosen=start_target(db,actor,data,rid)
                account,character,_=core.candidate(db,rows,name)
                if account is None or account.id!=parent.account_id or character.id!=chosen.id:fail('IDENTITY_CONFLICT')
    obs=accounts.lookup(principal,snapshot,name,proof=True,context=['ownership-v2-start',str(ticket)],on_roster=roster_guard)
    with session() as db,db.begin():
        uid=authorize(db,principal,write=True);credentials.check(db,principal,snapshot)
        name,r,d,selected=start_target(db,uid,data,rid if operation=='defense' else None)
        if guard and guard!=(r.id,r.version):fail('REVISION_CONFLICT')
        current=now(db);canonical=verification_context.resolve_input(name,obs.roster)
        context=verification_context.capture(canonical,obs.roster)
        if context is None:fail('UPSTREAM_UNAVAILABLE',503)
        a,c,kind=core.candidate(db,obs.roster,canonical)
        if operation=='defense':
            if a is None or a.id!=d.account_id or c.id!=selected.id:fail('IDENTITY_CONFLICT')
        else:
            ctx=core.context(db,uid,obs.roster,canonical,current)
            if not ctx['can_start_claim']:fail(ctx['blocked_reason'] if ctx['blocked_reason']!='IDENTITY_UNRESOLVED' else 'IDENTITY_CONFLICT')
            target=data.get('target_character')
            if target and context['target']!=[target['server_name'],target['character_name']]:fail('IDENTITY_CONFLICT')
        if a and (core.head(db,a.id).generation if core.head(db,a.id) else 1)!=generations.get(a.id,1):fail('REVISION_CONFLICT')
        try:slots=required_slots(obs.equipment or {})
        except EquipmentIncomplete:fail('EQUIPMENT_INCOMPLETE',400)
        baseline=equipment_proof.baseline(obs,canonical,current)
        if baseline is None:fail('UPSTREAM_UNAVAILABLE',503)
        expiry=current+timedelta(minutes=10)
        if d:expiry=min(expiry,core.defense_until(db,d))
        p=Proof(actor_id=uid,purpose='defense' if d else 'claim',source='dispute_defense' if d else data['source'],
            source_registration_id=r.id if r else None,registration_id=r.id if r else None,dispute_id=d.id if d else None,
            candidate_id=a.id if a else None,lookup_name=canonical,baseline={k:dict(name=v.name,grade=v.grade) for k,v in obs.equipment.items()},slots=list(slots),
            identity_snapshot=dict(candidate=core.stamp(db,a,c) if a else None,registration_version=r.version if r else None,
                proof_context=context,roster=obs.roster,credential_version=snapshot.version,server_equipment_baseline=baseline),
            created_at=current,expires_at=expiry)
        db.add(p);db.flush();core.touch_proof(db,uid)
        if d:core.member_head(db,uid,True).dispute_revision+=1
        result=commit_result(db,ticket,201,reads.proof_out(db,p,current));db.flush()
        if now(db)>=expiry:fail('DEFENSE_WINDOW_CLOSED')
        return result


def confirm(db,uid,p,obs,current):
    original={k:EquipmentItem(**v) for k,v in p.baseline.items()}
    code=compare_equipment(original,tuple(p.slots),obs.equipment or {})
    if code=='EQUIPMENT_MATCHED':
        code=verification_context.pending_code(p.identity_snapshot,p.lookup_name,obs.roster) or code
    if code=='EQUIPMENT_MATCHED' and (not equipment_proof.attests(obs,p.lookup_name) or not equipment_proof.validated(p,obs,current)):
        code='PROVIDER_EVIDENCE_PENDING'
    if code!='EQUIPMENT_MATCHED':
        p.result_code=code;p.version+=1;core.touch_proof(db,uid);return
    if p.purpose=='defense':
        d=db.get(Dispute,p.dispute_id)
        if current>=core.defense_until(db,d):core.finish_proof(db,p,'invalidated','blocked','DEFENSE_WINDOW_CLOSED',current);return
        for other in core.cohort(db,d):core.finish_dispute(db,other,'defended','OWNER_DEFENDED',current)
        core.head(db,d.account_id,True).generation+=1
        for actor in set(db.scalars(select(Proof.actor_id).where(Proof.candidate_id==d.account_id,Proof.status=='pending'))):
            core.touch_proof(db,actor)
        core.finish_proof(db,p,'passed','defended','OWNER_DEFENDED',current)
    elif p.candidate_id:
        a=db.get(Account,p.candidate_id);active=core.live(db,a.id)
        reason='DISPUTE_ALREADY_ACTIVE' if any(d.challenger_id==uid for d in active) else 'DISPUTE_CAPACITY_REACHED' if len(active)>=3 else None
        if reason:core.finish_proof(db,p,'passed','blocked',reason,current);return
        h=core.head(db,a.id,True);h.sequence+=1
        slot=next(n for n in (1,2,3) if n not in {d.slot for d in active})
        d=Dispute(account_id=a.id,owner_id=a.owner_id,challenger_id=uid,ownership_revision=a.ownership_revision,
            generation=h.generation,sequence=h.sequence,slot=slot,proof_id=p.id,started_at=current,deadline=current+timedelta(hours=24))
        db.add(d);db.flush();p.dispute_id=d.id
        core.finish_proof(db,p,'passed','dispute_opened','DISPUTE_OPENED',current);core.touch_dispute(db,d,'DISPUTE_OPENED')
    else:
        # Only an unclaimed fresh roster reaches the new-account success path.
        a,c,kind=core.candidate(db,obs.roster,p.lookup_name)
        if a is not None or kind!='unverified':fail('IDENTITY_CONFLICT')
        r=core.registration(db,uid,p.source_registration_id) if p.source_registration_id else accounts.existing_registration(db,uid,obs.roster)
        if r is None:r=accounts.create_registration(db,uid,p.lookup_name,p.lookup_name[:40],False,obs)
        if r.account_id:fail('IDENTITY_CONFLICT')
        a=Account(owner_id=uid,verified_at=current);db.add(a);db.flush()
        accounts.reconcile(db,a,obs,fresh=True)
        r.account_id=a.id;r.preview=obs.roster;r.fetched_at=obs.fetched_at;r.version+=1
        db.add(Configuration(user_id=uid,account_id=a.id))
        db.add(Audit(account_id=a.id,challenge_id=None,previous_owner=None,new_owner=uid,revision=a.ownership_revision,created_at=current))
        p.registration_id=r.id
        core.finish_proof(db,p,'passed','verified','VERIFIED',current)
