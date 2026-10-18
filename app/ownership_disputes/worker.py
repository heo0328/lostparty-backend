"""Durable due/lease loop. Provider I/O is outside the shared mutation transaction."""
import asyncio
import logging
import os
import uuid
from datetime import timedelta
from sqlalchemy import select
from app.auth.models import User
from app.core.database import session,now
from app.game_accounts import observations,service as accounts,lifecycle
from app.game_accounts.models import Account,Character,Registration,Configuration,Audit
from app.game_accounts.support import lock,fail,GameError
from app.lostark_keys.models import Credential
from app.lostark_keys import service as credentials,rate_limits
from app.ownership_disputes.models import Proof,Dispute
from app.ownership_disputes import core


def claim():
    with session() as db,db.begin():
        lock(db,'game-mutations-v1');current=now(db)
        rows=list(db.scalars(select(Dispute).where(Dispute.state=='defending',Dispute.deadline<=current,
            (Dispute.next_retry_at.is_(None)) | (Dispute.next_retry_at<=current),
            (Dispute.lease_until.is_(None)) | (Dispute.lease_until<=current)).order_by(Dispute.deadline,Dispute.sequence).limit(20)))
        for d in rows:
            cohort=core.cohort(db,d)
            if cohort and cohort[0].id!=d.id:
                core.retry(db,d,'WAITING_FOR_EARLIER_DISPUTE',current);continue
            a=db.get(Account,d.account_id)
            if a.owner_id!=d.owner_id or a.ownership_revision!=d.ownership_revision:
                core.finish_dispute(db,d,'invalidated','OWNER_CHANGED',current);continue
            d.lease_generation+=1;d.lease_until=current+timedelta(seconds=30)
            return d.id,d.lease_generation
    return None


def current_claim(db,ticket):
    d=db.get(Dispute,ticket[0]);current=now(db)
    if d is None or d.state!='defending' or d.lease_generation!=ticket[1] or not d.lease_until or current>=d.lease_until:return None
    cohort=core.cohort(db,d)
    if not cohort or cohort[0].id!=d.id:return None
    return d


def fetch(did):
    with session() as db:
        d=db.get(Dispute,did);p=db.get(Proof,d.proof_id);uid=d.challenger_id
        user=db.get(User,uid)
        if user is None or user.status!='active':fail('MEMBER_UNAVAILABLE')
        row=db.get(Credential,uid)
        if row is None or row.ciphertext is None:fail('LOSTARK_KEY_NOT_CONFIGURED')
        snapshot=credentials.decrypt(row,uid)
        name=p.lookup_name
        r=db.get(Registration,p.source_registration_id) if p.source_registration_id else None
        guard=(r.id,r.version) if r else None
    def before_call():
        with session() as db:
            u=db.get(User,uid);row=db.get(Credential,uid)
            if u is None or u.status!='active':fail('MEMBER_UNAVAILABLE')
            if row is None or row.ciphertext is None or row.version!=snapshot.version:fail('LOSTARK_KEY_NOT_CONFIGURED')
        rate_limits.acquire(snapshot.fingerprint)
    before_call()
    obs=observations.fetch(name,True,token=snapshot.token,before_armory=before_call,observer=rate_limits.observer(snapshot.fingerprint))
    return obs,snapshot.version,guard


