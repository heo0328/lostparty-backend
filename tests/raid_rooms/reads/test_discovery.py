"""Agreed opt-in discovery: disposable PostgreSQL and synthetic identities only."""
import json
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from app.core.database import session
from app.raid_rooms.common import cycles, beta_profile
from app.raid_rooms.reads import cycle_queries, discovery
from app.raid_rooms.schemas import beta_schemas, cycle_schemas
from app.raid_rooms.schemas import discovery as dto
from app.raid_rooms.models.cycle_models import RoomCycle, CycleGeneration, CycleMember
from app.raid_rooms.models.cycle_group_models import CycleGroupPolicy
from app.raid_rooms.models.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member
from app.raid_rooms.models.beta_models import BetaSchedule
from app.raid_rooms.api.router import optional_principal
from tests.groups.test_group_character_candidates import group_candidates
from tests.raid_rooms.group_links.test_cycle_group_policy import policy_db
from tests.raid_rooms.group_links.test_cycle_group_policy import group_beta, beta, current, candidate, ready, sources, imported, people, worlds
from tests.raid_rooms.group_links.test_cycle_group_policy import group, add, change
from tests.raid_rooms.admissions.test_beta_recruitment import create_beta
from tests.raid_rooms.admissions.test_recruitment_cycle_http import client as cycle_client
from tests.groups.test_group_foundation import actor

PARAMS = dict(response_profile='discovery-1', contract_profile='beta-recruitment-1',
              group_policy_version='cycle-group-policy-1', include_group_state='true')


def body(key, limit=50, cursor=None, **extra):
    return dict(dict(category='all', admission_scope=None, group_ids=[], filter_context_token=None,
        member_conditions=[], raid_ids=[], difficulty_ids=[], target_cycle_key=key, limit=limit, cursor=cursor), **extra)


