import threading
import logging
import jwt
import requests
import cachecontrol
from google.auth.transport.requests import Request
from google.auth.exceptions import TransportError
from google.oauth2 import id_token
from app.core.config import settings
from app.core.errors import AuthError


class BoundedRequest(Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 5
        return super().__call__(*args, **kwargs)


_local = threading.local()
logger = logging.getLogger(__name__)


def verify_google(token, nonce_digest):
    from app.auth.tokens import digest
    stage = "algorithm"
    try:
        if jwt.get_unverified_header(token).get("alg") != "RS256":
            raise ValueError()
        if not hasattr(_local, "request"):
            _local.request = BoundedRequest(session=cachecontrol.CacheControl(requests.Session()))
        stage = "signature_audience_time"
        claims = id_token.verify_oauth2_token(token, _local.request, settings.google_audience,
                                            clock_skew_in_seconds=30)
        stage = "issuer"
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError()
        stage = "subject"
        if not isinstance(claims.get("sub"), str) or not 1 <= len(claims["sub"]) <= 255:
            raise ValueError()
        stage = "nonce"
        if not isinstance(claims.get("nonce"), str) or digest(claims["nonce"]) != nonce_digest:
            raise ValueError()
        stage = "azp_allowlist"
        if claims.get("azp") and claims["azp"] not in (settings.google_audience, *settings.google_azp):
            raise ValueError()
        return claims["sub"]
    except (TransportError, requests.RequestException):
        logger.warning("Google verification unavailable stage=%s", stage)
        raise AuthError("AUTH_PROVIDER_UNAVAILABLE", 503) from None
    except Exception:
        # Only a controlled stage name, never exception text, token or claims.
        logger.warning("Google proof rejected stage=%s", stage)
        raise AuthError("GOOGLE_PROOF_INVALID") from None
