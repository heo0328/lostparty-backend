"""Confirmed composition checks for pending applications; disposable DB only."""
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import select, inspect, func

from app.core.database import session, now
from app.game_accounts.models import Character
from app.raid_rooms import cycle_commands as commands, cycle_creation as creation, cycle_wire as wire
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment, RecruitmentMembership as Member
from app.raid_rooms.source_models import TimeReservation
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from tests.test_recruitment_cycle_creation import candidate, ready, sources, imported, people, worlds, preflight, request, denied
from tests.test_recruitment_cycle_commands import create_room, context, admission_request, decision
from tests.test_group_foundation import actor
from tests.test_raid_room_migrations import table_digests


@pytest.fixture
def current(candidate):
    engine,a,b=candidate
    p=subprocess.run(['alembic','upgrade','0031_membership_actions'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert p.returncode==0,p.stderr.decode()[-1500:]
    return engine,a,b


def room(a, *, eight=False, bundle=False):
    c=preflight(a,continuation=True,bundle=bundle)
    if eight:
        raid=next(r for r in raids.catalog().raids if r.party_size==8)
        items=[wire.BCreateTarget(raid_id=raid.raid_id,difficulty_id=raid.difficulties[0].difficulty_id,expected_weekly_revision=1)]
        c=creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',items,None,c['data']['target_cycle_key'],True)
    ack=creation.create(actor(a['uid']),uuid.uuid4(),request(c,admission_mode='leader_only'))[1]['data']
    return uuid.UUID(ack['room_id']),*[r['target_cycle_key'] for r in ack['created_cycles']]


def change_class(w,name):
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(w['ids'][0]));c.summary={**c.summary,'class_name':name}


def leader_class(a):
    with session() as db:return db.get(Character,uuid.UUID(a['ids'][0])).summary['class_name']


def apply(w,rid,key,role='dealer',command=None):
    ctx=context(w,rid,key,'apply',role)
    return commands.admit(actor(w['uid']),rid,command or uuid.uuid4(),admission_request(ctx),applying=True)


def approve(a,app,rid,key):
    return commands.process(actor(a['uid']),uuid.UUID(app['application_id']),uuid.uuid4(),decision(app,context(a,rid,key,'apply')))


def occupancy():
    with session() as db:
        return tuple(db.scalar(select(func.count()).select_from(t)) for t in (Assignment,Member,WeeklyState,WeeklyOccupancy,TimeReservation))


def test_duplicate_context_and_forged_post_both_reject_readonly(current):
    engine,a,b=current;rid,c,n=room(a);change_class(b,leader_class(a))
    tables=set(inspect(engine).get_table_names());before=table_digests(engine,tables)
    ctx=context(b,rid,c,'apply');assert ctx['data']['permissions']['apply']==dict(allowed=False,reason='ROOM_COMPOSITION_CONFLICT',next_change_at=None)
    assert table_digests(engine,tables)==before
    denied('ROOM_COMPOSITION_CONFLICT',commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)
    with session() as db:assert db.scalar(select(func.count()).select_from(CycleApplication).where(CycleApplication.room_id==rid))==0
    # Other role remains valid: class identity is not a new blanket ban.
    assert context(b,rid,c,'apply','support')['data']['permissions']['apply']['allowed']


def test_pending_does_not_reserve_or_block_same_class_and_ack_survives(current,people):
    _,a,b=current;rid,c,n=room(a);other=people('same-pending-class');change_class(other,leader_class(b))
    before=occupancy();command=uuid.uuid4();ctx=context(b,rid,c,'apply');body=admission_request(ctx)
    original=commands.admit(actor(b['uid']),rid,command,body,applying=True)
    second=apply(other,rid,c)
    assert second[0]==201 and occupancy()==before
    # Approval changes confirmed composition; the first successful ACK remains original.
    approve(a,second[1]['data'],rid,c)
    assert commands.admit(actor(b['uid']),rid,command,body,applying=True)==original
    with session() as db:assert db.get(CycleApplication,uuid.UUID(original[1]['data']['application_id'])).state=='pending'


def test_context_then_composition_change_blocks_post(current,people):
    _,a,b=current;rid,c,n=room(a);saved=admission_request(context(b,rid,c,'apply'))
    other=people('composition-between-context-post');change_class(other,leader_class(b))
    approve(a,apply(other,rid,c)[1]['data'],rid,c)
    denied('TARGET_CONTEXT_STALE',commands.admit,actor(b['uid']),rid,uuid.uuid4(),saved,applying=True)
    assert context(b,rid,c,'apply')['data']['permissions']['apply']['reason']=='ROOM_COMPOSITION_CONFLICT'


def test_approval_rechecks_composition_and_preserves_pending(current,people):
    _,a,b=current;rid,c,n=room(a);first=apply(b,rid,c)[1]['data']
    other=people('approval-same-class');change_class(other,leader_class(b));second=apply(other,rid,c)[1]['data']
    approve(a,second,rid,c);before=occupancy()
    denied('ROOM_COMPOSITION_CONFLICT',approve,a,first,rid,c)
    assert occupancy()==before
    with session() as db:assert db.get(CycleApplication,uuid.UUID(first['application_id'])).state=='pending'


@pytest.mark.parametrize('role,reason',[('support','ROOM_COMPOSITION_CONFLICT'),('dealer','ROOM_COMPOSITION_CONFLICT'),('full','ROOM_FULL')])
def test_pending_role_and_full_capacity(current,people,role,reason):
    _,a,b=current;rid,c,n=room(a)
    roles={'support':['support'],'dealer':['dealer','dealer'],'full':['dealer','dealer','support']}[role]
    for i,r in enumerate(roles):
        w=people('composition-fill-'+str(i));approve(a,apply(w,rid,c,r)[1]['data'],rid,c)
    checkrole='dealer' if role=='full' else role
    ctx=context(b,rid,c,'apply',checkrole);assert ctx['data']['permissions']['apply']['reason']==reason
    denied(reason,commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)
    assert context(b,rid,n,'apply',checkrole)['data']['permissions']['apply']['allowed']


def test_eight_opposite_party_and_c_n_isolation(current):
    _,a,b=current;rid,c,n=room(a,eight=True);change_class(b,leader_class(a))
    ctx=context(b,rid,c,'apply');assert ctx['data']['permissions']['apply']['allowed']
    assert {t['party_no'] for t in ctx['data']['targets']}=={2}
    app=commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)[1]['data'];approve(a,app,rid,c)
    with session() as db:
        assert set(db.scalars(select(Assignment.party_no).where(Assignment.room_id==rid,Assignment.user_id==b['uid'])))=={2}
        assert set(db.scalars(select(WeeklyOccupancy.cycle_key).where(WeeklyOccupancy.room_id==rid,WeeklyOccupancy.user_id==b['uid'])))=={date.fromisoformat(c)}


