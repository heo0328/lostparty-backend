"""Policy facts and candidate leases. Mutations run under the game mutation lock."""
from datetime import timedelta
from uuid import UUID
from fastapi.encoders import jsonable_encoder
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from app.core.database import now
from app.game_accounts.models.analysis_candidates import CandidatePolicy, AnalysisCandidate
from app.game_accounts.models.models import Character, Configuration, Activity, RequestResult
from app.game_accounts.common.support import fail
from app.game_accounts.rosters import lifecycle

POLICY='analysis-candidates-1'

def policy(db, uid, account):
    return db.scalar(select(CandidatePolicy).where(CandidatePolicy.user_id==uid,
        CandidatePolicy.account_id==account.id,CandidatePolicy.ownership_revision==account.ownership_revision))

def ensure_legacy(db,uid,account):
    p=policy(db,uid,account)
    if p is None:
        p=CandidatePolicy(user_id=uid,account_id=account.id,ownership_revision=account.ownership_revision,baseline='legacy')
        db.add(p);db.flush()
        for c in db.scalars(select(Character).where(Character.account_id==account.id)):
            db.add(AnalysisCandidate(policy_id=p.id,character_id=c.id,legacy=True))
        db.flush()
    return p

def level(value):
    try:
        n=Decimal(value) if isinstance(value,str) else None
        return n if n is not None and n.is_finite() and n>=0 else None
    except InvalidOperation:
        return None

def observe(db, account, rows, fresh):
    p=policy(db,account.owner_id,account)
    if p is None:
        p=CandidatePolicy(user_id=account.owner_id,account_id=account.id,
            ownership_revision=account.ownership_revision,baseline='observed' if fresh else 'legacy')
        db.add(p);db.flush()
        if not fresh:
            for c in db.scalars(select(Character).where(Character.account_id==account.id)):
                db.add(AnalysisCandidate(policy_id=p.id,character_id=c.id,legacy=True))
            db.flush()
    chars={(c.server_name,c.character_name):c for c in db.scalars(select(Character).where(Character.account_id==account.id))}
    for row in rows:
        c=chars[(row['server_name'],row['character_name'])]
        fact=db.scalar(select(AnalysisCandidate).where(AnalysisCandidate.policy_id==p.id,AnalysisCandidate.character_id==c.id))
        if fact is None:
            fact=AnalysisCandidate(policy_id=p.id,character_id=c.id,legacy=False);db.add(fact);db.flush()
        n=level(row.get('item_level'))
        if n is None:continue
        if n<1700:
            if not fact.below_threshold:fact.below_threshold=True
        elif fact.reason is None and (not fact.legacy or fact.below_threshold):
            fact.reason='initial_verification' if fresh else 'first_threshold' if fact.below_threshold else 'new_at_threshold'
    db.flush()

def selected(db,uid,account,cid):
    conf=db.scalar(select(Configuration).where(Configuration.user_id==uid,Configuration.account_id==account.id,Configuration.ended_at.is_(None)))
    return conf, bool(conf and cid is not None and db.get(Activity,(conf.id,cid)))

def fact_for(db,p,cid):
    return db.scalar(select(AnalysisCandidate).where(AnalysisCandidate.policy_id==p.id,AnalysisCandidate.character_id==cid)) if p else None

def delta(db,uid,account,before,after,expected=None):
    p=ensure_legacy(db,uid,account)
    if expected is not None and p.revision!=expected:fail('REVISION_CONFLICT')
    for cid in {UUID(str(v)) for v in before}^{UUID(str(v)) for v in after}:
        cid=UUID(str(cid))
        f=fact_for(db,p,cid)
        if f is None:
            f=AnalysisCandidate(policy_id=p.id,character_id=cid,legacy=True);db.add(f);db.flush()
        f.excluded=cid not in {UUID(str(v)) for v in after}
        p.revision+=1
    db.flush()

def row(db,uid,a,c):
    p=policy(db,uid,a);return p,fact_for(db,p,c.id)

def code_guard(db,uid,a,c,command):
    p,f=row(db,uid,a,c)
    ctx=command.candidate_context
    if ctx is not None and (f is None or not f.reason or f.id!=ctx.candidate_id):
        fail('ANALYSIS_CANDIDATE_NOT_FOUND',404)
    return p,f

def original(command):
    return command.model_dump(mode='json',exclude_unset=True)

def reserve_candidate(db,uid,a,c,command):
    """Return skip code or reserve the single candidate execution."""
    p,f=code_guard(db,uid,a,c,command)
    ctx=command.candidate_context
    if f is None or f.reason is None:return None
    if f.state=='running' and f.command_id!=command.command_id:
        fail('ANALYSIS_CANDIDATE_IN_PROGRESS')
    resuming=f.state=='running' and f.command_id==command.command_id and f.command_body==original(command)
    if ctx and not resuming:
        conf,_=selected(db,uid,a,c.id)
        if (ctx.expected_generation!=f.generation or ctx.expected_policy_revision!=p.revision
                or ctx.expected_settings_version!=(conf.version if conf else 1)):
            fail('REVISION_CONFLICT')
        if f.state=='succeeded':return 'ANALYSIS_CANDIDATE_COMPLETED'
        if f.state=='blocked' and command.trigger=='automatic':return 'ANALYSIS_CANDIDATE_RETRY_REQUIRED'
        if ctx.purpose=='manual_retry' and f.state!='blocked':fail('REVISION_CONFLICT')
    if f.state=='succeeded':return None
    if f.state=='blocked' and command.trigger=='automatic' and not selected(db,uid,a,c.id)[1]:
        return 'ANALYSIS_CANDIDATE_RETRY_REQUIRED'
    if f.state=='blocked':f.generation+=1
    f.state='running';f.command_id=command.command_id;f.command_body=original(command)
    f.lease_until=now(db)+timedelta(seconds=30)
    return None

