"""L0 persistence/authority/concurrency tests, not real room API tests."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.core.database import session, now
from app.game_accounts.support import GameError, fail
from app.groups.models import Group, GroupMembership
from app.member_limits import service
from app.member_limits.models import MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit
from tests.test_group_foundation import actor, create
from tests.test_representative import selection


def server_authority_for_test(db, uid):
    # Explicit test-only trust. No application user/admin permission is introduced.
    pass


def change(uid, limits, expected=1, authority=server_authority_for_test):
    with session() as db, db.begin():
        return service.change_limits(db, uid, expected, limits, authority='test-server',
                                     reason='isolated-test', authorize_change=authority)


def rows():
    with session() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit))


def test_default_read_is_write_free_and_rooms_are_counted(selection):
    uid = selection['uid']
    for _ in range(2):
        out = service.get(actor(uid))
        assert out['limits'] == dict(group_capacity=15, joined_groups=5, raid_rooms=10)
        assert out['limits_revision'] == out['usage_revision'] == 1
        assert out['limit_source'] == 'default' and out['updated_at'] is None
        assert out['usage']['joined_groups'] == dict(used=0, remaining=5, state='within', can_increase=True)
        assert out['usage']['raid_rooms'] == dict(used=0, remaining=10, state='within', can_increase=True)
        assert out['issues'] == [] and out['evaluated_at'].utcoffset().total_seconds() == 0
        assert rows() == (0, 0, 0)


def test_group_creation_updates_usage_atomically_and_replay_does_not(selection):
    w = selection
    key = uuid.uuid4()
    result = create(w, key=key)
    out = service.get(actor(w['uid']))
    assert out['usage_revision'] == 2 and out['limit_source'] == 'account'
    assert out['usage']['joined_groups']['used'] == 1
    assert rows() == (1, 1, 0)
    assert create(w, key=key) == result
    assert service.get(actor(w['uid']))['usage_revision'] == 2


def test_failed_group_transaction_rolls_back_heads_and_limits(selection, monkeypatch):
    from app.groups import service as groups
    def reject(*args): raise RuntimeError('injected failure after usage update')
    monkeypatch.setattr(groups, 'advance_directory', reject)
    with pytest.raises(RuntimeError): create(selection)
    assert rows() == (0, 0, 0)
    assert service.get(actor(selection['uid']))['usage']['joined_groups']['used'] == 0


def test_usage_excludes_ended_membership_or_ended_group(selection):
    w = selection
    a, b = create(w)[1], create(w)[1]
    with session() as db, db.begin():
        m = db.get(GroupMembership, uuid.UUID(a['my_membership']['membership_id']))
        m.ended_at = now(db)
        service.record_group_membership_change(db, w['uid'])
        g = db.get(Group, uuid.UUID(b['group']['group_id']))
        g.ended_at = now(db)
        service.record_group_membership_change(db, w['uid'])
    out = service.get(actor(w['uid']))
    assert out['usage']['joined_groups']['used'] == 0 and out['usage_revision'] == 5


def test_change_is_cas_audited_noop_and_reduction_preserves_relations(selection):
    w = selection
    create(w)
    create(w)
    assert change(w['uid'], service.Limits(7, 1, 0)) == 2
    out = service.get(actor(w['uid']))
    assert out['limits'] == dict(group_capacity=7, joined_groups=1, raid_rooms=0)
    assert out['usage']['joined_groups'] == dict(used=2, remaining=0, state='exceeded', can_increase=False)
    assert out['issues'] == [dict(code='MEMBER_GROUP_LIMIT_EXCEEDED', dimension='joined_groups', used=2, limit=1)]
    with session() as db:
        audit = db.scalar(select(MemberUsageLimitAudit))
        assert audit.before == dict(group_capacity=15, joined_groups=5, raid_rooms=10)
        assert audit.after == out['limits'] and audit.revision == 2
        assert db.scalar(select(func.count()).select_from(GroupMembership)) == 2
    with pytest.raises(GameError, match='REVISION_CONFLICT'):
        change(w['uid'], service.Limits(), expected=1)
    assert change(w['uid'], service.Limits(7, 1, 0), expected=2) == 2
    assert rows() == (1, 1, 1)
    assert change(w['uid'], service.Limits(7, 2, 0), expected=2) == 3
    out = service.get(actor(w['uid']))
    assert out['usage']['joined_groups']['state'] == 'at_limit' and out['issues'] == []


def test_authority_denial_and_missing_authority_leave_no_rows(selection):
    uid = selection['uid']
    def denied(*args): fail('FORBIDDEN', 403)
    with pytest.raises(GameError, match='FORBIDDEN'):
        change(uid, service.Limits(20), authority=denied)
    with pytest.raises(TypeError):
        change(uid, service.Limits(20), authority=None)
    assert rows() == (0, 0, 0)


def test_concurrent_limit_changes_have_one_revision_winner(selection):
    uid = selection['uid']
    def attempt(value):
        try: return change(uid, service.Limits(value))
        except GameError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [20, 25]))
    assert sorted(map(str, outcomes)) == ['2', 'REVISION_CONFLICT']
    assert rows() == (1, 0, 1)


def test_internal_change_rollback_preserves_default(selection):
    with pytest.raises(RuntimeError):
        with session() as db, db.begin():
            service.change_limits(db, selection['uid'], 1, service.Limits(20),
                                  authority='test-server', reason='test', authorize_change=server_authority_for_test)
            db.flush()
            raise RuntimeError('abort')
    assert rows() == (0, 0, 0)


@pytest.mark.parametrize('bad', [-1, 2147483648, True, 1.0, '1', None])
def test_invalid_limits(bad):
    with pytest.raises(ValueError): service.Limits(joined_groups=bad)


@pytest.mark.parametrize('used,limit,state', [(0,0,'at_limit'), (5,5,'at_limit'), (6,5,'exceeded'), (4,5,'within')])
def test_exact_limit_and_zero(used, limit, state):
    assert service.metric(used, limit)['state'] == state
    assert service.metric(used, limit)['can_increase'] == (used < limit)


def test_database_enforces_nonnegative_and_audit_revision_uniqueness(selection):
    uid = selection['uid']
    with pytest.raises(IntegrityError):
        with session() as db, db.begin():
            db.add(MemberUsageLimits(user_id=uid, revision=1, group_capacity=-1,
                                     joined_groups=5, raid_rooms=10, updated_at=now(db)))
            db.flush()
    change(uid, service.Limits(20))
    with pytest.raises(IntegrityError):
        with session() as db, db.begin():
            db.add(MemberUsageLimitAudit(user_id=uid, revision=2, before={}, after={},
                                         authority='test', reason='test', created_at=now(db)))
            db.flush()
