"""Bounded analysis commands. Workers observe; the request thread commits fenced heads."""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from app.core.database import session, now
from app.core.errors import AuthError
from app.game_accounts.common.support import authorize, fail, reserve, commit_result
from app.game_accounts.character_profiles.profiles import owned_character
from app.game_accounts.models.models import Character, Account, Registration, Configuration, Activity, CharacterRoleSummary, RequestResult
from app.member_settings.models import MemberSettings
from app.game_accounts.provider_io import credentials
from app.game_accounts.analysis.fresh import collect
from app.game_accounts.schemas.analysis_schemas import AnalysisResult

OPERATION = 'character-analysis-refresh'
BUDGET_SECONDS = 20


def outcome(command, state, status, request_id, *, code=None, role=None, result=None, retry=None, retry_after=None, retry_at=None):
    if retry is None:
        retry = 'new_command' if code in ('REVISION_CONFLICT','UPSTREAM_NOT_CONFIGURED','LOSTARK_KEY_REJECTED','SERVER_KEY_CHANGED',
            'RATE_LIMITED','UPSTREAM_RATE_LIMITED','UPSTREAM_BUSY','UPSTREAM_UNAVAILABLE','UPSTREAM_INVALID_RESPONSE',
            'UPSTREAM_RESPONSE_TOO_LARGE','ANALYSIS_UNAVAILABLE','ROLE_DETECTION_UNAVAILABLE') else 'none'
    return dict(command_id=command.command_id, character_id=command.character_id, status=status, state=state,
        detected_role=role, retry=retry, result=result,
        error=dict(code=code, message=code, request_id=request_id, retry_after_seconds=retry_after,
                   retry_at=retry_at) if code else None)


def eligible(db, uid, account, character, trigger):
    if trigger == 'manual':
        return True
    conf = db.scalar(select(Configuration).where(Configuration.user_id==uid, Configuration.account_id==account.id,
                                                Configuration.ended_at.is_(None)))
    if conf is None or db.get(Activity, (conf.id, character.id)) is None:
        return False
    settings = db.get(MemberSettings, uid)
    if settings and settings.nice_group_auto_refresh_enabled:
        return True
    # NiceGroupPolicy counts the whole owned active roster, not just selected activity.
    others = db.scalars(select(Character).join(Account, Account.id==Character.account_id).join(
        Registration, Registration.account_id==Account.id).where(Account.owner_id==uid,
            Registration.user_id==uid, Registration.deleted_at.is_(None), Character.lifecycle_state=='active'))
    count = 0
    for row in others:
        if row.summary.get('class_name') != character.summary.get('class_name'):
            continue
        try:
            level = Decimal(row.summary.get('item_level') or '0')
            count += int(level.is_finite() and level >= 1700)
        except (InvalidOperation, TypeError, ValueError):
            continue
    return count < 2


def target(db, principal, command, *, write=False):
    uid = authorize(db, principal, write=write)
    account, character = owned_character(db, uid, command.character_id, write=True)
    if (account.ownership_revision != command.expected_ownership_revision or
            character.lifecycle_revision != command.expected_lifecycle_revision):
        fail('REVISION_CONFLICT')
    return uid, account, character


def scoped(db):
    db.execute(text("SET LOCAL statement_timeout = '500ms'"))
    db.execute(text("SET LOCAL lock_timeout = '500ms'"))


def existing(principal, command):
    with session() as db:
        scoped(db)
        target(db, principal, command)
        return db.scalar(select(RequestResult.id).where(RequestResult.actor_id==principal[0].id,
            RequestResult.operation==OPERATION, RequestResult.key==command.command_id)) is not None


def start(principal, command, request_id, deadline):
    with session() as db:
        scoped(db)
        target(db, principal, command)
    if time.monotonic() >= deadline-9 and not existing(principal, command):
        return None, outcome(command, 'not_processed', 503, request_id, code='BATCH_NOT_PROCESSED', retry='same_command'), None
    with session() as db:
        scoped(db)
        uid, account, character = target(db, principal, command)
        included = eligible(db, uid, account, character, command.trigger)
        selection = dict(character_id=character.id, ownership_revision=account.ownership_revision,
                    lifecycle_revision=character.lifecycle_revision, server_name=character.server_name,
                    character_name=character.character_name, class_name=character.summary.get('class_name'))
    ticket, replay = reserve(principal, OPERATION, command.command_id, command.model_dump(mode='json', exclude={'command_id'}))
    if replay:
        return None, replay[1], None
    if time.monotonic() >= deadline-9:
        return ticket, outcome(command, 'unknown', 503, request_id, code='SERVICE_UNAVAILABLE', retry='same_command'), None
    if not included:
        return ticket, outcome(command, 'skipped', 200, request_id, code='AUTOMATIC_TARGET_EXCLUDED'), None
    if not isinstance(selection['class_name'],str) or not selection['class_name'].strip():
        return ticket, outcome(command,'failed',503,request_id,code='ROLE_DETECTION_UNAVAILABLE'), None
    return ticket, None, selection


