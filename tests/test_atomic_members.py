"""Atomic #22/#23 effects and failure boundaries on disposable PostgreSQL."""
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import select
from app.core.database import session
from app.raid_rooms import atomic_members as service, atomic_member_schemas as schema
from tests.test_completion_corrections import corrected
from tests.test_recruitment_cycle_outcomes import (
    outcomes,planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,plan,actor,add_member,complete,fingerprints,denied,commands,cycles,life,graph,
    RoomCycle,CycleMember,CycleGeneration,Assignment,cancel_member,
)
from tests.test_recruitment_cycle_times_http import client


def departure(w,rid,c,index=0):
    round_id=uuid.UUID(plan(w,rid,c)['data']['game_items'][index]['round_id'])
    return service.get(actor(w['uid']),rid,c,round_id=round_id)


def depart_body(value):
    s=value['scope'];d=value['data'];m=d['subject']
    return schema.DepartureCommand.model_validate(dict(expected_cycle_key=s['current_cycle_key'],target_cycle_key=s['target_cycle_key'],
        room_cycle_id=s['room_cycle_id'],target_generation=s['target_generation'],expected_target_revision=s['target_revision'],
        actor_cycle_member_id=m['cycle_member_id'],expected_cycle_member_revision=m['cycle_member_revision'],
        round_id=m['round_id'],context_token=d['confirmation']['context_token']))


def member(w,rid,c):
    with session() as db:
        _,row=cycles.resolve(db,rid,c,commands.base.now(db))
        return life.actual_member(db,row,w['uid'],states=('participating','review_required')).id


def removal(a,b,rid,c):return service.get(actor(a['uid']),rid,c,cmid=member(b,rid,c))


def removal_body(value,mode='current_only'):
    s=value['scope'];d=value['data'];m=d['source']
    return schema.RemovalCommand.model_validate(dict(expected_cycle_key=s['current_cycle_key'],target_cycle_key=s['target_cycle_key'],
        room_cycle_id=s['room_cycle_id'],target_generation=s['target_generation'],expected_target_revision=s['target_revision'],
        target_membership_id=d['target_membership_id'],target_cycle_member_id=m['target_cycle_member_id'],
        expected_target_cycle_member_revision=m['target_cycle_member_revision'],mode=mode,
        context_token=d['options'][mode]['confirmation']['context_token']))


def cycle_hash(db,row):
    return service.encoded([service.cycle_proof(db,row),[service.bundle(db,row,m)[2] for m in db.scalars(select(CycleMember).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.state=='participating').order_by(CycleMember.id))]])


@pytest.mark.parametrize('leader',[False,True])
def test_departure_one_complete_rest_cancel_successor_preserve_n_ack(corrected,leader,monkeypatch):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    w=a if leader else b
    before_n={k:v for k,v in plan(a,rid,n)['data'].items() if k not in ('server_time','permissions')};before=fingerprints(engine)
    value=departure(w,rid,c);assert fingerprints(engine)==before
    repeat=departure(w,rid,c)
    assert value['data']['display']==repeat['data']['display']
    assert value['data']['impact']['departure_effect']==('automatic_successor' if leader else 'leave')
    disp=value['data']['display']['assignments']
    assert sorted(x['effect'] for x in disp)==['cancel','complete']
    assert all(x['raid_name'] and x['difficulty_name'] for x in disp)
    body=depart_body(value);key=uuid.uuid4();result=service.execute(actor(w['uid']),rid,key,body,departure=True)
    assert result[0]==200;effect=result[1]['data']['effects'][0]
    assert effect['state']=='cancelled' and len(effect['completed_assignment_ids'])==len(effect['cancelled_assignment_ids'])==1
    assert plan(a if not leader else b,rid,c)['data']['leadership']['leader_cycle_member_id']==str(member(a if not leader else b,rid,c))
    assert {k:v for k,v in plan(a,rid,n)['data'].items() if k not in ('server_time','permissions')}==before_n
    before=fingerprints(engine)
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=7))
    assert service.execute(actor(w['uid']),rid,key,body,departure=True)==result
    assert fingerprints(engine)==before


