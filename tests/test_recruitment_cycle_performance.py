"""W5 reproducible synthetic measurements, never a live server benchmark.

Optional W5_REPORT_DIR must be a /tmp directory inside the disposable runner.
Reports contain aggregate SQL/row/byte/timing/plan metrics, no parameters/data.
"""
import json, math, os, statistics, time, uuid, threading
from contextlib import contextmanager
from pathlib import Path
from datetime import date, timedelta
import pytest
from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, select, inspect, text
from app.core.database import session, now
from app.raid_rooms import cycle_card_batch as batch, cycle_queries as directory
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from tests.test_recruitment_cycle_outcomes import (outcomes,planning,consent,lifecycle,candidate,ready,sources,
    imported,people,worlds,scheduled,create_room,actor,add_member,cancel_member,preflight,request,creation,cycles)
from tests.test_recruitment_cycle_queries import search_request
from tests.test_raid_room_migrations import table_digests


@contextmanager
def measured(engine):
    values=dict(statements=0,rows=0,queries=[])
    owner=threading.get_ident()
    def after(conn,cursor,statement,parameters,context,many):
        if threading.get_ident()==owner and statement.lstrip().lower().startswith('select'):
            values['statements']+=1;values['rows']+=max(cursor.rowcount,0)
            values['queries'].append((statement,parameters))
    event.listen(engine,'after_cursor_execute',after)
    try:yield values
    finally:event.remove(engine,'after_cursor_execute',after)


def normalized(value):
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items() if k not in ('server_now','server_time','evaluated_at')}
    if isinstance(value,list):return [normalized(v) for v in value]
    return value


