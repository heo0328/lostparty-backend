import uuid
from sqlalchemy import select,or_
from app.core.database import session,now
from app.game_accounts import lifecycle
from app.game_accounts.models import Registration,Account
from app.game_accounts.support import authorize,cursor_encode,cursor_decode
from app.ownership_disputes import core
from app.ownership_disputes.models import Proof,Dispute


def proof_out(db,p,current):
    snap=p.identity_snapshot
    status,code,ended=p.status,p.result_code,p.ended_at
    if status=='pending' and current>=p.expires_at:
        status,code,ended='expired','VERIFICATION_EXPIRED',p.expires_at
    actions=[]
    if status=='pending':
        if core.scope_error(db,p) is None: actions.append('confirm')
        actions.append('cancel')
    if p.dispute_id: actions.append('view_dispute')
    if p.outcome=='verified' and p.registration_id:
        r=db.get(Registration,p.registration_id);a=db.get(Account,r.account_id) if r and r.account_id else None
        if r and not r.deleted_at and a and a.owner_id==p.actor_id: actions.append('open_registration')
    ctx=core.context(db,p.actor_id,snap['roster'],p.lookup_name,current)
    return dict(verification_id=p.id,version=p.version,purpose=p.purpose,source=p.source,
        source_registration_id=p.source_registration_id,equipment_status=status,ownership_outcome=p.outcome,
        ownership_context=ctx,target=dict(zip(('server_name','character_name'),snap['proof_context']['target'])),
        required_slots=p.slots,created_at=p.created_at,equipment_expires_at=p.expires_at,server_now=current,
        ended_at=ended,result_code=code,dispute_id=p.dispute_id,registration_id=p.registration_id,allowed_actions=actions)


def dispute_out(db,uid,d,current):
    a=db.get(Account,d.account_id)
    active=d.state in core.ACTIVE
    until=core.defense_until(db,d) if active and a.owner_id==d.owner_id and a.ownership_revision==d.ownership_revision else None
    until=until if until and until>current else None
    phase=('review_required' if d.state=='review_required' else 'finished' if not active else
           'awaiting_defense' if current<d.deadline else 'retrying_settlement' if d.next_retry_at and d.reason else 'settlement_due')
    r=db.scalar(select(Registration).where(Registration.user_id==uid,Registration.deleted_at.is_(None),Registration.account_id==d.account_id))
    p=db.get(Proof,d.proof_id)
    if r is None and p.source_registration_id and uid==d.challenger_id:
        stored=db.get(Registration,p.source_registration_id)
        if stored and not stored.deleted_at: r=stored
    q=select(Proof).where(Proof.actor_id==uid,Proof.status=='pending',Proof.expires_at>current)
    if uid==d.owner_id:
        q=q.where(Proof.purpose=='defense',Proof.candidate_id==d.account_id)
    else: q=q.where(Proof.dispute_id==d.id)
    proofs=[v.id for v in db.scalars(q) if core.scope_error(db,v) is None]
    actions=[]
    if uid==d.challenger_id and (d.state=='review_required' or (d.state=='defending' and current<d.deadline)):
        actions.append('cancel_dispute')
    if uid==d.owner_id and d.state=='defending' and until: actions.append('start_defense')
    if proofs: actions.append('view_my_verifications')
    if d.state=='defending' and current>=d.deadline: actions.append('request_settlement')
    if r and a.owner_id==uid: actions.append('open_registration')
    target=db.get(Proof,d.proof_id).identity_snapshot['proof_context']['target']
    return dict(dispute_id=d.id,version=d.version,viewer_role='owner' if uid==d.owner_id else 'challenger',
        state=d.state,phase=phase,target=dict(zip(('server_name','character_name'),target)),started_at=d.started_at,
        defense_deadline=d.deadline,server_now=current,defense_available_until=until,resolved_at=d.resolved_at,
        reason_code=d.reason,next_retry_at=d.next_retry_at,my_registration_id=r.id if r else None,
        my_active_verification_ids=proofs,allowed_actions=actions)


def get(principal,kind,rid):
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        uid=authorize(db,principal);current=now(db)
        return proof_out(db,core.owned_proof(db,uid,rid),current) if kind=='proof' else dispute_out(db,uid,core.visible_dispute(db,uid,rid),current)


def listing(principal,kind,role,view,limit,cursor):
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        uid=authorize(db,principal);current=now(db);h=core.member_head(db,uid)
        revision=(h.proof_revision if kind=='proof' else h.dispute_revision) if h else 1
        if kind=='proof':
            q=select(Proof).where(Proof.actor_id==uid)
            if role!='all': q=q.where(Proof.purpose==role)
            if view=='active': q=q.where(Proof.status=='pending',Proof.expires_at>current)
            rows=list(db.scalars(q.order_by(Proof.created_at.desc(),Proof.id.desc())))
            items=[proof_out(db,p,current) for p in rows]
            logical=[(str(p.id),i['equipment_status']) for p,i in zip(rows,items)]
        else:
            q=select(Dispute).where(or_(Dispute.owner_id==uid,Dispute.challenger_id==uid))
            if role=='owner':q=q.where(Dispute.owner_id==uid)
            if role=='challenger':q=q.where(Dispute.challenger_id==uid)
            if view=='active':q=q.where(Dispute.state.in_(core.ACTIVE))
            rows=list(db.scalars(q.order_by(Dispute.started_at.desc(),Dispute.id.desc())))
            items=[dispute_out(db,uid,d,current) for d in rows]
            logical=[(str(d.id),i['phase']) for d,i in zip(rows,items)]
        scope=f'ownership-v2:{uid}:{kind}:{role}:{view}:{limit}'
        stamp=lifecycle.digest([revision,logical])
        offset=cursor_decode(cursor,scope,stamp) if cursor else 0
        following=offset+limit
        return dict(items=items[offset:following],next_cursor=cursor_encode(dict(scope=scope,revision=stamp,offset=following)) if following<len(items) else None,
                    feed_revision=revision,server_now=current)
