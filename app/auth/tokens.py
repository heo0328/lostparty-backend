import base64
import hashlib
import json
import secrets
import uuid
from datetime import timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings
from app.core.errors import AuthError
from app.auth.schemas import SessionOut, Tokens


def secret():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def configured_keys():
    try:
        private = serialization.load_pem_private_key(settings.signing_key(), password=None)
        if not isinstance(private, RSAPrivateKey) or private.key_size < 2048:
            raise ValueError()
        return private, settings.recovery_key()
    except Exception:
        raise AuthError("SERVICE_UNAVAILABLE", 503) from None


def session_out(s):
    return SessionOut(id=s.id, remember_me=s.remember_me, created_at=s.created_at,
                      absolute_expires_at=s.absolute_expires_at, idle_expires_at=s.idle_expires_at,
                      expires_at=min(s.absolute_expires_at, s.idle_expires_at))


def issue(s, current, refresh):
    key, _ = configured_keys()
    expires = min(current + timedelta(minutes=10), s.absolute_expires_at, s.idle_expires_at)
    # NumericDate uses seconds; keep DTO and actual JWT expiry identical.
    expires = expires.replace(microsecond=0)
    access = jwt.encode({"sub": str(s.user_id), "sid": str(s.id), "iss": settings.issuer,
                         "aud": settings.audience, "iat": current, "exp": expires,
                         "jti": str(uuid.uuid4())}, key, algorithm="RS256", headers={"kid": settings.jwt_kid})
    return Tokens(token_type="Bearer", access_token=access, access_expires_at=expires,
                  refresh_token=refresh, refresh_expires_at=min(s.absolute_expires_at, s.idle_expires_at),
                  session=session_out(s))


def verify_access(token):
    try:
        key, _ = configured_keys()
        if jwt.get_unverified_header(token).get("kid") != settings.jwt_kid:
            raise AuthError("ACCESS_INVALID")
        payload = jwt.decode(token, key.public_key(), algorithms=["RS256"], issuer=settings.issuer,
                             audience=settings.audience, options={"require": ["sub", "sid", "exp", "iat", "jti"]})
        return uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"])
    except jwt.ExpiredSignatureError:
        raise AuthError("ACCESS_EXPIRED") from None
    except AuthError:
        raise
    except Exception:
        raise AuthError("ACCESS_INVALID") from None


def aad(sid, old_id, generation, request_digest):
    return json.dumps({"v": 1, "sid": str(sid), "old": str(old_id), "generation": generation,
                       "request": request_digest}, sort_keys=True, separators=(",", ":")).encode()


def encrypt(value, associated):
    _, key = configured_keys()
    nonce = secrets.token_bytes(12)
    return nonce, AESGCM(key).encrypt(nonce, value.model_dump_json().encode(), associated)


def decrypt(recovery, associated):
    try:
        key = settings.recovery_key(recovery.key_id)
        return Tokens.model_validate_json(AESGCM(key).decrypt(recovery.nonce, recovery.ciphertext, associated))
    except Exception:
        raise AuthError("SERVICE_UNAVAILABLE", 503) from None
