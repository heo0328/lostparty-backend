import uuid,json
from datetime import timedelta
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import session
from app.core.errors import register
from app.raid_rooms.admission_router import router as admissions
from app.raid_rooms.schedule_router import router as schedules
from app.raid_rooms.continuation_router import router as continuation
from app.raid_rooms.completion_router import router
from app.raid_rooms import admission_service
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentMembership as Member,RecruitmentRound as Round
from app.raid_rooms.source_models import TimeReservation as Reservation,ContinuationChoice as Choice
from app.raid_rooms.weekly_links import WeeklyOccupancy
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,creation,create_body,post,create,admission
from tests.test_recruitment_scheduling import plan,future,group_at
from tests.test_raid_room_http import err
from tests.test_raid_room_migrations import table_digests


@pytest.fixture
def http():
    from app.main import no_store
    app=FastAPI()
    for r in (admissions,schedules,continuation,router):app.include_router(r)
    register(app);app.middleware('http')(no_store)
    async def sql_error(request,error):raise error
    app.add_exception_handler(SQLAlchemyError,sql_error)
    with TestClient(app) as client:yield client


def bundle(http,w):
    items=[dict(raid_id='horizon_cathedral',difficulty_id='stage1'),dict(raid_id='kazeros_act4',difficulty_id='normal')]
    response=http.get('/v1/me/raid-room-creation-context',params=dict(character_id=w['ids'][0],selected_role='dealer',items=json.dumps(items)),headers=w['headers'])
    assert response.status_code==200,response.text
    group=group_at(future());group['alternatives'][0]['item_order']=[i['raid_id'] for i in items]
    body=create_body(response.json(),app_mode='mixed_bundle',continuation=dict(enabled=True,auto_open_enabled=False),schedule_groups=[group])
    response=post(http,w,'raid-rooms',body);assert response.status_code==201,response.text
    return next(r['id'] for r in response.json()['revisions'] if r['resource']=='room')


def context(http,w,rid,command,round_id=None):
    query=dict(command=command)
    if round_id:query['round_id']=round_id
    response=http.get(f'/v1/raid-rooms/{rid}/command-context',params=query,headers=w['headers'])
    assert response.status_code==200,response.text
    return response.json()


