"""Agreed calendar contract on a disposable, restricted-role database."""
import copy
import json
import os
import subprocess
import time
import tracemalloc
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, event
from app.auth.router import authenticated
from app.core.database import session, now
from app.core.errors import register
from app.game_accounts.common.support import GameError
from app.raid_rooms.api.personal_reservations_router import router
from app.raid_rooms.schedules import personal_reservations as service, reservation_cursor as cursors
from app.raid_rooms.schemas.personal_reservations import ReservationPage
from app.raid_rooms.models.source_models import TimeReservation
from app.raid_rooms.models.integrated_models import RecruitmentAssignment
from tests.raid_rooms.group_links.test_cycle_group_policy import (
    policy_db, group_beta, beta, current, candidate, ready, sources, imported, people, worlds,
    create_beta, actor, end_history_room,
)

@pytest.fixture
def calendar_db(policy_db):
    engine, a, b = policy_db
    result = subprocess.run(['alembic','upgrade','head'],env={**os.environ,'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True)
    assert result.returncode == 0
    return engine,a,b

def http(w):
    app=FastAPI();register(app);app.include_router(router)
    app.dependency_overrides[authenticated]=lambda:actor(w['uid'])
    return TestClient(app)

def key():
    with session() as db: return service.calendar_key(now(db)).isoformat()

def clone_rows(uid, count):
    with session() as db,db.begin():
        r=db.scalar(select(TimeReservation).where(TimeReservation.user_id==uid,TimeReservation.released_at.is_(None)).order_by(TimeReservation.starts_at))
        values={c.name:getattr(r,c.name) for c in TimeReservation.__table__.columns if c.name not in ('id','record_created_at','record_updated_at')}
        from app.raid_rooms.models.source_models import SessionParticipation
        from app.raid_rooms.models.integrated_models import RecruitmentSegment, RecruitmentSession
        segment=db.get(RecruitmentSegment,r.segment_id)
        part=db.get(SessionParticipation,r.participation_id)
        sess=db.get(RecruitmentSession,r.session_id)
        def fields(obj):return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name not in ('id','record_created_at','record_updated_at')}
        sessions=[];parts=[];segments=[];reservations=[]
        for _ in range(count):
            sid,pid,segid=uuid4(),uuid4(),uuid4()
            sessions.append(dict(id=sid,**fields(sess)))
            parts.append(dict(id=pid,**(fields(part)|dict(session_id=sid))))
            segments.append(dict(id=segid,**(fields(segment)|dict(session_id=sid))))
            reservations.append(dict(id=uuid4(),**(values|dict(session_id=sid,participation_id=pid,segment_id=segid))))
        for model, rows in [(RecruitmentSession,sessions),(SessionParticipation,parts),(RecruitmentSegment,segments),(TimeReservation,reservations)]:
            db.execute(model.__table__.insert(),rows)

@pytest.mark.parametrize('shape', ['normal','empty'])
def test_http_privacy_shape_and_unchanged_ledger(calendar_db,shape):
    engine,a,b=calendar_db
    rid,_,_,_,_=create_beta(a,combined=True)
    with http(a if shape=='normal' else b) as client:
        params={'calendar_week_key':key()}
        r=client.get('/v2/me/raid-reservations',params=params)
        assert r.status_code==200,r.json()
        assert r.headers['cache-control']=='no-store'
        page=r.json();ReservationPage.model_validate(page)
        from jsonschema import Draft202012Validator,FormatChecker
        spec=json.loads(Path('docs/features/rosters/activity-and-presentation/reservation-page.candidate.schema.json').read_text())
        Draft202012Validator(spec,format_checker=FormatChecker()).validate(page)
        if shape=='empty':assert page['data']['items']==[]
        else:
            assert page['data']['items'] and all(i['room_id']==str(rid) for i in page['data']['items'])
            assert all('room_title' not in i for i in page['data']['items'])
            from sqlalchemy import update
            fired=[]
            def concurrent_write(conn,cursor,statement,parameters,context,many):
                if not fired and statement.startswith('SELECT recruitment_reservations.id') and 'LEFT OUTER JOIN' in statement:
                    fired.append(True)
                    with engine.begin() as writer:
                        writer.execute(update(RecruitmentAssignment).where(RecruitmentAssignment.user_id==a['uid']).values(
                            display={'character_name':'snapshot changed','server_name':'test','class_name':None}))
            event.listen(engine,'after_cursor_execute',concurrent_write)
            try:during=client.get('/v2/me/raid-reservations',params=params)
            finally:event.remove(engine,'after_cursor_execute',concurrent_write)
            assert fired and during.status_code==200,during.json()
            assert during.json()['data']['result_revision']==page['data']['result_revision']
            after=client.get('/v2/me/raid-reservations',params=params).json()
            assert after['data']['result_revision']!=page['data']['result_revision']
            assert after['data']['items'][0]['character']['display']['name']=='snapshot changed'

        for bad in [params|{'limit':0},params|{'other':'x'},params|{'calendar_week_key':'2026-11-17'}]:
            assert client.get('/v2/me/raid-reservations',params=bad).status_code==400
        assert client.get('/v2/me/raid-reservations',params=[('calendar_week_key',key())]*2).status_code==400

def test_cursor_nullable_review_release_and_page_writes(calendar_db,monkeypatch):
    engine,a,b=calendar_db;rid,_,_,_,_=create_beta(a,combined=True)
    clone_rows(a['uid'],200)
    params={'calendar_week_key':key(),'limit':1}
    with http(a) as client:
        for size in (1,100,200):
            batch=client.get('/v2/me/raid-reservations',params=params|{'limit':size})
            assert batch.status_code==200,batch.json()
            assert len(batch.json()['data']['items'])==size
        all_ids=set();following=None
        while True:
            query=params|{'limit':100}
            if following:query['cursor']=following
            batch=client.get('/v2/me/raid-reservations',params=query).json()['data']
            ids={i['reservation_id'] for i in batch['items']}
            assert not ids & all_ids
            all_ids |= ids;following=batch['next_cursor']
            if not following:break
        assert len(all_ids)==201
        first=client.get('/v2/me/raid-reservations',params=params).json()
        token=first['data']['next_cursor'];assert token
        second=client.get('/v2/me/raid-reservations',params=params|{'cursor':token})
        assert second.status_code==200,second.json()
        assert second.json()['data']['result_revision']==first['data']['result_revision']
        assert second.json()['data']['items'][0]['reservation_id']!=first['data']['items'][0]['reservation_id']
        assert client.get('/v2/me/raid-reservations',params=params|{'cursor':token,'limit':2}).status_code==400
        with http(b) as foreign:assert foreign.get('/v2/me/raid-reservations',params=params|{'cursor':token}).status_code==400
        with session() as db,db.begin():
            first_reservation=db.scalar(select(TimeReservation).where(TimeReservation.user_id==a['uid']).order_by(TimeReservation.starts_at))
            assigned=db.get(RecruitmentAssignment,first_reservation.assignment_id)
            assigned.display={'character_name':'','class_name':None}
        stale=client.get('/v2/me/raid-reservations',params=params|{'cursor':token})
        assert stale.status_code==409 and stale.json()['error']['code']=='CURSOR_STALE'
        fresh=client.get('/v2/me/raid-reservations',params=params).json()
        assert fresh['data']['items'][0]['character']['display']['name'] is None
        monkeypatch.setattr(service,'MAX_BYTES',1)
        assert client.get('/v2/me/raid-reservations',params=params).status_code==413
        monkeypatch.setattr(service,'MAX_BYTES',1048576)
        from app.raid_rooms.models.integrated_models import RecruitmentRoom
        with session() as db,db.begin():db.get(RecruitmentRoom,rid).ended_at=now(db)
        remaining=client.get('/v2/me/raid-reservations',params=params|{'limit':200})
        assert remaining.status_code==200,remaining.json()
        assert len(remaining.json()['data']['items'])==200
        with session() as db,db.begin():db.get(RecruitmentRoom,rid).ended_at=None
        end_history_room(a,rid,create_key(rid))
        assert client.get('/v2/me/raid-reservations',params=params).json()['data']['items']==[]

def create_key(rid):
    from app.raid_rooms.models.cycle_models import RoomCycle
    with session() as db:return db.scalar(select(RoomCycle.cycle_key).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)).isoformat()

