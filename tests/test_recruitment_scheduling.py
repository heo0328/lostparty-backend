import uuid
from datetime import timedelta,datetime,timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import session,now
from app.core.errors import register
from app.raid_rooms import time_policy as policy
from app.raid_rooms.admission_router import router as admissions
from app.raid_rooms.schedule_router import router
from app.raid_rooms.availability_router import router as availability
from app.raid_rooms.source_models import TimeReservation as Reservation,SessionParticipation as Participation
from app.raid_rooms.integrated_models import RecruitmentSession as Session
from app.raids.service import KST,cycle
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,creation,create_body,post,create,admission


@pytest.fixture
def http():
    from app.main import no_store
    app=FastAPI();app.include_router(admissions);app.include_router(router);app.include_router(availability)
    register(app);app.middleware('http')(no_store)
    async def sql_error(request,error):raise error
    app.add_exception_handler(SQLAlchemyError,sql_error)
    with TestClient(app) as client:yield client


def plan(http,w,rid):
    response=http.get(f'/v1/me/raid-rooms/{rid}/plan',headers=w['headers'])
    assert response.status_code==200,response.text
    return response.json()


def group_at(start,*,mode='manual',scope='selected_weekdays',additional=None):
    local=start.astimezone(KST)
    return dict(client_group_key='primary',existing_group_id=None,expected_group_revision=None,occurrence_mode='one_of',planning_mode=mode,
        required=True,auto_confirm_additional_members=additional,day_scope=scope,alternatives=[] if scope=='any_current_cycle' else [dict(
        client_alternative_key='day',existing_session_id=None,expected_session_revision=None,weekday=local.isoweekday(),
        starts_local=local.strftime('%H:%M') if mode=='manual' else None,leader_latest_start_local=None,item_order=['horizon_cathedral'])])


def future():
    with session() as db:stamp=now(db)
    result=policy.ceil_tick(stamp+timedelta(hours=1))
    if result+timedelta(hours=1)>cycle(stamp).ends_at:pytest.skip('Current-cycle boundary fixture')
    return result


def manual(http,w):
    start=future();rid,_=create(http,w,schedule_groups=[group_at(start)])
    return rid,start


def proposal(http,w,rid,start):
    p=plan(http,w,rid);s=p['sessions'][0]
    out=post(http,w,f'raid-rooms/{rid}/schedule-proposals',dict(expected_cycle_key=p['cycle_key'],expected_plan_revision=p['revision'],
        expected_members_revision=p['members_revision'],targets=[dict(session_id=s['session_id'],expected_schedule_revision=s['schedule_revision'],
        starts_at=start.isoformat(),item_durations=[dict(item_id=i['item_id'],duration_minutes=None) for i in p['game_items']])]))
    assert out.status_code==200,out.text
    return plan(http,w,rid)['proposals'][-1]


def respond(http,w,rid,prop):
    p=plan(http,w,rid)
    return post(http,w,f"raid-schedule-proposals/{prop['proposal_id']}/responses",dict(expected_cycle_key=p['cycle_key'],
        expected_proposal_revision=prop['revision'],expected_proposal_plan_revision=prop['proposal_plan_revision'],
        expected_membership_revision=p['my_membership']['revision'],response='accept'))


@pytest.mark.parametrize('count,required',[(1,1),(2,2),(3,2),(4,2),(5,3),(6,3),(7,4),(8,4)])
def test_quorum(count,required):assert policy.quorum(count)==required


def test_interval_cycle_maintenance_and_weekly_coverage():
    from app.game_accounts.support import GameError
    start=datetime(2026,10,21,0,tzinfo=timezone.utc) # KST09 maintenance
    with pytest.raises(GameError) as error:policy.interval(start,start+timedelta(minutes=10),'2026-10-21')
    assert error.value.code=='MAINTENANCE_WINDOW'
    assert policy.covered(datetime(2026,10,25,14,tzinfo=timezone.utc),datetime(2026,10,25,16,tzinfo=timezone.utc),
        [dict(start_minute=10020,end_minute=10080),dict(start_minute=0,end_minute=60)])


