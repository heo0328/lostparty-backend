"""Personal correction and service archive against disposable restricted PostgreSQL."""
import os, subprocess, uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, text, inspect, func
from sqlalchemy.exc import DBAPIError
from app.core.database import session, now
from app.raid_rooms import completion_correction as service, completion_correction_schemas as schema
from app.raid_rooms import completed_room_lifecycle as archive, cycle_lists as lists, cycle_queries as directory
from app.raid_rooms.completion_correction_models import CompletionCorrection
from app.raid_weekly.models import WeeklyState
from app.game_accounts.models import Character, Account
from tests.test_recruitment_cycle_outcomes import (
    outcomes, planning, consent, lifecycle, candidate, ready, sources, imported, people, worlds,
    scheduled, plan, actor, complete, add_member, fingerprints, denied, cycles, life, graph, commands,
    RoomCycle, CycleMember, CycleGeneration, Assignment, cancel_member,
)
from tests.test_recruitment_cycle_times_http import client
from tests.test_raid_room_migrations import table_digests

@pytest.fixture
def corrected(outcomes):
    engine,a,b=outcomes
    tables=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0030_completion_corrections'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-1800:]
    assert table_digests(engine,tables)==before
    from app.raid_rooms import readiness
    with session() as db,db.begin():readiness.require_two_cycle_active(db)
    return engine,a,b

def target(w,rid,c):
    data=plan(w,rid,c)['data'];a=next(x for x in data['my_assignments'] if x['round_id']==data['game_items'][0]['round_id'])
    with session() as db,db.begin():item=db.get(graph.graph.Item,uuid.UUID(a['item_id']));raid=item.raid_id
    return uuid.UUID(a['character_id']),raid

def request(w,cid,raid,c):
    value=service.context(actor(w['uid']),cid,raid,c)
    d=value['data'];return schema.CorrectionCommand.model_validate(dict(target_cycle_key=c,
        expected_cycle_key=value['current_cycle_key'],expected_weekly_revision=d['weekly_revision'],
        expected_ownership_revision=d['ownership_revision'],expected_lifecycle_revision=d['lifecycle_revision'],
        correction_context_token=d['confirmation']['context_token']))

def seed(w,cid,raid,key,kind):
    from app.raid_weekly.service import parse_cycle
    with session() as db,db.begin():
        row=db.get(WeeklyState,(w['uid'],cid,raid,parse_cycle(key)))
        if row is None:row=WeeklyState(user_id=w['uid'],character_id=cid,raid_id=raid,cycle_key=parse_cycle(key),revision=1,updated_at=now(db));db.add(row)
        if kind in ('manual','both'):row.manual_completed_at=now(db);row.manual_difficulty_id='test-manual'
        if kind in ('party','both'):row.party_completed_at=now(db);row.completed_party_id=uuid.uuid4();row.party_difficulty_id='test-party'
        row.revision+=1

@pytest.mark.parametrize('kind',['manual','party','both'])
def test_clear_all_sources_immutable_audit_and_no_participation_restore(corrected,kind):
    engine,a,b=corrected;rid,c,n=scheduled(a);complete(a,rid,c,index=0)
    cid,raid=target(a,rid,c)
    with session() as db,db.begin():
        row=db.get(WeeklyState,(a['uid'],cid,raid,__import__('datetime').date.fromisoformat(c)))
        row.manual_completed_at=row.manual_difficulty_id=None
    seed(a,cid,raid,c,kind)
    before=plan(a,rid,c)['data']['my_assignments'];body=request(a,cid,raid,c);key=uuid.uuid4()
    status,result=service.execute(actor(a['uid']),cid,raid,key,body)
    assert status==200 and result['data']['completion_sources']==[]
    assert result['data']['weekly_revision']==body.expected_weekly_revision+1
    assert plan(a,rid,c)['data']['my_assignments']==before
    after=fingerprints(engine);assert service.execute(actor(a['uid']),cid,raid,key,body)==(status,result)
    assert fingerprints(engine)==after
    with session() as db,db.begin():
        audit=db.get(CompletionCorrection,uuid.UUID(result['data']['correction_id']))
        assert len(audit.sources)==(2 if kind=='both' else 1)
    with pytest.raises(DBAPIError),session() as db,db.begin():db.execute(text('UPDATE raid_completion_corrections SET after_revision=after_revision WHERE id=:id'),dict(id=result['data']['correction_id']))