def apply_transfer(db,d,obs,current):
    """Product-policy authority, never a fabricated provider BindingEvidence."""
    p=db.get(Proof,d.proof_id);a=db.get(Account,d.account_id);h=core.head(db,a.id)
    saved=p.identity_snapshot['candidate']
    c=db.get(Character,uuid.UUID(saved['target_id']))
    if a.owner_id!=d.owner_id or a.ownership_revision!=d.ownership_revision:
        core.finish_dispute(db,d,'invalidated','OWNER_CHANGED',current);return
    if h is None or h.generation!=d.generation or c is None or not lifecycle.usable(db,c) or core.stamp(db,a,c)!=saved:
        core.retry(db,d,'TARGET_CHANGED',current,True);return
    observed,target,kind=core.candidate(db,obs.roster,p.lookup_name)
    if observed is None or observed.id!=a.id or target.id!=c.id:
        core.retry(db,d,'TARGET_CHANGED',current,True);return
    # The fresh collector has checked exact Armory name/server; no new equipment challenge.
    context=p.identity_snapshot['proof_context']['target']
    if [target.server_name,target.character_name]!=context:
        core.retry(db,d,'TARGET_CHANGED',current,True);return
    from app.raid_weekly.models import WeeklyState
    cids=select(Character.id).where(Character.account_id==a.id)
    if db.scalar(select(WeeklyState.character_id).where(WeeklyState.character_id.in_(cids),WeeklyState.active_party_id.is_not(None)).limit(1)):
        core.retry(db,d,'PARTY_IMPACT_REVIEW_REQUIRED',current,True);return
    if p.source_registration_id:
        r=db.get(Registration,p.source_registration_id)
        if r is None or r.deleted_at:
            core.retry(db,d,'REGISTRATION_REMOVED',current,True);return
        if r.user_id!=d.challenger_id or r.account_id not in (None,a.id):
            core.retry(db,d,'REGISTRATION_CONFLICT',current,True);return
    else:
        registrations=list(db.scalars(select(Registration).where(Registration.user_id==d.challenger_id,Registration.deleted_at.is_(None))))
        matches=[r for r in registrations if r.account_id==a.id or (r.account_id is None and accounts.keys(r.preview)&accounts.keys(obs.roster))]
        if len(matches)>1:
            core.retry(db,d,'REGISTRATION_CONFLICT',current,True);return
        r=matches[0] if matches else None
        if r is None and len(registrations)>=20:
            core.retry(db,d,'REGISTRATION_LIMIT',current);return
    if r is None:r=accounts.create_registration(db,d.challenger_id,p.lookup_name,p.lookup_name[:40],False,obs)
    # Final authority and data changes share this transaction with every group/weekly writer.
    old=d.owner_id
    for conf in db.scalars(select(Configuration).where(Configuration.account_id==a.id,Configuration.ended_at.is_(None))):
        conf.ended_at=current;conf.version+=1
    db.flush()
    a.owner_id=d.challenger_id;a.ownership_revision+=1;a.verified_at=current
    for reg in db.scalars(select(Registration).where(Registration.account_id==a.id,Registration.deleted_at.is_(None))):
        reg.version+=1
    r.account_id=a.id;r.preview=obs.roster;r.fetched_at=obs.fetched_at;r.version+=1
    db.add(Configuration(user_id=d.challenger_id,account_id=a.id))
    db.add(Audit(account_id=a.id,challenge_id=None,previous_owner=old,new_owner=a.owner_id,revision=a.ownership_revision,created_at=current))
    p.registration_id=r.id;p.version+=1;core.touch_proof(db,p.actor_id)
    from app.groups.models import Group
    from app.groups.service import advance_directory
    groups=list(db.scalars(select(Group).where(Group.representative_character_id.in_(cids),Group.ended_at.is_(None))))
    for group in groups:group.revision+=1
    if groups:advance_directory(db)
    for other in core.cohort(db,d):
        core.finish_dispute(db,other,'transferred' if other.id==d.id else 'invalidated',
                            'OWNERSHIP_TRANSFERRED' if other.id==d.id else 'OWNER_CHANGED',current)
    h.generation+=1


def process(ticket):
    try:
        obs,version,guard=fetch(ticket[0])
    except Exception as error:
        # No exception text, provider payloads, IDs or credentials in worker output.
        reason=(error.code if isinstance(error,GameError) and error.code in ('LOSTARK_KEY_NOT_CONFIGURED','LOSTARK_KEY_REJECTED','MEMBER_UNAVAILABLE') else
                'LOSTARK_KEY_REJECTED' if getattr(error,'reason',None)=='LOSTARK_KEY_REJECTED' else 'UPSTREAM_UNAVAILABLE')
        with session() as db,db.begin():
            lock(db,'game-mutations-v1');d=current_claim(db,ticket)
            if d:core.retry(db,d,reason,now(db),reason=='MEMBER_UNAVAILABLE')
        return
    with session() as db,db.begin():
        lock(db,'game-mutations-v1');d=current_claim(db,ticket)
        if d is None:return
        u=db.scalar(select(User).where(User.id==d.challenger_id).with_for_update())
        row=db.scalar(select(Credential).where(Credential.user_id==d.challenger_id).with_for_update())
        if u is None or u.status!='active':core.retry(db,d,'MEMBER_UNAVAILABLE',now(db),True);return
        if row is None or row.ciphertext is None or row.version!=version:
            core.retry(db,d,'LOSTARK_KEY_NOT_CONFIGURED',now(db));return
        if guard:
            r=db.get(Registration,guard[0])
            if r is None or r.version!=guard[1] or r.deleted_at:
                core.retry(db,d,'REGISTRATION_REMOVED' if r is None or r.deleted_at else 'REGISTRATION_CONFLICT',now(db),True);return
        lease_deadline=d.lease_until
        with db.begin_nested() as attempt:
            apply_transfer(db,d,obs,now(db));db.flush()
            # A stale process cannot commit after a replacement lease is eligible.
            if now(db)>=lease_deadline:
                attempt.rollback()


def tick():
    ticket=claim()
    if ticket:process(ticket)


async def run():
    if os.getenv('OWNERSHIP_WORKER_ENABLED','1')=='0':return
    while True:
        await asyncio.sleep(5)
        try:await asyncio.to_thread(tick)
        except Exception:logging.getLogger(__name__).warning('Ownership settlement attempt failed')
