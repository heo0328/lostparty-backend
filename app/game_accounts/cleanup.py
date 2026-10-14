from datetime import timedelta
from sqlalchemy import select, delete, update, or_, and_
from app.core.database import session, now
from app.game_accounts.support import lock
from app.game_accounts.models import (RequestResult, Verification, PreviewCache, LimitEvent,
                                     Audit, Registration, FetchLease, PowerCache)


def clean():
    with session() as db, db.begin():
        lock(db,'game-mutations-v1')
        current=now(db)
        for v in db.scalars(select(Verification).where(Verification.status=='pending',Verification.expires_at<=current).with_for_update(skip_locked=True).limit(200)):
            v.status,v.terminal_at='expired',v.expires_at
        db.flush()
        expired=list(db.scalars(select(Verification.id).where(Verification.terminal_at<=current-timedelta(hours=24)).with_for_update(skip_locked=True).limit(200)))
        if expired:
            db.execute(update(Audit).where(Audit.challenge_id.in_(expired)).values(challenge_id=None))
            db.execute(delete(Verification).where(Verification.id.in_(expired)))
        for r in db.scalars(select(RequestResult).where(RequestResult.completed_at<=current-timedelta(hours=24)).with_for_update(skip_locked=True).limit(200)):
            r.result,r.state=None,'expired'
        db.execute(delete(RequestResult).where(RequestResult.completed_at<=current-timedelta(hours=48)))
        db.execute(delete(RequestResult).where(RequestResult.completed_at.is_(None),RequestResult.lease_expires_at<=current-timedelta(hours=48)))
        for r in db.scalars(select(Registration).where(Registration.deleted_at<=current-timedelta(hours=24)).with_for_update(skip_locked=True).limit(200)):
            r.preview=[]
            r.lookup_name='[deleted]'
            r.label='[deleted]'
        db.execute(delete(FetchLease).where(FetchLease.expires_at<=current-timedelta(minutes=90)))
        db.execute(delete(PreviewCache).where(PreviewCache.fetched_at<=current-timedelta(minutes=90)))
        db.execute(delete(LimitEvent).where(LimitEvent.created_at<=current-timedelta(minutes=2)))
        db.execute(delete(Audit).where(Audit.created_at<=current-timedelta(days=90)))
        db.execute(delete(PowerCache).where(
            or_(PowerCache.lease_expires_at.is_(None), PowerCache.lease_expires_at <= current),
            or_(PowerCache.checked_at <= current-timedelta(days=90),
                and_(PowerCache.status == 'unknown', PowerCache.value.is_(None)))))
