"""Allowlisted read projections; ORM objects and user identifiers never leave here."""
from decimal import Decimal, InvalidOperation
from uuid import UUID
from sqlalchemy import select
from app.auth.models import User
from app.game_accounts import lifecycle
from app.game_accounts.models import Account, Character, Registration, CharacterRoleSummary
from app.game_accounts.support import GameError, fail
from app.groups import admission_core as groups
from app.groups.service import display
from app.raids import service as raids
from app.raid_rooms import core, service, runtime
from app.raid_rooms.models import Membership


def permission(reason=None):
    return dict(allowed=reason is None, reason=reason)


def members(db, room):
    return list(db.scalars(select(Membership).where(Membership.room_id == room.id,
        Membership.ended_at.is_(None)).order_by(Membership.party_no, Membership.slot_no)))


def phase(room, round, stamp):
    return ('ended' if room.ended_at is not None or round.ended_at is not None else
            'current' if raids.cycle(stamp).cycle_key == round.cycle_key.isoformat() else 'cycle_closed')


def summary(db, room, round, stamp):
    rows = members(db, room)
    leader = db.get(Membership, room.leader_membership_id)
    return dict(room_id=room.id, revision=room.revision, round_id=round.id,
        round_revision=round.revision, members_revision=room.members_revision, title=room.title,
        state='active' if room.ended_at is None else 'ended', phase=phase(room, round, stamp),
        scope=room.scope, group_id=room.group_id, raid_id=round.raid_id,
        difficulty_id=round.difficulty_id, catalog_version=round.catalog_version, cycle_key=round.cycle_key,
        admission_mode=room.admission_mode, schedule=dict(starts_at=round.starts_at, ends_at=round.ends_at),
        party_count=round.party_count, member_count=len(rows),
        support_count=sum(m.selected_role == 'support' for m in rows),
        leader_display=display(leader.display) if leader else None,
        restricted=bool(core.issues(db, room)), created_at=room.created_at)


def registration(db, uid, character):
    if character is None:
        return None
    return db.scalar(select(Registration).where(Registration.user_id == uid,
        Registration.account_id == character.account_id, Registration.deleted_at.is_(None))
        .order_by(Registration.created_at, Registration.id).limit(1))


def member_status(db, m, round):
    character = db.get(Character, m.character_id)
    account = db.get(Account, character.account_id) if character else None
    reg = registration(db, m.user_id, character)
    user = db.get(User, m.user_id)
    if user is None or user.status != 'active':
        return 'ROOM_TARGET_UNAVAILABLE'
    if (account is None or reg is None or account.owner_id != m.user_id or
            account.ownership_revision != m.ownership_revision or account.verified_at is None):
        return 'OWNERSHIP_REQUIRED'
    if character.lifecycle_revision != m.lifecycle_revision or not lifecycle.usable(db, character):
        return 'CHARACTER_UNUSABLE'
    if not character.summary.get('class_name'):
        return 'CHARACTER_DATA_UNAVAILABLE'
    try:
        groups.selected_character(db, m.user_id, dict(registration_id=reg.id, character_id=character.id,
            expected_registration_version=reg.version, expected_ownership_revision=m.ownership_revision,
            expected_roster_revision=account.roster_revision, expected_lifecycle_revision=m.lifecycle_revision))
        difficulty = raids.difficulty(round.raid_id, round.difficulty_id, round.catalog_version)
        level = Decimal(str(character.summary.get('item_level')))
        if not raids.meets_item_level(level, difficulty):
            return 'RAID_ITEM_LEVEL_REQUIRED'
    except GameError as error:
        return error.code
    except raids.CatalogSelectionError as error:
        return error.code
    except (InvalidOperation, ValueError):
        return 'CHARACTER_DATA_UNAVAILABLE'
    return None


def build(db, uid, cid, ownership, role, snapshot, lifecycle_revision):
    # Legacy internal snapshots lack metadata. Do not invent their provenance.
    known = isinstance(snapshot, dict) and 'version' in snapshot and 'summary' in snapshot
    if not known:
        fail('SERVICE_UNAVAILABLE', 503)
    data = snapshot
    cid = UUID(str(cid))
    current = db.get(CharacterRoleSummary, (uid, cid, ownership, role))
    c = db.get(Character, cid)
    a = db.get(Account, c.account_id) if c else None
    valid = (a is not None and a.owner_id == uid and a.ownership_revision == ownership and
             c.lifecycle_revision == lifecycle_revision and lifecycle.usable(db, c))
    from datetime import datetime
    saved = data.get('saved_at')
    stamp = datetime.fromisoformat(saved.replace('Z', '+00:00')) if isinstance(saved, str) else saved
    stale = (not valid or data['version'] != (current.version if current else 1) or
             stamp != (current.saved_at if current else None))
    return dict(role=role, version=data['version'], summary=data['summary'],
                saved_at=data.get('saved_at'), stale=stale)


def member(db, room, round, m, uid):
    reason = member_status(db, m, round)
    return dict(membership_id=m.id, revision=m.revision, party_no=m.party_no, slot_no=m.slot_no,
        room_role='leader' if room.leader_membership_id == m.id else 'member',
        selected_role=m.selected_role, character_id=m.character_id, display=display(m.display),
        joined_at=m.joined_at, status='needs_review' if reason else 'valid', status_reason=reason,
        build=build(db, m.user_id, m.character_id, m.ownership_revision, m.selected_role, m.build,
                    m.lifecycle_revision), is_me=m.user_id == uid)


def progress_reason(db, room, round, stamp):
    if room.ended_at is not None:
        return 'ROOM_NOT_ACTIVE'
    if phase(room, round, stamp) != 'current':
        return 'CYCLE_CHANGED'
    if round.catalog_version != raids.catalog().catalog_version:
        return 'CATALOG_VERSION_CONFLICT'
    if stamp >= round.ends_at:
        return 'SCHEDULE_CONFLICT'
    if core.issues(db, room):
        return 'ROOM_RESTRICTED'
    return None