@pytest.mark.parametrize('historical',[False,True])
def test_anytime_correction_including_before_ten_and_past_inactive(corrected,monkeypatch,historical):
    engine,a,b=corrected;rid,c,n=scheduled(a);cid,raid=target(a,rid,c)
    from app.raid_weekly.service import parse_cycle
    # Use a separate historic source so existing active lease invariants remain real.
    old=(parse_cycle(c)-timedelta(days=7)).isoformat()
    if historical:seed(a,cid,raid,old,'both')
    else:
        complete(a,rid,c);old=c
        stamp=__import__('datetime').datetime.combine(parse_cycle(c),__import__('datetime').time(0),__import__('datetime').timezone.utc)
        with session() as db,db.begin():
            db.get(WeeklyState,(a['uid'],cid,raid,parse_cycle(c))).manual_completed_at=stamp-timedelta(minutes=5)
        monkeypatch.setattr(cycles,'now',lambda db:stamp)
        monkeypatch.setattr(commands.base,'now',lambda db:stamp)
    with session() as db,db.begin():db.get(Character,cid).lifecycle_state='retired'
    body=request(a,cid,raid,old);assert service.execute(actor(a['uid']),cid,raid,uuid.uuid4(),body)[0]==200

@pytest.mark.parametrize('case',['empty','foreign','future','tamper','revision','expired','audit_failure'])
def test_denials_readonly_and_atomic_rollback(corrected,monkeypatch,case):
    engine,a,b=corrected;rid,c,n=scheduled(a);cid,raid=target(a,rid,c)
    if case=='empty':
        before=fingerprints(engine);value=service.context(actor(a['uid']),cid,raid,c)
        assert value['data']['confirmation'] is None and not value['data']['permission']['allowed']
        assert fingerprints(engine)==before;return
    complete(a,rid,c);body=request(a,cid,raid,c)
    before=fingerprints(engine)
    if case=='foreign':denied('CHARACTER_NOT_FOUND',service.context,actor(b['uid']),cid,raid,c)
    elif case=='future':denied('INVALID_REQUEST',service.context,actor(a['uid']),cid,raid,n)
    elif case=='tamper':denied('CONTEXT_INVALID',service.execute,actor(a['uid']),cid,raid,uuid.uuid4(),body.model_copy(update={'correction_context_token':'invalid'}))
    elif case=='revision':denied('REVISION_CONFLICT',service.execute,actor(a['uid']),cid,raid,uuid.uuid4(),body.model_copy(update={'expected_weekly_revision':1}))
    elif case=='expired':
        real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(seconds=121))
        denied('COMMAND_CONTEXT_EXPIRED',service.execute,actor(a['uid']),cid,raid,uuid.uuid4(),body)
    elif case=='audit_failure':
        monkeypatch.setattr(service,'CompletionCorrection',lambda **kwargs:(_ for _ in ()).throw(RuntimeError('synthetic audit failure')))
        with pytest.raises(RuntimeError):service.execute(actor(a['uid']),cid,raid,uuid.uuid4(),body)
    assert fingerprints(engine)==before

@pytest.mark.parametrize('keep_n',[False,True])
def test_archive_all_items_not_zero_members_preserves_n_and_record_routes(corrected,keep_n):
    engine,a,b=corrected;rid,c,n=scheduled(a)
    if not keep_n:cancel_member(a,rid,n)
    complete(a,rid,c)
    with session() as db:assert not archive.is_archived(db,rid)
    complete(a,rid,c,index=1)
    with session() as db:assert archive.is_archived(db,rid)==(not keep_n)
    assert lists.memberships(actor(a['uid']),c,'current')['data']['items']==[]
    assert lists.memberships(actor(a['uid']),c,'ended')['data']['items']
    assert lists.memberships(actor(a['uid']),c,'all')['data']['items']
    value=plan(a,rid,c)
    assert value['data']['target_state']=='completed'
    if keep_n:
        assert lists.memberships(actor(a['uid']),n,'current')['data']['items']
        assert plan(a,rid,n)['data']['target_state']=='open'
    else:
        denied('ROOM_NOT_FOUND',directory.get_card,actor(a['uid']),rid,c)
        from app.raid_rooms import cycle_opening
        denied('ROOM_NOT_ACTIVE',cycle_opening.get,actor(a['uid']),rid,n,'reopen')
        from app.raid_rooms import cycle_member_reads
        detail=cycle_member_reads.detail(actor(a['uid']),rid,c)
        assert detail['data']['room']['state']=='ended' and detail['data']['room']['phase']=='ended'
        assert all(not p['allowed'] and p['reason']=='ROOM_NOT_ACTIVE' for p in value['data']['permissions'].values())
        assert all(not p['allowed'] for p in detail['data']['settings']['permissions'].values())
        cid,raid=target(a,rid,c);body=request(a,cid,raid,c)
        service.execute(actor(a['uid']),cid,raid,uuid.uuid4(),body)
        with session() as db:assert archive.is_archived(db,rid)


