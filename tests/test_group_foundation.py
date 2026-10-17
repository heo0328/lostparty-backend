"""Internal G1 foundation only: no HTTP contract or undecided product policy activated."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth.models import Session, User
from app.core.database import session, now
from app.core.errors import AuthError
from app.game_accounts.models import Account, Character, Configuration, NameClaim
from app.game_accounts.support import GameError, fail
from app.groups import service
from app.groups.commands import CreateGroup, RenameGroup
from app.groups.models import Group, GroupMembership, GroupDirectoryHead
from tests.test_representative import selection


def actor(uid):
    with session() as db:
        return db.get(User, uid), db.scalar(select(Session).where(Session.user_id == uid))


def command(w, **changes):
    data = dict(registration_id=w['rid'], character_id=w['ids'][0],
                expected_registration_version=1, expected_ownership_revision=1,
                expected_roster_revision=1, expected_lifecycle_revision=1)
    data.update(changes)
    return CreateGroup(**data)


def foundation_test_policy(db, uid, registration, account, character):
    # Explicit test-only acceptance; this is not a production no-limit/activity policy.
    assert registration.user_id == account.owner_id == uid
    assert character.account_id == account.id


def create(w, data=None, key=None, policy=foundation_test_policy):
    return service.create(actor(w['uid']), key or uuid.uuid4(), command(w) if data is None else data, policy=policy)


def rename(w, gid, name='renamed', revision=1, key=None, member_revision=1):
    return service.rename(actor(w['uid']), uuid.UUID(str(gid)), key or uuid.uuid4(),
                          RenameGroup(name=name, expected_revision=revision,
                                      expected_membership_revision=member_revision))


def counts():
    with session() as db:
        return (db.scalar(select(func.count()).select_from(Group)),
                db.scalar(select(func.count()).select_from(GroupMembership)),
                db.get(GroupDirectoryHead, 1).revision)


def second_actor(login, monkeypatch):
    from app.auth import service as auth
    monkeypatch.setattr(auth, 'verify_google', lambda *args: 'second-group-user')
    response, _ = login()
    return actor(uuid.UUID(response['user']['id']))


def test_create_is_atomic_snapshot_only_and_read_only_get(selection, monkeypatch):
    w = selection
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as keys
    def forbidden(*args, **kwargs): raise AssertionError('No external provider/key in group foundation')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(keys, 'capture', forbidden)
    before = counts()
    status, result = create(w)
    assert status == 201
    gid = uuid.UUID(result['group']['group_id'])
    assert result['group']['name'] == 'sample-0의 그룹'
    assert result['group']['member_count'] == 1
    assert result['group']['representative']['status'] == 'valid'
    assert result['my_membership']['role'] == 'leader'
    assert result['leader_membership_id'] == result['my_membership']['membership_id']
    assert result['permissions']['rename'] == dict(allowed=True, reason=None)
    assert counts() == (before[0]+1, before[1]+1, before[2]+1)
    stored = counts()
    for _ in range(2):
        out = service.get(actor(w['uid']), gid)
        assert str(out['my_membership']['membership_id']) == result['my_membership']['membership_id']
    assert counts() == stored
    with session() as db:
        c = db.get(Configuration, w['cid'])
        assert str(c.representative_id) == w['ids'][0] and c.version == 1


def test_optional_creation_policy_is_not_implicitly_enabled(selection):
    w = selection
    with pytest.raises(TypeError):
        service.create(actor(w['uid']), uuid.uuid4(), command(w))
    with pytest.raises(TypeError):
        create(w, policy=None)
    before = counts()
    def pending(*args): fail('GROUP_POLICY_NOT_READY')
    with pytest.raises(GameError, match='GROUP_POLICY_NOT_READY'):
        create(w, policy=pending)
    assert counts() == before
    # Test policy, not a final product choice: low/unselected UUID is still identity-valid.
    with session() as db, db.begin():
        character = db.get(Character, uuid.UUID(w['ids'][2]))
        character.summary = dict(character.summary, item_level='1200')
    assert create(w, command(w, character_id=w['ids'][2]))[0] == 201


@pytest.mark.parametrize('name', [None, '', '  ', 'a'*21, 'a\nb', 'x\x00', 'a\u2028b', 7])
def test_strict_internal_command_name(name):
    with pytest.raises(ValidationError):
        CreateGroup(registration_id=uuid.uuid4(), character_id=uuid.uuid4(), name=name,
                    expected_registration_version=1, expected_ownership_revision=1,
                    expected_roster_revision=1, expected_lifecycle_revision=1)


def test_explicit_names_trim_duplicate_and_auto_name_overflow(selection):
    w = selection
    assert create(w, command(w, name='  shared  '))[1]['group']['name'] == 'shared'
    assert create(w, command(w, name='shared'))[0] == 201
    # A valid canonical address can be long; default-name failure cannot leave half a group.
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(w['ids'][0]))
        claim = db.get(NameClaim, (c.server_name, c.character_name)); db.delete(claim); db.flush()
        c.character_name = 'x'*20; db.flush()
        db.add(NameClaim(server_name=c.server_name, character_name=c.character_name, character_id=c.id))
    before = counts()
    with pytest.raises(GameError, match='GROUP_NAME_REQUIRED'):
        create(w)
    assert counts() == before
    assert create(w, command(w, name='chosen'))[0] == 201


@pytest.mark.parametrize('field', ['expected_registration_version', 'expected_ownership_revision',
                                   'expected_roster_revision', 'expected_lifecycle_revision'])
def test_each_creation_fence(selection, field):
    before = counts()
    with pytest.raises(GameError, match='REVISION_CONFLICT'):
        create(selection, command(selection, **{field: 2}))
    assert counts() == before


@pytest.mark.parametrize('state,code', [('lost','OWNERSHIP_REQUIRED'), ('suspect','CHARACTER_UNUSABLE'),
                                      ('retired','CHARACTER_UNUSABLE'), ('claim_missing','CHARACTER_UNUSABLE'),
                                      ('unknown','CHARACTER_NOT_FOUND')])
def test_identity_checks_are_not_replaced_by_injected_policy(selection, state, code):
    w = selection; data = command(w)
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(w['ids'][0]))
        if state == 'lost': db.get(Account, w['aid']).owner_id = None
        elif state in ('suspect','retired'): c.lifecycle_state = state
        elif state == 'claim_missing': db.delete(db.get(NameClaim, (c.server_name,c.character_name)))
        else: data = command(w, character_id=uuid.uuid4())
    before = counts()
    with pytest.raises(GameError, match=code): create(w, data)
    assert counts() == before


def test_create_success_replay_conflict_and_transaction_rollback(selection, monkeypatch):
    w = selection; key = uuid.uuid4(); before = counts()
    saved = create(w, key=key)
    assert create(w, key=key) == saved and counts()[0] == before[0]+1
    with pytest.raises(GameError, match='IDEMPOTENCY_CONFLICT'):
        create(w, command(w, name='other'), key)
    original = service.commit_result
    monkeypatch.setattr(service, 'commit_result', lambda *args: fail('SERVICE_UNAVAILABLE',503))
    before = counts(); retry = uuid.uuid4()
    with pytest.raises(GameError, match='SERVICE_UNAVAILABLE'): create(w, key=retry)
    assert counts() == before
    monkeypatch.setattr(service, 'commit_result', original)
    assert create(w, key=retry)[0] == 201


def test_foreign_member_private_access_and_owner_survives_character_loss(selection, login, monkeypatch):
    w = selection; original_key = uuid.uuid4(); result = create(w, key=original_key)[1]
    gid = uuid.UUID(result['group']['group_id']); other = second_actor(login, monkeypatch)
    with pytest.raises(GameError, match='GROUP_MEMBERSHIP_REQUIRED'): service.get(other, gid)
    with pytest.raises(GameError, match='REGISTRATION_NOT_FOUND'):
        service.create(other, uuid.uuid4(), command(w), policy=foundation_test_policy)
    # Existing group membership is not a game ownership proof and does not disappear with it.
    with session() as db, db.begin():
        db.get(Account,w['aid']).owner_id = None
        db.get(Configuration,w['cid']).representative_id = uuid.UUID(w['ids'][1])
    out = service.get(actor(w['uid']), gid)
    assert out['group']['representative']['status'] == 'needs_update'
    assert out['group']['representative']['display'] == result['group']['representative']['display']
    assert out['my_membership']['role'] == 'leader' and out['permissions']['rename']['allowed']
    assert create(w,key=original_key)[1] == result  # Historical ACK, not current permissions/status.
    assert rename(w,gid)[0] == 200


def test_rename_cas_noop_replay_and_snapshot_invariants(selection):
    w = selection; first = create(w)[1]; gid = uuid.UUID(first['group']['group_id']); before = counts()
    assert rename(w,gid,name=first['group']['name'])[1]['group']['revision'] == 1
    assert counts() == before
    key = uuid.uuid4(); changed = rename(w,gid,key=key)
    assert changed[1]['group']['revision'] == 2 and changed[1]['members_revision'] == 1
    assert changed[1]['group']['representative'] == first['group']['representative']
    assert rename(w,gid,key=key) == changed
    with pytest.raises(GameError, match='REVISION_CONFLICT'): rename(w,gid)
    with pytest.raises(GameError, match='REVISION_CONFLICT'): rename(w,gid,revision=2,member_revision=2)
    with pytest.raises(GameError, match='IDEMPOTENCY_CONFLICT'): rename(w,gid,name='different',key=key)
    assert counts() == (before[0],before[1],before[2]+1)


def test_regular_member_has_no_leader_privilege(selection,login,monkeypatch):
    w = selection; result = create(w)[1]; gid = uuid.UUID(result['group']['group_id'])
    other = second_actor(login,monkeypatch)
    with session() as db,db.begin():
        db.add(GroupMembership(group_id=gid,user_id=other[0].id,revision=1,joined_at=now(db)))
    out = service.get(other,gid)
    assert out['my_membership']['role']=='member'
    assert out['permissions']['rename']==dict(allowed=False,reason='GROUP_LEADER_REQUIRED')
    with pytest.raises(GameError,match='GROUP_LEADER_REQUIRED'):
        service.rename(other,gid,uuid.uuid4(),RenameGroup(name='forged',expected_revision=1,expected_membership_revision=1))


@pytest.mark.parametrize('change,status', [('revoke',401),('disable',403),('end_membership',403),('end_group',404)])
def test_current_authority_applies_to_success_replay(selection,change,status):
    w = selection; key = uuid.uuid4(); result = create(w,key=key)[1]
    gid = uuid.UUID(result['group']['group_id'])
    with session() as db,db.begin():
        if change=='revoke':db.scalar(select(Session).where(Session.user_id==w['uid'])).revoked_at=now(db)
        elif change=='disable':db.get(User,w['uid']).status='disabled'
        elif change=='end_membership':db.get(GroupMembership,uuid.UUID(result['my_membership']['membership_id'])).ended_at=now(db)
        else:db.get(Group,gid).ended_at=now(db)
    with pytest.raises(AuthError) as error:create(w,key=key)
    assert error.value.status==status
    with pytest.raises(AuthError) as error:service.get(actor(w['uid']),gid)
    assert error.value.status==status


def test_concurrent_rename_and_duplicate_creation(selection):
    w=selection; gid=create(w)[1]['group']['group_id']
    def update(name):
        try:return rename(w,gid,name=name)[0]
        except GameError as e:return e.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update,['left','right']))==[200,409]
    before=counts();key=uuid.uuid4()
    def duplicate(_):
        try:return create(w,key=key)[0]
        except GameError as e:return e.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(duplicate,range(2)))
    assert statuses.count(201)>=1 and all(s in (201,409) for s in statuses)
    assert create(w,key=key)[0]==201 and counts()[0]==before[0]+1


def test_postgres_enforces_member_uniqueness_and_same_group_leader(selection):
    w=selection; first=create(w)[1]; second=create(w)[1]
    gid=uuid.UUID(first['group']['group_id'])
    with pytest.raises(IntegrityError):
        with session() as db,db.begin():
            db.add(GroupMembership(group_id=gid,user_id=w['uid'],revision=1,joined_at=now(db)))
            db.flush()
    # Deferred FK is checked at commit, including group identity, not just member UUID existence.
    with pytest.raises(IntegrityError):
        with session() as db,db.begin():
            db.get(Group,gid).leader_membership_id=uuid.UUID(second['my_membership']['membership_id'])
    assert str(service.get(actor(w['uid']),gid)['leader_membership_id'])==first['leader_membership_id']


def test_projection_contains_no_global_member_identity_or_secrets(selection):
    from fastapi.encoders import jsonable_encoder
    w=selection; gid=uuid.UUID(create(w)[1]['group']['group_id'])
    with session() as db:
        out=jsonable_encoder(service.summary(db,db.get(Group,gid)))
    assert set(out)=={'group_id','name','revision','member_count','representative','leader_display'}
    assert set(out['representative'])=={'display','status'}
    assert set(out['representative']['display'])=={'server_name','character_name','class_name'}
    assert str(w['uid']) not in str(out) and w['ids'][0] not in str(out)