@pytest.mark.parametrize('completed',[False,True])
def test_last_member_close_with_null_leader_and_completed_preserved(corrected,completed):
    engine,a,b=corrected;rid,c,n=scheduled(a)
    if completed:complete(a,rid,c,index=1)
    before_n={k:v for k,v in plan(a,rid,n)['data'].items() if k not in ('server_time','permissions')};value=departure(a,rid,c)
    assert value['data']['impact']['departure_effect']==('close_completed' if completed else 'close_incomplete')
    result=service.execute(actor(a['uid']),rid,uuid.uuid4(),depart_body(value),departure=True)[1]
    e=result['data']['effects'][0]
    assert e['leadership']['leader_cycle_member_id'] is None and e['leadership']['leader_membership_id'] is None
    assert {k:v for k,v in plan(a,rid,n)['data'].items() if k not in ('server_time','permissions')}==before_n
    with session() as db:
        row=db.get(RoomCycle,uuid.UUID(e['room_cycle_id']));gen=db.get(CycleGeneration,(row.id,row.generation))
        assert row.state=='closed' and gen.state==('completed' if completed else 'cancelled')
        assert commands.leadership(db,row)['leader_cycle_member_id'] is None
        from app.raid_rooms import cycle_card_batch
        assert cycle_card_batch.load(db,[row],a['uid'])[row.id]['leadership']['leader_cycle_member_id'] is None
        assert db.get(life.Member,uuid.UUID(result['data']['subject_membership_id'])).ended_at is None


def test_successor_unavailable_no_partial_completion(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    with session() as db,db.begin():db.get(CycleMember,member(b,rid,c)).state='review_required'
    before=fingerprints(engine);value=departure(a,rid,c)
    assert value['data']['permission']['reason']=='SUCCESSOR_UNAVAILABLE' and value['data']['confirmation'] is None
    assert fingerprints(engine)==before


@pytest.mark.parametrize('mode',['current_only','both'])
def test_removal_modes_preserve_other_cycle_and_completed(corrected,mode):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n);complete(b,rid,c,index=1)
    with session() as db:
        _,nr=cycles.resolve(db,rid,n,commands.base.now(db));before_n=cycle_hash(db,nr)
    before=fingerprints(engine);value=removal(a,b,rid,c);assert fingerprints(engine)==before
    assert value['data']['opposite_relation']['status']=='participating'
    body=removal_body(value,mode);key=uuid.uuid4();result=service.execute(actor(a['uid']),rid,key,body)
    assert len(result[1]['data']['effects'])==(2 if mode=='both' else 1)
    assert result[1]['data']['effects'][0]['preserved_completed_assignment_ids']
    with session() as db:
        _,nr=cycles.resolve(db,rid,n,commands.base.now(db))
        if mode=='current_only':assert cycle_hash(db,nr)==before_n
    before=fingerprints(engine);assert service.execute(actor(a['uid']),rid,key,body)==result
    assert fingerprints(engine)==before


@pytest.mark.parametrize('review',['member','cycle','badlease','unknown'])
def test_source_review_cleanup_boundaries(corrected,review):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);cmid=member(b,rid,c)
    with session() as db,db.begin():
        cm=db.get(CycleMember,cmid);row=db.get(RoomCycle,cm.cycle_id)
        if review=='member':cm.state='review_required'
        elif review=='cycle':row.state='review_required'
        elif review=='unknown':row.state='review_required';row.provenance='legacy_unknown'
        else:
            a1=life.assignments(db,row,cm)[0];item=db.get(graph.graph.Item,a1.item_id)
            db.delete(db.get(life.WeeklyOccupancy,(cm.user_id,a1.character_id,item.raid_id,row.cycle_key)))
    before=fingerprints(engine)
    if review=='unknown':denied('ROOM_REVIEW_REQUIRED',service.get,actor(a['uid']),rid,c,cmid=cmid);return
    value=service.get(actor(a['uid']),rid,c,cmid=cmid)
    assert fingerprints(engine)==before
    if review=='badlease':
        assert value['data']['options']['current_only']['permission']['reason']=='ROOM_REVIEW_REQUIRED';return
    assert value['data']['options']['current_only']['permission']['allowed']
    assert not value['data']['options']['both']['permission']['allowed']
    assert service.execute(actor(a['uid']),rid,uuid.uuid4(),removal_body(value))[0]==200


