"""G2 requests, current roles and atomic membership admission. No provider I/O."""
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.auth.models import User
from app.core.database import session, now
from app.core.rate_limit import check
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Character, Registration
from app.game_accounts.support import authorize, fail, reserve, release, commit_result, cursor_encode, cursor_decode
from app.groups import service as groups, http_service
from app.groups import admission_core as core
from app.groups.models import Group, GroupMembership
from app.groups.admission_models import GroupJoinSubject, GroupJoinRelation
from app.member_limits.models import MemberUsageLimits, MemberUsageHead


def execute(principal, operation, key, payload, run, replay_check):
    ticket, replay = reserve(principal, operation, key, payload)
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            replay_check(db, authorize(db, principal), replay[1])
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            status, body, final_guard = run(db, uid)
            result = commit_result(db, ticket, status, body)
            db.flush()
            if final_guard:
                final_guard(now(db))
            return result
    except Exception:
        release(ticket)
        raise


def group_cas(value, data, membership=None):
    if value.revision != data['expected_group_revision']:
        fail('REVISION_CONFLICT')
    if 'expected_members_revision' in data and value.members_revision != data['expected_members_revision']:
        fail('REVISION_CONFLICT')
    if membership is not None and membership.revision != data['expected_membership_revision']:
        fail('REVISION_CONFLICT')


def touch(subject, current):
    subject.revision += 1
    subject.updated_at = current


def relation(db, rid):
    value = db.get(GroupJoinRelation, rid)
    if value is None:
        fail('GROUP_RELATION_NOT_FOUND', 404)
    groups.group(db, value.group_id)
    return value


def role(db, uid, value):
    group = groups.group(db, value.group_id)
    membership = db.scalar(select(GroupMembership).where(GroupMembership.group_id == group.id,
                          GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None)))
    is_leader = membership is not None and membership.id == group.leader_membership_id
    is_sender = (value.kind == 'invitation' and membership is not None and
                 membership.id == value.issuer_membership_id and value.issuer_user_id == uid)
    is_target = value.target_user_id == uid
    if not (is_target or is_sender or is_leader):
        fail('GROUP_RELATION_FORBIDDEN', 403)
    return group, is_target, is_sender, is_leader


def output(db, uid, value, current=None):
    group, target, sender, leader = role(db, uid, value)
    state = core.relation_state(db, value, current or now(db))
    subject = db.get(GroupJoinSubject, value.subject_id)
    pending = state == 'pending'
    def permission(allowed):
        return dict(allowed=bool(allowed), reason=None if allowed else 'RELATION_NOT_PENDING' if not pending else 'GROUP_RELATION_FORBIDDEN')
    return dict(relation_id=value.id, subject_id=value.subject_id, kind=value.kind, state=state,
                revision=value.revision, group=groups.summary(db, group), members_revision=group.members_revision,
                display=groups.display(value.display), created_at=value.created_at, expires_at=value.expires_at,
                ended_at=value.expires_at if state == 'expired' and value.ended_at is None else value.ended_at,
                application_count=subject.application_count,
                permissions=dict(accept=permission(pending and target and value.kind == 'invitation'),
                    approve=permission(pending and leader and value.kind == 'application'),
                    reject=permission(pending and ((target and value.kind == 'invitation') or (leader and value.kind == 'application'))),
                    cancel=permission(pending and ((target and value.kind == 'application') or (value.kind == 'invitation' and (sender or leader)))),
                    block=permission(leader)))


def check_replay_relation(db, uid, body):
    role(db, uid, relation(db, uuid.UUID(body['relation_id'])))


def check_replay_membership(db, uid, body):
    groups.member(db, uid, groups.group(db, uuid.UUID(body['group']['group_id'])))


def decimal_string(value):
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
        return str(value) if parsed.is_finite() and parsed >= 0 else None
    except InvalidOperation:
        return None


def invitation_target(db, cid):
    character = db.get(Character, cid)
    account = db.get(Account, character.account_id) if character else None
    user = db.get(User, account.owner_id) if account and account.owner_id else None
    registration = db.scalar(select(Registration.id).where(Registration.account_id == account.id,
                Registration.user_id == account.owner_id, Registration.deleted_at.is_(None))) if account else None
    if (not character or not account or not user or user.status != 'active' or
            account.verified_at is None or registration is None or not lifecycle.usable(db, character)):
        fail('GROUP_TARGET_UNAVAILABLE', 404)
    return character, account


