"""G1 real HTTP over isolated PostgreSQL, fake login/provider-free fixture."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from app.auth.models import User, Session
from app.core.database import session, now
from app.game_accounts.models import Activity, Character, Configuration, NameClaim
from app.groups.models import Group, GroupMembership, GroupDirectoryHead
from app.member_limits.models import MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit
from app.member_limits.service import Limits
from tests.test_representative import selection, error
from tests.test_group_foundation import second_actor
from tests.test_member_limits import change


def body(w, **updates):
    out = dict(registration_id=w['rid'], character_id=w['ids'][0], expected_registration_version=1,
               expected_ownership_revision=1, expected_roster_revision=1, expected_lifecycle_revision=1,
               expected_limits_revision=1, expected_usage_revision=1, name='sample group')
    out.update(updates)
    return out


def create(client, w, data=None, key=None):
    return client.post('/v1/groups', json=body(w) if data is None else data,
                       headers={**w['headers'], 'Idempotency-Key': str(key or uuid.uuid4())})


def limits(client, w):
    out = client.get('/v1/me/usage-limits', headers=w['headers'])
    assert out.status_code == 200, out.text
    return out.json()


def fresh_body(client, w, **updates):
    snapshot = limits(client, w)
    return body(w, expected_limits_revision=snapshot['limits_revision'],
                expected_usage_revision=snapshot['usage_revision'], **updates)


def rename(client, w, gid, name='changed', rev=1, key=None):
    return client.patch('/v1/groups/'+gid, headers={**w['headers'], 'Idempotency-Key': str(key or uuid.uuid4())},
                        json=dict(name=name, expected_revision=rev, expected_membership_revision=1))


def test_http_create_public_private_members_lists_replay_no_provider(client, selection, monkeypatch):
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as keys
    def forbidden(*args, **kwargs): raise AssertionError('No provider/key on G1')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(keys, 'capture', forbidden)
    w = selection
    assert limits(client, w)['limit_source'] == 'default'
    key = uuid.uuid4()
    out = create(client, w, key=key)
    assert out.status_code == 201, out.text
    data = out.json(); gid = data['group']['group_id']
    assert data['capacity'] == dict(limit=15, used=1, remaining=14, state='within')
    assert create(client, w, key=key).json() == data
    assert create(client, w, body(w, name='different'), key).status_code == 409
    assert limits(client, w)['usage_revision'] == 2
    public = client.get('/v1/groups/'+gid)
    assert public.status_code == 200 and public.json() == data['group']
    assert client.get('/v1/groups/'+gid, headers=w['headers']).json() == public.json()
    assert client.get('/v1/groups').json()['items'] == [data['group']]
    assert client.get('/v1/me/groups/'+gid, headers=w['headers']).json() == data
    assert client.get('/v1/me/groups', headers=w['headers']).json()['items'] == [data]
    members = client.get('/v1/groups/'+gid+'/members', headers=w['headers']).json()
    assert members['items'][0]['is_me'] and members['items'][0]['role'] == 'leader'
    assert members['next_cursor'] is None
    assert str(w['uid']) not in public.text and w['ids'][0] not in public.text
    assert set(data['permissions']) == {'rename', 'list_members'}
    for r in (out, public): assert r.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('path', ['/v1/groups', '/v1/me/groups', '/v1/me/usage-limits'])
def test_get_writes_nothing(client, selection, path):
    w = selection
    with session() as db:
        before = [db.scalar(select(func.count()).select_from(m)) for m in (Group, GroupMembership, MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit)]
    for _ in range(2):
        assert client.get(path, headers=w['headers']).status_code == 200
    with session() as db:
        assert before == [db.scalar(select(func.count()).select_from(m)) for m in (Group, GroupMembership, MemberUsageLimits, MemberUsageHead, MemberUsageLimitAudit)]


@pytest.mark.parametrize('update', [dict(expected_limits_revision=2),dict(expected_usage_revision=2)])
def test_policy_cas(client, selection, update):
    error(create(client, selection, body(selection, **update)), 409, 'POLICY_CONTEXT_CHANGED')
    assert limits(client, selection)['usage']['joined_groups']['used'] == 0


def test_activity_required_no_floor_and_later_deselection_preserves_rights(client, selection):
    w = selection
    error(create(client, w, body(w, character_id=w['ids'][2])),409,'ACTIVITY_SELECTION_REQUIRED')
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(w['ids'][0]))
        c.summary = dict(c.summary, item_level='1000')
    out = create(client,w)
    assert out.status_code == 201
    gid = out.json()['group']['group_id']
    with session() as db, db.begin():
        db.execute(delete(Activity).where(Activity.settings_id==w['cid']))
    assert client.get('/v1/me/groups/'+gid, headers=w['headers']).status_code == 200
    assert rename(client,w,gid).status_code == 200


def test_limit_exact_over_reduction_and_existing_operations(client, selection):
    w = selection
    change(w['uid'], Limits(15,1,10))
    out = create(client,w, fresh_body(client,w))
    assert out.status_code == 201
    gid = out.json()['group']['group_id']
    assert limits(client,w)['usage']['joined_groups']['state'] == 'at_limit'
    error(create(client,w,fresh_body(client,w)),409,'GROUP_MEMBERSHIP_LIMIT_REACHED')
    change(w['uid'], Limits(0,0,0),expected=2)
    current=client.get('/v1/me/groups/'+gid,headers=w['headers']).json()
    assert current['capacity']['state']=='exceeded'
    assert current['permissions']['rename']['allowed']
    assert rename(client,w,gid).status_code==200
    assert limits(client,w)['usage']['joined_groups']['state']=='exceeded'
    error(create(client,w,fresh_body(client,w)),409,'GROUP_CAPACITY_REACHED')


@pytest.mark.parametrize('extra', [dict(actor='fake'),dict(expected_usage_revision=True),dict(name=None),dict(name='a\nb'),dict(name='')])
def test_strict_create(client,selection,extra):
    error(create(client,selection,body(selection,**extra)),400,'INVALID_REQUEST')


def test_omitted_name_default_and_explicit_null_rejected(client,selection):
    data=body(selection);data.pop('name')
    out=create(client,selection,data)
    assert out.status_code==201 and out.json()['group']['name']=='sample-0의 그룹'


@pytest.mark.parametrize('suffix', ['?limit=0','?limit=51','?limit=2&limit=3','?unknown=1','?cursor=','?q=a&q=b'])
def test_strict_public_query(client,suffix):
    error(client.get('/v1/groups'+suffix),400,'INVALID_REQUEST')


def test_strict_get_body_and_write_query_and_no_limit_write(client, selection):
    w=selection
    error(client.request('GET','/v1/groups',json={}),400,'INVALID_REQUEST')
    error(client.get('/v1/me/usage-limits?user_id=x',headers=w['headers']),400,'INVALID_REQUEST')
    assert client.put('/v1/me/usage-limits',headers=w['headers'],json={'raid_rooms':100}).status_code==405
    error(client.post('/v1/groups?unexpected=1',headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())},json=body(w)),400,'INVALID_REQUEST')
    error(client.post('/v1/groups',headers=w['headers'],json=body(w)),400,'INVALID_REQUEST')


def test_private_authorization_and_revoked_replay(client,selection,login,monkeypatch):
    w=selection; key=uuid.uuid4()
    out=create(client,w,key=key);gid=out.json()['group']['group_id']
    second=second_actor(login,monkeypatch)
    # Obtain a separate active login for its bearer token.
    auth,_=login();other={'Authorization':'Bearer '+auth['access_token']}
    for path in ('/v1/me/groups/'+gid,'/v1/groups/'+gid+'/members'):
        error(client.get(path,headers=other),403,'GROUP_MEMBERSHIP_REQUIRED')
        error(client.get(path),401,'ACCESS_INVALID')
    with session() as db, db.begin():
        membership=db.get(GroupMembership,uuid.UUID(out.json()['my_membership']['membership_id']))
        membership.ended_at=now(db)
    error(create(client,w,key=key),403,'GROUP_MEMBERSHIP_REQUIRED')


def test_search_normalization_saved_representative_and_literal_wildcards(client,selection):
    w=selection
    with session() as db, db.begin():
        original=db.get(Character,uuid.UUID(w['ids'][0]))
        c=Character(account_id=original.account_id,server_name=original.server_name,character_name='한글Hero',
                    summary=dict(original.summary,character_name='한글Hero'),fetched_at=now(db),confirmed_at=now(db))
        db.add(c);db.flush();cid=str(c.id)
        db.add(NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id))
        db.add(Activity(settings_id=w['cid'],account_id=c.account_id,character_id=c.id))
    out=create(client,w,body(w,name='A%_B 그룹',character_id=cid)); assert out.status_code==201
    for q in ('  a%_b  ','한글hero','한글HERO','%_'):
        assert len(client.get('/v1/groups',params={'q':q}).json()['items'])==1
    assert client.get('/v1/groups',params={'q':'unmatched%'}).json()['items']==[]
    assert client.get('/v1/groups',params={'q':'_Z'}).json()['items']==[]


def test_paging_scope_stale_order_and_rename_noop(client,selection,login,monkeypatch):
    w=selection;groups=[]
    for i in range(3):
        r=create(client,w,fresh_body(client,w,name=f'group{i}'));assert r.status_code==201
        groups.append(r.json()['group']['group_id'])
    first=client.get('/v1/groups?limit=1').json()
    assert first['items'][0]['group_id']==groups[-1]
    cursor=first['next_cursor'];assert cursor
    second=client.get('/v1/groups',params={'limit':1,'cursor':cursor}).json()
    assert second['items'][0]['group_id']==groups[-2]
    for params in ({'limit':2,'cursor':cursor},{'limit':1,'q':'group','cursor':cursor},{'limit':1,'cursor':cursor+'x'}):
        error(client.get('/v1/groups',params=params),400,'INVALID_REQUEST')
    mine=client.get('/v1/me/groups?limit=1',headers=w['headers']).json()['next_cursor']
    auth=second_actor(login,monkeypatch);resp,_=login();other={'Authorization':'Bearer '+resp['access_token']}
    error(client.get('/v1/me/groups',params={'limit':1,'cursor':mine},headers=other),400,'INVALID_REQUEST')
    assert rename(client,w,groups[-1],name='group2').json()['group']['revision']==1
    assert client.get('/v1/groups',params={'limit':1,'cursor':cursor}).status_code==200
    assert rename(client,w,groups[-1]).status_code==200
    error(client.get('/v1/groups',params={'limit':1,'cursor':cursor}),409,'CURSOR_STALE')


def test_http_parallel_last_group_limit_has_one_winner(client,selection):
    w=selection;change(w['uid'],Limits(15,1,10))
    data=fresh_body(client,w)
    from app.main import app
    def attempt(_):
        with TestClient(app) as c:return create(c,w,data).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(attempt,range(2)))
    assert sorted(codes)==[201,409]
    assert limits(client,w)['usage']['joined_groups']['used']==1


def test_deleted_character_marks_update_but_preserves_group_rights_and_replay(client,selection):
    w=selection;key=uuid.uuid4();out=create(client,w,key=key);gid=out.json()['group']['group_id']
    with session() as db, db.begin():
        c=db.get(Character,uuid.UUID(w['ids'][0]));c.lifecycle_state='suspect'
    current=client.get('/v1/me/groups/'+gid,headers=w['headers'])
    assert current.status_code==200 and current.json()['group']['representative']['status']=='needs_update'
    assert current.json()['permissions']['rename']['allowed']
    assert create(client,w,key=key).json()==out.json()
    assert rename(client,w,gid).status_code==200


def test_member_pages_bind_actor_and_revision_and_member_cannot_rename(client,selection,login,monkeypatch):
    w=selection;gid=create(client,w).json()['group']['group_id']
    other=second_actor(login,monkeypatch);auth,_=login()
    headers={'Authorization':'Bearer '+auth['access_token']}
    with session() as db,db.begin():
        db.add(GroupMembership(group_id=uuid.UUID(gid),user_id=other[0].id,revision=1,joined_at=now(db)))
        g=db.get(Group,uuid.UUID(gid));g.members_revision+=1
        db.get(GroupDirectoryHead,1).revision+=1
    current=client.get('/v1/me/groups/'+gid,headers=headers).json()
    assert current['my_membership']['role']=='member'
    assert current['permissions']['rename']==dict(allowed=False,reason='GROUP_LEADER_REQUIRED')
    error(client.patch('/v1/groups/'+gid,headers={**headers,'Idempotency-Key':str(uuid.uuid4())},
                       json=dict(name='forged',expected_revision=1,expected_membership_revision=1)),403,'GROUP_LEADER_REQUIRED')
    path='/v1/groups/'+gid+'/members'
    first=client.get(path,params={'limit':1},headers=w['headers']).json()
    assert first['items'][0]['is_me'] and first['items'][0]['role']=='leader'
    cursor=first['next_cursor'];assert cursor
    error(client.get(path,params={'limit':1,'cursor':cursor},headers=headers),400,'INVALID_REQUEST')
    last=client.get(path,params={'limit':1,'cursor':cursor},headers=w['headers']).json()
    assert not last['items'][0]['is_me'] and last['next_cursor'] is None
    assert str(other[0].id) not in str(last)
    rename(client,w,gid)
    error(client.get(path,params={'limit':1,'cursor':cursor},headers=w['headers']),409,'CURSOR_STALE')