@pytest.mark.parametrize('case',['stale','expired','tamper','second_failure','audit_failure'])
def test_atomic_failures_rollback_both_and_personal(corrected,monkeypatch,case):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    value=removal(a,b,rid,c);body=removal_body(value,'both')
    if case=='stale':
        with session() as db,db.begin():db.get(CycleMember,member(b,rid,n)).revision+=1
    before=fingerprints(engine)
    if case=='stale':denied('TARGET_CONTEXT_STALE',service.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    elif case=='expired':
        real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(seconds=121))
        denied('COMMAND_CONTEXT_EXPIRED',service.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    elif case=='tamper':denied('CONTEXT_INVALID',service.execute,actor(a['uid']),rid,uuid.uuid4(),body.model_copy(update={'context_token':'bad'}))
    else:
        old=service.cleanup;calls=[]
        def injected(*args,**kwargs):
            calls.append(1)
            if len(calls)==2:raise RuntimeError('synthetic second target failure')
            return old(*args,**kwargs)
        if case=='second_failure':monkeypatch.setattr(service,'cleanup',injected)
        else:monkeypatch.setattr(life,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('synthetic audit failure')))
        with pytest.raises(RuntimeError):service.execute(actor(a['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(engine)==before


def test_current_only_token_ignores_unrelated_opposite_change(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    body=removal_body(removal(a,b,rid,c))
    with session() as db,db.begin():db.get(CycleMember,member(b,rid,n)).revision+=1
    assert service.execute(actor(a['uid']),rid,uuid.uuid4(),body)[0]==200


def test_http_closed_queries_and_dedicated_ack(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a)
    rd=plan(a,rid,c)['data']['game_items'][0]['round_id'];path=f'/v2/raid-rooms/{rid}/personal-completion-departure'
    with client(a) as http:
        value=http.get(path+'-context',params=dict(target_cycle_key=c,round_id=rd))
        assert value.status_code==200,value.text
        assert value.headers['cache-control']=='no-store'
        body=depart_body(value.json()).model_dump(mode='json');key=str(uuid.uuid4())
        bad=http.post(path+'s',json={**body,'extra':True},headers={'Idempotency-Key':key});assert bad.status_code==400
        result=http.post(path+'s',json=body,headers={'Idempotency-Key':key})
        assert result.status_code==200,result.text
        assert http.post(path+'s',json=body,headers={'Idempotency-Key':key}).json()==result.json()
        assert http.get(path+'-context',params=[('target_cycle_key',c),('target_cycle_key',c),('round_id',rd)]).status_code==400

@pytest.mark.parametrize('opposite',['none','no_actor','review','no_authority','target_leader'])
def test_opposite_relationship_permissions(corrected,opposite):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    if opposite!='none':add_member(b,rid,n)
    if opposite in ('no_actor','no_authority','target_leader','review'):
        with session() as db,db.begin():
            _,row=cycles.resolve(db,rid,n,commands.base.now(db))
            if opposite=='review':db.get(CycleMember,member(b,rid,n)).state='review_required'
            elif opposite=='no_actor':db.get(CycleMember,member(a,rid,n)).state='review_required'
            else:db.get(CycleGeneration,(row.id,row.generation)).leader_cycle_member_id=member(b,rid,n)
    value=removal(a,b,rid,c);d=value['data']
    assert d['options']['current_only']['permission']['allowed']
    assert not d['options']['both']['permission']['allowed']
    reason=d['options']['both']['permission']['reason']
    assert reason==('OTHER_TARGET_NOT_PARTICIPATING' if opposite=='none' else 'ROOM_REVIEW_REQUIRED' if opposite=='review' else 'TARGET_LEADER_REQUIRED')
    if opposite in ('none','no_actor','review'):assert d['opposite_relation']['target'] is None


@pytest.mark.parametrize('change',['ownership','display','week','expiry','audit'])
def test_departure_stale_final_boundary_and_rollback(corrected,monkeypatch,change):
    engine,a,b=corrected;rid,c,n=scheduled(a);value=departure(a,rid,c);body=depart_body(value)
    if change in ('ownership','display'):
        with session() as db,db.begin():
            cm=db.get(CycleMember,body.actor_cycle_member_id);row=db.get(RoomCycle,cm.cycle_id)
            assignment=life.assignments(db,row,cm)[0]
            if change=='ownership':
                from app.game_accounts.models import Character,Account
                char=db.get(Character,assignment.character_id);db.get(Account,char.account_id).ownership_revision+=1
            else:assignment.display={**assignment.display,'character_name':'changed synthetic display'}
    before=fingerprints(engine)
    if change=='ownership':
        denied('OWNERSHIP_REQUIRED',service.execute,actor(a['uid']),rid,uuid.uuid4(),body,departure=True)
    elif change=='display':denied('TARGET_CONTEXT_STALE',service.execute,actor(a['uid']),rid,uuid.uuid4(),body,departure=True)
    else:
        if change=='audit':
            monkeypatch.setattr(service.outcomes,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('synthetic completion audit failure')))
            with pytest.raises(RuntimeError):service.execute(actor(a['uid']),rid,uuid.uuid4(),body,departure=True)
        else:
            real=cycles.now;calls=[]
            def late(db):
                calls.append(1);stamp=real(db)
                return stamp if len(calls)==1 else stamp+timedelta(days=7) if change=='week' else stamp+timedelta(seconds=121)
            monkeypatch.setattr(cycles,'now',late)
            denied('CYCLE_CHANGED' if change=='week' else 'COMMAND_CONTEXT_EXPIRED',service.execute,actor(a['uid']),rid,uuid.uuid4(),body,departure=True)
    assert fingerprints(engine)==before


@pytest.fixture(autouse=True)
def capture_contract_examples(request,monkeypatch):
    import json
    from pathlib import Path
    values=[]
    def validate(value):
        import jsonschema
        model=schema.ActionResult if value['data'].get('outcome')=='applied' else schema.DepartureContext if value['data']['action']=='personal_completion_departure' else schema.RemovalContext
        jsonschema.validate(value,model.model_json_schema())
    original_get=service.get;original_execute=service.execute
    def capture_get(*args,**kwargs):
        value=original_get(*args,**kwargs);validate(value);values.append(value);return value
    def capture_execute(*args,**kwargs):
        value=original_execute(*args,**kwargs);validate(value[1]);values.append(value[1]);return value
    monkeypatch.setattr(service,'get',capture_get);monkeypatch.setattr(service,'execute',capture_execute)
    yield
    def redacted(value):
        if isinstance(value,dict):return {k:'<opaque-redacted>' if k=='context_token' else redacted(v) for k,v in value.items()}
        if isinstance(value,list):return [redacted(v) for v in value]
        return value
    folder=Path('/tmp/atomic-contract-examples');folder.mkdir(exist_ok=True)
    (folder/(request.node.name+'.json')).write_text(json.dumps(redacted(values),ensure_ascii=False,indent=2))


def test_opposite_unknown_generation_is_review_not_absent(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    with session() as db,db.begin():
        source=db.get(CycleMember,member(b,rid,c));_,other=cycles.resolve(db,rid,n,commands.base.now(db))
        db.add(CycleMember(id=uuid.uuid4(),room_id=rid,cycle_id=other.id,generation=None,membership_id=source.membership_id,
            user_id=b['uid'],state='review_required',revision=1,joined_order=None,joined_at=None,ended_at=None))
    value=removal(a,b,rid,c)['data']
    assert value['opposite_relation']['status']=='review_required' and value['opposite_relation']['target'] is None
    assert value['options']['both']['permission']['reason']=='ROOM_REVIEW_REQUIRED'
    assert value['options']['current_only']['permission']['allowed']


def test_http_removal_options_and_atomic_ack(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    cmid=member(b,rid,c);path=f'/v2/raid-rooms/{rid}/member-removal'
    with client(a) as http:
        ctx=http.get(path+'-context',params=dict(target_cycle_key=c,target_cycle_member_id=str(cmid)))
        assert ctx.status_code==200,ctx.text
        schema.RemovalContext.model_validate(ctx.json())
        body=removal_body(ctx.json(),'both').model_dump(mode='json')
        result=http.post(path+'s',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.text
        assert len(schema.ActionResult.model_validate(result.json()).data.effects)==2
        assert result.headers['cache-control']=='no-store'


def test_concurrent_removal_same_key_once(corrected):
    from concurrent.futures import ThreadPoolExecutor
    from app.game_accounts.support import GameError
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    value=removal(a,b,rid,c);body=removal_body(value);key=uuid.uuid4()
    def call():
        try:return service.execute(actor(a['uid']),rid,key,body)
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:call(),range(2)))
    successful=[r for r in results if isinstance(r,tuple)]
    assert successful and all(r==successful[0] or r=='REQUEST_IN_PROGRESS' for r in results)
    assert service.execute(actor(a['uid']),rid,key,body)==successful[0]
    with session() as db:
        cm=db.get(CycleMember,body.target_cycle_member_id)
        assert cm.revision==body.expected_target_cycle_member_revision+1
        events=list(db.scalars(select(life.ParticipationEvent).where(life.ParticipationEvent.command_id==key)))
        assert len(events)==1 and events[0].action=='removed'


def test_target_registration_change_requires_new_removal_confirmation(corrected):
    from app.game_accounts.models import Registration
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c)
    body=removal_body(removal(a,b,rid,c))
    with session() as db,db.begin():
        registration=db.scalar(select(Registration).where(Registration.user_id==b['uid'],Registration.deleted_at.is_(None)))
        registration.version+=1
    before=fingerprints(engine)
    denied('TARGET_CONTEXT_STALE',service.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(engine)==before


def test_n_source_both_ack_order_and_personal_n_denied(corrected):
    engine,a,b=corrected;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    rd=uuid.UUID(plan(a,rid,n)['data']['game_items'][0]['round_id'])
    denied('TARGET_SCOPE_MISMATCH',service.get,actor(a['uid']),rid,c,round_id=rd)
    ctx=service.get(actor(a['uid']),rid,n,round_id=rd)
    assert ctx['data']['permission']['reason']=='TARGET_CYCLE_NOT_CURRENT' and ctx['data']['confirmation'] is None
    value=removal(a,b,rid,n);body=removal_body(value,'both')
    result=service.execute(actor(a['uid']),rid,uuid.uuid4(),body)[1]
    assert result['scope']['target_cycle_key']==n and result['scope']['current_cycle_key']==c
    assert result['data']['affected_cycle_keys']==[n,c]
    assert [x['target_cycle_key'] for x in result['data']['effects']]==[n,c]