def test_http_new_context_command_closed_dto_and_original_ack(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);complete(a,rid,c);cid,raid=target(a,rid,c)
    path=f'/v2/me/characters/{cid}/raid-weekly-states/{raid}'
    with client(a) as http:
        before=fingerprints(engine)
        value=http.get(path+'/completion-correction-context',params={'target_cycle_key':c})
        assert value.status_code==200,value.json();schema.CorrectionContext.model_validate(value.json())
        assert fingerprints(engine)==before and value.headers['cache-control']=='no-store'
        assert http.get(path+'/completion-correction-context',params=[('target_cycle_key',c),('target_cycle_key',c)]).status_code==400
        body=request(a,cid,raid,c).model_dump(mode='json');headers={'Idempotency-Key':str(uuid.uuid4())}
        assert http.post(path+'/completion-corrections',headers=headers,json=body|{'unexpected':True}).status_code==400
        result=http.post(path+'/completion-corrections',headers=headers,json=body)
        assert result.status_code==200,result.json();schema.CorrectionResult.model_validate(result.json())
        assert http.post(path+'/completion-corrections',headers=headers,json=body).json()==result.json()


def test_same_command_concurrent_once_and_other_member_preserved(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);complete(a,rid,c,'complete_item')
    cid,raid=target(a,rid,c);body=request(a,cid,raid,c);command=uuid.uuid4()
    def call(_):
        from app.game_accounts.support import GameError
        try:return service.execute(actor(a['uid']),cid,raid,command,body)
        except GameError as e:
            assert e.code=='REQUEST_IN_PROGRESS'
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(call,range(2)))
    result=service.execute(actor(a['uid']),cid,raid,command,body)
    assert any(results) and all(x is None or x==result for x in results)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(CompletionCorrection))==1
        assert db.scalar(select(WeeklyState.party_completed_at).where(WeeklyState.user_id==b['uid'],WeeklyState.raid_id==raid)) is not None


def export(name,value):
    import json
    from pathlib import Path
    p=Path('/tmp/completion-correction-wire-examples.json')
    def clean(v):
        if isinstance(v,dict):return {k:('<opaque-redacted>' if k in ('context_token','correction_context_token') else clean(x)) for k,x in v.items()}
        if isinstance(v,list):return [clean(x) for x in v]
        return v
    values=json.loads(p.read_text()) if p.exists() else {}
    values[name]=clean(value);p.write_text(json.dumps(values,indent=2,ensure_ascii=False))


def test_explicit_review_unknown_generation_nullable_wire_and_no_fake_card(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a)
    from datetime import date
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        cm=life.actual_member(db,row,a['uid']);cm.state='review_required';row.state='review_required'
        db.get(CycleGeneration,(row.id,row.generation)).state='review_required'
    explicit=lists.memberships(actor(a['uid']),n,'current')
    assert explicit['data']['items'][0]['room']['target_state']=='review_required'
    assert explicit['data']['items'][0]['target_generation']==1
    export('explicit_generation_review_membership',explicit)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        mid=db.scalar(select(CycleMember.membership_id).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation))
        row.state='review_required';row.provenance='legacy_unknown';row.generation=None;row.settings_snapshot=None
        cm=CycleMember(id=uuid.uuid4(),room_id=rid,cycle_id=row.id,generation=None,membership_id=mid,
            user_id=a['uid'],state='review_required',revision=1,joined_order=None,joined_at=None,ended_at=None)
        db.add(cm)
    value=lists.memberships(actor(a['uid']),n,'current');item=value['data']['items'][0]
    assert item['room'] is None and item['target_generation'] is None
    assert item['room_cycle_id'] and item['cycle_member_id'] and item['cycle_member_revision']==1
    assert item['target_participation_state']=='review_required' and item['recovery_only']
    assert item['target_role']=='none' and item['joined_order'] is None and item['assignments']==[]
    assert not item['permissions']['view_plan']['allowed']
    export('explicit_unknown_generation_review_membership',value)


def test_new_wire_examples_ready_empty_command_result_and_archived_record(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);cancel_member(a,rid,n)
    cid,raid=target(a,rid,c)
    export('no_completion_context',service.context(actor(a['uid']),cid,raid,c))
    complete(a,rid,c);complete(a,rid,c,index=1)
    cid,raid=target(a,rid,c)
    export('ready_context',service.context(actor(a['uid']),cid,raid,c))
    body=request(a,cid,raid,c);export('correction_command',body.model_dump(mode='json'))
    export('archived_member_plan',plan(a,rid,c))
    from app.raid_rooms import cycle_member_reads
    export('archived_member_detail',cycle_member_reads.detail(actor(a['uid']),rid,c))
    export('correction_result',service.execute(actor(a['uid']),cid,raid,uuid.uuid4(),body)[1])