def test_manual_creation_join_reservations_and_n1_explicit_response(ready,http):
    target,a,b,_=ready;rid,start=manual(http,a)
    p=plan(http,a,rid)
    assert p['schedule_state']=='confirmed' and len(p['my_participations'])==1
    with session() as db:assert db.scalar(select(func.count()).select_from(Reservation).where(Reservation.released_at.is_(None)))==1
    prop=proposal(http,a,rid,start+timedelta(minutes=10))
    assert prop['my_response']['response']=='pending' and plan(http,a,rid)['sessions'][0]['schedule_revision']==1
    out=respond(http,a,rid,prop);assert out.status_code==200,out.text
    assert out.json()['outcome']=='applied'
    data=admission(http,b,rid);out=post(http,b,f'raid-rooms/{rid}/join',data)
    assert out.status_code==200,out.text
    assert plan(http,b,rid)['my_participations'][0]['reservation_state']=='active'


def test_newcomer_changes_n1_quorum_and_nonacceptor_needs_confirmation(ready,http):
    target,a,b,_=ready;rid,start=manual(http,a);prop=proposal(http,a,rid,start+timedelta(minutes=20))
    out=post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid));assert out.status_code==200,out.text
    out=respond(http,a,rid,prop);assert out.status_code==200 and out.json()['outcome']=='recorded',out.text
    out=respond(http,b,rid,prop);assert out.status_code==200 and out.json()['outcome']=='applied',out.text
    assert plan(http,b,rid)['my_participations'][0]['confirmed_schedule_revision']==2


def test_automatic_all_week_waits_for_explicit_submissions(ready,http):
    target,a,b,_=ready;rid,_=create(http,a,schedule_groups=[group_at(future(),mode='coordinated',scope='any_current_cycle',additional=1)])
    p=plan(http,a,rid);assert p['sessions']==[] and p['schedule_groups'][0]['alternatives']==[]
    out=post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid));assert out.status_code==200,out.text
    for w in (a,b):
        data=dict(expected_version=1,timezone='Asia/Seoul',intervals=[dict(weekday=d,start='00:00',end='00:00',end_day_offset=1) for d in range(1,8)])
        out=http.put('/v1/me/play-availability',json=data,headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())});assert out.status_code==200,out.text
        out=http.put(f'/v1/me/raid-rooms/{rid}/availability-submission',json=dict(expected_personal_version=2,expected_submission_revision=1,expected_membership_revision=1),
            headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())});assert out.status_code==200,out.text
    p=plan(http,a,rid);assert p['schedule_state']=='confirmed' and len(p['sessions'])==1
    assert p['schedule_groups'][0]['alternatives']==[]


def test_exact_admission_deadline_rejects_new_member_but_existing_confirmation_allowed(ready,http,monkeypatch):
    from app.raid_rooms import admission_service,schedule_service
    from tests.test_raid_room_http import err
    target,a,b,_=ready;rid,start=manual(http,a);data=admission(http,b,rid)
    monkeypatch.setattr(admission_service,'now',lambda db:start-timedelta(minutes=30))
    err(post(http,b,f'raid-rooms/{rid}/join',data),409,'RECRUITMENT_CLOSED')
    p=plan(http,a,rid);s=p['sessions'][0];own=p['my_participations'][0]
    monkeypatch.setattr(schedule_service,'now',lambda db:start-timedelta(minutes=20))
    out=post(http,a,f"raid-sessions/{s['session_id']}/participation-confirmations",dict(expected_cycle_key=p['cycle_key'],expected_schedule_revision=s['schedule_revision'],expected_membership_revision=p['my_membership']['revision'],expected_participation_revision=own['revision']))
    assert out.status_code==200,out.text


def test_each_initial_evaluation_never_recreates_already_confirmed_occurrences(ready,http):
    from app.raid_rooms import scheduling
    target,a,b,_=ready;group=group_at(future(),mode='coordinated',additional=1)
    group['occurrence_mode']='each'
    rid,_=create(http,a,schedule_groups=[group])
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    raw=[dict(weekday=n,start='00:00',end='00:00',end_day_offset=1) for n in range(1,8)]
    for w in (a,b):
        out=http.put('/v1/me/play-availability',json=dict(expected_version=1,timezone='Asia/Seoul',intervals=raw),headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())});assert out.status_code==200,out.text
        out=http.put(f'/v1/me/raid-rooms/{rid}/availability-submission',json=dict(expected_personal_version=2,expected_submission_revision=1,expected_membership_revision=1),headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())});assert out.status_code==200,out.text
    before=plan(http,a,rid);ids={s['session_id'] for s in before['sessions']};assert len(ids)==1
    from app.raid_rooms.integrated_models import RecruitmentRoom
    with session() as db,db.begin():scheduling.evaluate_initial(db,db.get(RecruitmentRoom,uuid.UUID(rid)),now(db))
    after=plan(http,a,rid)
    assert {s['session_id'] for s in after['sessions']}==ids and after['revision']==before['revision']
