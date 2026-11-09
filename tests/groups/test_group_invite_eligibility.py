"""Invite identity feedback; fabricated actors and disposable PostgreSQL only."""
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import select

from app.core.database import session
from app.core.database import now
from app.game_accounts.models.models import Account
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import NameClaim
from app.game_accounts.provider_io.provider import LostArkProvider
from app.groups.admission_models import GroupJoinRelation
from app.groups.admission_models import GroupJoinSubject
from app.groups.display_schemas import EligibleInviteCandidates
from app.groups.models import GroupMembership
from app.lostark_keys import service as credentials
from tests.groups.test_group_admissions import worlds
from tests.groups.test_group_admissions import group
from tests.groups.test_group_admissions import invite
from tests.groups.test_group_admissions import accept
from tests.groups.test_group_admissions import post
from tests.groups.test_group_display import group_features
from tests.groups.test_group_display import add
from tests.groups.test_group_invite_display import candidates
from tests.groups.test_group_invite_display import rename
from tests.game_accounts.test_representative import error
from tests.raid_rooms.common.test_raid_room_migrations import isolated_app_database
from app.core import database

PROFILE = 'group-invite-eligibility-1'


@pytest.fixture(params=['0034_group_features', '0035_cycle_group_policy'])
def eligibility_world(request, client, worlds, monkeypatch):
    with isolated_app_database() as (target, _, upgrade):
        upgrade(request.param)
        monkeypatch.setattr(database, 'engine', lambda: target)
        a, b = worlds('eligibility-a'), worlds('eligibility-b')
        yield target, a, b, group(client, a)


def test_current_owner_self_member_other_group_and_ended_membership(eligibility_world, client):
    target, a, b, gid = eligibility_world
    # Activity selection and membership's representative character do not define identity.
    name = rename(a, 2, 'SelfAltHero')
    page = candidates(client, a, gid, name, PROFILE)
    assert page['profile'] == PROFILE and page['items'][0]['invitation_eligibility'] == 'self'
    name = rename(b, 2, 'MemberAltHero')
    assert candidates(client, a, gid, name, PROFILE)['items'][0]['invitation_eligibility'] == 'eligible'
    other_gid = group(client, b)
    assert other_gid != gid
    assert candidates(client, a, gid, name, PROFILE)['items'][0]['invitation_eligibility'] == 'eligible'
    mid = add(client, a, b, gid)
    item = candidates(client, a, gid, name, PROFILE)['items'][0]
    assert item['invitation_eligibility'] == 'already_member'
    assert item['target_character_id'] == b['ids'][2]
    assert candidates(client, b, gid, name, PROFILE)['items'][0]['invitation_eligibility'] == 'self'
    old = candidates(client, a, gid, name)
    assert {k: v for k, v in item.items() if k != 'invitation_eligibility'} == old['items'][0]
    assert 'invitation_eligibility' not in candidates(client, a, gid, name, False)['items'][0]
    with session() as db, db.begin():
        db.get(GroupMembership, uuid.UUID(mid)).ended_at = now(db)
    assert candidates(client, a, gid, name, PROFILE)['items'][0]['invitation_eligibility'] == 'eligible'