def settle(db,uid,a,c,command,result):
    p,f=row(db,uid,a,c)
    if not f or not f.reason or f.command_id!=command.command_id or f.state!='running':return
    if result['state']=='saved':
        f.state='succeeded';f.completed_at=now(db);f.completed_command_id=command.command_id
    elif result['state']=='failed':
        f.state='blocked';f.last_error=jsonable_encoder(result['error'])
    elif result['state']=='skipped':f.state='pending'
    else:return
    f.lease_until=None

def can_automatic(db,uid,a,c,command):
    p,f=row(db,uid,a,c)
    if f and f.excluded:return False
    if selected(db,uid,a,c.id)[1]:return True
    return bool(command.candidate_context and f and f.reason and f.state in ('pending','running')
                and f.id==command.candidate_context.candidate_id)

def validate_save(db,uid,a,c,command,selection):
    p,f=row(db,uid,a,c)
    if selection.get('candidate_lease'):
        conf,_=selected(db,uid,a,c.id)
        if (not f or f.state!='running' or f.command_id!=command.command_id
                or f.generation!=selection['candidate_generation'] or f.lease_until<=now(db)
                or p.revision!=selection['policy_revision'] or (conf.version if conf else 1)!=selection['settings_version']):
            fail('REVISION_CONFLICT')

def recover_expired(db,uid,a,c,command):
    """Never resubmit a retained candidate command after its ledger lifetime."""
    p,f=row(db,uid,a,c)
    if not f or f.command_id!=command.command_id:return None
    if f.command_body!=original(command):fail('IDEMPOTENCY_CONFLICT')
    ledger=db.scalar(select(RequestResult).where(RequestResult.actor_id==uid,
        RequestResult.operation=='character-analysis-refresh',RequestResult.key==command.command_id))
    at=now(db)
    expired=ledger is None or ledger.state=='expired' or (ledger.completed_at is not None and at>=ledger.completed_at+timedelta(hours=24)) or (ledger.completed_at is None and ledger.record_created_at is not None and at>=ledger.record_created_at+timedelta(hours=48))
    if not expired:return None
    if f.state!='running' and command.candidate_context is None:return None
    if f.state=='running':
        f.state='blocked';f.lease_until=None
    return 'ANALYSIS_CANDIDATE_COMPLETED' if f.state=='succeeded' else 'ANALYSIS_CANDIDATE_RECONCILED'

def projection(db,uid,a,r):
    from app.game_accounts.analysis.service import nice_allowed
    p=policy(db,uid,a);conf,_=selected(db,uid,a,None)
    out=dict(policy_version=POLICY,policy_revision=p.revision if p else 1,baseline=p.baseline if p else 'not_initialized',
        game_account_id=a.id,registration_id=r.id,ownership_revision=a.ownership_revision,
        settings_version=conf.version if conf else 1,complete=True,candidates=[])
    if not p:return out
    facts=list(db.scalars(select(AnalysisCandidate).where(AnalysisCandidate.policy_id==p.id,AnalysisCandidate.reason.is_not(None)).order_by(AnalysisCandidate.id).limit(201)))
    if len(facts)>200:fail('BOOTSTRAP_LIMIT_EXCEEDED')
    for f in facts:
        c=db.get(Character,f.character_id)
        eligible=('character_unusable' if not lifecycle.usable(db,c) else 'explicitly_excluded' if f.excluded
                  else 'nice_group_disabled' if not nice_allowed(db,uid,a,c) else 'command_unresolved' if f.state=='running' else 'eligible')
        recovery=None
        if f.state=='running':
            ledger=db.scalar(select(RequestResult).where(RequestResult.actor_id==uid,RequestResult.operation=='character-analysis-refresh',RequestResult.key==f.command_id))
            recovery='same_command' if ledger and ledger.state!='expired' and (now(db)<ledger.completed_at+timedelta(hours=24) if ledger.completed_at else ledger.record_created_at is not None and now(db)<ledger.record_created_at+timedelta(hours=48)) else 'reconcile_required'
        out['candidates'].append(dict(candidate_id=f.id,character_id=f.character_id,generation=f.generation,reason=f.reason,
            state=f.state,eligibility=eligible,next_attempt_at=None,last_error=f.last_error,
            unresolved_command=dict(command=f.command_body,recovery=recovery) if recovery else None,
            completed_at=f.completed_at,completed_command_id=f.completed_command_id))
    return out
