"""Domain-separated keyset cursor; original expiry is never extended."""
import base64
import hashlib
import hmac
import json
import re
from datetime import datetime
from uuid import UUID
from app.core.config import settings
from app.game_accounts.common.support import fail

DOMAIN = b'personal-reservations-1:'

def encode(scope, revision, last, expires):
    raw = json.dumps(dict(scope=scope, revision=revision, last=last, expires=expires),
                     sort_keys=True, separators=(',', ':')).encode()
    signature = hmac.new(settings.recovery_key(), DOMAIN + raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + signature).decode().rstrip('=')

def decode(token, scope, revision, stamp):
    try:
        if not 1 <= len(token) <= 8192 or re.fullmatch(r'[A-Za-z0-9_-]+', token) is None:
            raise ValueError()
        raw = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        data, signature = raw[:-32], raw[-32:]
        expected = hmac.new(settings.recovery_key(), DOMAIN + data, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected): raise ValueError()
        value = json.loads(data)
        if set(value) != {'scope', 'revision', 'last', 'expires'} or value['scope'] != scope:
            raise ValueError()
        if type(value['expires']) is not int or type(value['last']) is not list or len(value['last']) != 2:
            raise ValueError()
        instant = datetime.fromisoformat(value['last'][0].replace('Z', '+00:00'))
        if instant.utcoffset() is None or str(UUID(value['last'][1])) != value['last'][1]: raise ValueError()
        if not isinstance(value['revision'], str): raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        fail('INVALID_REQUEST', 400)
    if value['revision'] != revision or stamp.timestamp() >= value['expires']:
        fail('CURSOR_STALE', 409)
    return value['last'], value['expires']
