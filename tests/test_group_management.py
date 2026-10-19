"""Internal G3 tests; no new HTTP contract is exposed by this checkpoint."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from app.core.database import session, now
from app.core.errors import AuthError
from app.auth.models import Session, User
from app.game_accounts.models import Account, RequestResult
from app.game_accounts.support import GameError
from app.groups import admissions, management
from app.groups.commands import LeaveGroup, TransferLeadership
from app.groups.models import Group, GroupMembership, GroupDirectoryHead
from app.groups.admission_models import GroupJoinRelation
from app.member_limits.models import MemberUsageHead
from app.member_limits.service import Limits
from tests.test_group_admissions import (worlds, group, apply, action, new_code, join,
                                        invite, accept, relation, action_body, own_selection,
                                        limits, post)
from tests.test_group_foundation import actor
from tests.test_member_limits import change


def command(w, gid, target=None):
    state = management.get(actor(w['uid']), uuid.UUID(gid))
    member = state['my_membership']
    data = dict(expected_group_revision=state['group_revision'],
                expected_members_revision=state['members_revision'],
                expected_membership_id=member['membership_id'],
                expected_membership_revision=member['revision'])
    if target:
        with session() as db:
            m = db.scalar(select(GroupMembership).where(GroupMembership.group_id == uuid.UUID(gid),
                GroupMembership.user_id == target['uid'], GroupMembership.ended_at.is_(None)))
            return TransferLeadership(**data, target_membership_id=m.id,
                                      expected_target_membership_revision=m.revision)
    return LeaveGroup(**data)


def setup(client, worlds):
    a, b = worlds('leader'), worlds('member')
    gid = group(client, a)
    pending = apply(client, b, gid).json()
    assert action(client, a, pending['relation_id'], 'approve').status_code == 200
    return a, b, gid


def invoke(fn, w, gid, data, key=None):
    return fn(actor(w['uid']), uuid.UUID(gid), key or uuid.uuid4(), data)


def denied(code, fn, *args):
    with pytest.raises(AuthError) as exc:
        fn(*args)
    assert exc.value.code == code


def snapshot(gid, uid):
    with session() as db:
        g = db.get(Group, uuid.UUID(gid))
        h = db.get(MemberUsageHead, uid)
        return (g.revision, g.members_revision, g.leader_membership_id,
                g.representative_character_id, g.representative_display,
                db.get(GroupDirectoryHead, 1).revision, h.revision if h else 1)


def test_transfer_preserves_representative_code_usage_and_changes_roles(client, worlds):
    a, b, gid = setup(client, worlds)
    code = new_code(client, a, gid).json()['code']
    before = snapshot(gid, a['uid'])
    data = command(a, gid, b)
    result = invoke(management.transfer, a, gid, data)[1]
    after = snapshot(gid, a['uid'])
    assert after[:2] == (before[0]+1, before[1]+1)
    assert after[3:5] == before[3:5] and after[-1] == before[-1]
    assert after[5] == before[5]+1
    assert result['leader_membership_id'] == str(data.target_membership_id)
    assert management.get(actor(a['uid']), uuid.UUID(gid))['my_membership']['role'] == 'member'
    assert management.get(actor(b['uid']), uuid.UUID(gid))['my_membership']['role'] == 'leader'
    assert client.get('/v1/groups/'+gid+'/join-code', headers=b['headers']).json()['code'] == code
    denied('GROUP_LEADER_REQUIRED', invoke, management.transfer, a, gid, data)


def test_transfer_capacity_rechecks_and_allows_exact_limit_despite_personal_excess(client, worlds):
    a, b, gid = setup(client, worlds)
    data = command(a, gid, b)
    change(b['uid'], Limits(1, 0, 0))
    before = snapshot(gid, b['uid'])
    denied('GROUP_CAPACITY_REACHED', invoke, management.transfer, a, gid, data)
    assert snapshot(gid, b['uid']) == before
    change(b['uid'], Limits(2, 0, 0), expected=2)
    assert invoke(management.transfer, a, gid, data)[0] == 200


def test_relationship_cleanup_does_not_require_old_character_ownership(client, worlds):
    a, b, gid = setup(client, worlds)
    with session() as db, db.begin():
        db.get(Account, a['aid']).owner_id = None
        db.get(Account, b['aid']).owner_id = None
    assert invoke(management.transfer, a, gid, command(a, gid, b))[0] == 200
    assert invoke(management.leave, a, gid, command(a, gid))[0] == 200


def test_leave_ends_only_senders_pending_invitations_and_preserves_history(client, worlds):
    a, b, gid = setup(client, worlds)
    c, d, e = worlds('c'), worlds('d'), worlds('e')
    rid = invite(client, b, c, gid).json()['relation_id']
    expired = invite(client, b, d, gid).json()['relation_id']
    other = invite(client, a, e, gid).json()['relation_id']
    with session() as db, db.begin():
        r = db.get(GroupJoinRelation, uuid.UUID(expired))
        r.created_at = now(db)-timedelta(hours=25)
        r.expires_at = now(db)-timedelta(hours=1)
    before = snapshot(gid, b['uid'])
    data = command(b, gid)
    ack = invoke(management.leave, b, gid, data)[1]
    assert set(ack) == {'group_id', 'membership_id', 'membership_revision', 'ended_at'}
    assert snapshot(gid, b['uid'])[-1] == before[-1]+1
    with session() as db:
        assert db.get(GroupMembership, data.expected_membership_id).ended_at is not None
        assert db.get(GroupJoinRelation, uuid.UUID(rid)).state == 'cancelled'
        r = db.get(GroupJoinRelation, uuid.UUID(expired))
        assert r.state == 'expired' and r.ended_at == r.expires_at
        assert db.get(GroupJoinRelation, uuid.UUID(other)).state == 'pending'
    assert relation(client, c, rid)['state'] == 'cancelled'
    assert accept(client, c, rid).status_code == 409


def test_leave_replay_after_rejoin_preserves_new_membership_and_usage(client, worlds):
    a, b, gid = setup(client, worlds)
    code = new_code(client, a, gid).json()['code']
    data, key = command(b, gid), uuid.uuid4()
    ack = invoke(management.leave, b, gid, data, key)
    assert invoke(management.leave, b, gid, data, key) == ack
    rejoined = join(client, b, code).json()['my_membership']['membership_id']
    assert rejoined != str(data.expected_membership_id)
    before = snapshot(gid, b['uid'])
    assert invoke(management.leave, b, gid, data, key) == ack
    assert snapshot(gid, b['uid']) == before
    # Even matching numeric revisions cannot substitute a previous membership ID.
    fresh = command(b, gid).model_copy(update={'expected_membership_id': data.expected_membership_id})
    denied('REVISION_CONFLICT', invoke, management.leave, b, gid, fresh)
    with session() as db:
        assert db.get(GroupMembership, uuid.UUID(rejoined)).ended_at is None


def test_transfer_ack_recovers_after_actor_leaves_and_group_ends(client, worlds):
    a, b, gid = setup(client, worlds)
    data, key = command(a, gid, b), uuid.uuid4()
    ack = invoke(management.transfer, a, gid, data, key)
    invoke(management.leave, a, gid, command(a, gid))
    with session() as db, db.begin():
        db.get(Group, uuid.UUID(gid)).ended_at = now(db)  # Future disband fixture, not an API.
    assert invoke(management.transfer, a, gid, data, key) == ack
    altered = data.model_copy(update={'expected_group_revision': 100})
    denied('IDEMPOTENCY_CONFLICT', invoke, management.transfer, a, gid, altered, key)


def test_replay_expiry(client, worlds):
    a, b, gid = setup(client, worlds)
    data, key = command(b, gid), uuid.uuid4()
    principal = actor(b['uid'])
    management.leave(principal, uuid.UUID(gid), key, data)
    with session() as db, db.begin():
        r = db.scalar(select(RequestResult).where(RequestResult.operation == 'group-leave'))
        r.completed_at = now(db)-timedelta(hours=24)
    denied('IDEMPOTENCY_EXPIRED', management.leave, principal, uuid.UUID(gid), key, data)


def test_replay_still_requires_active_session(client, worlds):
    a, b, gid = setup(client, worlds)
    data, key = command(b, gid), uuid.uuid4()
    principal = actor(b['uid'])
    management.leave(principal, uuid.UUID(gid), key, data)
    with session() as db, db.begin():
        db.get(Session, principal[1].id).revoked_at = now(db)
    denied('SESSION_REVOKED', management.leave, principal, uuid.UUID(gid), key, data)


def test_management_read_permissions_no_writes_and_outsider_denial(client, worlds):
    a, b, gid = setup(client, worlds)
    before = snapshot(gid, b['uid'])
    leader = management.get(actor(a['uid']), uuid.UUID(gid))
    member = management.get(actor(b['uid']), uuid.UUID(gid))
    assert leader['permissions']['transfer_leadership']['allowed']
    assert not leader['permissions']['leave']['allowed']
    assert member['permissions']['leave']['allowed']
    assert not member['permissions']['disband']['allowed']
    assert snapshot(gid, b['uid']) == before
    c = worlds('outsider')
    denied('GROUP_MEMBERSHIP_REQUIRED', management.get, actor(c['uid']), uuid.UUID(gid))


def test_disabled_target_cannot_receive_leadership(client, worlds):
    a, b, gid = setup(client, worlds)
    data = command(a, gid, b)
    with session() as db, db.begin():
        db.get(User, b['uid']).status = 'disabled'
    denied('GROUP_TARGET_UNAVAILABLE', invoke, management.transfer, a, gid, data)


def test_leader_cannot_leave_and_self_transfer_is_rejected(client, worlds):
    a, b, gid = setup(client, worlds)
    denied('GROUP_LEADER_TRANSFER_REQUIRED', invoke, management.leave, a, gid, command(a, gid))
    data = command(a, gid, a)
    denied('GROUP_TRANSFER_TARGET_INVALID', invoke, management.transfer, a, gid, data)


def test_stale_target_and_foreign_membership_are_rejected(client, worlds):
    a, b, gid = setup(client, worlds)
    data = command(a, gid, b)
    stale = data.model_copy(update={'expected_target_membership_revision': 99})
    denied('REVISION_CONFLICT', invoke, management.transfer, a, gid, stale)
    c = worlds('outsider')
    other = group(client, c)
    foreign = command(c, other).expected_membership_id
    denied('GROUP_TARGET_UNAVAILABLE', invoke, management.transfer, a, gid,
           data.model_copy(update={'target_membership_id': foreign}))


def test_failure_rolls_back_membership_invitation_heads_and_ack(client, worlds, monkeypatch):
    a, b, gid = setup(client, worlds)
    c = worlds('c')
    rid = invite(client, b, c, gid).json()['relation_id']
    data, key = command(b, gid), uuid.uuid4()
    before = snapshot(gid, b['uid'])
    original = admissions.commit_result
    def crash(*args):
        raise RuntimeError('injected ACK failure')
    monkeypatch.setattr(admissions, 'commit_result', crash)
    with pytest.raises(RuntimeError):
        invoke(management.leave, b, gid, data, key)
    assert snapshot(gid, b['uid']) == before
    assert relation(client, c, rid)['state'] == 'pending'
    assert command(b, gid) == data
    monkeypatch.setattr(admissions, 'commit_result', original)
    assert invoke(management.leave, b, gid, data, key)[0] == 200


def test_concurrent_transfers_have_one_winner(client, worlds):
    a, b, gid = setup(client, worlds)
    c = worlds('c')
    rid = apply(client, c, gid).json()['relation_id']
    assert action(client, a, rid, 'approve').status_code == 200
    commands = [command(a, gid, w) for w in (b, c)]
    def attempt(data):
        try:
            return invoke(management.transfer, a, gid, data)[0]
        except GameError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, commands)) == [200, 403]


def test_transfer_failure_rolls_back_both_memberships_and_group(client, worlds, monkeypatch):
    a, b, gid = setup(client, worlds)
    data, key = command(a, gid, b), uuid.uuid4()
    before = snapshot(gid, a['uid'])
    original = admissions.commit_result
    def crash(*args):
        raise RuntimeError('injected transfer ACK failure')
    monkeypatch.setattr(admissions, 'commit_result', crash)
    with pytest.raises(RuntimeError):
        invoke(management.transfer, a, gid, data, key)
    assert snapshot(gid, a['uid']) == before
    with session() as db:
        assert db.get(GroupMembership, data.expected_membership_id).revision == data.expected_membership_revision
        assert db.get(GroupMembership, data.target_membership_id).revision == data.expected_target_membership_revision
    monkeypatch.setattr(admissions, 'commit_result', original)
    assert invoke(management.transfer, a, gid, data, key)[0] == 200


def test_concurrent_leave_and_invitation_accept_use_current_membership(client, worlds):
    a, b, gid = setup(client, worlds)
    c = worlds('c')
    rid = invite(client, b, c, gid).json()['relation_id']
    leave_data = command(b, gid)
    body = dict(**action_body(client, c, rid), **own_selection(c),
                expected_limits_revision=limits(client, c)['limits_revision'],
                expected_usage_revision=limits(client, c)['usage_revision'])
    principal = actor(b['uid'])
    from fastapi.testclient import TestClient
    from app.main import app
    def leave():
        try:
            return management.leave(principal, uuid.UUID(gid), uuid.uuid4(), leave_data)[0]
        except GameError as exc:
            return exc.status
    def accept_invitation():
        with TestClient(app) as other:
            return post(other, c, '/v1/group-relations/'+rid+'/accept', body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(leave), pool.submit(accept_invitation)
        left, accepted = first.result(), second.result()
    # Each changes members_revision, so the other stale command must fail.
    assert sorted([left, accepted]) == [200, 409]
    with session() as db:
        members = set(db.scalars(select(GroupMembership.user_id).where(
            GroupMembership.group_id == uuid.UUID(gid), GroupMembership.ended_at.is_(None))))
        assert (b['uid'] in members) == (left != 200)
        assert (c['uid'] in members) == (accepted == 200)


def test_members_cursor_invalidated_on_transfer_and_leave(client, worlds):
    a, b, gid = setup(client, worlds)
    path = '/v1/groups/'+gid+'/members'
    cursor = client.get(path, headers=b['headers'], params={'limit': 1}).json()['next_cursor']
    invoke(management.transfer, a, gid, command(a, gid, b))
    stale = client.get(path, headers=b['headers'], params={'limit': 1, 'cursor': cursor})
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'CURSOR_STALE'
    cursor = client.get(path, headers=b['headers'], params={'limit': 1}).json()['next_cursor']
    invoke(management.leave, a, gid, command(a, gid))
    stale = client.get(path, headers=b['headers'], params={'limit': 1, 'cursor': cursor})
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'CURSOR_STALE'


def test_transfer_and_leave_pending_lease_cannot_run_twice(client, worlds):
    a, b, gid = setup(client, worlds)
    data, key = command(b, gid), uuid.uuid4()
    from app.game_accounts.support import reserve, release
    from fastapi.encoders import jsonable_encoder
    ticket, _ = reserve(actor(b['uid']), 'group-leave', key,
                        dict(group_id=gid, body=jsonable_encoder(data)))
    denied('REQUEST_IN_PROGRESS', invoke, management.leave, b, gid, data, key)
    release(ticket)
    ack = invoke(management.leave, b, gid, data, key)
    assert invoke(management.leave, b, gid, data, key) == ack


@pytest.mark.parametrize('value', [True, 1.5, '1', 0, None])
def test_internal_revision_input_is_strict(value):
    with pytest.raises(ValidationError):
        LeaveGroup(expected_group_revision=value, expected_members_revision=1,
                   expected_membership_id=uuid.uuid4(), expected_membership_revision=1)
