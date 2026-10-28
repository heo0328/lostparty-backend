"""Current membership management; no group-role authority over raid commands."""
from sqlalchemy import select, func
from fastapi.encoders import jsonable_encoder
from app.core.database import now
from app.game_accounts.support import fail
from app.groups import service as groups, admission_core, admissions, management, features, display, raid_state
from app.groups.models import GroupMembership
from app.groups.admission_models import GroupJoinRelation, GroupJoinSubject, GroupJoinCode
from app.member_limits import service as limits


def blockers(db, group, stamp):
    count = db.scalar(select(func.count()).select_from(GroupMembership).where(
        GroupMembership.group_id == group.id, GroupMembership.ended_at.is_(None)))
    pending = any(admission_core.relation_state(db, r, stamp) == 'pending' for r in db.scalars(
        select(GroupJoinRelation).where(GroupJoinRelation.group_id == group.id, GroupJoinRelation.state == 'pending')))
    state, _ = raid_state.evaluate(db, group, stamp)
    reason = ('GROUP_DISBAND_SOLE_MEMBER_REQUIRED' if count != 1 else
        'GROUP_PENDING_RELATIONS_EXIST' if pending else
        'GROUP_RECRUITMENT_STATE_UNAVAILABLE' if state['state'] == 'unavailable' else
        'GROUP_ACTIVE_RECRUITMENT_EXISTS' if state['state'] == 'blocked' else None)
    return reason, state


def get(principal, gid):
    with display.snapshot(principal) as (db, uid, stamp):
        group = groups.group(db, gid); own = groups.member(db, uid, group)
        leader = own.id == group.leader_membership_id
        reason, state = blockers(db, group, stamp)
        def allowed(is_allowed, why): return dict(allowed=is_allowed, reason=None if is_allowed else why)
        return dict(profile='group-management-1', group_id=gid, group_revision=group.revision,
            members_revision=group.members_revision, my_membership=dict(membership_id=own.id,
                role='leader' if leader else 'member', revision=own.revision, joined_at=own.joined_at),
            permissions=dict(transfer_leadership=allowed(leader,'GROUP_LEADER_REQUIRED'),
                leave=allowed(not leader,'GROUP_LEADER_TRANSFER_REQUIRED'),
                disband=allowed(leader and reason is None,reason if leader else 'GROUP_LEADER_REQUIRED'),
                remove_member=allowed(leader,'GROUP_LEADER_REQUIRED'), change_representative=allowed(leader,'GROUP_LEADER_REQUIRED')),
            recruitment_state=state['state'], blocking_room_count=state['blocking_room_count'], evidence_revision=state['evidence_revision'])


def end_membership(db, group, member, stamp):
    """Shared leave/remove cleanup, never modifies raid membership or block state."""
    member.ended_at = stamp; member.revision += 1
    for relation in db.scalars(select(GroupJoinRelation).where(GroupJoinRelation.group_id == group.id,
            GroupJoinRelation.issuer_membership_id == member.id, GroupJoinRelation.kind == 'invitation',
            GroupJoinRelation.state == 'pending')):
        expired = stamp >= relation.expires_at
        admission_core.finish(relation, 'expired' if expired else 'cancelled', relation.expires_at if expired else stamp)
        admissions.touch(db.get(GroupJoinSubject, relation.subject_id), stamp)
    limits.record_group_membership_change(db, member.user_id)


def replay(db, uid, body, gid, data, target=None):
    member = db.get(GroupMembership, data.expected_membership_id)
    if member is None or member.user_id != uid or member.group_id != gid or body.get('group_id') != str(gid):
        fail('GROUP_MEMBERSHIP_REQUIRED', 403)
    if target is not None and body.get('membership_id') != str(target):
        fail('GROUP_MEMBERSHIP_REQUIRED', 403)


def command(principal, gid, key, data, operation, target=None):
    def run(db, uid):
        features.ready(db)
        group = groups.group(db, gid); own = admission_core.leader(db, uid, group)
        management._cas(group, own, data)
        stamp = now(db)
        if operation == 'representative':
            char = admission_core.selected_character(db, uid, data.model_dump(mode='json'))
            shown = admission_core.display(char)
            changed = (group.representative_character_id, group.representative_user_id, group.representative_display) != (char.id, uid, shown)
            if changed:
                group.representative_character_id = char.id; group.representative_user_id = uid
                group.representative_display = shown; group.revision += 1; groups.advance_directory(db)
            return 200, dict(group_id=gid, group_revision=group.revision, character_id=char.id,
                representative=dict(display=shown,status='valid'), changed_at=stamp if changed else None,
                outcome='applied' if changed else 'noop'), None
        if operation == 'disband':
            reason, _ = blockers(db, group, stamp)
            if reason: fail(reason)
            for relation in db.scalars(select(GroupJoinRelation).where(GroupJoinRelation.group_id == gid,
                    GroupJoinRelation.state == 'pending')):
                state = admission_core.relation_state(db, relation, stamp)
                admission_core.finish(relation,state,relation.expires_at if state == 'expired' else stamp)
            for code in db.scalars(select(GroupJoinCode).where(GroupJoinCode.group_id == gid, GroupJoinCode.revoked_at.is_(None))):
                code.revoked_at = stamp; code.revision += 1
            group.ended_at = stamp; subject = own
        else:
            subject = db.get(GroupMembership, target)
            if subject is None or subject.group_id != gid or subject.ended_at is not None:
                fail('GROUP_TARGET_UNAVAILABLE', 404)
            if subject.id in (own.id, group.leader_membership_id): fail('GROUP_REMOVAL_TARGET_INVALID')
            if subject.revision != data.expected_target_membership_revision: fail('REVISION_CONFLICT')
        end_membership(db,group,subject,stamp)
        group.revision += 1; group.members_revision += 1; groups.advance_directory(db)
        return 200, dict(group_id=gid,membership_id=subject.id,membership_revision=subject.revision,
            group_revision=group.revision,members_revision=group.members_revision,ended_at=stamp), None
    return admissions.execute(principal,'group-'+operation,key,
        dict(group_id=str(gid), target=str(target) if target else None, body=jsonable_encoder(data)),run,
        lambda db,uid,body:replay(db,uid,body,gid,data,target))