def test_10000_bound_query_cost_and_snapshot_projection(calendar_db, capsys):
    engine,a,b=calendar_db;create_beta(a)
    clone_rows(a['uid'],10000)
    queries=[]
    def counted(conn,cursor,statement,parameters,context,many):queries.append(statement)
    event.listen(engine,'before_cursor_execute',counted)
    tracemalloc.start();started=time.perf_counter()
    try:
        with pytest.raises(GameError) as error:service.page(actor(a['uid']),key())
        assert error.value.code=='RESERVATION_QUERY_LIMIT_EXCEEDED'
        with session() as db,db.begin():
            r=db.scalar(select(TimeReservation).where(TimeReservation.user_id==a['uid']).order_by(TimeReservation.id))
            r.released_at=now(db);r.released_reason='future_cancel'
        pages=service.page(actor(a['uid']),key(),200)
        assert len(pages['data']['items'])==200 and pages['data']['next_cursor']
        with capsys.disabled():
            print('RESERVATION_BENCH',json.dumps(dict(seconds=time.perf_counter()-started,peak_bytes=tracemalloc.get_traced_memory()[1],queries=len(queries),page_bytes=len(json.dumps(pages).encode()))),flush=True)
        from sqlalchemy import text
        with session() as db:
            stmt=service.query(a['uid'],*service.window(now(db),key())[1:]).compile(db.bind,compile_kwargs={'literal_binds':True})
            plan=db.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+str(stmt))).scalar()
        with capsys.disabled():print('RESERVATION_EXPLAIN',json.dumps(plan),flush=True)
        tracemalloc.stop()
        single_started=time.perf_counter();single=service.page(actor(a['uid']),key(),200)
        with capsys.disabled():print('RESERVATION_SINGLE_REQUEST',json.dumps(dict(seconds=time.perf_counter()-single_started,page_bytes=len(json.dumps(single,ensure_ascii=False,separators=(',',':')).encode()))),flush=True)
        assert sum(q.startswith('SELECT') and 'LEFT OUTER JOIN' in q and 'recruitment_reservations' in q for q in queries)==3
    finally:tracemalloc.stop();event.remove(engine,'before_cursor_execute',counted)

