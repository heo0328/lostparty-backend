"""Current own-group evidence for the existing common-settings command."""

from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy import func

from app.groups import features

from app.groups.models import Group
from app.groups.models import GroupMembership

from app.member_limits.models import MemberUsageLimits

from app.member_limits import service as limits

from app.game_accounts.common.support import fail
from app.game_accounts.common.support import GameError

from app.raid_rooms.participation import participation_core

from app.raid_rooms.schedules.cycle_planning import snapshot as row_snapshot

def snapshot(value):
    return row_snapshot(value) if value is not None else None

def evaluate(db,uid,gid):
    features.ready(db)
    group=db.get(Group,gid)
    if group is None or group.ended_at is not None:fail('GROUP_NOT_ACTIVE')
    member=db.scalar(select(GroupMembership).where(GroupMembership.group_id==gid,
        GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None)))
    if member is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)
    leader=db.get(GroupMembership,group.leader_membership_id)
    if leader is None or leader.ended_at is not None:fail('SERVICE_UNAVAILABLE',503)
    reason=None
    try:participation_core._group(db,SimpleNamespace(scope='group',group_id=gid),uid)
    except GameError as error:
        if error.status==503:raise
        reason=error.code
    public=dict(group_id=gid,group_revision=group.revision,members_revision=group.members_revision,
        membership_id=member.id,membership_revision=member.revision,permission=dict(allowed=reason is None,reason=reason,next_change_at=None))
    proof=[snapshot(group),snapshot(member),snapshot(leader),
        snapshot(db.get(MemberUsageLimits,uid)),snapshot(db.get(MemberUsageLimits,leader.user_id)),
        limits.joined_group_count(db,uid),db.scalar(select(func.count()).select_from(GroupMembership).where(
            GroupMembership.group_id==gid,GroupMembership.ended_at.is_(None)))]
    return public,proof
