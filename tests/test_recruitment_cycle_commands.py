"""Target admission lifecycle and isolation against real PostgreSQL."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_commands as commands, cycle_creation as creation, cycle_wire as wire, cycles
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raids import service as raids
from tests.test_recruitment_cycle_creation import candidate, ready, sources, imported, people, worlds, preflight, request, denied
from tests.test_group_foundation import actor


def create_room(a, *, mode='direct_join', combined=True, bundle=False):
    return creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,continuation=combined,bundle=bundle),
        admission_mode=mode))[1]['data']


def context(w,rid,key,intent='join',role='dealer'):
    return commands.get_context(actor(w['uid']),rid,key,uuid.UUID(w['ids'][0]),role,intent)


def admission_request(ctx,**updates):
    c=ctx['data']
    data=dict(expected_cycle_key=c['expected_cycle_key'],expected_room_revision=c['room_revision'],
        expected_members_revision=c['members_revision'],expected_plan_revision=c['plan_revision'],
        expected_policy_snapshot=c['policy_snapshot'],expected_catalog_version=c['catalog_version'],
        selection_context=dict(context_token=c['context_token']),selection=c['selection'],target_items=c['targets'],
        target_session_ids=[],target_cycle_key=c['target_cycle_key'],expected_target_revision=c['expected_target_revision'])
    return wire.InputContract3PostV2RaidRoomsRoomIdJoin.model_validate(data|updates)


def decision(app,ctx):
    c=ctx['data']
    return wire.InputContract3PostV2RaidRoomApplicationsApplicationIdApprove.model_validate(dict(
        expected_cycle_key=c['expected_cycle_key'],expected_application_revision=app['revision'],
        expected_room_revision=c['room_revision'],expected_members_revision=c['members_revision'],
        expected_plan_revision=c['plan_revision'],target_cycle_key=c['target_cycle_key'],
        expected_target_revision=c['expected_target_revision'],
        expected_leadership_revision=c['leadership']['leadership_revision']))


def test_join_is_target_only_and_does_not_consume_second_room_unit(candidate):
    _,a,b=candidate
    room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id'])
    c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    next_ctx=context(b,rid,n)
    current_ctx=context(b,rid,c)
    data=admission_request(current_ctx);command=uuid.uuid4()
    result=commands.admit(actor(b['uid']),rid,command,data)
    assert commands.admit(actor(b['uid']),rid,command,data)==result
    with session() as db,db.begin():
        rows={r.cycle_key.isoformat():r for r in db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid))}
        assert rows[c].revision==2 and rows[n].revision==1
        assert admission_count(db,rows[c])==2 and admission_count(db,rows[n])==1
        assert db.get(Room,rid).revision==1
    # New persistent membership changes the actor's usage CAS; fetch fresh N context.
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,n)))
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(Member).where(Member.room_id==rid,Member.user_id==b['uid']))==1
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid,WeeklyOccupancy.user_id==b['uid']))==4


def admission_count(db,row):
    return commands.admission.member_count(db,row)


def test_pending_c_and_n_independent_approve_n_only(candidate):
    _,a,b=candidate
    room=create_room(a,mode='leader_only');rid=uuid.UUID(room['room_id'])
    c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    apps=[]
    for key in (c,n):
        ctx=context(b,rid,key,'apply')
        apps.append(commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)[1]['data'])
        assert context(b,rid,key,'apply')['data']['permissions']['apply']['reason']=='ROOM_APPLICATION_EXISTS'
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==0
        saved=db.get(CycleApplication,uuid.UUID(apps[1]['application_id']))
        assert saved.expires_at==raids.cycle(now(db)).ends_at+timedelta(days=7)
    leadctx=context(a,rid,n,'apply')
    result=commands.process(actor(a['uid']),uuid.UUID(apps[1]['application_id']),uuid.uuid4(),decision(apps[1],leadctx))
    assert result[0]==200
    with session() as db,db.begin():
        assert db.get(CycleApplication,uuid.UUID(apps[0]['application_id'])).state=='pending'
        assert db.get(CycleApplication,uuid.UUID(apps[1]['application_id'])).state=='accepted'
        assert set(db.scalars(select(WeeklyOccupancy.cycle_key).where(WeeklyOccupancy.user_id==b['uid'])))=={raids.cycle(now(db)).starts_at.astimezone(raids.KST).date()+timedelta(days=7)}


@pytest.mark.parametrize('action',['reject','withdraw'])
def test_application_finish_has_no_occupancy_or_participant_side_effect(candidate,action):
    _,a,b=candidate
    room=create_room(a,mode='leader_only');rid=uuid.UUID(room['room_id']);key=room['created_cycles'][0]['target_cycle_key']
    ctx=context(b,rid,key,'apply')
    app=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)[1]['data']
    if action=='reject':data=decision(app,context(a,rid,key,'apply'));who=a
    else:
        who=b
        data=wire.InputContract3PostV2RaidRoomApplicationsApplicationIdWithdraw.model_validate(dict(
            expected_application_revision=1,target_cycle_key=key,expected_cycle_key=ctx['data']['expected_cycle_key'],
            expected_target_revision=ctx['data']['expected_target_revision']))
    command=uuid.uuid4();aid=uuid.UUID(app['application_id'])
    result=commands.process(actor(who['uid']),aid,command,data,action=action)
    assert result==commands.process(actor(who['uid']),aid,command,data,action=action)
    assert result[1]['data']['state']==('rejected' if action=='reject' else 'withdrawn')
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.user_id==b['uid']))==0
        assert db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id'])).revision==1


def test_cross_target_round_or_context_cannot_join(candidate):
    _,a,b=candidate
    room=create_room(a);rid=uuid.UUID(room['room_id']);c,n=[v['target_cycle_key'] for v in room['created_cycles']]
    cc,nc=context(b,rid,c),context(b,rid,n)
    denied('CONTEXT_INVALID',commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(nc,
        selection_context=dict(context_token=cc['data']['context_token'])))
    denied('REVISION_CONFLICT',commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(nc,
        target_items=cc['data']['targets']))


def test_application_privacy_and_leadership_cas(candidate):
    _,a,b=candidate
    room=create_room(a,mode='leader_only');rid=uuid.UUID(room['room_id']);key=room['created_cycles'][0]['target_cycle_key']
    app=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,key,'apply')),applying=True)[1]['data']
    aid=uuid.UUID(app['application_id']);data=decision(app,context(a,rid,key,'apply'))
    assert commands.application(actor(b['uid']),aid)['data']['target_generation']==1
    denied('ROOM_LEADER_REQUIRED',commands.process,actor(b['uid']),aid,uuid.uuid4(),data)
    with session() as db,db.begin():
        db.get(CycleGeneration,(uuid.UUID(room['created_cycles'][0]['room_cycle_id']),1)).leadership_revision+=1
    denied('LEADERSHIP_CHANGED',commands.process,actor(a['uid']),aid,uuid.uuid4(),data)


def test_concurrent_last_slot_has_one_winner(candidate,people):
    _,a,b=candidate
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);key=room['created_cycles'][0]['target_cycle_key']
    third=people('w2-last-third')
    for w in (b,third):commands.admit(actor(w['uid']),rid,uuid.uuid4(),admission_request(context(w,rid,key)))
    contenders=[people('w2-support-one'),people('w2-support-two')]
    requests=[admission_request(context(w,rid,key,role='support')) for w in contenders]
    def join(pair):
        w,data=pair
        try:return commands.admit(actor(w['uid']),rid,uuid.uuid4(),data)[0]
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(join,zip(contenders,requests)))
    assert sorted(map(str,results))==['200','TARGET_CONTEXT_STALE']
    with session() as db,db.begin():
        target=db.get(RoomCycle,uuid.UUID(room['created_cycles'][0]['room_cycle_id']))
        assert admission_count(db,target)==4


def test_public_origin_application_survives_later_group_scope(candidate):
    from tests.test_group_foundation import create as group_create
    _,a,b=candidate
    room=create_room(a,mode='leader_only',combined=False);rid=uuid.UUID(room['room_id']);key=room['created_cycles'][0]['target_cycle_key']
    app=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,key,'apply')),applying=True)[1]['data']
    gid=uuid.UUID(group_create(a)[1]['group']['group_id'])
    with session() as db,db.begin():
        row=db.get(Room,rid);row.scope='group';row.group_id=gid;row.revision+=1
    command=decision(app,context(a,rid,key,'apply'))
    result=commands.process(actor(a['uid']),uuid.UUID(app['application_id']),uuid.uuid4(),command)
    assert result[0]==200
    assert commands.application(actor(b['uid']),uuid.UUID(app['application_id']))['data']['admission_origin']['scope']=='public'
