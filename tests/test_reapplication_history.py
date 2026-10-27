"""Personal departure reentry: synthetic C/N actors, isolated PostgreSQL only."""
import uuid
import os,subprocess
from datetime import date
from copy import deepcopy
import pytest
from sqlalchemy import select
from app.core.database import session
from app.game_accounts.models import Character
from app.raid_rooms import (beta_profile,cycle_commands as commands,admission_candidates,atomic_members,
    cycle_management,membership_readers,cycle_lifecycle as life)
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleAssignment
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment
from tests.test_beta_recruitment import beta,current,candidate,ready,sources,imported,people,worlds,create_beta,beta_join,actor
from tests.test_recruitment_cycle_commands import context,admission_request,decision
from tests.test_recruitment_cycle_management import settings
from tests.test_atomic_members import departure,depart_body
from tests.test_recruitment_cycle_times import fingerprints


def setup_reentry(data,mode='leader_only'):
    engine,a,b=data;rid,c,_,_,_=create_beta(a,combined=True)
    with session() as db:
        keys=list(db.scalars(select(RoomCycle.cycle_key).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)))
    n=keys[1].isoformat();beta_join(b,rid,c);beta_join(b,rid,n)
    alternate=deepcopy(a);alternate['ids']=[a['ids'][1],*a['ids'][2:]]
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(alternate['ids'][0]));char.summary={**char.summary,'class_name':'synthetic-reapplication','item_level':'2000'}
    with beta_profile.using():
        ctx=departure(a,rid,c);old_cm=uuid.UUID(ctx['data']['subject']['cycle_member_id'])
        atomic_members.execute(actor(a['uid']),rid,uuid.uuid4(),depart_body(ctx),departure=True)
        old=membership_readers.get(actor(a['uid']),rid,c,'plan',cycle_member_id=old_cm,
            membership_id=uuid.UUID(ctx['data']['subject']['membership_id']))['data']['record']
        if mode!='direct_join':cycle_management.command(actor(b['uid']),rid,uuid.uuid4(),settings(b,rid,c,admission_mode=mode),'settings')
    return engine,a,b,alternate,rid,c,n,old_cm,old


@pytest.fixture
def reapplication_ready(beta):
    engine,_,_=beta
    from sqlalchemy import inspect
    from tests.test_raid_room_migrations import table_digests
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0033_reapplication_history'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-1500:]
    assert table_digests(engine,tables)==before
    from app.raid_rooms.readiness import require_two_cycle_active
    with session() as db:require_two_cycle_active(db)
    return beta


def test_reapplication_candidate_context_apply_approval_and_old_record(reapplication_ready):
    engine,a,b,alternate,rid,c,n,old_cm,old=setup_reentry(reapplication_ready)
    with beta_profile.using():
        page=admission_candidates.get(actor(a['uid']),rid,c,'apply')['data']
        assert any(v['character_id']==alternate['ids'][0] for v in page['items'])
        value=context(alternate,rid,c,'apply')
        assert value['data']['permissions']['apply']['allowed'],value['data']['permissions']['apply']
        status,ack=commands.admit(actor(a['uid']),rid,uuid.uuid4(),admission_request(value),applying=True)
        assert status==201
        aid=uuid.UUID(ack['data']['application_id']);review=commands.application(actor(b['uid']),aid)
        assert review['data']['permissions']['approve']['allowed']
        before=fingerprints(engine)
        with session() as db:assert db.get(CycleMember,old_cm).state=='cancelled'
        leader=context(b,rid,c,'apply');command=uuid.uuid4();body=decision(ack['data'],leader)
        result=commands.process(actor(b['uid']),aid,command,body)
        assert result[0]==200
        fresh=membership_readers.get(actor(a['uid']),rid,c,'plan')['data']['viewer']
        assert fresh['cycle_member_id']!=str(old_cm)
        with session() as db:
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            cm=life.actual_member(db,row,a['uid']);assert cm.id!=old_cm
            assert not {str(v.id) for v in life.assignments(db,row,cm)} & {v['assignment_id'] for v in old['assignments']}
        again=membership_readers.get(actor(a['uid']),rid,c,'plan',cycle_member_id=old_cm,membership_id=uuid.UUID(old['locator']['membership_id']))['data']['record']
        assert again==old
        after=fingerprints(engine);assert commands.process(actor(b['uid']),aid,command,body)==result;assert fingerprints(engine)==after


