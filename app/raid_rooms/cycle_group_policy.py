"""Generation-local group authority shared by commands, reads and succession."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
from types import SimpleNamespace
from sqlalchemy import select, text, or_, and_
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail, GameError
from app.groups.models import Group, GroupMembership
from app.raid_rooms.cycle_group_models import CycleGroupPolicy as Policy

VERSION = 'cycle-group-policy-1'
_client = ContextVar('cycle_group_policy_client', default=False)


@contextmanager
def using(enabled=True):
    token = _client.set(enabled)
    try:
        yield
    finally:
        _client.reset(token)


def enabled(db):
    if 'cycle_group_policy_enabled' not in db.info:
        db.info['cycle_group_policy_enabled'] = db.scalar(text('SELECT version_num FROM public.alembic_version')) == '0035_cycle_group_policy'
    return db.info['cycle_group_policy_enabled']


def marker(db):
    return {'group_policy_version': VERSION} if db is not None and enabled(db) else {}


def require_client(db, operation, payload=None, ticket=None):
    if _client.get() and not enabled(db):fail('GROUP_FEATURE_NOT_READY',503)
    if enabled(db) and not _client.get():
        fail('CLIENT_UPGRADE_REQUIRED')
    if enabled(db) and ticket is not None:
        from app.game_accounts.models import RequestResult
        request=db.get(RequestResult,ticket[0])
        cutover=db.scalar(text('SELECT public.cycle_group_policy_cutover_at()'))
        if request is None or request.record_created_at is None or request.record_created_at < cutover:
            fail('CLIENT_UPGRADE_REQUIRED')
    if enabled(db) and payload is not None:
        from app.raid_rooms.command_context import unseal
        def check(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ('context_token','correction_context_token','resume_context_token') and item is not None:
                        if unseal(item).get('group_policy_version')!=VERSION:fail('CLIENT_UPGRADE_REQUIRED')
                    else:check(item)
            elif isinstance(value,list):
                for item in value:check(item)
        check(payload)


def get(db, row, *, required=True, generation=None):
    value = db.get(Policy, (row.id, generation if generation is not None else row.generation)) if row and (generation or row.generation) else None
    if required and value is None:
        fail('ROOM_REVIEW_REQUIRED')
    return value


def state(value):
    return dict(scope=value.scope, group_id=value.group_id, revision=value.revision) if value else None


def member(db, gid, uid):
    if gid is None or uid is None:
        return None
    return db.scalar(select(GroupMembership).join(Group, Group.id == GroupMembership.group_id).where(
        Group.id == gid, Group.ended_at.is_(None), GroupMembership.user_id == uid,
        GroupMembership.ended_at.is_(None)))


class RoomView:
    def __init__(self, room, row, value):
        self._room = getattr(room, '_room', room)
        self._cycle_row = row
        self.scope, self.group_id = value.scope, value.group_id
    def __getattr__(self, name):
        return getattr(self._room, name)


def project(db, room, row, uid=None):
    if not enabled(db):
        return room
    value = get(db, row)
    view = RoomView(room, row, value)
    if uid is not None:
        authorize(db, view, row, uid)
    return view


def authorize(db, room, row, uid):
    from app.raid_rooms.cycle_models import CycleMember
    from app.raid_rooms.integrated_models import RecruitmentMembership as Member
    # Exact target history/participation is retained; a different T is no grant.
    own = db.scalar(select(CycleMember.id).join(Member,Member.id==CycleMember.membership_id).where(CycleMember.cycle_id == row.id,
        CycleMember.generation == row.generation, CycleMember.user_id == uid,Member.ended_at.is_(None),
        CycleMember.state.in_(('participating','completed','stopped','review_required')))) if uid else None
    if room.scope != 'public' and not own and member(db, room.group_id, uid) is None:
        fail('ROOM_NOT_FOUND', 404)


def visible(uid, row):
    from app.raid_rooms.cycle_models import CycleMember
    from app.raid_rooms.integrated_models import RecruitmentMembership as Member
    joined = select(Policy.cycle_id).where(Policy.cycle_id == row.id,
        Policy.generation == row.generation, Policy.scope == 'public').correlate(row).exists()
    if uid is None:
        return joined
    group = select(Policy.cycle_id).join(Group, Group.id == Policy.group_id).join(
        GroupMembership, GroupMembership.group_id == Group.id).where(
        Policy.cycle_id == row.id, Policy.generation == row.generation,
        Group.ended_at.is_(None), GroupMembership.user_id == uid,
        GroupMembership.ended_at.is_(None)).correlate(row).exists()
    own = select(CycleMember.id).join(Member,Member.id==CycleMember.membership_id).where(CycleMember.cycle_id == row.id,
        CycleMember.generation == row.generation, CycleMember.user_id == uid,Member.ended_at.is_(None),
        CycleMember.state.in_(('participating','completed','stopped','review_required'))).correlate(row).exists()
    return or_(joined, group, own)


def install(db, row, scope, gid):
    if not enabled(db):
        return
    if (scope == 'public' and gid is not None) or (scope == 'group' and gid is None):
        fail('INVALID_REQUEST', 400)
    db.add(Policy(cycle_id=row.id, generation=row.generation, scope=scope, group_id=gid, revision=1))
    db.flush()


def apply(db, row, after):
    from uuid import UUID
    after=dict(after,group_id=UUID(str(after['group_id'])) if after['group_id'] is not None else None)
    value = get(db, row)
    if (value.scope, value.group_id) == (after['scope'], after['group_id']):
        return False
    if value.revision >= 2147483647 or row.settings_revision >= 2147483647:
        fail('REVISION_CONFLICT')
    value.scope, value.group_id = after['scope'], after['group_id']
    value.revision += 1
    row.settings_revision += 1
    return True


def inherited(db, source, uid):
    value = get(db, source)
    keep = value.scope == 'group' and member(db, value.group_id, uid) is not None
    return dict(scope='group' if keep else 'public', group_id=value.group_id if keep else None)


def effect(db, row, after=None):
    value = get(db, row)
    before = state(value)
    return dict(room_id=row.room_id, target_cycle_key=row.cycle_key, room_cycle_id=row.id,
        generation=row.generation, before=before,
        after=after or dict(scope=value.scope, group_id=value.group_id))


def candidates(db, room, row, members, qualify):
    """Eligibility under the prospective policy; membership alone is never enough."""
    current = get(db, row)
    result, proof = [], []
    for cm in members:
        same = current.scope == 'group' and member(db, current.group_id, cm.user_id) is not None
        value = SimpleNamespace(scope=current.scope if same else 'public', group_id=current.group_id if same else None)
        view = RoomView(room, row, value)
        reason, evidence = qualify(view, cm)
        membership = member(db, current.group_id, cm.user_id)
        proof.append([str(cm.id), cm.revision, str(cm.joined_order), reason, evidence,
            str(membership.id) if membership else None, membership.revision if membership else None,
            group_evidence(db,current.group_id,cm.user_id)])
        result.append((cm, reason, same))
    eligible = [(cm, same) for cm, reason, same in result if reason is None and cm.joined_order is not None]
    eligible.sort(key=lambda item: (not item[1], item[0].joined_order, str(item[0].id)))
    chosen = eligible[0][0] if eligible and all(cm.joined_order is not None for cm in members) else None
    keep = chosen is not None and current.scope == 'group' and member(db, current.group_id, chosen.user_id) is not None
    after = dict(scope='group' if keep else 'public', group_id=current.group_id if keep else None)
    reasons={reason for _, reason, _ in result if reason}
    if any(cm.joined_order is None for cm in members):reasons.add('JOIN_ORDER_UNVERIFIED')
    return chosen, proof, sorted(reasons), after, result


_CURRENT_GENERATION = object()


def metadata(db, row, generation=_CURRENT_GENERATION):
    generation=row.generation if generation is _CURRENT_GENERATION else generation
    value = get(db, row, required=False, generation=generation) if generation is not None else None
    return dict(room_id=row.room_id, target_cycle_key=row.cycle_key, room_cycle_id=row.id,
        generation=generation,
        scope=value.scope if value else None, group_id=value.group_id if value else None,
        revision=value.revision if value else None, state='known' if value else 'unavailable')


def qualify_editor(db, uid, room, row):
    from app.raid_rooms import cycle_commands as commands, cycle_lifecycle as life
    if row.state!='open':fail('ROOM_REVIEW_REQUIRED' if row.state=='review_required' else 'ROUND_NOT_ACTIVE')
    if room.ended_at is not None:fail('ROOM_NOT_ACTIVE')
    if commands.leadership(db,row)['leader_cycle_member_id'] is None:fail('ROOM_LEADER_REQUIRED',403)
    commands.require_leader(db,uid,row)
    actor=life.actual_member(db,row,uid)
    if actor is None:fail('TARGET_LEADER_REQUIRED',403)
    public=RoomView(room,row,SimpleNamespace(scope='public',group_id=None))
    _,proof=life.qualify(db,public,row,actor)
    return proof


def settings_context(db, uid, room, row, gid, stamp):
    from app.raid_rooms import cycle_commands as commands, cycle_lifecycle as life, group_connection
    from app.raid_rooms.command_context import seal
    from app.game_accounts.lifecycle import digest
    actor_proof=qualify_editor(db,uid,room,row)
    current = get(db, row)
    target, proof = group_connection.evaluate(db, uid, gid) if gid else (None, None)
    if target and not target['permission']['allowed']:
        fail(target['permission']['reason'])
    after = dict(scope='group' if gid else 'public', group_id=gid)
    impact = effect(db, row, after)
    basis = jsonable_encoder([uid, row.id, row.generation, row.revision, row.settings_revision,
        commands.leadership(db,row), state(current), after, proof, actor_proof])
    expires = min(stamp+timedelta(seconds=120), commands.raids.cycle(stamp).ends_at)
    token = seal(dict(actor=str(uid), room=str(room.id), target=row.cycle_key.isoformat(),
        command='edit_group_policy', digest=digest(basis), group_policy_version=VERSION,
        target_group_id=str(gid) if gid else None, expires=expires.isoformat()))
    return dict(scope=life.scope(stamp,row.cycle_key.isoformat(),row),
        data=dict(room_id=room.id, context_token=token, issued_at=stamp, expires_at=expires,
            permission=dict(allowed=True,reason=None,next_change_at=None)),
        group_policy_version=VERSION, group_policy=metadata(db,row), group_policy_effect=impact)


def verify_settings(db,uid,room,row,body,stamp):
    from app.raid_rooms.command_context import unseal
    from datetime import datetime
    change=body.get('group_policy')
    if not change or not body.get('context_token'):fail('CLIENT_UPGRADE_REQUIRED')
    if (change['scope']=='group') != (change['group_id'] is not None):fail('INVALID_REQUEST',400)
    token=unseal(body['context_token'])
    if token.get('group_policy_version')!=VERSION:fail('CLIENT_UPGRADE_REQUIRED')
    if (token.get('actor'),token.get('room'),token.get('target'),token.get('command'))!=(str(uid),str(room.id),row.cycle_key.isoformat(),'edit_group_policy'):
        fail('TARGET_SCOPE_MISMATCH',400)
    if stamp>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
    if token.get('target_group_id')!=(str(change['group_id']) if change['group_id'] else None):fail('TARGET_SCOPE_MISMATCH',400)
    current=settings_context(db,uid,room,row,change['group_id'],stamp)
    if unseal(current['data']['context_token'])['digest']!=token['digest']:fail('TARGET_CONTEXT_STALE')
    if get(db,row).revision!=change['expected_revision']:fail('REVISION_CONFLICT')
    return current['group_policy_effect']


def enrich(db, result):
    if not enabled(db):return result
    from uuid import UUID
    from app.raid_rooms.cycle_models import RoomCycle
    result=dict(result,group_policy_version=VERSION)
    scope=result.get('scope',{})
    target=result.get('data',{}).get('target',{})
    rid=scope.get('room_cycle_id') or target.get('room_cycle_id')
    if rid:
        row=db.get(RoomCycle,UUID(str(rid)))
        if row:result['group_policy']=jsonable_encoder(metadata(db,row,generation=target['target_generation']) if 'target_generation' in target else metadata(db,row))
    return result


def group_evidence(db, gid, uid):
    """Exact current relationship, including leave/rejoin and ended group epochs."""
    group=db.get(Group,gid) if gid is not None else None
    own=member(db,gid,uid)
    return [str(group.id),group.revision,group.members_revision,group.ended_at,
        str(own.id) if own else None,own.revision if own else None] if group else None
