"""G1 HTTP policies/projections over the existing transactional group core."""
import unicodedata
from sqlalchemy import func, or_, select, text
from app.core.database import session
from app.game_accounts import service as accounts
from app.game_accounts.models import Activity
from app.game_accounts.support import authorize, cursor_decode, cursor_encode, fail
from app.groups import service as core
from app.groups.models import Group, GroupMembership, GroupDirectoryHead
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageLimits, MemberUsageHead


def search_key(value):
    # Flutter's published normalizer composes Hangul + trim/lower. PostgreSQL NFC
    # also handles other canonical decompositions, without changing display/identity.
    return unicodedata.normalize('NFC', value).strip().lower()


def detail(db, value, membership):
    result = core.detail(db, value, membership)
    leader = db.get(GroupMembership, value.leader_membership_id)
    capacity = limits.values(db.get(MemberUsageLimits, leader.user_id)).group_capacity
    used = result['group']['member_count']
    result['capacity'] = dict(limit=capacity, used=used, remaining=max(0, capacity-used),
                              state=limits.metric(used, capacity)['state'])
    return result


def create(principal, key, command):
    def policy(db, uid, registration, account, character):
        configuration = accounts.config(db, uid, account.id)
        if configuration is None or db.get(Activity, (configuration.id, character.id)) is None:
            fail('ACTIVITY_SELECTION_REQUIRED')
        row, head = db.get(MemberUsageLimits, uid), db.get(MemberUsageHead, uid)
        if ((row.revision if row else 1) != command.expected_limits_revision or
                (head.revision if head else 1) != command.expected_usage_revision):
            fail('POLICY_CONTEXT_CHANGED')
        effective = limits.values(row)
        if effective.group_capacity < 1:
            fail('GROUP_CAPACITY_REACHED')
        if limits.joined_group_count(db, uid) >= effective.joined_groups:
            fail('GROUP_MEMBERSHIP_LIMIT_REACHED')
    return core.create(principal, key, command, policy=policy,
                       _operation='group-create', _project=detail)


def rename(principal, gid, key, command):
    return core.rename(principal, gid, key, command, _operation='group-rename', _project=detail)


def get_public(gid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        return core.summary(db, core.group(db, gid))


def get_private(principal, gid):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        value = core.group(db, gid)
        return detail(db, value, core.member(db, uid, value))


def directory_revision(db):
    head = db.get(GroupDirectoryHead, 1)
    if head is None:
        fail('SERVICE_UNAVAILABLE', 503)
    return head.revision


def page(db, query, scope, revision, limit, cursor):
    offset = cursor_decode(cursor, scope, revision) if cursor else 0
    rows = list(db.scalars(query.offset(offset).limit(limit+1)))
    following = cursor_encode(dict(scope=scope, revision=revision, offset=offset+limit)) if len(rows) > limit else None
    return rows[:limit], following


def public_list(q, limit, cursor):
    q = search_key(q)
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        revision = directory_revision(db)
        query = select(Group).where(Group.ended_at.is_(None))
        if q:
            # SQLAlchemy escapes %, _ and the escape character; user input is bound.
            name = func.lower(func.normalize(Group.name, text('NFC')))
            representative = func.lower(func.normalize(Group.representative_display['character_name'].astext, text('NFC')))
            query = query.where(or_(name.contains(q, autoescape=True), representative.contains(q, autoescape=True)))
        query = query.order_by(Group.created_at.desc(), Group.id.desc())
        rows, following = page(db, query, dict(path='/v1/groups', q=q, limit=limit), revision, limit, cursor)
        return dict(items=[core.summary(db, value) for value in rows],
                    directory_revision=revision, next_cursor=following)


def my_list(principal, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        revision = directory_revision(db)
        query = select(Group).join(GroupMembership, GroupMembership.group_id == Group.id).where(
            Group.ended_at.is_(None), GroupMembership.user_id == uid,
            GroupMembership.ended_at.is_(None)).order_by(Group.created_at.desc(), Group.id.desc())
        rows, following = page(db, query, dict(path='/v1/me/groups', actor=str(uid), limit=limit), revision, limit, cursor)
        return dict(items=[detail(db, value, core.member(db, uid, value)) for value in rows],
                    directory_revision=revision, next_cursor=following)


def members(principal, gid, limit, cursor):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
        uid = authorize(db, principal)
        value = core.group(db, gid)
        core.member(db, uid, value)
        query = select(GroupMembership).where(GroupMembership.group_id == gid,
                  GroupMembership.ended_at.is_(None)).order_by(GroupMembership.joined_at, GroupMembership.id)
        revision = [value.revision, value.members_revision]
        rows, following = page(db, query, dict(path=f'/v1/groups/{gid}/members', actor=str(uid), limit=limit),
                               revision, limit, cursor)
        return dict(group_id=gid, group_revision=value.revision, members_revision=value.members_revision,
                    items=[dict(membership_id=m.id, role='leader' if m.id == value.leader_membership_id else 'member',
                                revision=m.revision, display=core.display(m.display), joined_at=m.joined_at,
                                is_me=m.user_id == uid) for m in rows], next_cursor=following)