def candidates(principal, gid, name):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        groups.member(db, uid, groups.group(db, gid))
        check(('group-invite-search', str(uid)), 30)
        rows = db.scalars(select(Character.id).where(Character.character_name == name.strip())
                          .order_by(Character.server_name, Character.id).limit(50))
        items = []
        for cid in rows:
            try:
                c, account = invitation_target(db, cid)
            except Exception as error:
                from app.game_accounts.support import GameError
                if isinstance(error, GameError) and error.code == 'GROUP_TARGET_UNAVAILABLE':
                    continue
                raise
            items.append(dict(target_character_id=c.id, display=core.display(c), ownership_revision=account.ownership_revision,
                              lifecycle_revision=c.lifecycle_revision, item_level=decimal_string(c.summary.get('item_level')),
                              combat_power=decimal_string(c.summary.get('combat_power'))))
        return dict(items=items)


def new_request(principal, gid, key, command, kind):
    data = jsonable_encoder(command)
    def run(db, uid):
        group = groups.group(db, gid)
        if kind == 'invitation':
            membership = groups.member(db, uid, group)
            group_cas(group, data, membership)
            character, account = invitation_target(db, uuid.UUID(data['target_character_id']))
            if (account.ownership_revision != data['expected_target_ownership_revision'] or
                    character.lifecycle_revision != data['expected_target_lifecycle_revision']):
                fail('REVISION_CONFLICT')
            target = account.owner_id
            selection = None
        else:
            group_cas(group, data)
            target = uid
            selection = {key: value for key, value in data.items() if key != 'expected_group_revision'}
            character = core.selected_character(db, uid, selection)
            membership = None
        core.require_not_member(db, group, target)
        core.require_unblocked(db, group, target)
        current = now(db)
        if core.pending(db, group, target, current) is not None:
            fail('GROUP_RELATION_EXISTS')
        subject = core.subject(db, group, target, create=True, snapshot=core.display(character))
        subject.display = core.display(character)
        if kind == 'application':
            subject.application_count += 1
        touch(subject, current)
        value = GroupJoinRelation(group_id=gid, subject_id=subject.id, target_user_id=target, issuer_user_id=uid,
                    issuer_membership_id=membership.id if membership else None, kind=kind, state='pending', revision=1,
                    selection=selection, display=core.display(character), created_at=current, expires_at=current+timedelta(hours=24))
        db.add(value); db.flush()
        return 201, output(db, uid, value), None
    return execute(principal, 'group-'+kind+'-create', key, dict(group_id=str(gid), body=data), run, check_replay_relation)


