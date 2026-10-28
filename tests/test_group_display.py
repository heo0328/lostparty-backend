"""Group display on a disposable PostgreSQL database owned by a restricted role."""
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import select, inspect, event, text
from app.core import database
from app.core.database import session, now
from app.game_accounts.models import Character, Activity, CharacterRoleSummary, Account
from app.game_accounts.power_success import capture
from app.groups.feature_models import GroupActivityHead, SubjectCharacterReference
from app.groups.admission_models import GroupJoinRelation, GroupJoinSubject
from app.groups.models import GroupMembership
from tests.test_group_admissions import worlds, group, apply, action, invite, accept, post, own_selection
from tests.test_raid_room_migrations import isolated_app_database, table_digests
from tests.test_group_foundation import actor
from tests.test_role_summaries import summary

PROFILE = {'reader_profile': 'group-display-1'}


@pytest.fixture
def group_features(client, worlds, monkeypatch):
    with isolated_app_database() as (target, role, upgrade):
        upgrade('0033_reapplication_history')
        with monkeypatch.context() as patch:
            patch.setattr(database, 'engine', lambda: target)
            a, b = worlds('group-display-a'), worlds('group-display-b')
            gid = group(client, a)
            tables = set(inspect(target).get_table_names()) - {'alembic_version'}
            before = table_digests(target, tables)
            upgrade('0034_group_features')
            assert table_digests(target, tables) == before
            yield target, a, b, gid


def get(client, w, path, **params):
    response = client.get(path, headers=w['headers'], params=params)
    assert response.status_code == 200, response.text
    return response.json()


def add(client, a, b, gid):
    pending = apply(client, b, gid).json()
    assert action(client, a, pending['relation_id'], 'approve').status_code == 200
    return get(client, b, '/v1/me/groups/' + gid)['my_membership']['membership_id']


def test_old_schema_and_profile_contract(client, worlds):
    a = worlds('group-old-schema'); gid = group(client, a)
    assert client.get('/v1/groups/'+gid+'/members', headers=a['headers']).status_code == 200
    response = client.get('/v1/groups/'+gid+'/members', headers=a['headers'], params=PROFILE)
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'GROUP_FEATURE_NOT_READY'


def test_migration_legacy_unknown_and_bulk_activity_read_only(group_features, client):
    target, a, b, gid = group_features
    assert get(client, a, '/v1/me/groups/'+gid, **PROFILE)['last_activity_at'] is None
    mid = add(client, a, b, gid)
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split()[0].upper())
    event.listen(target, 'before_cursor_execute', record)
    try:
        old = get(client, a, '/v1/groups/'+gid+'/members')
        shown = get(client, a, '/v1/groups/'+gid+'/members', **PROFILE)
        activity = get(client, a, f'/v1/groups/{gid}/members/{mid}/activity-characters')
    finally:
        event.remove(target, 'before_cursor_execute', record)
    assert set(statements) <= {'SELECT', 'SET'}
    assert all('character_spec' not in v for v in old['items'])
    assert len(shown['items']) == 2 and len(activity['items']) == 2
    assert {v['character_id'] for v in activity['items']} == set(b['ids'][:2])
    assert all(v['character_spec']['item_level'] == '1700' for v in activity['items'])
    assert str(b['uid']) not in str(activity) and b['rid'] not in str(activity)
    assert get(client, a, '/v1/me/groups/'+gid, **PROFILE)['last_activity_at'] is not None


def test_cursor_changes_on_activity_and_rejects_other_session_or_target(group_features, client):
    _, a, b, gid = group_features; mid = add(client, a, b, gid)
    path = f'/v1/groups/{gid}/members/{mid}/activity-characters'
    page = get(client, a, path, limit=1); cursor = page['next_cursor']; assert cursor
    assert get(client, a, path, limit=1, cursor=cursor)['next_cursor'] is None
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(b['ids'][0])); c.summary = dict(c.summary, item_level='1701')
    response = client.get(path, headers=a['headers'], params={'limit':1,'cursor':cursor})
    assert response.status_code == 409 and response.json()['error']['code'] == 'CURSOR_STALE'
    response = client.get(path, headers=b['headers'], params={'limit':1,'cursor':cursor})
    assert response.status_code == 400
    assert client.get(f'/v1/groups/{gid}/members/{uuid.uuid4()}/activity-characters',headers=a['headers']).status_code == 404