def sample(engine,call,*,runs=12):
    call();call() # warm imports/connections, deliberately excluded
    timings=[];counts=[];rows=[];sizes=[]
    for _ in range(runs):
        with measured(engine) as m:
            start=time.perf_counter();value=call();timings.append(1000*(time.perf_counter()-start))
        counts.append(m['statements']);rows.append(m['rows']);sizes.append(len(json.dumps(jsonable_encoder(value),separators=(',',':'),ensure_ascii=False).encode()))
    plans=[]
    with engine.connect() as connection:
        connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        for sql,params in m['queries']:
            plan=connection.exec_driver_sql('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql,params).scalar()[0]
            root=plan['Plan']
            plans.append(dict(node=root['Node Type'],actual_rows=root['Actual Rows'],estimated_rows=root['Plan Rows'],
                execution_ms=plan['Execution Time'],shared_hit_blocks=root.get('Shared Hit Blocks',0),shared_read_blocks=root.get('Shared Read Blocks',0)))
    return value,dict(samples=runs,p50_ms=round(statistics.median(timings),3),
        p95_ms=round(sorted(timings)[math.ceil(.95*runs)-1],3),select_statements=sorted(set(counts)),
        returned_sql_rows=sorted(set(rows)),response_bytes=sorted(set(sizes)),explain=dict(select_plans=len(plans),
            total_execution_ms=round(sum(p['execution_ms'] for p in plans),3),
            shared_hit_blocks=sum(p['shared_hit_blocks'] for p in plans),shared_read_blocks=sum(p['shared_read_blocks'] for p in plans),
            slowest_roots=sorted(plans,key=lambda p:p['execution_ms'],reverse=True)[:5]))


def report(name,value):
    print('W5_MEASURE '+name+' '+json.dumps({k:({x:y for x,y in v.items() if x!='explain'} if isinstance(v,dict) else v) for k,v in value.items()},separators=(',',':')))
    if path:=os.environ.get('W5_REPORT_DIR'):
        directory=Path(path).resolve();assert directory.is_relative_to('/tmp')
        directory.mkdir(parents=True,exist_ok=True)
        (directory/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')


def test_directory_50_cards_batch_equivalence_group_pages_and_measurements(outcomes,people,monkeypatch):
    from app.groups.models import Group,GroupMembership
    from tests.test_group_foundation import create as group_create
    engine,a,b=outcomes
    gid=uuid.UUID(group_create(a)[1]['group']['group_id'])
    from tests.test_member_limits import change
    from app.member_limits.service import Limits
    change(a['uid'],Limits(group_capacity=60,joined_groups=5,raid_rooms=10))
    created=[]
    for i in range(50):
        # Synthetic provisioning only: avoid coupling the dataset to login throttling.
        from app.auth.router import _limits
        _limits.clear()
        w=people(f'w5-directory-{i}')
        with session() as db,db.begin():
            db.add(GroupMembership(id=uuid.uuid4(),group_id=gid,user_id=w['uid'],character_id=uuid.UUID(w['ids'][0]),
                display=None,revision=1,joined_at=now(db)));db.get(Group,gid).members_revision+=1
        ctx=preflight(w,continuation=True,gid=gid)
        result=creation.create(actor(w['uid']),uuid.uuid4(),request(ctx,group_id=str(gid),scope='group' if i%2 else 'public'))[1]['data']
        created.append(result)
    c,n=[r['target_cycle_key'] for r in created[0]['created_cycles']]
    with engine.begin() as connection:connection.execute(text('ANALYZE'))
    principal=actor(a['uid']);tables=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,tables)
    real_load=batch.load
    for key in (c,n):
        data=search_request(key,limit=50)
        with monkeypatch.context() as patch:
            patch.setattr(batch,'load',lambda db,rows,uid:{r.id:None for r in rows})
            old,old_stats=sample(engine,lambda:directory.search(principal,data))
        new,new_stats=sample(engine,lambda:directory.search(principal,data))
        assert len(new['data']['items'])==50
        assert normalized(old)==normalized(new)
        assert new_stats['select_statements'][0]<old_stats['select_statements'][0]
        with measured(engine) as small:directory.search(principal,search_request(key,limit=1))
        assert small['statements']==new_stats['select_statements'][0]
        report('directory_'+('C' if key==c else 'N'),dict(baseline='same search/snapshot, original per-card loader',
            optimized='request-local batched card loader',rooms=50,cycles=2,before=old_stats,after=new_stats))
    source=directory.filters.get_context(principal,[gid])
    params=dict(group_ids=[gid],filter_context_token=source['filter_context_token'],limit=7)
    data=search_request(n,**params)
    with monkeypatch.context() as patch:
        patch.setattr(batch,'load',lambda db,rows,uid:{r.id:None for r in rows})
        old,old_stats=sample(engine,lambda:directory.search(principal,data))
    new,new_stats=sample(engine,lambda:directory.search(principal,data))
    assert normalized(old)==normalized(new)
    report('group_page_7',dict(rooms=50,page_size=7,before=old_stats,after=new_stats))
    pages=[];cursor=None
    while True:
        page=directory.search(principal,search_request(n,**params,cursor=cursor))['data']
        pages.extend(i['room_id'] for i in page['items']);cursor=page['next_cursor']
        if cursor is None:break
    assert len(pages)==len(set(pages))==50
    public=directory.search(None,search_request(n,limit=50))
    assert len(public['data']['items'])==25
    outsider=directory.search(actor(b['uid']),search_request(n,limit=50))
    assert len(outsider['data']['items'])==25
    assert table_digests(engine,tables)==before
    assert batch.load is real_load


def test_card_batch_same_snapshot_bundle_sessions_generations_and_member_isolation(outcomes,people,monkeypatch):
    from tests.test_recruitment_cycle_http import validate
    engine,a,b=outcomes;rid,c,n=scheduled(a,alternatives=2)
    add_member(b,rid,n)
    # Read all projections against the exact same DB clock and RR snapshot.
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    for uid in (None,a['uid'],b['uid']):
        with session() as db,db.begin():
            db.connection(execution_options={'isolation_level':'REPEATABLE READ'});db.execute(text('SET TRANSACTION READ ONLY'))
            rows=list(db.execute(select(Room,RoomCycle).join(RoomCycle,RoomCycle.room_id==Room.id).where(Room.id==rid)))
            loaded=batch.load(db,[row for _,row in rows],uid);stamp=now(db)
            for room,row in rows:
                assert directory.card(db,room,row,uid,stamp,loaded[row.id])==directory.card(db,room,row,uid,stamp)
    assert table_digests(engine,tables)==before
    data=search_request(c)
    with monkeypatch.context() as patch:
        patch.setattr(batch,'load',lambda db,rows,uid:{r.id:None for r in rows})
        old,old_stats=sample(engine,lambda:directory.search(actor(a['uid']),data))
    new,new_stats=sample(engine,lambda:directory.search(actor(a['uid']),data))
    assert normalized(old)==normalized(new)
    report('bundle_sessions',dict(items=2,sessions=2,before=old_stats,after=new_stats))
    # Cancel/reopen N produces generation 2 with different actual group links.
    cancel_member(b,rid,n);cancel_member(a,rid,n)
    from tests.test_recruitment_cycle_lifecycle import opening,opening_body
    ctx=opening.get(actor(a['uid']),rid,n,'reopen',uuid.UUID(a['ids'][0]),'dealer')
    opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx,'reopen'))
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        assert row.generation==2
        loaded=batch.load(db,[row],a['uid']);room=db.get(Room,rid);stamp=now(db)
        assert directory.card(db,room,row,a['uid'],stamp,loaded[row.id])==directory.card(db,room,row,a['uid'],stamp)
    # Every directory result continues to satisfy the fixed wire schema.
    page=directory.search(actor(a['uid']),search_request(n))
    validate('/v2/raid-rooms/search','post',200,page)


