"""Encrypted, member-visible codes; plaintext never enters the idempotency store."""
import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from app.core.config import settings
from app.core.database import session, now
from app.core.rate_limit import check
from app.game_accounts.support import authorize, fail
from app.game_accounts.models import Character, Account
from app.groups import service as groups, http_service, admissions
from app.groups import admission_core as core
from app.groups.admission_models import GroupJoinCode
from app.member_limits.models import MemberUsageLimits, MemberUsageHead

ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
COOLDOWN = timedelta(minutes=10)


def normalized(raw):
    value = raw.strip().upper()
    if len(value) != 6 or any(c not in ALPHABET for c in value):
        fail('GROUP_JOIN_CODE_INVALID', 404)
    return value


def key_material(kid, purpose):
    try:
        return hmac.new(settings.recovery_key(kid), purpose, hashlib.sha256).digest()
    except (OSError, ValueError):
        fail('GROUP_CODE_UNAVAILABLE', 503)


def digest(value, kid):
    return hmac.new(key_material(kid, b'group-join-code-lookup-v1'), value.encode(), hashlib.sha256).hexdigest()


def encrypt(value, group_id, code_id, kid):
    nonce = secrets.token_bytes(12)
    aad = f'group-code-v1:{group_id}:{code_id}'.encode()
    encrypted = AESGCM(key_material(kid, b'group-join-code-encryption-v1')).encrypt(nonce, value.encode(), aad)
    return nonce, encrypted


def decrypt(value):
    try:
        aad = f'group-code-v1:{value.group_id}:{value.id}'.encode()
        return AESGCM(key_material(value.key_id, b'group-join-code-encryption-v1')).decrypt(value.nonce, value.ciphertext, aad).decode()
    except (ValueError, UnicodeError):
        fail('GROUP_CODE_UNAVAILABLE', 503)
    except Exception as error:
        from cryptography.exceptions import InvalidTag
        if isinstance(error, InvalidTag):
            fail('GROUP_CODE_UNAVAILABLE', 503)
        raise


def lookup(db, raw):
    value = normalized(raw)
    # Keep historical key IDs so original completed commands remain recoverable after revocation/rotation.
    kids = list(db.scalars(select(GroupJoinCode.key_id).distinct()))
    for kid in kids:
        row = db.scalar(select(GroupJoinCode).where(GroupJoinCode.digest == digest(value, kid)))
        if row is not None:
            return row
    return None


def latest(db, gid):
    return db.scalar(select(GroupJoinCode).where(GroupJoinCode.group_id == gid)
                     .order_by(GroupJoinCode.created_at.desc(), GroupJoinCode.id.desc()).limit(1))


def metadata(value):
    return dict(code_id=value.id if value else None, revision=value.revision if value else 1,
                active=value is not None and value.revoked_at is None,
                visible_to_members=bool(value.visible_to_members) if value else False,
                code=None, created_at=value.created_at if value else None,
                regenerate_available_at=value.created_at+COOLDOWN if value else None)


def may_read(db, uid, group, code):
    membership = groups.member(db, uid, group)
    return membership.id == group.leader_membership_id or bool(code.visible_to_members)


