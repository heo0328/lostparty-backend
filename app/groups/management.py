"""G3 membership management with historical minimal success acknowledgements.

Current membership, not character ownership, authorizes relationship cleanup.
All mutations and their minimal historical ACK share the G2 transaction runner.
"""
from sqlalchemy import func, select
from fastapi.encoders import jsonable_encoder
from app.auth.models import User
from app.core.database import session, now
from app.game_accounts.support import authorize, fail
from app.groups import service as groups, admissions, admission_core
from app.groups.commands import LeaveGroup, TransferLeadership
from app.groups.models import GroupMembership
from app.groups.admission_models import GroupJoinRelation, GroupJoinSubject
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageLimits


def get(principal, gid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        group = groups.group(db, gid)
        membership = groups.member(db, uid, group)
        leader = membership.id == group.leader_membership_id
        return dict(group_id=group.id, group_revision=group.revision,
                    members_revision=group.members_revision,
                    my_membership=dict(membership_id=membership.id,
                        role='leader' if leader else 'member', revision=membership.revision,
                        joined_at=membership.joined_at),
                    permissions=dict(
                        transfer_leadership=dict(allowed=leader,
                            reason=None if leader else 'GROUP_LEADER_REQUIRED'),
                        leave=dict(allowed=not leader,
                            reason='GROUP_LEADER_TRANSFER_REQUIRED' if leader else None),
                        disband=dict(allowed=False, reason='GROUP_RECRUITMENT_STATE_UNAVAILABLE'
                            if leader else 'GROUP_LEADER_REQUIRED')))


def _cas(group, membership, command):
    if (group.revision != command.expected_group_revision or
            group.members_revision != command.expected_members_revision or
            membership.id != command.expected_membership_id or
            membership.revision != command.expected_membership_revision):
        fail('REVISION_CONFLICT')


def _replay(db, uid, body, gid, command, transfer):
    # Never require current membership/leadership for a historical success ACK.
    # reserve() already binds actor, operation, target, key and complete payload.
    mid = command.expected_membership_id
    membership = db.get(GroupMembership, mid)
    field = 'previous_leader_membership_id' if transfer else 'membership_id'
    if (membership is None or membership.group_id != gid or membership.user_id != uid or
            body.get('group_id') != str(gid) or body.get(field) != str(mid)):
        fail('GROUP_MEMBERSHIP_REQUIRED', 403)
    if transfer:
        target = db.get(GroupMembership, command.target_membership_id)
        if (target is None or target.group_id != gid or
                body.get('leader_membership_id') != str(target.id)):
            fail('GROUP_MEMBERSHIP_REQUIRED', 403)


def transfer(principal, gid, key, command: TransferLeadership):
    def run(db, uid):
        group = groups.group(db, gid)
        membership = admission_core.leader(db, uid, group)
        _cas(group, membership, command)
        if command.target_membership_id == membership.id:
            fail('GROUP_TRANSFER_TARGET_INVALID')
        target = db.get(GroupMembership, command.target_membership_id)
        if target is None or target.group_id != gid or target.ended_at is not None:
            fail('GROUP_TARGET_UNAVAILABLE')
        user = db.scalar(select(User).where(User.id == target.user_id).with_for_update())
        if user is None or user.status != 'active':
            fail('GROUP_TARGET_UNAVAILABLE')
        if target.revision != command.expected_target_membership_revision:
            fail('REVISION_CONFLICT')
        capacity = limits.values(db.get(MemberUsageLimits, target.user_id)).group_capacity
        count = db.scalar(select(func.count()).select_from(GroupMembership).where(
            GroupMembership.group_id == gid, GroupMembership.ended_at.is_(None)))
        if count > capacity:
            fail('GROUP_CAPACITY_REACHED')
        group.leader_membership_id = target.id
        group.revision += 1
        group.members_revision += 1
        membership.revision += 1
        target.revision += 1
        groups.advance_directory(db)
        return 200, dict(group_id=gid, previous_leader_membership_id=membership.id,
            leader_membership_id=target.id, group_revision=group.revision,
            members_revision=group.members_revision,
            previous_leader_membership_revision=membership.revision,
            leader_membership_revision=target.revision, transferred_at=now(db)), None
    return admissions.execute(principal, 'group-leadership-transfer', key,
        dict(group_id=str(gid), body=jsonable_encoder(command)), run,
        lambda db, uid, body: _replay(db, uid, body, gid, command, True))


def leave(principal, gid, key, command: LeaveGroup):
    def run(db, uid):
        group = groups.group(db, gid)
        membership = groups.member(db, uid, group)
        if membership.id == group.leader_membership_id:
            fail('GROUP_LEADER_TRANSFER_REQUIRED')
        _cas(group, membership, command)
        current = now(db)
        from app.groups.extended_management import end_membership
        end_membership(db, group, membership, current)
        group.revision += 1
        group.members_revision += 1
        groups.advance_directory(db)
        return 200, dict(group_id=gid, membership_id=membership.id,
            membership_revision=membership.revision, ended_at=current), None
    return admissions.execute(principal, 'group-leave', key,
        dict(group_id=str(gid), body=jsonable_encoder(command)), run,
        lambda db, uid, body: _replay(db, uid, body, gid, command, False))