def candidates(db, room, rows, mine):
    return [dict(membership_id=m.id, revision=m.revision, display=display(m.display)) for m in rows
            if m.id != mine.id and (u := db.get(User, m.user_id)) is not None and u.status == 'active']


def management(db, room, round, mine, stamp):
    rows = members(db, room)
    leader = room.leader_membership_id == mine.id
    targets = candidates(db, room, rows, mine) if leader else []
    return dict(room_id=room.id, revision=room.revision, members_revision=room.members_revision,
        my_membership=dict(membership_id=mine.id, revision=mine.revision, room_role='leader' if leader else 'member'),
        round_id=round.id, round_revision=round.revision, round_phase=phase(room, round, stamp),
        transfer_candidates=targets, permissions=dict(
            leave=permission('ROOM_LEADER_TRANSFER_REQUIRED' if leader else None),
            transfer_leadership=permission('ROOM_LEADER_REQUIRED' if not leader else
                                          'ROOM_TARGET_UNAVAILABLE' if not targets else None),
            end=permission('ROOM_LEADER_REQUIRED' if not leader else
                           'ROOM_LAST_MEMBER_REQUIRED' if len(rows) != 1 else None)))


def detail(db, room, round, mine, stamp):
    rows = members(db, room)
    is_leader = room.leader_membership_id == mine.id
    recovery = management(db, room, round, mine, stamp)['permissions']
    issues = []
    by_id = {str(m.id): m for m in rows}
    dimensions = dict(MEMBER_RAID_LIMIT_EXCEEDED='raid_rooms', MEMBER_GROUP_LIMIT_EXCEEDED='joined_groups',
                      GROUP_CAPACITY_EXCEEDED='group_capacity')
    for issue in core.issues(db, room):
        m = by_id.get(issue['membership_id'])
        issues.append(dict(code=issue['code'], dimension=dimensions[issue['code']], used=issue['used'],
            limit=issue['limit'], member_ref=dict(membership_id=m.id, display=display(m.display)) if m else None,
            origin_group_id=room.group_id if issue['code'] == 'GROUP_CAPACITY_EXCEEDED' else None))
    reason = 'ROOM_LEADER_REQUIRED' if not is_leader else progress_reason(db, room, round, stamp)
    reason = reason or ('ROOM_FEATURE_UNSUPPORTED' if room.admission_mode != 'leader_only' else None)
    reason = reason or runtime.admission_reason()
    reject = ('ROOM_LEADER_REQUIRED' if not is_leader else
              'ROOM_NOT_ACTIVE' if room.ended_at else
              'CYCLE_CHANGED' if phase(room, round, stamp) != 'current' else
              'CATALOG_VERSION_CONFLICT' if round.catalog_version != raids.catalog().catalog_version else
              'SCHEDULE_CONFLICT' if stamp >= round.ends_at else None)
    return dict(room=summary(db, room, round, stamp), members=[member(db, room, round, m, mine.user_id) for m in rows],
        my_membership_id=mine.id, access=dict(state='restricted' if issues else 'normal',
            policy_snapshot=core.policy_snapshot(db, room), evaluated_at=stamp, issues=issues),
        permissions=dict(apply=permission('ROOM_MEMBER_EXISTS'), join=permission('ROOM_MEMBER_EXISTS'),
            approve=permission(reason), reject=permission(reject), **recovery,
            **{k: permission('ROOM_FEATURE_UNSUPPORTED') for k in
               ('complete', 'change_character', 'move_slot', 'repeat', 'change_scope')}))


def application(db, room, round, row, uid, stamp):
    state = service.application_state(db, row, stamp)
    ended = row.ended_at
    if row.state == 'pending' and state == 'expired':
        ended = row.expires_at
    elif row.state == 'pending' and state == 'cancelled':
        m = db.scalar(select(Membership).where(Membership.room_id == room.id, Membership.user_id == row.user_id,
                      Membership.ended_at.is_(None)))
        ended = room.ended_at if room.ended_at is not None else m.joined_at if m else None
    leader = db.scalar(select(Membership.id).where(Membership.room_id == room.id, Membership.user_id == uid,
             Membership.ended_at.is_(None))) == room.leader_membership_id
    reason = 'ROOM_LEADER_REQUIRED' if not leader else 'APPLICATION_NOT_PENDING' if state != 'pending' else None
    # Rejection is recovery: room limits do not block it, while cycle/end guards still apply.
    reject = reason or ('ROOM_NOT_ACTIVE' if room.ended_at else
                       'CYCLE_CHANGED' if phase(room, round, stamp) != 'current' else
                       'CATALOG_VERSION_CONFLICT' if round.catalog_version != raids.catalog().catalog_version else
                       'SCHEDULE_CONFLICT' if stamp >= round.ends_at else None)
    data = row.selection
    return dict(application_id=row.id, room_id=room.id, revision=row.revision, state=state,
        created_at=row.created_at, expires_at=row.expires_at, ended_at=ended, display=display(row.display),
        character_id=data['character_id'], party_no=data['party_no'], selected_role=data['selected_role'],
        build=build(db, row.user_id, data['character_id'], data['expected_ownership_revision'],
                    data['selected_role'], row.build, data['expected_lifecycle_revision']),
        permissions=dict(approve=permission(reason or progress_reason(db, room, round, stamp) or runtime.admission_reason()),
            reject=permission(reject), withdraw=permission('ROOM_APPLICATION_NOT_FOUND' if row.user_id != uid else
                                                         'APPLICATION_NOT_PENDING' if state != 'pending' else None)))