def protected(engine,old_cm,rid,n):
    """Exact historical rows and opposite cycle business rows, never mutable C heads."""
    from sqlalchemy import text
    result={}
    with engine.connect() as conn:
        params={'cm':old_cm,'rid':rid,'n':date.fromisoformat(n)}
        for table,where in {
            'recruitment_cycle_members':'id=:cm OR cycle_id IN (SELECT id FROM recruitment_room_cycles WHERE room_id=:rid AND cycle_key=:n)',
            'recruitment_cycle_assignments':'cycle_member_id=:cm OR cycle_id IN (SELECT id FROM recruitment_room_cycles WHERE room_id=:rid AND cycle_key=:n)',
            'recruitment_assignments':'id IN (SELECT assignment_id FROM recruitment_cycle_assignments WHERE cycle_member_id=:cm) OR round_id IN (SELECT round_id FROM recruitment_cycle_rounds cr JOIN recruitment_room_cycles c ON c.id=cr.cycle_id WHERE c.room_id=:rid AND c.cycle_key=:n)',
            'recruitment_participation_events':'cycle_member_id=:cm',
            'recruitment_cycle_consents':'cycle_member_id=:cm',
            'recruitment_reservations':'assignment_id IN (SELECT assignment_id FROM recruitment_cycle_assignments WHERE cycle_member_id=:cm)',
            'recruitment_room_cycles':'room_id=:rid AND cycle_key=:n',
            'recruitment_cycle_generations':'cycle_id IN (SELECT id FROM recruitment_room_cycles WHERE room_id=:rid AND cycle_key=:n)',
            'recruitment_beta_schedules':'cycle_id IN (SELECT id FROM recruitment_room_cycles WHERE room_id=:rid AND cycle_key=:n)',
        }.items():
            result[table]=sorted(str(v) for v in conn.scalars(text(f'SELECT to_jsonb(t)::text FROM {table} t WHERE {where}'),params))
    return result


def test_direct_rejoin_fresh_identity_old_rows_opposite_and_ack(reapplication_ready):
    from app.raid_rooms.source_models import TimeReservation
    from app.raid_rooms import cycle_member_reads
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    before=protected(engine,old_cm,rid,n)
    with beta_profile.using():
        readonly=fingerprints(engine)
        ctx=context(alt,rid,c);assert ctx['data']['permissions']['join']['allowed']
        assert context(a,rid,c)['data']['permissions']['join']['reason']=='WEEKLY_ALREADY_COMPLETED'
        page=admission_candidates.get(actor(a['uid']),rid,c,'join')['data']
        assert a['ids'][0] not in {v['character_id'] for v in page['items']}
        assert fingerprints(engine)==readonly
        data=admission_request(ctx);command=uuid.uuid4();result=commands.admit(actor(a['uid']),rid,command,data)
        assert result[0]==200
        assert protected(engine,old_cm,rid,n)==before
        with session() as db:
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            fresh=life.actual_member(db,row,a['uid']);assert fresh.id!=old_cm
            assert fresh.joined_order>db.get(CycleMember,old_cm).joined_order
            assert {v.character_id for v in life.assignments(db,row,fresh)}=={uuid.UUID(alt['ids'][0])}
            assert db.scalar(select(TimeReservation).where(TimeReservation.assignment_id.in_([v.id for v in life.assignments(db,row,fresh)]),TimeReservation.released_at.is_(None)))
            from sqlalchemy import insert
            from sqlalchemy.exc import IntegrityError
            saved=life.assignments(db,row,fresh)[0]
            for state in ('active','stopped_incomplete'):
                duplicate={col.name:getattr(saved,col.name) for col in Assignment.__table__.columns}
                duplicate.update(id=uuid.uuid4(),slot_no=4,state=state,ended_at=None if state=='active' else saved.joined_at)
                with pytest.raises(IntegrityError) as failure:
                    with db.begin_nested():db.execute(insert(Assignment).values(**duplicate))
                assert failure.value.orig.diag.constraint_name=='uq_recruitment_current_assignment'
        assert membership_readers.get(actor(a['uid']),rid,c,'plan',cycle_member_id=old_cm,membership_id=uuid.UUID(old['locator']['membership_id']))['data']['record']==old
        after=fingerprints(engine);assert commands.admit(actor(a['uid']),rid,command,data)==result;assert fingerprints(engine)==after
        assert context(alt,rid,c)['data']['permissions']['join']['reason']=='ROOM_MEMBER_EXISTS'


@pytest.mark.parametrize('change,reason',[('class','ROOM_COMPOSITION_CONFLICT'),('level','RAID_ITEM_LEVEL_REQUIRED'),('power','COMBAT_POWER_REQUIRED')])
def test_reentry_keeps_eligibility_guards(reapplication_ready,change,reason):
    from copy import deepcopy
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(alt['ids'][0]))
        if change=='class':char.summary={**char.summary,'class_name':db.get(Character,uuid.UUID(b['ids'][0])).summary['class_name']}
        elif change=='level':char.summary={**char.summary,'item_level':'1'}
        else:
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            cfg=deepcopy(row.settings_snapshot);cfg['combat_requirement'].update(dealer_min='999999',input_mode='per_role');row.settings_snapshot=cfg
    before=fingerprints(engine)
    with beta_profile.using():
        ctx=context(alt,rid,c);assert ctx['data']['permissions']['join']['reason']==reason
        page=admission_candidates.get(actor(a['uid']),rid,c,'join')['data']
        assert alt['ids'][0] not in {v['character_id'] for v in page['items']}
    assert fingerprints(engine)==before