@pytest.mark.parametrize('kind',['level','manual','party','other_room'])
def test_bundle_existing_level_and_weekly_guards(current,kind):
    _,a,b=current
    if kind=='other_room':
        first=create_room(b,combined=False);other_id=uuid.UUID(first['room_id'])
    rid,c,n=room(a,bundle=True)
    with session() as db,db.begin():
        cid=uuid.UUID(b['ids'][0]);target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        item,rd=commands.admission.rounds(db,target)[-1]
        if kind=='level':
            char=db.get(Character,cid);char.summary={**char.summary,'item_level':'1.00'}
        elif kind in ('manual','party'):
            values=dict(user_id=b['uid'],character_id=cid,raid_id=item.raid_id,cycle_key=date.fromisoformat(c),revision=1,updated_at=now(db))
            if kind=='manual':values.update(manual_completed_at=now(db),manual_difficulty_id=rd.difficulty_id)
            else:values.update(party_completed_at=now(db),completed_party_id=uuid.uuid4(),party_difficulty_id=rd.difficulty_id)
            db.add(WeeklyState(**values))
    expected={'level':'RAID_ITEM_LEVEL_REQUIRED','manual':'WEEKLY_ALREADY_COMPLETED','party':'WEEKLY_ALREADY_COMPLETED','other_room':'WEEKLY_ALREADY_PARTICIPATING'}[kind]
    ctx=context(b,rid,c,'apply');assert ctx['data']['permissions']['apply']['reason']==expected
    denied(expected,commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)
    if kind!='level':assert context(b,rid,n,'apply')['data']['permissions']['apply']['allowed']


def test_concurrent_approval_last_slot_one_winner(current,people):
    _,a,b=current;rid,c,n=room(a)
    for i in range(2):
        w=people('approval-fill-'+str(i));approve(a,apply(w,rid,c)[1]['data'],rid,c)
    other=people('approval-contender');apps=[apply(w,rid,c,'support')[1]['data'] for w in (b,other)]
    lead=context(a,rid,c,'apply');bodies=[decision(app,lead) for app in apps]
    def run(pair):
        app,body=pair
        try:return commands.process(actor(a['uid']),uuid.UUID(app['application_id']),uuid.uuid4(),body)[0]
        except commands.GameError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,zip(apps,bodies)))
    assert sorted(map(str,results))==['200','TARGET_CONTEXT_STALE']
    with session() as db:
        target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        assert commands.admission.member_count(db,target)==4
        assert sorted(db.scalars(select(CycleApplication.state).where(CycleApplication.id.in_([uuid.UUID(app['application_id']) for app in apps]))))==['accepted','pending']


def test_real_http_context_post_existing_contract(current):
    from tests.test_recruitment_cycle_times_http import client
    from tests.test_recruitment_cycle_http import validate
    _,a,b=current;rid,c,n=room(a);change_class(b,leader_class(a))
    with client(b) as http:
        route=f'/v2/raid-rooms/{rid}'
        response=http.get(route+'/admission-context',params=dict(target_cycle_key=c,character_id=b['ids'][0],selected_role='dealer',intent='apply'))
        assert response.status_code==200 and response.headers['cache-control']=='no-store'
        validate('/v2/raid-rooms/{room_id}/admission-context','get',200,response.json())
        assert response.json()['data']['permissions']['apply']['reason']=='ROOM_COMPOSITION_CONFLICT'
        payload=admission_request(response.json()).model_dump(mode='json')
        response=http.post(route+'/applications',json=payload,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==409 and response.json()['error']['code']=='ROOM_COMPOSITION_CONFLICT'
        assert response.headers['cache-control']=='no-store'
        validate('/v2/raid-rooms/{room_id}/applications','post',409,response.json())


@pytest.mark.parametrize('delta',['-0.01','0'])
def test_exact_level_boundary(current,delta):
    from decimal import Decimal
    _,a,b=current;rid,c,n=room(a)
    with session() as db,db.begin():
        target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        item,rd=commands.admission.rounds(db,target)[0]
        minimum=Decimal(raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version).min_item_level)
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.summary={**char.summary,'item_level':str(minimum+Decimal(delta))}
    permission=context(b,rid,c,'apply')['data']['permissions']['apply']
    if delta=='0':
        assert permission['allowed'];assert apply(b,rid,c)[0]==201
    else:assert permission['reason']=='RAID_ITEM_LEVEL_REQUIRED'