def test_counts_expiration_issuer_leave_and_replay_activity(group_features, client):
    _, a, b, gid = group_features
    key = uuid.uuid4(); response = invite(client, a, b, gid, key); assert response.status_code == 201
    counts = get(client, b, '/v1/me/group-request-counts')
    assert (counts['received_invitations'], counts['action_required']) == (1,1)
    leader = get(client, a, f'/v1/groups/{gid}/join-request-counts')
    assert (leader['pending_invitations'],leader['action_required']) == (1,0)
    with session() as db: before = db.get(GroupActivityHead, uuid.UUID(gid)).last_activity_at
    # Same original request and key; no write on replay.
    again = invite(client, a, b, gid, key); assert again.json() == response.json()
    with session() as db: assert db.get(GroupActivityHead,uuid.UUID(gid)).last_activity_at == before
    with session() as db, db.begin():
        r = db.get(GroupJoinRelation, uuid.UUID(response.json()['relation_id']))
        r.created_at = now(db)-timedelta(days=2); r.expires_at = now(db)-timedelta(days=1)
    assert get(client,b,'/v1/me/group-request-counts')['action_required'] == 0


def test_counts_more_than_page_and_disabled_source(group_features, client, worlds):
    _, a, b, gid = group_features
    for i in range(23):
        from app.auth.router import _limits
        _limits.clear()  # Independent fabricated identities; this test measures relation pagination.
        w = worlds('count-'+str(i)); assert apply(client,w,gid).status_code == 201
    assert len(get(client,a,f'/v1/groups/{gid}/join-relations')['items']) == 20
    counts = get(client,a,'/v1/me/group-request-counts')
    assert counts['managed_applications'] == counts['action_required'] == 23
    assert counts['sent_applications'] == 0
    assert client.get(f'/v1/groups/{gid}/join-request-counts',headers=b['headers']).status_code == 403


def test_role_success_current_error_and_ownership_loss(group_features, client):
    _, a, b, gid = group_features; mid = add(client,a,b,gid)
    with session() as db, db.begin():
        payload=summary(); payload['combat_power']='123.45'
        head=CharacterRoleSummary(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),ownership_revision=1,
            role='dealer',version=2,summary=payload,saved_at=now(db));db.add(head);db.flush();capture(db,head)
        payload=dict(payload,combat_power=None,combat_power_observed_at=None,integrity_status='error',issues=[{'code':'GEM_INVALID','severity':'error'}])
        head.summary=payload;head.version=3
    shown=get(client,a,f'/v1/groups/{gid}/members/{mid}/activity-characters')['items'][0]['character_spec']
    assert shown['dealer']['combat_power']=='123.45'
    assert shown['dealer']['analysis']['integrity_status']=='error'
    with session() as db,db.begin():db.get(Account,b['aid']).owner_id=None
    assert get(client,a,f'/v1/groups/{gid}/members/{mid}/activity-characters')['items']==[]
    members=get(client,a,f'/v1/groups/{gid}/members',**PROFILE)
    assert len(members['items'])==2
    assert next(r for r in members['items'] if r['membership_id']==mid)['character_spec']['state']=='unavailable'


def test_subject_provenance_and_no_name_relink(group_features,client):
    _,a,b,gid=group_features
    pending=apply(client,b,gid).json()
    assert action(client,a,pending['relation_id'],'reject',{'block_future':True}).status_code==200
    value=get(client,a,f'/v1/groups/{gid}/blocked-subjects',**PROFILE)['items'][0]
    assert value['character_spec']['character_id']==b['ids'][0]
    with session() as db,db.begin():
        ref=db.get(SubjectCharacterReference,uuid.UUID(value['subject_id']));db.delete(ref)
    value=get(client,a,f'/v1/groups/{gid}/blocked-subjects',**PROFILE)['items'][0]
    assert value['application_count']==1
    assert value['character_spec']['reason']=='CHARACTER_REFERENCE_UNAVAILABLE'


def test_activity_matches_existing_search_candidates_and_membership_refresh(group_features, client):
    from app.raid_rooms import search, character_candidates
    from app.groups import management
    from tests.test_group_management import command
    _, a, b, gid = group_features; mid = add(client,a,b,gid); group_id=uuid.UUID(gid)
    shown=get(client,a,f'/v1/groups/{gid}/members/{mid}/activity-characters')
    ctx=search.get_context(actor(a['uid']),[group_id])
    page=character_candidates.get(actor(a['uid']),group_id,ctx['filter_context_token'])
    target=next(m for m in page['groups'] if str(m['alias']['group_membership_id'])==mid)
    assert {str(c['character_id']) for c in target['characters']} == {c['character_id'] for c in shown['items']}
    management.leave(actor(b['uid']),group_id,uuid.uuid4(),command(b,gid))
    fresh=search.get_context(actor(a['uid']),[group_id])
    assert fresh['filter_context_token'] != ctx['filter_context_token']
    assert client.get(f'/v1/groups/{gid}/members/{mid}/activity-characters',headers=a['headers']).status_code==404
    from app.game_accounts.support import GameError
    with pytest.raises(GameError) as exc:
        character_candidates.get(actor(a['uid']),group_id,ctx['filter_context_token'])
    assert exc.value.code=='FILTER_CONTEXT_STALE'
