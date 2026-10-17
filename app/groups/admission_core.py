"""Shared G2 identity/admission checks; caller owns authorization and transaction."""
import uuid
from sqlalchemy import func, select
from app.auth.models import User
from app.core.database import now
from app.game_accounts import lifecycle, service as accounts
from app.game_accounts.models import Activity, Character
from app.game_accounts.support import fail
from app.groups import service as groups
from app.groups.models import GroupMembership
from app.groups.admission_models import GroupJoinSubject, GroupJoinRelation
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageLimits


def leader(db, uid, group):
    membership = groups.member(db, uid, group)
    if membership.id != group.leader_membership_id:
        fail('GROUP_LEADER_REQUIRED', 403)
    return membership


def selected_character(db, uid, selection):
    registration = accounts.reg(db, uid, uuid.UUID(str(selection['registration_id'])))
    account, status = accounts.ownership(db, uid, registration)
    if status != 'owned' or account.verified_at is None:
        fail('OWNERSHIP_REQUIRED', 403)
    character = db.get(Character, uuid.UUID(str(selection['character_id'])))
    if character is None or character.account_id != account.id:
        fail('CHARACTER_NOT_FOUND', 404)
    lifecycle.require_usable(db, character)
    if (registration.version != selection['expected_registration_version'] or
            account.ownership_revision != selection['expected_ownership_revision'] or
            account.roster_revision != selection['expected_roster_revision'] or
            character.lifecycle_revision != selection['expected_lifecycle_revision']):
        fail('REVISION_CONFLICT')
    config = accounts.config(db, uid, account.id)
    if config is None or db.get(Activity, (config.id, character.id)) is None:
        fail('ACTIVITY_SELECTION_REQUIRED')
    return character


def display(character):
    return dict(server_name=character.server_name, character_name=character.character_name,
                class_name=character.summary.get('class_name'))


def subject(db, group, uid, *, create=False, snapshot=None):
    value = db.scalar(select(GroupJoinSubject).where(GroupJoinSubject.group_id == group.id,
                                                    GroupJoinSubject.user_id == uid))
    if value is None and create:
        current = now(db)
        value = GroupJoinSubject(group_id=group.id, user_id=uid, revision=1, application_count=0,
                                 display=snapshot, created_at=current, updated_at=current)
        db.add(value); db.flush()
    return value


def require_unblocked(db, group, uid):
    value = subject(db, group, uid)
    if value is not None and value.blocked_at is not None:
        fail('GROUP_JOIN_BLOCKED', 403)


def require_not_member(db, group, uid):
    if db.scalar(select(GroupMembership.id).where(GroupMembership.group_id == group.id,
             GroupMembership.user_id == uid, GroupMembership.ended_at.is_(None))) is not None:
        fail('ALREADY_GROUP_MEMBER')


def relation_state(db, value, current):
    if value.state != 'pending':
        return value.state
    if current >= value.expires_at:
        return 'expired'
    if value.kind == 'invitation':
        issuer = db.get(GroupMembership, value.issuer_membership_id)
        if issuer is None or issuer.ended_at is not None:
            return 'cancelled'
    return 'pending'


def finish(value, state, current):
    value.state, value.ended_at = state, current
    value.revision += 1


def pending(db, group, uid, current):
    value = db.scalar(select(GroupJoinRelation).where(GroupJoinRelation.group_id == group.id,
                      GroupJoinRelation.target_user_id == uid, GroupJoinRelation.state == 'pending'))
    if value is not None:
        state = relation_state(db, value, current)
        if state != 'pending':
            finish(value, state, current)
            db.flush()
            return None
    return value


def admit(db, group, uid, selection):
    user = db.scalar(select(User).where(User.id == uid).with_for_update())
    if user is None or user.status != 'active':
        fail('GROUP_TARGET_UNAVAILABLE', 409)
    require_unblocked(db, group, uid)
    require_not_member(db, group, uid)
    character = selected_character(db, uid, selection)
    leader_member = db.get(GroupMembership, group.leader_membership_id)
    capacity = limits.values(db.get(MemberUsageLimits, leader_member.user_id)).group_capacity
    count = db.scalar(select(func.count()).select_from(GroupMembership).where(
        GroupMembership.group_id == group.id, GroupMembership.ended_at.is_(None)))
    if count >= capacity:
        fail('GROUP_CAPACITY_REACHED')
    own = limits.values(db.get(MemberUsageLimits, uid))
    if limits.joined_group_count(db, uid) >= own.joined_groups:
        fail('GROUP_MEMBERSHIP_LIMIT_REACHED')
    membership = GroupMembership(group_id=group.id, user_id=uid, character_id=character.id,
                                  display=display(character), revision=1, joined_at=now(db))
    db.add(membership); db.flush()
    group.members_revision += 1
    limits.record_group_membership_change(db, uid)
    groups.advance_directory(db)
    return membership