def test_personal_partial_then_keep_preserves_other_item_times_and_future_intent(ready,http):
    target,a,b,_=ready;rid=bundle(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    p=plan(http,a,rid);first,second=[i['round_id'] for i in p['game_items']]
    before={s['segment_id']:(s['starts_at'],s['ends_at']) for s in p['session_segments'][0]['segments'] if s['round_id']==second}
    c=context(http,a,rid,'personal_completion',first)
    body=dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token'],continuation_resolution=None,leadership_resolution=None)
    out=post(http,a,f'raid-rounds/{first}/personal-completion',body);assert out.status_code==200,out.text
    after=plan(http,a,rid)
    assert {s['segment_id']:(s['starts_at'],s['ends_at']) for s in after['session_segments'][0]['segments'] if s['round_id']==second}==before
    own=next(v for v in after['my_assignments'] if v['round_id']==first)
    assert own['state']=='completed' and own['completion_source']=='manual' and own['completed_at']
    c=context(http,a,rid,'personal_completion',second)
    body=dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token'],continuation_resolution=dict(action='keep',expected_choices_revision=c['continuation']['choices_revision']),leadership_resolution=None)
    key=uuid.uuid4();out=post(http,a,f'raid-rounds/{second}/personal-completion',body,key);assert out.status_code==200,out.text
    assert post(http,a,f'raid-rounds/{second}/personal-completion',body,key).json()==out.json()
    with session() as db:
        assert db.scalar(select(Member.ended_at).where(Member.room_id==uuid.UUID(rid),Member.user_id==a['uid'])) is None
        assert db.scalar(select(func.count()).select_from(Choice).where(Choice.user_id==a['uid'],Choice.ended_at.is_(None)))==2
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==2


def test_nonleader_weekly_closure_is_room_wide_and_preserves_completed_history(ready,http):
    target,a,b,_=ready;rid=bundle(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    c=context(http,b,rid,'close_weekly');assert c['permission']['allowed']
    assert 'weekly_revision' not in json.dumps(c) and str(a['uid']) not in json.dumps(c)
    out=post(http,b,f'raid-rooms/{rid}/weekly-incomplete-closures',dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token']))
    assert out.status_code==200,out.text
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==0
        assert {r.state for r in db.scalars(select(Round).where(Round.room_id==uuid.UUID(rid)))}=={'stopped_incomplete'}
        assert all(m.ended_at is None for m in db.scalars(select(Member).where(Member.room_id==uuid.UUID(rid))))


def test_aead_tamper_and_stale_set_do_not_change_any_source(ready,http):
    target,a,b,_=ready;rid=bundle(http,a);round_id=plan(http,a,rid)['game_items'][0]['round_id']
    c=context(http,a,rid,'complete_item',round_id)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    before=table_digests(target,{'recruitment_assignments','raid_weekly_states','recruitment_reservations'})
    body=dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token'])
    err(post(http,a,f'raid-rounds/{round_id}/completion',body),409,'COMMAND_CONTEXT_STALE')
    body['context_token']=body['context_token'][:50]+('a' if body['context_token'][50]!='a' else 'b')+body['context_token'][51:]
    err(post(http,a,f'raid-rounds/{round_id}/completion',body),400,'CONTEXT_INVALID')
    assert table_digests(target,set(before))==before


def test_minimal_ack_replays_after_personal_completion_ended_membership_and_expiry(ready,http,monkeypatch):
    target,a,b,_=ready;rid,_=create(http,a);round_id=plan(http,a,rid)['game_items'][0]['round_id']
    c=context(http,a,rid,'personal_completion',round_id)
    body=dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token'],continuation_resolution=None,
        leadership_resolution=dict(action='end',target_membership_id=None,expected_target_revision=None))
    key=uuid.uuid4();out=post(http,a,f'raid-rounds/{round_id}/personal-completion',body,key)
    assert out.status_code==200,out.text
    original=admission_service.now
    monkeypatch.setattr(admission_service,'now',lambda db:original(db)+timedelta(minutes=3))
    assert post(http,a,f'raid-rounds/{round_id}/personal-completion',body,key).json()==out.json()
    err(post(http,a,f'raid-rounds/{round_id}/personal-completion',body),409,'COMMAND_CONTEXT_EXPIRED')


def test_weekly_resume_needs_explicit_n1_vote_and_keeps_stopped_generation(ready,http):
    target,a,b,_=ready;rid=bundle(http,a)
    p=plan(http,a,rid);old_rounds={v['round_id'] for v in p['game_items']}
    c=context(http,a,rid,'close_weekly')
    out=post(http,a,f'raid-rooms/{rid}/weekly-incomplete-closures',dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token']))
    assert out.status_code==200,out.text
    p=plan(http,a,rid)
    from app.raid_rooms.integrated_models import RecruitmentRoom
    with session() as db:room_revision=db.get(RecruitmentRoom,uuid.UUID(rid)).revision
    body=dict(expected_cycle_key=p['cycle_key'],expected_room_revision=room_revision,expected_members_revision=p['members_revision'],expected_plan_revision=p['revision'],expected_membership_revision=p['my_membership']['revision'])
    out=post(http,a,f'raid-rooms/{rid}/weekly-resume-proposals',dict(body,schedule_groups=None))
    assert out.status_code==200,out.text
    pid=next(r['id'] for r in out.json()['revisions'] if r['resource']=='proposal')
    with session() as db:
        assert all(db.get(Round,uuid.UUID(r)).state=='stopped_incomplete' for r in old_rounds)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==0
    out=post(http,a,f'raid-schedule-proposals/{pid}/responses',dict(expected_cycle_key=p['cycle_key'],expected_proposal_revision=1,expected_proposal_plan_revision=1,expected_membership_revision=p['my_membership']['revision'],response='accept'))
    assert out.status_code==200,out.text
    restored=plan(http,a,rid)
    assert restored['schedule_state']=='confirmed' and len(restored['game_items'])==2
    with session() as db:
        assert all(db.get(Round,uuid.UUID(r)).state=='stopped_incomplete' for r in old_rounds)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==2


def test_nonleader_cannot_end_room_and_completed_segment_survives_remaining_proposal(ready,http):
    from app.raid_rooms.integrated_models import RecruitmentRoom
    target,a,b,_=ready;rid=bundle(http,a)
    assert post(http,b,f'raid-rooms/{rid}/join',admission(http,b,rid)).status_code==200
    p=plan(http,b,rid)
    with session() as db:room_revision=db.get(RecruitmentRoom,uuid.UUID(rid)).revision
    body=dict(expected_cycle_key=p['cycle_key'],expected_room_revision=room_revision,expected_members_revision=p['members_revision'],expected_plan_revision=p['revision'],expected_membership_revision=p['my_membership']['revision'])
    err(post(http,b,f'raid-rooms/{rid}/end',body),403,'ROOM_LEADER_REQUIRED')
    p=plan(http,a,rid);finished=p['game_items'][0]['round_id'];c=context(http,a,rid,'complete_item',finished)
    out=post(http,a,f'raid-rounds/{finished}/completion',dict(expected_cycle_key=c['cycle_key'],context_token=c['context_token']))
    assert out.status_code==200,out.text
    p=plan(http,a,rid);s=p['sessions'][0]
    old=next(seg for seg in p['session_segments'][0]['segments'] if seg['round_id']==finished)
    out=post(http,a,f'raid-rooms/{rid}/schedule-proposals',dict(expected_cycle_key=p['cycle_key'],expected_plan_revision=p['revision'],expected_members_revision=p['members_revision'],targets=[dict(session_id=s['session_id'],expected_schedule_revision=s['schedule_revision'],starts_at=s['starts_at'],item_durations=[dict(item_id=i['item_id'],duration_minutes=None) for i in p['game_items'] if i['round_id']!=finished])]))
    assert out.status_code==200,out.text
    p=plan(http,b,rid);prop=p['proposals'][-1]
    out=post(http,b,f"raid-schedule-proposals/{prop['proposal_id']}/responses",dict(expected_cycle_key=p['cycle_key'],expected_proposal_revision=prop['revision'],expected_proposal_plan_revision=prop['proposal_plan_revision'],expected_membership_revision=p['my_membership']['revision'],response='accept'))
    assert out.status_code==200,out.text
    after=plan(http,a,rid)
    assert next(seg for seg in after['session_segments'][0]['segments'] if seg['round_id']==finished)==old


def test_command_context_has_bounded_opaque_payload_and_exact_lifetime(ready,http):
    from app.raid_rooms.command_context import unseal,LIFETIME_SECONDS,MAX_TOKEN_BYTES
    from datetime import datetime
    target,a,b,_=ready;rid=bundle(http,a)
    c=context(http,a,rid,'close_weekly');token=c['context_token'];payload=unseal(token)
    assert len(token.encode('ascii'))<=MAX_TOKEN_BYTES
    assert str(a['uid']) not in token and 'assignment' not in token
    assert set(payload)=={'actor','room','command','round','cycle','expires_at','digest'}
    assert 0<(datetime.fromisoformat(c['expires_at'].replace('Z','+00:00'))-datetime.fromisoformat(c['issued_at'].replace('Z','+00:00'))).total_seconds()<=LIFETIME_SECONDS
    print('command-context measured token bytes:',len(token),'private source size represented by SHA-256 digest')