def test_pending_rechecks_and_failed_approval_preserves_history(reapplication_ready):
    from app.raid_rooms.cycle_application_models import CycleApplication
    from tests.test_application_composition import occupancy
    from app.game_accounts.support import GameError
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready)
    before=protected(engine,old_cm,rid,n)
    with beta_profile.using():
        counts=occupancy();ctx=context(alt,rid,c,'apply')
        app=commands.admit(actor(a['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)[1]['data']
        assert occupancy()==counts and protected(engine,old_cm,rid,n)==before
        with session() as db,db.begin():
            char=db.get(Character,uuid.UUID(alt['ids'][0]));char.summary={**char.summary,'item_level':'1'}
        body=decision(app,context(b,rid,c,'apply'));snapshot=fingerprints(engine)
        with pytest.raises(GameError,match='RAID_ITEM_LEVEL_REQUIRED'):
            commands.process(actor(b['uid']),uuid.UUID(app['application_id']),uuid.uuid4(),body)
        assert fingerprints(engine)==snapshot
        with session() as db:assert db.get(CycleApplication,uuid.UUID(app['application_id'])).state=='pending'
        assert protected(engine,old_cm,rid,n)==before


def test_reentry_install_failure_rolls_back(reapplication_ready,monkeypatch):
    from app.raid_rooms import cycles
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    with beta_profile.using():
        data=admission_request(context(alt,rid,c));before=fingerprints(engine);original=cycles.record_bundle_join
        def fail_after(*args,**kwargs):
            original(*args,**kwargs);raise RuntimeError('synthetic fresh CM installation failure')
        with monkeypatch.context() as m:
            m.setattr(cycles,'record_bundle_join',fail_after)
            with pytest.raises(RuntimeError,match='synthetic fresh CM'):commands.admit(actor(a['uid']),rid,uuid.uuid4(),data)
        assert fingerprints(engine)==before


def test_concurrent_reentry_one_writer(reapplication_ready):
    from concurrent.futures import ThreadPoolExecutor
    from app.game_accounts.support import GameError
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    with beta_profile.using():data=admission_request(context(alt,rid,c))
    def join(_):
        with beta_profile.using():
            try:return commands.admit(actor(a['uid']),rid,uuid.uuid4(),data)[0]
            except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(join,range(2)))
    assert sorted(map(str,results))==['200','TARGET_CONTEXT_STALE']
    with session() as db:
        rows=list(db.scalars(select(CycleMember).where(CycleMember.room_id==rid,CycleMember.user_id==a['uid'],CycleMember.id!=old_cm)))
        assert len(rows)==2  # new C plus the original N


def test_populated_0032_upgrade_old_event_fallback_and_schema_guards(beta,monkeypatch):
    from sqlalchemy import inspect,text
    from tests.test_raid_room_migrations import table_digests
    from app.raid_rooms import readiness,beta_schedule,cycle_worker
    from app.game_accounts.support import GameError
    # Simulate the original writer's old event shape, before insertion; immutable stored events are never rewritten.
    original=life.event
    def old_event(db,row,cm,command,action,stamp,evidence):
        evidence=dict(evidence);evidence.pop('record_schedule_segments',None)
        return original(db,row,cm,command,action,stamp,evidence)
    with monkeypatch.context() as m:
        m.setattr(life,'event',old_event);engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(beta,'direct_join')
    assert old['schedule_segments'] and all(v['state']=='released' for v in old['schedule_segments'])
    with beta_profile.using():
        assert context(alt,rid,c)['data']['permissions']['join']['reason']=='RECRUITMENT_COMMAND_NOT_READY'
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0033_reapplication_history'],env={**os.environ,'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-1200:]
    assert table_digests(engine,tables)==before
    with session() as db:
        readiness.require_two_cycle_active(db);readiness.require_cycle_worker(db);assert beta_schedule.available(db)
        predicate=db.scalar(text("SELECT pg_get_expr(indpred,indrelid) FROM pg_index WHERE indexrelid='uq_recruitment_current_assignment'::regclass"))
        assert all(f"'{v}'" in predicate for v in ['left','legacy_ended','completed'])
    with beta_profile.using():
        beta_join(alt,rid,c)
        # Reused session participation and new planned reservation cannot rewrite the old record.
        assert membership_readers.get(actor(a['uid']),rid,c,'plan',cycle_member_id=old_cm,membership_id=uuid.UUID(old['locator']['membership_id']))['data']['record']==old
    with session() as db,db.begin():
        db.execute(text("UPDATE alembic_version SET version_num='9999_unapproved'"))
        with pytest.raises(GameError):readiness.require_two_cycle_active(db)
        assert not beta_schedule.available(db)


def test_reentry_http_candidates_context_join_and_historical_reader(reapplication_ready):
    from tests.test_recruitment_cycle_http import client
    from tests.test_beta_recruitment import PROFILE
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    before=protected(engine,old_cm,rid,n)
    with client(a) as http:
        query={**PROFILE,'target_cycle_key':c,'intent':'join'}
        page=http.get(f'/v2/raid-rooms/{rid}/admission-character-candidates',params=query)
        assert page.status_code==200,page.json();assert page.json()['data']['actor'] is None
        assert any(v['character_id']==alt['ids'][0] for v in page.json()['data']['items'])
        ctx=http.get(f'/v2/raid-rooms/{rid}/admission-context',params={**query,'character_id':alt['ids'][0],'selected_role':'dealer'})
        assert ctx.status_code==200,ctx.json();assert ctx.json()['data']['permissions']['join']['allowed']
        data=admission_request(ctx.json()).model_dump(mode='json');key={'Idempotency-Key':str(uuid.uuid4())}
        ack=http.post(f'/v2/raid-rooms/{rid}/join',params=PROFILE,json=data,headers=key)
        assert ack.status_code==200,ack.json()
        assert http.post(f'/v2/raid-rooms/{rid}/join',params=PROFILE,json=data,headers=key).json()==ack.json()
        anchor={**PROFILE,'reader_profile':'membership-actions-1','target_cycle_key':c,'cycle_member_id':str(old_cm),'membership_id':old['locator']['membership_id']}
        record=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=anchor)
        assert record.status_code==200,record.json();assert record.json()['data']['record']==old
    assert protected(engine,old_cm,rid,n)==before