def test_summary_50_characters_500_entries_same_rows_measurements(outcomes,monkeypatch):
    from app.game_accounts.models import Character,NameClaim
    from app.raid_rooms import weekly_summary as summary,weekly_summary_schemas as weekly_schemas
    engine,a,b=outcomes;created=create_room(a);c,n=[r['target_cycle_key'] for r in created['created_cycles']]
    with session() as db,db.begin():
        stamp=now(db)
        for i in range(47):
            char=Character(id=uuid.uuid4(),account_id=a['aid'],server_name='w5-summary',character_name=f'synthetic-{i}',summary={},
                status='confirmed',lifecycle_state='active',lifecycle_revision=1,fetched_at=stamp,confirmed_at=stamp)
            db.add(char);db.flush();db.add(NameClaim(server_name=char.server_name,character_name=char.character_name,character_id=char.id))
        ids=list(db.scalars(select(Character.id).where(Character.account_id==a['aid'])))
    assert len(ids)==50
    principal=actor(a['uid']);data=weekly_schemas.SummaryRequest(character_ids=ids,target_cycle_keys=[c,n])
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})
    with monkeypatch.context() as patch:
        patch.setattr(summary,'cycle_evidence',lambda *args:(None,set()))
        old,old_stats=sample(engine,lambda:summary.summary(principal,data))
    new,new_stats=sample(engine,lambda:summary.summary(principal,data))
    assert len(new['entries'])==500 and normalized(old)==normalized(new)
    with measured(engine) as one:summary.summary(principal,weekly_schemas.SummaryRequest(character_ids=ids[:1],target_cycle_keys=[c,n]))
    assert one['statements']==new_stats['select_statements'][0]
    assert table_digests(engine,set(before))==before
    report('summary_500',dict(baseline='same 0029 data, pre-cycle-evidence projection; no declined/review cases',
        characters=50,entries=500,before=old_stats,after=new_stats))


def test_directory_eight_actual_participants_count_and_permissions(outcomes,people,monkeypatch):
    from app.raid_rooms import cycle_wire as wire,cycle_admission
    from app.raids import service as raids
    from tests.test_recruitment_cycle_commands import context,admission_request,commands
    engine,a,b=outcomes
    raid=next(r for r in raids.catalog().raids if r.raid_id=='kazeros_act4')
    with session() as db:key=raids.cycle(now(db)).cycle_key
    ctx=creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',[
        wire.BCreateTarget(raid_id=raid.raid_id,difficulty_id=raid.difficulties[0].difficulty_id,expected_weekly_revision=1)],None,key,True,None,None)
    result=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx))[1]['data'];rid=uuid.UUID(result['room_id'])
    n=result['created_cycles'][1]['target_cycle_key']
    for i in range(7):
        from app.auth.router import _limits
        _limits.clear();w=people(f'w5-eight-{i}')
        body=admission_request(context(w,rid,n,role='support' if i in (2,6) else 'dealer'))
        commands.admit(actor(w['uid']),rid,uuid.uuid4(),body)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        room=db.get(Room,rid);stamp=now(db)
        for uid in (None,a['uid'],w['uid'],b['uid']):
            loaded=batch.load(db,[row],uid)
            card=directory.card(db,room,row,uid,stamp,loaded[row.id])
            assert card==directory.card(db,room,row,uid,stamp)
            assert card['app_capacity']==card['app_member_count']==8
            assert card['permissions']['view_plan']['allowed']==(uid in (a['uid'],w['uid']))
    principal=actor(a['uid']);data=search_request(n)
    with monkeypatch.context() as patch:
        patch.setattr(batch,'load',lambda db,rows,uid:{r.id:None for r in rows})
        old,old_stats=sample(engine,lambda:directory.search(principal,data))
    new,new_stats=sample(engine,lambda:directory.search(principal,data))
    assert normalized(old)==normalized(new)
    report('eight_participants',dict(participants=8,before=old_stats,after=new_stats))


def test_batch_rows_do_not_grow_with_resumed_leader_assignment_history(outcomes):
    from tests.test_recruitment_cycle_outcomes import complete,propose_resume,vote
    engine,a,b=outcomes;rid,c,n=scheduled(a);rows=[]
    for _ in range(3):
        complete(a,rid,c,'close_weekly');pid=propose_resume(a,rid,c);vote(a,rid,c,pid)
        with session() as db,db.begin():
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            room=db.get(Room,rid);stamp=now(db)
            with measured(engine) as stats:loaded=batch.load(db,[row],a['uid'])
            rows.append(stats['rows'])
            assert directory.card(db,room,row,a['uid'],stamp,loaded[row.id])==directory.card(db,room,row,a['uid'],stamp)
    # Past rounds/evidence accumulate; the selected card's fetched rows do not.
    assert rows[0]==rows[1]==rows[2]
