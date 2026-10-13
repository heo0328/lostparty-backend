import hmac
from datetime import timedelta
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from app.auth.models import User, Identity, Transaction, Session, Credential, Recovery
from app.auth import tokens
from app.auth.google import verify_google
from app.auth.schemas import ChallengeOut, LoginOut, UserOut
from app.core.database import session, now
from app.core.errors import AuthError
from app.core.config import settings
from app.core.rate_limit import check as rate_check

ISSUER = "https://accounts.google.com"


def user_out(u):
    return UserOut(id=u.id, status=u.status, created_at=u.created_at)


def idle(s):
    return timedelta(days=7) if s.remember_me else timedelta(hours=2)


def active(u, s, current, refresh=False):
    if u.status != "active":
        raise AuthError("ACCOUNT_DISABLED", 403)
    if s.revoked_at:
        raise AuthError("SESSION_REVOKED")
    if current >= min(s.absolute_expires_at, s.idle_expires_at):
        raise AuthError("REFRESH_EXPIRED" if refresh else "SESSION_EXPIRED")


def challenge(data):
    tokens.configured_keys()
    nonce = tokens.secret()
    with session() as db, db.begin():
        current = now(db)
        transaction = Transaction(nonce_digest=tokens.digest(nonce), secret_digest=data.transaction_secret_hash,
                                  expires_at=current + timedelta(minutes=5))
        db.add(transaction)
        db.flush()
        result = ChallengeOut(transaction_id=transaction.id, nonce=nonce, expires_at=transaction.expires_at)
    return result


def check_transaction(t, data, current):
    if t is None or not hmac.compare_digest(t.secret_digest, tokens.digest(data.transaction_secret)):
        raise AuthError("AUTH_TRANSACTION_INVALID", 400)
    if current >= t.expires_at:
        raise AuthError("AUTH_TRANSACTION_EXPIRED")
    if t.consumed_at:
        raise AuthError("AUTH_TRANSACTION_CONSUMED")


def login(data):
    tokens.configured_keys()
    with session() as db:
        t = db.get(Transaction, data.transaction_id)
        check_transaction(t, data, now(db))
        subject = verify_google(data.google_id_token, t.nonce_digest)
    # Uniqueness race rolls back every insert, then retries using winning identity.
    for attempt in range(3):
        try:
            with session() as db, db.begin():
                t = db.scalar(select(Transaction).where(Transaction.id == data.transaction_id).with_for_update())
                current = now(db)
                check_transaction(t, data, current)
                identity = db.scalar(select(Identity).where(Identity.provider == "google", Identity.issuer == ISSUER, Identity.subject == subject))
                new = identity is None
                if new:
                    u = User(created_at=current, updated_at=current, last_login_at=current)
                    db.add(u)
                    db.flush()
                    db.add(Identity(user_id=u.id, provider="google", issuer=ISSUER, subject=subject, linked_at=current))
                    db.flush()
                else:
                    u = db.scalar(select(User).where(User.id == identity.user_id).with_for_update())
                if u.status != "active":
                    raise AuthError("ACCOUNT_DISABLED", 403)
                u.last_login_at = u.updated_at = current
                s = Session(user_id=u.id, remember_me=data.remember_me, created_at=current,
                            absolute_expires_at=current + (timedelta(days=30) if data.remember_me else timedelta(hours=12)),
                            idle_expires_at=current + (timedelta(days=7) if data.remember_me else timedelta(hours=2)))
                db.add(s)
                db.flush()
                refresh = tokens.secret()
                db.add(Credential(session_id=s.id, generation=0, token_digest=tokens.digest(refresh),
                                  issued_at=current, expires_at=min(s.absolute_expires_at, s.idle_expires_at)))
                t.consumed_at = current
                result = LoginOut(**tokens.issue(s, current, refresh).model_dump(), user=user_out(u), is_new_user=new)
            return result
        except IntegrityError:
            if attempt == 2:
                raise AuthError("SERVICE_UNAVAILABLE", 503) from None


