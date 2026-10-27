import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.database import session,now
from app.core.errors import register
from app.groups.models import Group,GroupMembership
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from app.raid_rooms.admission_router import router as admissions
from app.raid_rooms.search_router import router
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,post,create,admission
from tests.test_raid_room_http import err


@pytest.fixture
def http():
    app=FastAPI();app.include_router(admissions);app.include_router(router);register(app)
    from sqlalchemy.exc import SQLAlchemyError
    async def sql_error(request,error):raise error
    app.add_exception_handler(SQLAlchemyError,sql_error)
    with TestClient(app) as c:yield c


def groups(a,b):
    result=[]
    with session() as db,db.begin():
        stamp=now(db)
        for n in range(2):
            gid=uuid.uuid4();aid=uuid.uuid4();bid=uuid.uuid4()
            db.add(Group(id=gid,name='합성 검색',revision=1,members_revision=1,leader_membership_id=aid,representative_character_id=uuid.UUID(a['ids'][0]),representative_user_id=a['uid'],representative_display={},created_at=stamp));db.flush()
            db.add_all([GroupMembership(id=aid,group_id=gid,user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),display={},revision=1,joined_at=stamp),GroupMembership(id=bid,group_id=gid,user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),display={},revision=1,joined_at=stamp)])
            db.flush();result.append(gid)
    return result


def test_member_alias_dedup_and_member_character_and_filters(ready,http):
    target,a,b,_=ready;gids=groups(a,b);rid,_=create(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    with session() as db,db.begin():db.get(Room,uuid.UUID(rid)).group_id=gids[0]
    response=http.get('/v1/me/raid-room-filter-context',params=dict(group_ids=','.join(map(str,gids))),headers=a['headers'])
    assert response.status_code==200,response.text
    c=response.json();assert len(c['members'])==2 and all(len(m['aliases'])==2 for m in c['members'])
    assert str(a['uid']) not in response.text and str(b['uid']) not in response.text
    with session() as db:
        aid=db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==gids[0],GroupMembership.user_id==a['uid']))
    ar=next(m['member_ref'] for m in c['members'] if any(alias['group_membership_id']==str(aid) for alias in m['aliases']));br=next(m['member_ref'] for m in c['members'] if m['member_ref']!=ar)
    data=dict(category='group_linked',admission_scope='public',group_ids=list(map(str,gids)),filter_context_token=c['filter_context_token'],
        member_conditions=[dict(member_ref=ar,character_ids=[a['ids'][0]]),dict(member_ref=br,character_ids=[b['ids'][0]])],raid_ids=[],difficulty_ids=[],limit=1,cursor=None)
    response=http.post('/v1/raid-rooms/search',json=data,headers=a['headers'])
    assert response.status_code==200,response.text
    assert [r['room_id'] for r in response.json()['items']]==[rid]
    data['member_conditions'][1]['character_ids']=[a['ids'][0]]
    response=http.post('/v1/raid-rooms/search',json=data,headers=a['headers']);assert response.status_code==200,response.text
    assert response.json()['items']==[]
    with session() as db,db.begin():db.get(Group,gids[1]).members_revision+=1
    err(http.post('/v1/raid-rooms/search',json=data,headers=a['headers']),409,'FILTER_CONTEXT_STALE')


def test_filter_context_never_returns_partial_unauthorized_groups(ready,http):
    target,a,b,s=ready
    err(http.get('/v1/me/raid-room-filter-context',params=dict(group_ids=str(uuid.uuid4())),headers=a['headers']),404,'GROUP_NOT_FOUND')