def get(principal, gid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        group = groups.group(db, gid)
        groups.member(db, uid, group)
        code = latest(db, gid)
        out = metadata(code)
        if code and code.revoked_at is None and may_read(db, uid, group, code):
            out['code'] = decrypt(code)
        return out


def code_cas(code, data):
    if (str(code.id) if code else None) != (str(data['expected_code_id']) if data['expected_code_id'] else None):
        fail('REVISION_CONFLICT')
    if (code.revision if code else 1) != data['expected_code_revision']:
        fail('REVISION_CONFLICT')


def mutate(principal, gid, operation, key, command):
    from fastapi.encoders import jsonable_encoder
    data = jsonable_encoder(command)
    def check_replay(db, uid, body):
        core.leader(db, uid, groups.group(db, gid))
    def run(db, uid):
        group = groups.group(db, gid)
        membership = core.leader(db, uid, group)
        admissions.group_cas(group, data, membership)
        old = latest(db, gid)
        code_cas(old, data)
        current = now(db)
        if operation in ('create', 'regenerate'):
            if operation == 'create' and old and old.revoked_at is None:
                fail('GROUP_CODE_ALREADY_ACTIVE')
            if operation == 'regenerate' and (old is None or old.revoked_at is not None):
                fail('GROUP_JOIN_CODE_INVALID', 404)
            if old and current < old.created_at+COOLDOWN:
                fail('GROUP_CODE_REGENERATION_COOLDOWN')
            raw = None
            for _ in range(32):
                candidate = ''.join(secrets.choice(ALPHABET) for _ in range(6))
                if any(c.isdigit() for c in candidate) and any(c.isalpha() for c in candidate) and lookup(db, candidate) is None:
                    raw = candidate
                    break
            if raw is None:
                fail('GROUP_CODE_UNAVAILABLE', 503)
            if old and old.revoked_at is None:
                old.revoked_at = current
                old.revision += 1
                db.flush()
            cid = uuid.uuid4()
            nonce, ciphertext = encrypt(raw, gid, cid, settings.recovery_kid)
            code = GroupJoinCode(id=cid, group_id=gid, revision=1, digest=digest(raw, settings.recovery_kid),
                                 key_id=settings.recovery_kid, nonce=nonce, ciphertext=ciphertext,
                                 visible_to_members=int(data.get('visible_to_members', bool(old.visible_to_members) if old else False)),
                                 created_at=current)
            db.add(code); db.flush()
        else:
            if old is None:
                fail('GROUP_JOIN_CODE_INVALID', 404)
            code = old
            if operation == 'revoke':
                if code.revoked_at is None:
                    code.revoked_at = current
                    code.revision += 1
            else:
                if code.revoked_at is not None:
                    fail('GROUP_JOIN_CODE_INVALID', 404)
                if bool(code.visible_to_members) != data['visible_to_members']:
                    code.visible_to_members = int(data['visible_to_members'])
                    code.revision += 1
        return 201 if operation == 'create' else 200, metadata(code), None
    status, result = admissions.execute(principal, 'group-code-'+operation, key,
                       dict(group_id=str(gid), body=data), run, check_replay)
    # Persisted ACK contains metadata only. Re-authorize before adding a secret to the HTTP response.
    if operation in ('create', 'regenerate', 'visibility') and result['active']:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            uid = authorize(db, principal)
            group = groups.group(db, gid)
            core.leader(db, uid, group)
            code = db.get(GroupJoinCode, uuid.UUID(str(result['code_id'])))
            result = dict(result, code=decrypt(code))
    return status, result


def check_attempt(principal, client_host):
    # Single-process local deployment, matching the existing auth limiter. No proxy-header trust.
    check(('group-code-member', str(principal[0].id)), 20)
    check(('group-code-host', client_host), 60)


def preview(principal, raw, client_host):
    check_attempt(principal, client_host)
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        code = lookup(db, raw)
        if code is None or code.revoked_at is not None:
            fail('GROUP_JOIN_CODE_INVALID', 404)
        group = groups.group(db, code.group_id)
        core.require_unblocked(db, group, uid)
        # Visibility affects display only; a previously copied private code remains usable.
        return dict(group=groups.summary(db, group), members_revision=group.members_revision,
                    code_id=code.id, code_revision=code.revision)


def join(principal, key, command, client_host):
    from fastapi.encoders import jsonable_encoder
    data = jsonable_encoder(command)
    check_attempt(principal, client_host)
    with session() as db, db.begin():
        authorize(db, principal)
        row = lookup(db, data['code'])
        if row is None:
            fail('GROUP_JOIN_CODE_INVALID', 404)
        cid = row.id
    safe = {key: value for key, value in data.items() if key != 'code'}
    # A retained, resolved code ID is stable across revoke/rotate and avoids plaintext/guessable body digests.
    safe['resolved_code_id'] = str(cid)
    def run(db, uid):
        code = db.get(GroupJoinCode, cid)
        if code.revoked_at is not None:
            fail('GROUP_JOIN_CODE_INVALID', 404)
        if str(code.id) != data['expected_code_id'] or code.revision != data['expected_code_revision']:
            fail('REVISION_CONFLICT')
        group = groups.group(db, code.group_id)
        admissions.group_cas(group, data)
        row, head = db.get(MemberUsageLimits, uid), db.get(MemberUsageHead, uid)
        if ((row.revision if row else 1) != data['expected_limits_revision'] or
                (head.revision if head else 1) != data['expected_usage_revision']):
            fail('POLICY_CONTEXT_CHANGED')
        membership = core.admit(db, group, uid, data)
        current = now(db)
        pending = core.pending(db, group, uid, current)
        if pending:
            core.finish(pending, 'joined_by_code', current)
        subject = core.subject(db, group, uid, create=True, snapshot=membership.display)
        subject.display = membership.display
        from app.groups.features import remember
        character = db.get(Character, uuid.UUID(data['character_id']))
        remember(db, subject, character, db.get(Account, character.account_id))
        admissions.touch(subject, current)
        return 200, http_service.detail(db, group, membership), None
    return admissions.execute(principal, 'group-code-join', key, safe, run, admissions.check_replay_membership)