def test_profile_privacy_read_only_batch_and_search_compatibility(group_features, client, monkeypatch):
    target, a, b, gid = group_features
    name = rename(a, 2, 'MixedIdentity한글')
    rename(b, 2, name)
    def forbidden(*args, **kwargs):
        raise AssertionError('No provider or key access')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(credentials, 'capture', forbidden)
    statements = []
    def record(conn, cursor, sql, parameters, context, many):
        statements.append(sql)
    event.listen(target, 'before_cursor_execute', record)
    try:
        page = candidates(client, a, gid, ' mixedidentity한글 ', PROFILE)
    finally:
        event.remove(target, 'before_cursor_execute', record)
    assert set(sql.lstrip().split()[0].upper() for sql in statements) <= {'SELECT', 'SET'}
    batch = [sql for sql in statements if 'group_memberships.user_id IN' in sql]
    assert len(batch) == 1
    assert {i['invitation_eligibility'] for i in page['items']} == {'self', 'eligible'}
    assert [i['target_character_id'] for i in page['items']] == [
        i['target_character_id'] for i in candidates(client, a, gid, name)['items']]
    for actor in (a, b):
        for private in ('uid', 'rid', 'aid'):
            assert str(actor[private]) not in str(page)
    for query in ('MixedIdentity', 'MixedIdentity%', '_'):
        assert candidates(client, a, gid, query, PROFILE)['items'] == []
    path = f'/v1/groups/{gid}/invite-candidates'
    error(client.get(path, headers=b['headers'], params={'character_name': name, 'reader_profile': PROFILE}),
          403, 'GROUP_MEMBERSHIP_REQUIRED')
    for params in ([('character_name', name), ('reader_profile', PROFILE), ('reader_profile', PROFILE)],
                   {'character_name': name, 'reader_profile': 'unknown'},
                   {'character_name': name, 'reader_profile': PROFILE, 'user_id': str(a['uid'])}):
        error(client.get(path, headers=a['headers'], params=params), 400, 'INVALID_REQUEST')
    item = dict(page['items'][0])
    for invalid in (None, 'blocked'):
        bad = dict(page, items=[dict(item, invitation_eligibility=invalid)])
        with pytest.raises(ValueError):
            EligibleInviteCandidates.model_validate(bad)
    del item['invitation_eligibility']
    with pytest.raises(ValueError):
        EligibleInviteCandidates.model_validate(dict(page, items=[item]))


def counts():
    with session() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (GroupJoinSubject, GroupJoinRelation, GroupMembership))


def test_search_keeps_server_order_and_fifty_candidate_limit(group_features, client):
    _, a, b, gid = group_features
    with session() as db, db.begin():
        current = now(db)
        for index in range(51):
            server = f'limit-server-{index:02}'
            char = Character(account_id=b['aid'], server_name=server, character_name='LimitHero',
                             summary={'class_name': 'test-class'}, fetched_at=current, confirmed_at=current)
            db.add(char)
            db.flush()
            db.add(NameClaim(server_name=server, character_name='LimitHero', character_id=char.id))
    items = candidates(client, a, gid, 'limithero', PROFILE)['items']
    assert len(items) == 50
    assert [item['display']['server_name'] for item in items] == [f'limit-server-{i:02}' for i in range(50)]
    assert {item['invitation_eligibility'] for item in items} == {'eligible'}


def test_self_post_precedence_and_no_side_effects(group_features, client):
    _, a, b, gid = group_features
    before = counts()
    error(invite(client, a, a, gid), 409, 'SELF_INVITATION')
    alt = dict(a, ids=[a['ids'][2]])
    error(invite(client, a, alt, gid), 409, 'SELF_INVITATION')
    detail = client.get('/v1/me/groups/' + gid, headers=a['headers']).json()
    body = dict(target_character_id=a['ids'][0], expected_target_ownership_revision=2,
                expected_target_lifecycle_revision=1, expected_group_revision=detail['group']['revision'],
                expected_membership_revision=detail['my_membership']['revision'])
    error(post(client, a, f'/v1/groups/{gid}/invitations', body), 409, 'REVISION_CONFLICT')
    error(post(client, b, f'/v1/groups/{gid}/invitations', body), 403, 'GROUP_MEMBERSHIP_REQUIRED')
    assert counts() == before


def test_stale_search_membership_ownership_and_successful_replay(group_features, client):
    _, a, b, gid = group_features
    name = rename(b, 0, 'NewMemberHero')
    assert candidates(client, a, gid, name, PROFILE)['items'][0]['invitation_eligibility'] == 'eligible'
    key = uuid.uuid4()
    first = invite(client, a, b, gid, key)
    assert first.status_code == 201, first.text
    assert invite(client, a, b, gid, key).json() == first.json()
    assert accept(client, b, first.json()['relation_id']).status_code == 200
    before = counts()
    error(invite(client, a, b, gid), 409, 'ALREADY_GROUP_MEMBER')
    assert counts() == before
    # Ownership changes after GET cannot use the earlier generation to send an invite.
    with session() as db, db.begin():
        db.get(Account, b['aid']).ownership_revision += 1
    error(invite(client, a, b, gid), 409, 'REVISION_CONFLICT')
    assert counts() == before
