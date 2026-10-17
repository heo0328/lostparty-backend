"""Internal group foundation. A future HTTP adapter must bind reviewed policies.

CreationPolicy is mandatory: activity/limit decisions have no permissive default.
No module in app.main exposes these functions through HTTP.
"""
import uuid
from typing import Protocol
from sqlalchemy import func, select
from app.core.database import session, now
from app.game_accounts import lifecycle, service as accounts
from app.game_accounts.models import Account, Character, Registration
from app.game_accounts.support import authorize, fail, reserve, commit_result, release
from app.groups.commands import CreateGroup, RenameGroup, normalize_name
from app.groups.models import Group, GroupMembership, GroupDirectoryHead


class CreationPolicy(Protocol):
    def __call__(self, db, user_id, registration: Registration, account: Account,
                 character: Character) -> None:
        """Apply reviewed activity/limit policy under the write lock, without network I/O."""
        ...


def group(db, gid):
    value = db.get(Group, gid)
    if value is None or value.ended_at is not None:
        fail('GROUP_NOT_FOUND', 404)
    return value


def member(db, uid, value):
    membership = db.scalar(select(GroupMembership).where(
        GroupMembership.group_id == value.id, GroupMembership.user_id == uid,
        GroupMembership.ended_at.is_(None)))
    if membership is None:
        fail('GROUP_MEMBERSHIP_REQUIRED', 403)
    return membership


def display(snapshot):
    if snapshot is None:
        return None
    return {key: snapshot.get(key) for key in ('server_name', 'character_name', 'class_name')}


def summary(db, value):
    """Safe projection only; public/guest access remains an HTTP policy decision."""
    character = db.get(Character, value.representative_character_id)
    account = db.get(Account, character.account_id) if character else None
    owner_member = db.scalar(select(GroupMembership.id).where(
        GroupMembership.group_id == value.id, GroupMembership.user_id == value.representative_user_id,
        GroupMembership.ended_at.is_(None)))
    valid = (character is not None and account is not None and owner_member is not None and
             account.owner_id == value.representative_user_id and account.verified_at is not None and
             lifecycle.usable(db, character))
    leader = db.get(GroupMembership, value.leader_membership_id)
    count = db.scalar(select(func.count()).select_from(GroupMembership).where(
        GroupMembership.group_id == value.id, GroupMembership.ended_at.is_(None)))
    return dict(group_id=value.id, name=value.name, revision=value.revision, member_count=count,
                representative=dict(display=display(value.representative_display),
                                    status='valid' if valid else 'needs_update'),
                leader_display=display(leader.display) if leader else None)


def detail(db, value, membership):
    leader = membership.id == value.leader_membership_id
    return dict(group=summary(db, value), created_at=value.created_at,
                leader_membership_id=value.leader_membership_id, members_revision=value.members_revision,
                my_membership=dict(membership_id=membership.id, role='leader' if leader else 'member',
                                   revision=membership.revision, joined_at=membership.joined_at),
                permissions=dict(rename=dict(allowed=leader, reason=None if leader else 'GROUP_LEADER_REQUIRED'),
                                 list_members=dict(allowed=True, reason=None)))


def get(principal, gid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        value = group(db, gid)
        return detail(db, value, member(db, uid, value))


def advance_directory(db):
    head = db.get(GroupDirectoryHead, 1)
    if head is None:
        fail('SERVICE_UNAVAILABLE', 503)
    head.revision += 1


def create(principal, key, command: CreateGroup, *, policy: CreationPolicy):
    # Required policy injection is intentional; no implicit unlimited/active-selection policy.
    if not callable(policy):
        raise TypeError('A reviewed creation policy must be explicitly supplied')
    ticket, replay = reserve(principal, 'group-core-create', key,
                             {'body': command.model_dump(exclude_unset=True)})
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            uid = authorize(db, principal)
            member(db, uid, group(db, uuid.UUID(replay[1]['group']['group_id'])))
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            registration = accounts.reg(db, uid, command.registration_id)
            account, status = accounts.ownership(db, uid, registration)
            if status != 'owned' or account.verified_at is None:
                fail('OWNERSHIP_REQUIRED', 403)
            character = db.get(Character, command.character_id)
            if character is None or character.account_id != account.id:
                fail('CHARACTER_NOT_FOUND', 404)
            lifecycle.require_usable(db, character)
            if (registration.version != command.expected_registration_version or
                    account.ownership_revision != command.expected_ownership_revision or
                    account.roster_revision != command.expected_roster_revision or
                    character.lifecycle_revision != command.expected_lifecycle_revision):
                fail('REVISION_CONFLICT')
            policy(db, uid, registration, account, character)
            try:
                name = command.name if command.name is not None else normalize_name(character.character_name + '의 그룹')
            except ValueError:
                fail('GROUP_NAME_REQUIRED', 400)
            stamp = now(db)
            gid, mid = uuid.uuid4(), uuid.uuid4()
            snapshot = dict(server_name=character.server_name, character_name=character.character_name,
                            class_name=character.summary.get('class_name'))
            value = Group(id=gid, name=name, revision=1, members_revision=1,
                          leader_membership_id=mid, representative_character_id=character.id,
                          representative_user_id=uid, representative_display=snapshot, created_at=stamp)
            db.add(value); db.flush()  # Leader FK is deferred; membership's parent must exist first.
            membership = GroupMembership(id=mid, group_id=gid, user_id=uid, character_id=character.id,
                                         display=dict(snapshot), revision=1, joined_at=stamp)
            db.add(membership); db.flush()
            advance_directory(db)
            result = detail(db, value, membership)
            return commit_result(db, ticket, 201, result)
    except Exception:
        release(ticket)
        raise


def rename(principal, gid, key, command: RenameGroup):
    ticket, replay = reserve(principal, 'group-core-rename', key,
                             {'target': str(gid), 'body': command.model_dump()})
    if replay:
        with session() as db, db.begin():
            db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            uid = authorize(db, principal)
            member(db, uid, group(db, gid))
        return replay
    try:
        with session() as db, db.begin():
            uid = authorize(db, principal, write=True)
            value = group(db, gid)
            membership = member(db, uid, value)
            if membership.id != value.leader_membership_id:
                fail('GROUP_LEADER_REQUIRED', 403)
            if (value.revision != command.expected_revision or
                    membership.revision != command.expected_membership_revision):
                fail('REVISION_CONFLICT')
            if value.name != command.name:
                value.name = command.name
                value.revision += 1
                advance_directory(db)
            db.flush()
            return commit_result(db, ticket, 200, detail(db, value, membership))
    except Exception:
        release(ticket)
        raise
