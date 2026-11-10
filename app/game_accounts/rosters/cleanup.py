from datetime import timedelta
from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy import or_
from sqlalchemy import and_
from sqlalchemy import literal
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import session
from app.core.database import now
from app.lostark_keys.models import MemberPreview
from app.lostark_keys.models import MemberFetch
from app.lostark_keys.models import ProviderLimit
from app.game_accounts.common.support import lock
from app.game_accounts.models.models import RequestResult
from app.game_accounts.models.models import Verification
from app.game_accounts.models.models import PreviewCache
from app.game_accounts.models.models import LimitEvent
from app.game_accounts.models.models import Audit
from app.game_accounts.models.models import Registration
from app.game_accounts.models.models import FetchLease
from app.game_accounts.models.models import PowerCache
from app.game_accounts.models.models import ScopedPowerCache
from app.game_accounts.models.models import ScopedRosterCache
from app.game_accounts.models.models import ScopedRosterLease


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
        # Completed rows must not consume the next batch. Null-safe JSONB
        # comparison also repairs partial masking and JSON null previews.
        registrations = (select(Registration).where(
            Registration.deleted_at <= current-timedelta(hours=24),
            or_(Registration.preview.is_distinct_from(literal([], type_=JSONB)),
                Registration.lookup_name.is_distinct_from('[deleted]'),
                Registration.label.is_distinct_from('[deleted]')))
            .order_by(Registration.deleted_at, Registration.id)
            .with_for_update(skip_locked=True).limit(200))
        for r in db.scalars(registrations):
            r.preview=[]
            r.lookup_name='[deleted]'
            r.label='[deleted]'
        db.execute(delete(FetchLease).where(FetchLease.expires_at<=current-timedelta(minutes=90)))
        db.execute(delete(PreviewCache).where(PreviewCache.fetched_at<=current-timedelta(minutes=90)))
        db.execute(delete(ProviderLimit).where(ProviderLimit.blocked_until<=current-timedelta(minutes=2)))
        db.execute(delete(ScopedRosterLease).where(ScopedRosterLease.expires_at<=current-timedelta(minutes=90)))
        db.execute(delete(ScopedRosterCache).where(ScopedRosterCache.fetched_at<=current-timedelta(minutes=90)))
        db.execute(delete(MemberFetch).where(MemberFetch.expires_at<=current-timedelta(minutes=90)))
        db.execute(delete(MemberPreview).where(MemberPreview.fetched_at<=current-timedelta(minutes=90)))
        db.execute(delete(LimitEvent).where(LimitEvent.created_at<=current-timedelta(minutes=2)))
        db.execute(delete(Audit).where(Audit.created_at<=current-timedelta(days=90)))
        for cache in (PowerCache,ScopedPowerCache):
            db.execute(delete(cache).where(
                or_(cache.lease_expires_at.is_(None), cache.lease_expires_at <= current),
                or_(cache.checked_at <= current-timedelta(days=90),
                    and_(cache.status == 'unknown', cache.value.is_(None)))))