@pytest.mark.parametrize('hour,game,calendar',[ (0,'2026-11-11','2026-11-18'),(5,'2026-11-11','2026-11-18'),(6,'2026-11-18','2026-11-18')])
def test_midnight_independent_of_game_week(hour,game,calendar):
    stamp=datetime(2026,11,18,hour,tzinfo=service.raids.KST)
    assert service.calendar_key(stamp).isoformat()==calendar
    assert service.raids.cycle(stamp).cycle_key==game
    _,start,end=service.window(stamp,calendar);assert end-start==timedelta(days=7)


def test_cursor_signature_expiry_and_original_deadline():
    stamp=datetime(2026,11,18,tzinfo=timezone.utc);scope=['own','window'];revision='a'*64
    last=['2026-11-18T00:00:00Z',str(uuid4())];expires=int(stamp.timestamp())+600
    token=cursors.encode(scope,revision,last,expires)
    assert cursors.decode(token,scope,revision,stamp)==(last,expires)
    for wrong,code in [(token[:-3]+'xyz','INVALID_REQUEST'),(token,'CURSOR_STALE')]:
        with pytest.raises(GameError) as err:cursors.decode(wrong,scope,revision,stamp+timedelta(seconds=600))
        assert err.value.code==code

@pytest.mark.parametrize('value,expected',[ (None,None),('',None),('  ',None),(' 이름 ',' 이름 '),('😀','😀')])
def test_snapshot_display_normalization(value,expected):assert service.label(value,128)==expected


@pytest.mark.parametrize('value',[3, True, 'x'*129])
def test_bad_snapshot_display_fails_explicitly(value):
    with pytest.raises(GameError) as error:service.label(value,128)
    assert error.value.code=='RESERVATION_DATA_UNAVAILABLE'