def get_relation(principal, rid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        return output(db, uid, relation(db, rid))


def action(principal, rid, operation, key, command):
    data = jsonable_encoder(command)
    def run(db, uid):
        value = relation(db, rid)
        group, target, sender, leader = role(db, uid, value)
        current = now(db)
        allowed = {
            'accept': target and value.kind == 'invitation',
            'approve': leader and value.kind == 'application',
            'reject': (target and value.kind == 'invitation') or (leader and value.kind == 'application'),
            'cancel': (target and value.kind == 'application') or (value.kind == 'invitation' and (sender or leader)),
        }[operation]
        if not allowed:
            fail('GROUP_RELATION_FORBIDDEN', 403)
        if data.get('block_future') and not (leader and value.kind == 'application'):
            fail('GROUP_LEADER_REQUIRED', 403)
        if value.revision != data['expected_relation_revision']:
            fail('REVISION_CONFLICT')
        group_cas(group, data)
        if core.relation_state(db, value, current) != 'pending':
            fail('RELATION_NOT_PENDING')
        subject = db.get(GroupJoinSubject, value.subject_id)
        if operation in ('accept', 'approve'):
            if operation == 'accept':
                row = db.get(MemberUsageLimits, uid)
                head = db.get(MemberUsageHead, uid)
                if ((row.revision if row else 1) != data['expected_limits_revision'] or
                        (head.revision if head else 1) != data['expected_usage_revision']):
                    fail('POLICY_CONTEXT_CHANGED')
                selection = data
            else:
                selection = value.selection
            membership = core.admit(db, group, value.target_user_id, selection)
            core.finish(value, 'accepted', now(db))
            touch(subject, now(db))
            body = http_service.detail(db, group, membership)
            if operation == 'approve':
                # The approver is not the new member; never return the target's private my_membership.
                body = output(db, uid, value)
        else:
            core.finish(value, 'rejected' if operation == 'reject' else 'cancelled', current)
            if data.get('block_future'):
                subject.blocked_at = current
            touch(subject, current)
            body = output(db, uid, value)
        def guard(final_time):
            if final_time >= value.expires_at:
                fail('RELATION_NOT_PENDING')
        return 200, body, guard
    check_replay = check_replay_membership if operation == 'accept' else check_replay_relation
    return execute(principal, 'group-relation-'+operation, key, dict(relation_id=str(rid), body=data), run, check_replay)


def subject_output(value):
    return dict(subject_id=value.id, revision=value.revision, display=groups.display(value.display),
                application_count=value.application_count, blocked=value.blocked_at is not None, blocked_at=value.blocked_at)


def block(principal, gid, sid, blocked, key, command):
    data = jsonable_encoder(command)
    def authorize_resource(db, uid):
        group = groups.group(db, gid)
        membership = core.leader(db, uid, group)
        value = db.get(GroupJoinSubject, sid)
        if value is None or value.group_id != gid:
            fail('GROUP_JOIN_SUBJECT_NOT_FOUND', 404)
        return group, membership, value
    def run(db, uid):
        group, membership, value = authorize_resource(db, uid)
        group_cas(group, data, membership)
        if value.revision != data['expected_subject_revision']:
            fail('REVISION_CONFLICT')
        if (value.blocked_at is not None) != blocked:
            current = now(db)
            value.blocked_at = current if blocked else None
            if blocked:
                pending = core.pending(db, group, value.user_id, current)
                if pending:
                    core.finish(pending, 'blocked', current)
            touch(value, current)
        return 200, subject_output(value), None
    return execute(principal, 'group-subject-'+('block' if blocked else 'unblock'), key,
                   dict(group_id=str(gid), subject_id=str(sid), body=data), run,
                   lambda db, uid, body: authorize_resource(db, uid))


def relation_list(principal, view, state, limit, cursor, gid=None):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        query = select(GroupJoinRelation).join(Group, Group.id == GroupJoinRelation.group_id).where(Group.ended_at.is_(None))
        if gid is not None:
            core.leader(db, uid, groups.group(db, gid))
            query = query.where(GroupJoinRelation.group_id == gid)
        elif view == 'received_invitations':
            query = query.where(GroupJoinRelation.kind == 'invitation', GroupJoinRelation.target_user_id == uid)
        elif view == 'sent_applications':
            query = query.where(GroupJoinRelation.kind == 'application', GroupJoinRelation.target_user_id == uid)
        else:
            # Sent invitations remain private to their current sender membership (or current group leader).
            query = query.join(GroupMembership, GroupMembership.id == GroupJoinRelation.issuer_membership_id).where(
                GroupJoinRelation.kind == 'invitation', GroupJoinRelation.issuer_user_id == uid, GroupMembership.ended_at.is_(None))
        rows = list(db.scalars(query.order_by(GroupJoinRelation.created_at.desc(), GroupJoinRelation.id.desc())))
        current = now(db)
        items = [output(db, uid, value, current) for value in rows]
        if state == 'pending':
            items = [item for item in items if item['state'] == 'pending']
        revision = lifecycle.digest([(str(item['relation_id']), item['revision'], item['state'],
                                      item['group']['revision'], item['members_revision']) for item in items])
        scope = dict(path='group-relations', actor=str(uid), group_id=str(gid) if gid else None,
                     view=view, state=state, limit=limit)
        offset = cursor_decode(cursor, scope, revision) if cursor else 0
        following = offset+limit
        return dict(items=items[offset:following], next_cursor=cursor_encode(dict(scope=scope, revision=revision, offset=following)) if following < len(items) else None)


def blocked_list(principal, gid, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        core.leader(db, uid, groups.group(db, gid))
        rows = list(db.scalars(select(GroupJoinSubject).where(GroupJoinSubject.group_id == gid,
                    GroupJoinSubject.blocked_at.is_not(None)).order_by(GroupJoinSubject.created_at.desc(), GroupJoinSubject.id.desc())))
        revision = lifecycle.digest([(str(row.id), row.revision) for row in rows])
        scope = dict(path='blocked-subjects', actor=str(uid), group_id=str(gid), limit=limit)
        offset = cursor_decode(cursor, scope, revision) if cursor else 0
        return dict(items=[subject_output(row) for row in rows[offset:offset+limit]],
             next_cursor=cursor_encode(dict(scope=scope, revision=revision, offset=offset+limit)) if offset+limit < len(rows) else None)
