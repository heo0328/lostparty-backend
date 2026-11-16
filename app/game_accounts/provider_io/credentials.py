"""One server-only credential. No member credential database or wire representation."""
import hashlib
import hmac
from dataclasses import dataclass, field
from pathlib import Path
from app.core.config import settings
from app.game_accounts.common.support import authorize, fail


@dataclass(frozen=True, repr=False)
class Snapshot:
    generation: str = field(repr=False)
    fingerprint: str = field(repr=False)
    token: str = field(repr=False)

    def __repr__(self):
        return '<server Lost Ark credential redacted>'


def capture():
    try:
        token = Path(settings.secret_dir, 'lostark-api-token').read_text(encoding='ascii').strip()
    except FileNotFoundError:
        fail('UPSTREAM_NOT_CONFIGURED', 503)
    except (OSError, UnicodeError):
        fail('UPSTREAM_NOT_CONFIGURED', 503)
    try:
        material = Path(settings.secret_dir, 'lostark-fingerprint.key').read_bytes()
        if len(material) != 32 or not token or len(token) > 16384 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError()
        generation = hmac.new(material, b'server-lostark-v1:' + token.encode('ascii'), hashlib.sha256).hexdigest()
        return Snapshot(generation, generation, token)
    except (OSError, ValueError):
        fail('UPSTREAM_NOT_CONFIGURED', 503)


def current(snapshot):
    if not hmac.compare_digest(capture().generation, snapshot.generation):
        fail('SERVER_KEY_CHANGED', 503)


def check(db, principal, snapshot):
    authorize(db, principal)
    current(snapshot)


def before_call(principal, snapshot):
    from app.core.database import session
    from app.game_accounts.provider_io.rate_limits import acquire
    with session() as db:
        check(db, principal, snapshot)
    acquire(snapshot.fingerprint)
