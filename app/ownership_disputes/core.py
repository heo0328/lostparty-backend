"""Authority checks shared by HTTP commands and the durable settlement worker."""
import uuid
from datetime import timedelta
from sqlalchemy import select
from app.core.database import now
from app.game_accounts import lifecycle, verification_context
from app.game_accounts.models import Account, Character, Registration, NameClaim
from app.game_accounts.support import fail
from app.ownership_disputes.models import AccountHead, MemberHead, Proof, Dispute, Event

ACTIVE = ('defending','review_required')


def head(db, aid, create=False):
    row = db.get(AccountHead, aid)
    if row is None and create:
        row = AccountHead(account_id=aid, generation=1, sequence=0)
        db.add(row); db.flush()
    return row


def member_head(db, uid, create=False):
    row = db.get(MemberHead, uid)
    if row is None and create:
        row = MemberHead(user_id=uid, proof_revision=1, dispute_revision=1)
        db.add(row); db.flush()
    return row


def touch_proof(db, uid):
    member_head(db, uid, True).proof_revision += 1


def touch_dispute(db, d, kind):
    db.add(Event(dispute_id=d.id, revision=d.version, kind=kind, created_at=now(db)))
    for uid in (d.owner_id, d.challenger_id):
        member_head(db, uid, True).dispute_revision += 1


def live(db, aid):
    return list(db.scalars(select(Dispute).where(Dispute.account_id==aid, Dispute.state.in_(ACTIVE)).order_by(Dispute.sequence)))


def cohort(db, d):
    return [v for v in live(db,d.account_id) if v.owner_id==d.owner_id and v.ownership_revision==d.ownership_revision]


def defense_until(db, d):
    rows = cohort(db,d)
    return min((v.deadline for v in rows), default=d.deadline)


def candidate(db, rows, name):
    """An exact current claim is a candidate, never proof of control or identity."""
    canonical = verification_context.resolve_input(name,rows)
    if canonical is None:
        return None,None,'unresolved'
    context = verification_context.capture(canonical,rows)
    accounts=set()
    for row in rows:
        claim=db.get(NameClaim,(row['server_name'],row['character_name']))
        if claim:
            c=db.get(Character,claim.character_id)
            if c is None or c.lifecycle_state=='retired': return None,None,'unresolved'
            accounts.add(c.account_id)
    if not accounts: return None,None,'unverified'
    if len(accounts)!=1: return None,None,'unresolved'
    a=db.get(Account,next(iter(accounts)))
    claim=db.get(NameClaim,tuple(context['target']))
    c=db.get(Character,claim.character_id) if claim else None
    if a is None or a.owner_id is None or a.verified_at is None or c is None or c.account_id!=a.id or not lifecycle.usable(db,c):
        return None,None,'unresolved'
    return a,c,'known'


def context(db, uid, rows, name, current):
    a,c,kind=candidate(db,rows,name)
    relation=('self' if a.owner_id==uid else 'other') if a else kind
    reason=None
    if relation=='self': reason='ALREADY_VERIFIED'
    elif relation=='unresolved': reason='IDENTITY_UNRESOLVED'
    elif a:
        active=live(db,a.id)
        if any(v.challenger_id==uid for v in active): reason='DISPUTE_ALREADY_ACTIVE'
        elif len(active)>=3: reason='DISPUTE_CAPACITY_REACHED'
    return dict(relation=relation,notice_code='OTHER_OWNER_VERIFIED' if relation=='other' else None,
                observed_at=current,can_start_claim=reason is None,blocked_reason=reason)


def owned_proof(db, uid, pid):
    p=db.get(Proof,pid)
    if p is None or p.actor_id!=uid: fail('VERIFICATION_NOT_FOUND',404)
    return p


def visible_dispute(db, uid, did):
    d=db.get(Dispute,did)
    if d is None or uid not in (d.owner_id,d.challenger_id): fail('DISPUTE_NOT_FOUND',404)
    return d


def cas(row, expected):
    if row.version!=expected: fail('REVISION_CONFLICT')


def registration(db, uid, rid):
    from app.game_accounts.service import reg
    return reg(db,uid,uuid.UUID(str(rid)))


def stamp(db, a, c):
    h=head(db,a.id)
    return dict(account_id=str(a.id),owner_id=str(a.owner_id),ownership_revision=a.ownership_revision,
                generation=h.generation if h else 1,target_id=str(c.id),target_stamp=lifecycle.digest(lifecycle.character_stamp(db,c)))


def scope_error(db, p, rows=None):
    snap=p.identity_snapshot
    if p.source_registration_id:
        r=db.get(Registration,p.source_registration_id)
        if r is None or r.deleted_at or r.user_id!=p.actor_id or r.version!=snap['registration_version']:
            return 'REVISION_CONFLICT'
    from app.lostark_keys.models import Credential
    credential=db.get(Credential,p.actor_id)
    if credential is None or credential.ciphertext is None or credential.version!=snap['credential_version']:
        return 'LOSTARK_KEY_CHANGED'
    saved=snap['candidate']
    if saved:
        a=db.get(Account,p.candidate_id); c=db.get(Character,uuid.UUID(saved['target_id']))
        if a is None or c is None or not lifecycle.usable(db,c) or stamp(db,a,c)!=saved:
            return 'REVISION_CONFLICT'
    if p.purpose=='defense':
        d=db.get(Dispute,p.dispute_id)
        if d is None or d.state!='defending': return 'PARENT_DISPUTE_ENDED'
        if defense_until(db,d)<=now(db): return 'DEFENSE_WINDOW_CLOSED'
    if rows is not None:
        a,c,kind=candidate(db,rows,p.lookup_name)
        if (a.id if a else None)!=p.candidate_id or kind=='unresolved': return 'IDENTITY_CONFLICT'
    return None


def finish_proof(db, p, status, outcome, code, current):
    p.status,p.outcome,p.result_code,p.ended_at=status,outcome,code,current
    p.version+=1
    touch_proof(db,p.actor_id)
    if p.purpose=='defense':member_head(db,p.actor_id,True).dispute_revision+=1


def finish_dispute(db, d, state, reason, current):
    d.state,d.reason,d.resolved_at=state,reason,current
    d.next_retry_at,d.lease_until=None,None
    d.lease_generation+=1;d.version+=1
    touch_dispute(db,d,reason)


def retry(db,d,reason,current,review=False):
    d.state='review_required' if review else 'defending'
    d.reason=reason;d.next_retry_at=None if review else current+timedelta(seconds=60)
    d.lease_until=None;d.version+=1
    touch_dispute(db,d,reason)