def save(principal, command, ticket, observed, snapshot, request_id, deadline, selection):
    with session() as db, db.begin():
        scoped(db)
        uid, account, character = target(db, principal, command, write=True)
        credentials.check(db, principal, snapshot)
        if (character.server_name,character.character_name,character.summary.get('class_name')) != (
                selection['server_name'],selection['character_name'],selection['class_name']):
            fail('REVISION_CONFLICT')
        if time.monotonic() >= deadline:
            fail('UPSTREAM_UNAVAILABLE', 503)
        if not eligible(db, uid, account, character, command.trigger):
            result = outcome(command, 'skipped', 200, request_id, code='AUTOMATIC_TARGET_EXCLUDED')
        else:
            role = observed['role']
            head = db.get(CharacterRoleSummary, (uid, character.id, account.ownership_revision, role))
            version = head.version if head else 1
            if version != getattr(command.expected_summary_versions, role) or version >= 2147483647:
                fail('REVISION_CONFLICT')
            # Validate projection and correlated provenance before any business write.
            at = now(db)
            result = AnalysisResult.model_validate(dict(character_id=character.id, game_account_id=account.id,
                ownership_revision=account.ownership_revision, lifecycle_revision=character.lifecycle_revision,
                role=role, analysis=dict(version=version+1, saved_at=at, summary=observed['summary'], detail=observed['detail'])))
            if head is None:
                head = CharacterRoleSummary(user_id=uid, character_id=character.id, ownership_revision=account.ownership_revision, role=role)
                db.add(head)
            head.version, head.summary, head.detail, head.saved_at = version+1, observed['summary'], observed['detail'], at
            result = outcome(command, 'saved', 200, request_id, role=role, result=jsonable_encoder(result))
        commit_result(db, ticket, result['status'], result)
        return result


def finish(ticket, result):
    with session() as db, db.begin():
        scoped(db)
        commit_result(db, ticket, result['status'], result)
    return result


def rejected(command, request_id, exc):
    if exc.code == 'REQUEST_IN_PROGRESS':
        return outcome(command,'in_progress',409,request_id,code=exc.code,retry='same_command',retry_after=2)
    return outcome(command,'failed',exc.status,request_id,code=exc.code,
                   retry_after=getattr(exc,'retry_after',None),retry_at=getattr(exc,'retry_at',None))


def refresh(principal, data, request_id):
    deadline = time.monotonic()+BUDGET_SECONDS
    with session() as db:
        scoped(db)
        authorize(db, principal)
    results = [None]*len(data.items)
    pool = ThreadPoolExecutor(max_workers=2)
    pending = {}
    next_index = 0
    try:
        while next_index < len(data.items) or pending:
            while next_index < len(data.items) and len(pending) < 2:
                index = next_index;next_index += 1
                command = data.items[index];ticket = None
                if index>0 and time.monotonic()>=deadline:
                    results[index]=outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
                    continue
                try:
                    ticket, immediate, selection = start(principal, command, request_id, deadline)
                    if immediate is not None:
                        results[index] = finish(ticket, immediate) if ticket and immediate['state'] in ('skipped','failed') else immediate
                        continue
                    snapshot = credentials.capture()
                    future = pool.submit(collect, principal, selection, snapshot, deadline-1)
                    pending[future] = (index, command, ticket, snapshot, selection)
                except AuthError as exc:
                    result = rejected(command, request_id, exc)
                    try:
                        results[index] = finish(ticket,result) if ticket else result
                    except (SQLAlchemyError, AuthError):
                        results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
                except SQLAlchemyError:
                    results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
            if not pending:
                continue
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                for future, (index, command, ticket, snapshot, selection) in pending.items():
                    future.cancel()
                    results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
                pending.clear()
                continue
            done, _ = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
            for future in done:
                index, command, ticket, snapshot, selection = pending.pop(future)
                try:
                    observed = future.result()
                    results[index] = save(principal, command, ticket, observed, snapshot, request_id, deadline, selection)
                except (AuthError, ValidationError) as exc:
                    result = rejected(command, request_id, exc) if isinstance(exc,AuthError) else outcome(command,'failed',503,request_id,code='ANALYSIS_UNAVAILABLE')
                    try:
                        results[index] = finish(ticket,result)
                    except (SQLAlchemyError, AuthError):
                        results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
                except Exception:
                    # Commit may have succeeded. Do not release or overwrite its ledger.
                    results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
        for future, (index, command, ticket, snapshot, selection) in pending.items():
            future.cancel()
            results[index] = outcome(command,'unknown',503,request_id,code='SERVICE_UNAVAILABLE',retry='same_command')
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return dict(evaluated_at=datetime.now(timezone.utc), items=results)
