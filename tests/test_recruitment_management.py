import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import session
from app.core.errors import register
from app.raid_rooms.admission_router import router as admission_router
from app.raid_rooms.management_router import router
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRoom as Room
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,post,create,admission
from tests.test_recruitment_scheduling import plan
from tests.test_raid_room_http import err


@pytest.fixture
def http():
    app=FastAPI();app.include_router(admission_router);app.include_router(router);register(app)
    async def sql_error(request,error):raise error
    app.add_exception_handler(SQLAlchemyError,sql_error)
    with TestClient(app) as c:yield c


def test_settings_no_retroactive_expulsion_and_nonleader_denied(ready,http):
    target,a,b,_=ready;rid,_=create(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    s=http.get(f'/v1/me/raid-rooms/{rid}/settings',headers=a['headers']).json();p=plan(http,a,rid)
    body=dict(expected_cycle_key=p['cycle_key'],expected_room_revision=s['room_revision'],expected_settings_revision=s['revision'],
        experience_level='experienced',combat_requirement=dict(input_mode='shared',dealer_min='99999999',support_min='99999999'),admission_mode='leader_only')
    err(http.put(f'/v1/raid-rooms/{rid}/settings',json=body,headers={**b['headers'],'Idempotency-Key':str(uuid.uuid4())}),403,'ROOM_LEADER_REQUIRED')
    out=http.put(f'/v1/raid-rooms/{rid}/settings',json=body,headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())})
    assert out.status_code==200,out.text
    with session() as db:
        assert len(list(db.scalars(select(Assignment).where(Assignment.room_id==uuid.UUID(rid),Assignment.state=='active'))))==2


def test_formation_swap_is_atomic_and_does_not_change_weekly_ownership(ready,http):
    target,a,b,_=ready;rid,_=create(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    p=plan(http,a,rid)
    with session() as db:
        rows=list(db.scalars(select(Assignment).where(Assignment.room_id==uuid.UUID(rid)).order_by(Assignment.slot_no)))
        placements=[dict(membership_id=str(r.membership_id),expected_revision=1,item_id=str(r.item_id),party_no=1,slot_no=rows[1-i].slot_no) for i,r in enumerate(rows)]
    out=http.put(f'/v1/raid-rooms/{rid}/formation',json=dict(expected_cycle_key=p['cycle_key'],expected_members_revision=p['members_revision'],expected_plan_revision=p['revision'],placements=placements),headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())})
    assert out.status_code==200,out.text
    with session() as db:
        for pos in placements:
            row=db.scalar(select(Assignment).where(Assignment.membership_id==uuid.UUID(pos['membership_id']),Assignment.state=='active'))
            assert row.slot_no==pos['slot_no']


def test_character_change_replaces_exact_weekly_link_and_preserves_completed_history(ready,http):
    target,a,b,_=ready;rid,_=create(http,a);p=plan(http,a,rid)
    response=http.get(f'/v1/raid-rooms/{rid}/admission-context',params=dict(character_id=a['ids'][1],selected_role='dealer',intent='change_character'),headers=a['headers'])
    assert response.status_code==200,response.text
    c=response.json();data=dict(expected_cycle_key=c['expected_cycle_key'],expected_room_revision=c['room_revision'],expected_members_revision=c['members_revision'],expected_plan_revision=c['plan_revision'],expected_policy_snapshot=c['policy_snapshot'],expected_catalog_version=c['catalog_version'],selection=c['selection'],selection_context=dict(context_token=c['context_token']),target_items=c['targets'],target_session_ids=[],expected_membership_revision=p['my_membership']['revision'],assignments=[dict(assignment_id=v['assignment_id'],expected_revision=v['revision']) for v in p['my_assignments']],choices=[])
    response=post(http,a,f'raid-rooms/{rid}/character-changes',data)
    assert response.status_code==200,response.text
    from app.raid_rooms.weekly_links import WeeklyOccupancy
    with session() as db:
        arow=db.scalar(select(Assignment).where(Assignment.room_id==uuid.UUID(rid)))
        assert str(arow.character_id)==a['ids'][1] and arow.state=='active'
        links=list(db.scalars(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid))))
        assert len(links)==1 and links[0].character_id==arow.character_id and links[0].assignment_id==arow.id
