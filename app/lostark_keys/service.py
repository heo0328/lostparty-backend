"""Member secrets: never serialize snapshots or include token in dedup payloads."""
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings
from app.core.database import session, now
from app.game_accounts.support import authorize, fail, reserve, release, commit_result, quota
from app.lostark_keys.models import Credential


def material(kind, kid=None):
    try:
        current = os.getenv('LOSTARK_CREDENTIAL_KEY_ID', 'local-1')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', current) or (kid and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', kid)):
            raise ValueError()
        name = 'lostark-fingerprint.key' if kind == 'fingerprint' else (
            'lostark-credential.key' if kid is None or kid == current else f'lostark-credential-{kid}.key')
        key = Path(settings.secret_dir, name).read_bytes()
        if len(key) != 32:
            raise ValueError()
        return key
    except Exception:
        fail('LOSTARK_KEY_UNAVAILABLE', 503)


def fingerprint(token):
    return hmac.new(material('fingerprint'), b'credential-fingerprint-v1:' + token.encode('ascii'), hashlib.sha256).hexdigest()


def aad(uid, version, kid):
    return json.dumps({'format': 1, 'user_id': str(uid), 'version': version, 'key_id': kid},
                      sort_keys=True, separators=(',', ':')).encode()


def output(row):
    return {'configured': row is not None and row.ciphertext is not None,
            'version': row.version if row else 1, 'updated_at': row.updated_at if row else None}


def get(principal):
    with session() as db, db.begin():
        uid = authorize(db, principal)
        return output(db.get(Credential, uid))


def mutate(principal, key, version, token=None):
    digest = fingerprint(token) if token is not None else None
    ticket, replay = reserve(principal, 'lostark-key-put' if token is not None else 'lostark-key-delete', key,
                             {'target': '/v1/me/lostark-api-key', 'version': version, 'fingerprint': digest})
    if replay:
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            row = db.get(Credential, uid)
            if output(row)['version'] != version:
                fail('REVISION_CONFLICT')
            if token is not None:
                kid = os.getenv('LOSTARK_CREDENTIAL_KEY_ID', 'local-1')
                encryption_key = material('encryption')
                if row is None:
                    row = Credential(user_id=uid, version=1)
                    db.add(row)
                row.version += 1
                row.nonce = os.urandom(12)
                row.key_id = kid
                row.ciphertext = AESGCM(encryption_key).encrypt(row.nonce, token.encode('ascii'), aad(uid, row.version, kid))
                row.fingerprint = digest
                row.updated_at = now(db)
            elif row is not None and row.ciphertext is not None:
                row.version += 1
                row.ciphertext = row.nonce = row.key_id = row.fingerprint = None
                row.updated_at = now(db)
            db.flush()
            return commit_result(db, ticket, 200, output(row))
    except Exception:
        release(ticket)
        raise


@dataclass(frozen=True, repr=False)
class Snapshot:
    user_id: object
    version: int
    fingerprint: str = field(repr=False)
    token: str = field(repr=False)
    def __repr__(self):
        return '<Lost Ark credential snapshot redacted>'


def capture(principal):
    with session() as db, db.begin():
        uid = authorize(db, principal)
        row = db.get(Credential, uid)
        if row is None or row.ciphertext is None:
            fail('LOSTARK_KEY_NOT_CONFIGURED')
        try:
            token = AESGCM(material('encryption', row.key_id)).decrypt(row.nonce, row.ciphertext,
                         aad(uid, row.version, row.key_id)).decode('ascii')
            if not hmac.compare_digest(row.fingerprint, fingerprint(token)):
                raise ValueError()
            return Snapshot(uid, row.version, row.fingerprint, token)
        except Exception:
            fail('LOSTARK_KEY_UNAVAILABLE', 503)


def check(db, principal, snapshot):
    # Caller holds the shared mutation lock, or this read is only a pre-call check.
    uid = authorize(db, principal)
    row = db.get(Credential, uid, populate_existing=True)
    if uid != snapshot.user_id or row is None or row.ciphertext is None or row.version != snapshot.version:
        fail('LOSTARK_KEY_CHANGED')


def before_call(principal, snapshot):
    with session() as db, db.begin():
        check(db, principal, snapshot)
    quota('lostark-token:' + snapshot.fingerprint, 80)