@pytest.mark.parametrize('case',['final_expiry','final_rollover','ownership','lifecycle','source','other_body'])
def test_final_boundaries_identity_and_source_cas(corrected,monkeypatch,case):
    engine,a,b=corrected;rid,c,n=scheduled(a);complete(a,rid,c);cid,raid=target(a,rid,c)
    body=request(a,cid,raid,c);key=uuid.uuid4()
    if case=='other_body':
        service.execute(actor(a['uid']),cid,raid,key,body)
        denied('IDEMPOTENCY_CONFLICT',service.execute,actor(a['uid']),cid,raid,key,body.model_copy(update={'expected_weekly_revision':1}));return
    if case in ('ownership','lifecycle','source'):
        with session() as db,db.begin():
            if case=='ownership':db.get(Account,db.get(Character,cid).account_id).ownership_revision+=1
            elif case=='lifecycle':db.get(Character,cid).lifecycle_revision+=1
            else:
                from datetime import date
                row=db.get(WeeklyState,(a['uid'],cid,raid,date.fromisoformat(c)))
                row.manual_completed_at=row.manual_completed_at+timedelta(seconds=1)
        expected='COMPLETION_CONTEXT_CHANGED' if case=='source' else 'REVISION_CONFLICT'
    else:
        clock=cycles.now;calls=[]
        with session() as db:stamp=now(db)
        limit=commands.raids.cycle(stamp).ends_at if case=='final_rollover' else stamp+timedelta(seconds=121)
        def final_clock(db):calls.append(1);return clock(db) if len(calls)==1 else limit
        monkeypatch.setattr(cycles,'now',final_clock)
        expected='CYCLE_CHANGED' if case=='final_rollover' else 'COMMAND_CONTEXT_EXPIRED'
    before=fingerprints(engine)
    denied(expected,service.execute,actor(a['uid']),cid,raid,key,body)
    assert fingerprints(engine)==before


def test_actual_synthetic_bearer_revoked_session_no_store_and_request_limit(corrected):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    from app.auth.models import Session
    engine,a,b=corrected;rid,c,n=scheduled(a);complete(a,rid,c);cid,raid=target(a,rid,c)
    app=FastAPI();register(app);app.include_router(router);app.middleware('http')(no_store)
    path=f'/v2/me/characters/{cid}/raid-weekly-states/{raid}'
    with TestClient(app,raise_server_exceptions=False) as http:
        for headers in ({},{'Authorization':'Bearer invalid'}):
            r=http.get(path+'/completion-correction-context',params={'target_cycle_key':c},headers=headers)
            assert r.status_code==401 and r.headers['cache-control']=='no-store'
        r=http.get(path+'/completion-correction-context',params={'target_cycle_key':c},headers=a['headers'])
        assert r.status_code==200 and r.json()['data']['confirmation']
        assert http.get(path+'/completion-correction-context',params={'target_cycle_key':c},headers=b['headers']).status_code in (403,404)
        body=request(a,cid,raid,c).model_dump(mode='json');headers=dict(a['headers'])|{'Idempotency-Key':str(uuid.uuid4())}
        assert http.post(path+'/completion-corrections',headers=headers,content=' '*32769).status_code==413
        r=http.post(path+'/completion-corrections',headers=headers,json=body)
        assert r.status_code==200 and r.headers['cache-control']=='no-store'
        with session() as db,db.begin():db.scalar(select(Session).where(Session.user_id==a['uid'])).revoked_at=now(db)
        assert http.post(path+'/completion-corrections',headers=headers,json=body).status_code==401


def test_completed_archive_blocks_new_write_but_old_ack_and_new_completion_survive(corrected,monkeypatch):
    engine,a,b=corrected;rid,c,n=scheduled(a);cancel_member(a,rid,n)
    # Capture original completion command for replay after service archive.
    from tests.test_recruitment_cycle_outcomes import context,outcome_body
    from app.raid_rooms import cycle_outcomes
    first=context(a,rid,c);command=uuid.uuid4();body=outcome_body(first)
    original=cycle_outcomes.execute(actor(a['uid']),None,uuid.UUID(first['data']['target_round_id']),command,body,'personal_completion')
    complete(a,rid,c,index=1)
    assert cycle_outcomes.execute(actor(a['uid']),None,uuid.UUID(first['data']['target_round_id']),command,body,'personal_completion')==original
    with session() as db:denied('ROOM_NOT_ACTIVE',archive.require_active,db,rid)
    cid,raid=target(a,rid,c);data=request(a,cid,raid,c);key=uuid.uuid4()
    result=service.execute(actor(a['uid']),cid,raid,key,data)
    seed(a,cid,raid,c,'party')
    before=fingerprints(engine)
    assert service.execute(actor(a['uid']),cid,raid,key,data)==result
    assert fingerprints(engine)==before
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=14))
    assert service.execute(actor(a['uid']),cid,raid,key,data)==result
