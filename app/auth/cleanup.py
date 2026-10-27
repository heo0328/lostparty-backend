import asyncio
from sqlalchemy import select, delete, update
from app.core.database import session, now
from app.auth.models import Transaction, Session, Credential, Recovery


def cleanup():
    with session() as db, db.begin():
        current = now(db)
        expired = select(Recovery.id).where(Recovery.expires_at <= current).limit(500).with_for_update(skip_locked=True)
        db.execute(delete(Recovery).where(Recovery.id.in_(expired)))
        transactions = select(Transaction.id).where(Transaction.expires_at <= current).limit(500).with_for_update(skip_locked=True)
        db.execute(delete(Transaction).where(Transaction.id.in_(transactions)))
    # Use the same user -> session locking order as refresh/logout.
    from app.auth.models import User
    with session() as db, db.begin():
        current = now(db)
        candidates = db.execute(select(Session.id, Session.user_id).where(Session.absolute_expires_at <= current).limit(500)).all()
        for sid, uid in candidates:
            if db.scalar(select(User.id).where(User.id == uid).with_for_update(skip_locked=True)) is None:
                continue
            s = db.scalar(select(Session).where(Session.id == sid).with_for_update(skip_locked=True))
            if s is None:
                continue
            ids = select(Credential.id).where(Credential.session_id == sid)
            db.execute(delete(Recovery).where(Recovery.old_id.in_(ids)))
            db.execute(update(Credential).where(Credential.session_id == sid).values(successor_id=None))
            db.execute(delete(Credential).where(Credential.session_id == sid))
            db.delete(s)


def cleanup_all():
    cleanup()
    from app.game_accounts.cleanup import clean
    clean()


async def run():
    from app.core.observability import run_job
    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(run_job, 'auth_cleanup', cleanup_all)
        except Exception:
            # run_job records a safe failure; preserve the existing retry loop.
            pass