def locked(db, token):
    c = db.scalar(select(Credential).where(Credential.token_digest == tokens.digest(token)))
    if c is None:
        raise AuthError("REFRESH_INVALID")
    s = db.get(Session, c.session_id)
    u = db.scalar(select(User).where(User.id == s.user_id).with_for_update())
    s = db.scalar(select(Session).where(Session.id == s.id).with_for_update().execution_options(populate_existing=True))
    c = db.scalar(select(Credential).where(Credential.id == c.id).with_for_update().execution_options(populate_existing=True))
    return u, s, c


def remove_recoveries(db, s):
    ids = select(Credential.id).where(Credential.session_id == s.id)
    db.execute(delete(Recovery).where(Recovery.old_id.in_(ids)))


def refresh(data):
    error = None
    with session() as db, db.begin():
        u, s, c = locked(db, data.refresh_token)
        current = now(db)
        active(u, s, current, refresh=True)
        rate_check(("refresh-session", str(s.id)), 30)
        request_hash = tokens.digest(data.refresh_request_id)
        if c.consumed_at:
            if c.request_digest != request_hash:
                s.revoked_at, s.revoked_reason = current, "refresh_reused"
                remove_recoveries(db, s)
                error = AuthError("REFRESH_REUSED")
            else:
                successor = db.get(Credential, c.successor_id)
                if successor and successor.consumed_at:
                    raise AuthError("REFRESH_RESULT_SUPERSEDED", 409)
                r = db.scalar(select(Recovery).where(Recovery.old_id == c.id).with_for_update())
                if r is None or current >= r.expires_at:
                    raise AuthError("REFRESH_RECOVERY_EXPIRED", 409)
                if r.resend_count >= 2:
                    raise AuthError("REFRESH_RECOVERY_LIMITED", 409)
                result = tokens.decrypt(r, tokens.aad(s.id, c.id, successor.generation, request_hash))
                r.resend_count += 1
        else:
            if db.scalar(select(Credential.id).where(Credential.session_id == s.id, Credential.request_digest == request_hash)):
                raise AuthError("INVALID_REQUEST", 400)
            s.idle_expires_at = min(current + idle(s), s.absolute_expires_at)
            raw = tokens.secret()
            successor = Credential(session_id=s.id, generation=c.generation + 1, token_digest=tokens.digest(raw),
                                   issued_at=current, expires_at=min(s.absolute_expires_at, s.idle_expires_at))
            db.add(successor)
            db.flush()
            # Previously recovered result is no longer usable once its successor is consumed.
            db.execute(delete(Recovery).where(Recovery.successor_id == c.id))
            c.consumed_at, c.request_digest, c.successor_id = current, request_hash, successor.id
            result = tokens.issue(s, current, raw)
            nonce, ciphertext = tokens.encrypt(result, tokens.aad(s.id, c.id, successor.generation, request_hash))
            db.add(Recovery(old_id=c.id, successor_id=successor.id, request_digest=request_hash,
                            expires_at=now(db) + timedelta(seconds=60), resend_count=0,
                            key_id=settings.recovery_kid, nonce=nonce, ciphertext=ciphertext))
        # Raising replay error inside db.begin would roll back session revocation.
    if error:
        raise error
    return result


def logout(data):
    with session() as db, db.begin():
        _, s, _ = locked(db, data.refresh_token)
        current = now(db)
        if current >= s.absolute_expires_at:
            raise AuthError("REFRESH_INVALID")
        if not s.revoked_at:
            s.revoked_at, s.revoked_reason = current, "logout"
        remove_recoveries(db, s)


def principal(token):
    uid, sid = tokens.verify_access(token)
    with session() as db:
        u, s = db.get(User, uid), db.get(Session, sid)
        if u is None or s is None or s.user_id != uid:
            raise AuthError("SESSION_REVOKED")
        active(u, s, now(db))
        return user_out(u), tokens.session_out(s)