@pytest.mark.parametrize('damage',['missing_binding','missing_event','generation'])
def test_incomplete_termination_evidence_never_authorizes_reentry(reapplication_ready,damage,monkeypatch):
    from app.raid_rooms import admission_history
    from app.game_accounts.support import GameError
    engine,a,b,alt,rid,c,n,old_cm,old=setup_reentry(reapplication_ready,'direct_join')
    # Simulate incomplete returned evidence at the read boundary, without bypassing immutable DB guards.
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        from app.raid_rooms.integrated_models import RecruitmentMembership as Member
        member=db.get(Member,uuid.UUID(old['locator']['membership_id']))
        original=db.scalars;scalar=db.scalar
        def scalars(query,*args,**kwargs):
            if damage=='missing_binding' and 'recruitment_cycle_assignments' in str(query):return []
            return original(query,*args,**kwargs)
        def one(query,*args,**kwargs):
            if damage=='missing_event' and 'recruitment_participation_events' in str(query):return None
            return scalar(query,*args,**kwargs)
        with monkeypatch.context() as m:
            m.setattr(db,'scalars',scalars);m.setattr(db,'scalar',one)
            if damage=='generation':row.generation+=1;assert admission_history.resolve(db,row,member) is None
            else:
                with pytest.raises(GameError,match='TARGET_CONTEXT_STALE'):admission_history.resolve(db,row,member)


def test_mixed_completed_left_bundle_creates_all_fresh_assignments(reapplication_ready):
    from tests.test_recruitment_cycle_times import scheduled
    engine,a,b=reapplication_ready;rid,c,n=scheduled(a,bundle=True)
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,c)))
    alt=deepcopy(a);alt['ids']=[a['ids'][1],*a['ids'][2:]]
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(alt['ids'][0]));char.summary={**char.summary,'class_name':'synthetic-bundle-reentry','item_level':'2000'}
    ctx=departure(a,rid,c);old_cm=uuid.UUID(ctx['data']['subject']['cycle_member_id'])
    atomic_members.execute(actor(a['uid']),rid,uuid.uuid4(),depart_body(ctx),departure=True)
    before=protected(engine,old_cm,rid,n)
    with session() as db:
        old=list(db.scalars(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).where(CycleAssignment.cycle_member_id==old_cm)))
        assert {v.state for v in old}=={'completed','left'};old_ids={v.id for v in old}
    value=context(alt,rid,c);assert value['data']['permissions']['join']['allowed']
    commands.admit(actor(a['uid']),rid,uuid.uuid4(),admission_request(value))
    assert protected(engine,old_cm,rid,n)==before
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        fresh=life.actual_member(db,row,a['uid']);rows=life.assignments(db,row,fresh)
        assert len(rows)==2 and fresh.id!=old_cm and not old_ids & {v.id for v in rows}