def fetch(http, key, *, params=None, **extra):
    r = http.post('/v2/raid-rooms/search', params=PARAMS if params is None else params, json=body(key, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def clones(rid, key, number):
    """Minimal open legacy targets: leader graph, no active assignment leases.

    These synthetic targets test directory cardinality, not create/admit policy.
    """
    def values(row):
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}
    with session() as db, db.begin():
        room=db.get(Room,rid)
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        gen=db.get(CycleGeneration,(row.id,row.generation));cm=db.get(CycleMember,gen.leader_cycle_member_id)
        member=db.get(Member,cm.membership_id)
        originals={cls:values(obj) for cls,obj in [(Room,room),(RoomCycle,row),(CycleGeneration,gen),(CycleMember,cm),(Member,member)]}
        result=[]
        for _ in range(number):
            mapping={v:uuid.uuid4() for v in (room.id,row.id,cm.id,member.id)}
            for cls in (Room,Member,RoomCycle,CycleGeneration,CycleMember):
                data={k:mapping.get(v,v) if isinstance(v,uuid.UUID) else v for k,v in originals[cls].items()}
                db.add(cls(**data))
                db.flush()
            db.add(CycleGroupPolicy(cycle_id=mapping[row.id],generation=row.generation,scope='public',group_id=None,revision=1))
            result.append(mapping[room.id])
        cycles.touch_directory(db,row.cycle_key)
    return result


def test_fifty_pages_count_stable_order_filters_and_legacy_compatibility(policy_db,capsys,monkeypatch):
    _,a,b=policy_db;rid,key,_,_,_=create_beta(a)
    cloned=clones(rid,key,101)
    with cycle_client(b) as http:
        first=fetch(http,key)
        assert first['data']['total_count']==102 and len(first['data']['items'])==50
        revision=first['data']['result_revision']
        seen=[v['room_id'] for v in first['data']['items']]
        assert len(first['cycle_groups'])==50 and first['group_states']==[]
        cursor=first['data']['next_cursor']
        sizes=[]
        while cursor:
            page=fetch(http,key,cursor=cursor)
            assert page['data']['total_count']==102 and page['data']['result_revision']==revision
            sizes.append(len(page['data']['items']))
            seen += [v['room_id'] for v in page['data']['items']]
            cursor=page['data']['next_cursor']
        assert sizes==[50,2] and len(set(seen))==102
        assert set(seen)=={str(rid),*map(str,cloned)}
        item=first['data']['items'][0]
        assert not {'game_items','leadership','permissions','beta_schedule','recruitment_identity'} & item.keys()
        assert item['view_detail_permission']['allowed'] is True
        legacy=fetch(http,key,params={k:v for k,v in PARAMS.items() if k!='response_profile'})
        assert 'total_count' not in legacy['data'] and 'result_revision' not in legacy['data']
        assert 'game_items' in legacy['data']['items'][0]
        # All 102 own actual-T targets are excluded before both count and pagination.
    with cycle_client(a) as http:
        assert fetch(http,key)['data']['total_count']==0
    with cycle_client(b) as http:
        empty=fetch(http,key,raid_ids=['nonexistent'])
        assert empty['data']['total_count']==0 and empty['data']['items']==[] and empty['data']['next_cursor'] is None
        assert empty['cycle_groups']==[] and empty['group_states']==[]
        for limit in (1,20,50):
            page=fetch(http,key,limit=limit)
            assert len(page['data']['items'])==limit and page['data']['total_count']==102
        for slot,expected in ([3],1),([4],101):
            assert fetch(http,key,remaining_slot_counts=slot)['data']['total_count']==expected
        benchmark(policy_db[0],http,key,capsys,monkeypatch)
        cursor=first['data']['next_cursor']
        bad=http.post('/v2/raid-rooms/search',params=PARAMS,json=body(key,cursor=cursor+'x'))
        assert bad.status_code==400
        changed=http.post('/v2/raid-rooms/search',params=PARAMS,json=body(key,limit=20,cursor=cursor))
        assert changed.status_code==409
        other=http.post('/v2/raid-rooms/search',params=PARAMS,json=body((date.fromisoformat(key)+timedelta(days=7)).isoformat(),cursor=cursor))
        assert other.status_code==400
        # Changes invalidate the continuation, not a mixed append.
        with session() as db,db.begin():cycles.touch_directory(db,date.fromisoformat(key))
        stale=http.post('/v2/raid-rooms/search',params=PARAMS,json=body(key,cursor=cursor))
        assert stale.status_code==409 and stale.json()['error']['code']=='CURSOR_STALE'


def test_profiles_group_labels_coordination_and_permission(policy_db,client):
    _,a,b=policy_db
    gid=group(client,a)
    add(client,a,b,gid)
    rid,key,_,_,_=create_beta(a,enabled=True)
    with cycle_client(b) as http:
        r=fetch(http,key)
        schedule=r['data']['items'][0]['schedule']
        assert schedule['coordination_progress']==dict(status='waiting_members',missing_members=1)
        assert schedule['coordination_state']=='coordinating'
        plain=fetch(http,key,params=dict(response_profile='discovery-1'))
        assert 'cycle_groups' not in plain and 'group_states' not in plain
        assert plain['data']['items'][0]['schedule'] is None
        off=fetch(http,key,params={**PARAMS,'include_group_state':'false'})
        assert 'cycle_groups' not in off and 'group_states' not in off
        for params in ({**PARAMS,'response_profile':''},{**PARAMS,'response_profile':'wrong'},
                       {**PARAMS,'include_coordination_wait':'true'}, {**PARAMS,'contract_profile':'wrong'}):
            assert http.post('/v2/raid-rooms/search',params=params,json=body(key)).status_code==400
        duplicate=[*PARAMS.items(),('response_profile','discovery-1')]
        assert http.post('/v2/raid-rooms/search',params=duplicate,json=body(key)).status_code==400
        assert http.get('/v2/raid-rooms',params=dict(target_cycle_key=key,response_profile='discovery-1')).status_code==400
        http.app.dependency_overrides[optional_principal]=lambda:None
        public=fetch(http,key)
        assert public['data']['items'][0]['view_detail_permission']==dict(allowed=False,reason='AUTH_REQUIRED',next_change_at=None)
    change(a,rid,key,gid)
    with cycle_client(b) as http:
        linked=fetch(http,key)
        assert linked['cycle_groups'][0]['group_id']==gid and linked['cycle_groups'][0]['state']=='known'
        assert linked['group_states'][0]['state']=='active' and linked['group_states'][0]['name']
        assert linked['data']['items'][0]['group_id']==gid


def test_count_and_page_share_snapshot_even_with_interleaved_write(policy_db,monkeypatch):
    _,a,b=policy_db;rid,key,_,_,_=create_beta(a)
    from app.raid_rooms.reads import cycle_card_batch
    original=cycle_card_batch.load
    def mutate(db,rows,uid):
        with session() as writer,writer.begin():
            writer.get(Room,rid).ended_at=db.scalar(select(__import__('sqlalchemy').func.now()))
            cycles.touch_directory(writer,date.fromisoformat(key))
        return original(db,rows,uid)
    monkeypatch.setattr(cycle_card_batch,'load',mutate)
    with cycle_client(b) as http:
        page=fetch(http,key)
        assert page['data']['total_count']==1 and page['data']['items'][0]['room_id']==str(rid)
        monkeypatch.setattr(cycle_card_batch,'load',original)
        assert fetch(http,key)['data']['total_count']==0


def test_clock_and_cursor_identity(policy_db,monkeypatch):
    _,a,b=policy_db;rid,key,base,_,_=create_beta(a,enabled=True)
    clones(rid,key,1)
    with cycle_client(b) as http:
        first=fetch(http,key,limit=1)
        cursor=first['data']['next_cursor'];assert cursor
        http.app.dependency_overrides[optional_principal]=lambda:actor(a['uid'])
        assert http.post('/v2/raid-rooms/search',params=PARAMS,json=body(key,limit=1,cursor=cursor)).status_code==400
        http.app.dependency_overrides[optional_principal]=lambda:actor(b['uid'])
        from app.raid_rooms.reads import queries
        monkeypatch.setattr(queries,'now',lambda db:base-timedelta(minutes=29))
        stale=http.post('/v2/raid-rooms/search',params=PARAMS,json=body(key,limit=1,cursor=cursor))
        assert stale.status_code==409
        newer=fetch(http,key,limit=1)
        assert newer['data']['result_revision']!=first['data']['result_revision']


@pytest.mark.parametrize('state,expected',[('coordinating','waiting_members'),('base_committed','not_applicable'),
    ('early_confirmed','not_applicable'),('base_confirmed','not_applicable'),('proposal_confirmed','not_applicable'),
    ('deadline_pending','not_applicable'),('needs_review','not_applicable'),('ended','not_applicable')])
def test_progress_state_null_contract(state,expected,monkeypatch):
    monkeypatch.setattr(discovery.beta_schedule,'display_state',lambda *args:dict(coordination_state=state))
    for count in (0,1,2,3,8):
        value=discovery.schedule(SimpleNamespace(early_enabled=True,early_additional_members=1),None,None,None,count)
        progress=value['coordination_progress']
        assert progress['status']==('coordinating' if state=='coordinating' and count>=2 else expected)
        assert progress['missing_members']==(2-count if state=='coordinating' and count<2 else None)
        dto.CoordinationProgress.model_validate(progress)
    with pytest.raises(ValidationError):dto.CoordinationProgress(status='coordinating',missing_members=0)


def benchmark(engine,http,key,capsys,monkeypatch):
    """Synthetic ASGI timing, warm repetitions; never production latency claims."""
    from sqlalchemy import event
    from time import perf_counter
    from statistics import median
    from math import ceil
    metrics=[];active={};last_count=[]
    def before(conn,cursor,statement,parameters,context,many):
        context._discovery_started=perf_counter()
    def after(conn,cursor,statement,parameters,context,many):
        elapsed=(perf_counter()-context._discovery_started)*1000
        active['sql_ms']=active.get('sql_ms',0)+elapsed
        active['sql_count']=active.get('sql_count',0)+1
        if 'count(*)' in statement and 'anon_1' in statement:
            active['count_ms']=active.get('count_ms',0)+elapsed
            last_count[:]=[statement,parameters]
    original_cards,original_render=discovery.cards,discovery.render
    def timed_cards(*args,**kwargs):
        start=perf_counter();value=original_cards(*args,**kwargs)
        active['projection_ms']=(perf_counter()-start)*1000
        return value
    def timed_render(*args,**kwargs):
        start=perf_counter();value=original_render(*args,**kwargs)
        active['render_ms']=(perf_counter()-start)*1000
        return value
    monkeypatch.setattr(discovery,'cards',timed_cards);monkeypatch.setattr(discovery,'render',timed_render)
    event.listen(engine,'before_cursor_execute',before);event.listen(engine,'after_cursor_execute',after)
    try:
        for label,params,extra in [('legacy20',{k:v for k,v in PARAMS.items() if k!='response_profile'},dict(limit=20)),
                ('discovery20',PARAMS,dict(limit=20)),('discovery50',PARAMS,dict(limit=50)),
                ('empty50',PARAMS,dict(limit=50,raid_ids=['nonexistent'])),
                ('slots50',PARAMS,dict(limit=50,remaining_slot_counts=[3]))]:
            samples=[]
            for index in range(11):
                active.clear();start=perf_counter()
                response=http.post('/v2/raid-rooms/search',params=params,json=body(key,**extra))
                elapsed=(perf_counter()-start)*1000
                assert response.status_code==200,response.text
                if index:samples.append(dict(active,total_ms=elapsed,bytes=len(response.content)))
            entry=dict(case=label,n=10)
            for field in ('total_ms','sql_ms','sql_count','count_ms','projection_ms','render_ms','bytes'):
                vals=sorted(sample.get(field,0) for sample in samples)
                entry[field]=dict(p50=round(median(vals),3),p95=round(vals[ceil(.95*len(vals))-1],3))
            metrics.append(entry)
    finally:
        event.remove(engine,'before_cursor_execute',before);event.remove(engine,'after_cursor_execute',after)
        monkeypatch.setattr(discovery,'cards',original_cards);monkeypatch.setattr(discovery,'render',original_render)
    plan=None
    if last_count:
        with engine.connect() as conn:
            explain=conn.exec_driver_sql('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+last_count[0],last_count[1]).scalar_one()[0]
            plan=dict(planning_ms=explain['Planning Time'],execution_ms=explain['Execution Time'],
                shared_hit_blocks=explain['Plan'].get('Shared Hit Blocks'),shared_read_blocks=explain['Plan'].get('Shared Read Blocks'))
    with capsys.disabled():
        print('DISCOVERY_BENCHMARK '+json.dumps(dict(fixture='102 synthetic public targets, 1 beta target/101 minimal legacy graphs, one live assignment lease; ASGI TestClient, no external network',
            warmup=1,samples=metrics,last_count_explain=plan)),flush=True)


def test_discovery_candidate_validation_precedes_count(group_candidates):
    from tests.groups.test_group_character_candidates import page, search
    from app.game_accounts.common.support import GameError
    _,a,_,gid=group_candidates
    first=page(a,gid,limit=1);whole=page(a,gid)
    member=whole['groups'][-1];cid=member['characters'][-1]['character_id']
    req=search(a,gid,first,member,[cid])
    response=cycle_queries.search(actor(a['uid']),req,response_profile=dto.PROFILE)
    assert response['data']['total_count']==0 and response['data']['items']==[]
    for changes,code in [(dict(group_character_candidates_token='0'*64),'GROUP_CHARACTER_CANDIDATES_STALE'),
                         (dict(member_conditions=[dict(member_ref=member['member_ref'],character_ids=[str(uuid.uuid4())])]),'INVALID_REQUEST')]:
        data=cycle_schemas.Search.model_validate(req.model_dump(mode='json',exclude_unset=True) | changes)
        with pytest.raises(GameError) as error:cycle_queries.search(actor(a['uid']),data,response_profile=dto.PROFILE)
        assert error.value.code==code
    from app.groups.models import Group
    with session() as db,db.begin():db.get(Group,gid).members_revision+=1
    with pytest.raises(GameError) as error:cycle_queries.search(actor(a['uid']),req,response_profile=dto.PROFILE)
    assert error.value.code=='FILTER_CONTEXT_STALE'