def test_group_projection_uses_the_same_multigroup_filter_reference(ready,http):
    from app.raid_rooms import member_reads
    from tests.test_group_foundation import actor
    target,a,b,_=ready;gids=groups(a,b);rid,_=create(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    with session() as db,db.begin():db.get(Room,uuid.UUID(rid)).group_id=gids[0]
    c=http.get('/v1/me/raid-room-filter-context',params=dict(group_ids=','.join(map(str,gids))),headers=a['headers']).json()
    result=member_reads.projections(actor(a['uid']),gids[0],[uuid.UUID(rid)],c['filter_context_token'],gids)
    assert {m['member_ref'] for m in result['rooms'][0]['members']}=={m['member_ref'] for m in c['members']}


def test_member_count_sort_remaining_slots_before_page_and_cursor_binding(ready,http):
    from app.raid_rooms import core
    target,a,b,_=ready;gid=groups(a,b)[0];first,_=create(http,a)
    assert post(http,b,f'raid-rooms/{first}/join',admission(http,b,first)).status_code==200
    aa=dict(a,ids=[a['ids'][1],a['ids'][0],*a['ids'][2:]])
    bb=dict(b,ids=[b['ids'][1],b['ids'][0],*b['ids'][2:]])
    second,_=create(http,aa);third,_=create(http,bb)
    with session() as db,db.begin():
        stamp=now(db)
        for rid in (first,second,third):db.get(Room,uuid.UUID(rid)).group_id=gid
        for rid in (second,third):db.get(Room,uuid.UUID(rid)).created_at=stamp
        core.directory(db)
    tied=sorted([second,third],reverse=True)
    data=dict(category='group_linked',admission_scope='public',group_ids=[str(gid)],filter_context_token=None,member_conditions=[],raid_ids=['horizon_cathedral'],difficulty_ids=['stage1'],limit=1,cursor=None)
    def fetch(body):
        out=http.post('/v1/raid-rooms/search',json=body,headers=a['headers']);assert out.status_code==200,out.text
        return out.json()
    page=fetch(data);assert [r['room_id'] for r in page['items']]==[first]
    cursor=page['next_cursor'];assert cursor
    page=fetch(dict(data,cursor=cursor));assert page['items'][0]['room_id']==tied[0]
    err(http.post('/v1/raid-rooms/search',json=dict(data,cursor=cursor,sort=dict(criterion='member_count',direction='ascending')),headers=a['headers']),409,'CURSOR_STALE')
    assert fetch(dict(data,sort=dict(criterion='member_count',direction='ascending')))['items'][0]['room_id']==tied[0]
    assert fetch(dict(data,remaining_slot_counts=[3]))['items'][0]['room_id']==tied[0]
    assert fetch(dict(data,remaining_slot_counts=[1]))['items']==[]
    page=fetch(dict(data,remaining_slot_counts=[3,2]));assert page['items'][0]['room_id']==first
    assert fetch(dict(data,remaining_slot_counts=[2,3],cursor=page['next_cursor']))['items'][0]['room_id']==tied[0]
    for extra in (dict(remaining_slot_counts=[True]),dict(remaining_slot_counts=[0]),dict(remaining_slot_counts=[8]),dict(remaining_slot_counts=[2,2]),dict(sort=dict(criterion='remaining_slots',direction='ascending'))):
        err(http.post('/v1/raid-rooms/search',json=dict(data,**extra),headers=a['headers']),400,'INVALID_REQUEST')
    from app.auth.models import User
    from app.raid_rooms.integrated_models import RecruitmentMembership as Member
    with session() as db,db.begin():
        stamp=now(db)
        for _ in range(2):
            uid=uuid.uuid4();db.add(User(id=uid,status='active',created_at=stamp,updated_at=stamp,last_login_at=stamp));db.flush()
            db.add(Member(id=uuid.uuid4(),room_id=uuid.UUID(first),user_id=uid,revision=1,joined_at=stamp))
        core.directory(db)
    assert fetch(data)['items'][0]['room_id']==first
    assert fetch(dict(data,remaining_slot_counts=list(range(1,8))))['items'][0]['room_id']==tied[0]
    err(http.post('/v1/raid-rooms/search',json=dict(data,cursor=cursor),headers=a['headers']),409,'CURSOR_STALE')
