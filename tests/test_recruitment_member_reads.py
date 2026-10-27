import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.errors import register
from app.raid_rooms.member_router import router
from app.raid_rooms.admission_router import router as admissions
from app.raid_rooms.schedule_router import router as schedules
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,post,create,admission
from tests.test_recruitment_completion import bundle
from tests.test_raid_room_http import err


@pytest.fixture
def http():
    app=FastAPI();register(app)
    for r in (router,admissions,schedules):app.include_router(r)
    with TestClient(app) as c:yield c


def test_detail_and_member_only_time_context_are_distinct_read_projections(ready,http):
    target,a,b,_=ready;rid=bundle(http,a)
    response=http.get(f'/v1/raid-rooms/{rid}',headers=b['headers']);assert response.status_code==200,response.text
    assert response.json()['room_id']==rid
    response=http.get(f'/v1/raid-rooms/{rid}/detail',headers=a['headers']);assert response.status_code==200,response.text
    assert response.json()['my_membership'] is not None
    err(http.get(f'/v1/me/raid-rooms/{rid}/schedule-context',headers=b['headers']),403,'ROOM_MEMBERSHIP_REQUIRED')
    response=http.get(f'/v1/me/raid-rooms/{rid}/schedule-context',headers=a['headers']);assert response.status_code==200,response.text
    assert 'user_id' not in response.text and response.json()['members'][0]['submission']['state']=='missing'
    response=http.get('/v1/me/raid-room-memberships',headers=a['headers']);assert response.status_code==200,response.text
    assert response.json()['items'][0]['current_week_state']=='participating'
    response=http.get('/v1/me/raid-schedule-overlaps',headers=a['headers']);assert response.status_code==200,response.text
    assert response.json()['pair_count']==0


def test_explicit_overlap_preserves_both_and_busy_hides_other_room_identity(ready,http):
    from tests.test_recruitment_scheduling import future,group_at,plan
    target,a,b,_=ready;start=future();rid,_=create(http,a,schedule_groups=[group_at(start)])
    alternate=dict(a,ids=[a['ids'][1],a['ids'][0],*a['ids'][2:]])
    second,_=create(http,alternate,schedule_groups=[group_at(start)])
    p=plan(http,a,rid)
    assert p['my_participations'][0]['overlap_warning']
    out=http.get(f'/v1/me/raid-rooms/{rid}/schedule-context',headers=a['headers']);assert out.status_code==200,out.text
    assert second not in out.text and rid in out.text
    assert len(out.json()['members'][0]['anonymous_busy']['intervals'])==1
    out=http.get('/v1/me/raid-schedule-overlaps',params=dict(limit=1),headers=a['headers']);assert out.status_code==200,out.text
    assert out.json()['pair_count']==1 and out.json()['affected_room_count']==2
    pair=out.json()['items'][0];assert {pair['left']['room_id'],pair['right']['room_id']}=={rid,second}
    assert http.get('/v1/me/raid-schedule-overlaps',headers=b['headers']).json()['items']==[]


def test_ended_membership_does_not_grant_current_private_room_disclosure(ready,http):
    import uuid
    from sqlalchemy import select
    from app.core.database import session,now
    from app.raid_rooms import completion
    from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentMembership as Member
    from app.groups.models import GroupMembership
    from tests.test_recruitment_search import groups
    target,a,b,_=ready;gid=groups(a,b)[0];rid,_=create(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    with session() as db,db.begin():
        stamp=now(db);room=db.get(Room,uuid.UUID(rid));room.scope='group';room.group_id=gid
        member=db.scalar(select(Member).where(Member.room_id==room.id,Member.user_id==b['uid']))
        completion.drop_membership(db,room,member,stamp)
        gm=db.scalar(select(GroupMembership).where(GroupMembership.group_id==gid,GroupMembership.user_id==b['uid']));gm.ended_at=stamp;gm.revision+=1
    out=http.get('/v1/me/raid-room-memberships',params=dict(state='all'),headers=b['headers'])
    assert out.status_code==200,out.text
    assert out.json()['items'][0]['history_only'] and out.json()['items'][0]['room'] is None
    err(http.get(f'/v1/raid-rooms/{rid}',headers=b['headers']),404,'ROOM_NOT_FOUND')
