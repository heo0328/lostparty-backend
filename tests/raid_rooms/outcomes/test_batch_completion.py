"""Issue47 real transactions and HTTP; synthetic actors in disposable PostgreSQL."""
import copy
import json
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import inspect, select

from app.core.database import session, now
from app.game_accounts.common.support import GameError
from app.raid_rooms.common import beta_profile, cycles, command_context
from app.raid_rooms.group_links import cycle_group_policy as policy
from app.raid_rooms.participation import roster_participation as rp
from app.raid_rooms.outcomes import batch_completion as service
from app.raid_rooms.schemas import batch_completion_schemas as wire
from app.raid_rooms.models.cycle_models import RoomCycle, CycleMember, CycleGeneration
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_weekly.models import WeeklyState
from tests.raid_rooms.participation.test_roster_public_contract import (
    presence_db, policy_db, group_beta, beta, current, candidate, ready,
    sources, imported, people, worlds, bundle, actor, Q, P,
)
from tests.raid_rooms.admissions.test_beta_recruitment import beta_join
from tests.raid_rooms.schedules.test_recruitment_cycle_times_http import client
from tests.raid_rooms.outcomes.test_batch_snapshot import clone_completed
from tests.raid_rooms.common.test_raid_room_migrations import table_digests

DRAFT=json.loads(Path('docs/features/recruitment/completion-and-records/examples/batch-completion-v3.schema.json').read_text())


@contextmanager
def profiles():
    with policy.using(), beta_profile.using(), rp.using(P):
        yield


def row_for(db,rid,key):
    return db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))


def rounds(rid,key):
    with session() as db:
        row=row_for(db,rid,key)
        return sorted([rd.id for _,rd in service.life.admission.rounds(db,row) if rd.state=='active'],key=str)


def context(w,rid,key,selected=None,*,personal=False):
    with profiles():
        return service.get(actor(w['uid']),rid,key,rounds(rid,key) if selected is None else selected,personal=personal)


def body(ctx):
    s,d=ctx['scope'],ctx['data']
    return wire.BatchCommand.model_validate(dict(expected_cycle_key=s['current_cycle_key'],target_cycle_key=s['target_cycle_key'],
        room_cycle_id=s['room_cycle_id'],target_generation=s['target_generation'],expected_target_revision=s['target_revision'],
        actor_cycle_member_id=d['actor_cycle_member_id'],expected_cycle_member_revision=d['actor_cycle_member_revision'],
        round_ids=d['round_ids'],context_token=d['confirmation']['context_token']))


def execute(w,rid,ctx,*,personal=False,key=None):
    with profiles():return service.execute(actor(w['uid']),rid,key or uuid.uuid4(),body(ctx),personal=personal)


def valid(name,value):
    schema={**DRAFT,'$ref':'#/$defs/'+name};schema.pop('oneOf')
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(value)


def business(engine):
    tables={t for t in inspect(engine).get_table_names() if t.startswith(('recruitment_','raid_'))}
    return table_digests(engine,tables)


def test_party_partial_full_and_original_ack(presence_db,monkeypatch):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    ids=rounds(rid,c);before=business(engine)
    ctx=context(a,rid,c,ids[:1]);valid('PartyContext',ctx)
    assert business(engine)==before
    assert len(ctx['data']['display']['rounds'])==2
    assert len(ctx['data']['impact']['completed_assignment_ids'])==2
    assert len(ctx['data']['impact']['preserved_active_assignment_ids'])==2
    key=uuid.uuid4();result=execute(a,rid,ctx,key=key);valid('PartyAck',result[1])
    assert result[1]['data']['impact']==ctx['data']['impact']
    with session() as db:
        assert row_for(db,rid,c).state=='open' and row_for(db,rid,n).state=='open'
    remaining=context(a,rid,c,ids[1:]);assert remaining['data']['impact']['preserved_completed']['assignment_count']==2
    final=execute(a,rid,remaining)[1];assert final['data']['state']['generation_state']=='completed'
    before=business(engine);real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=7))
    assert execute(a,rid,ctx,key=key)==result
    assert business(engine)==before


@pytest.mark.parametrize('mode',['leave','successor','last_full','last_partial'])
def test_personal_departure_modes_and_other_week(presence_db,mode):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    if mode in ('leave','successor'):
        with profiles():beta_join(b,rid,c)
    w=b if mode=='leave' else a
    ids=rounds(rid,c);ctx=context(w,rid,c,ids[:1] if mode=='last_partial' else ids,personal=True)
    valid('PersonalContext',ctx)
    expected={'leave':'leave','successor':'automatic_successor','last_full':'close_completed','last_partial':'close_incomplete'}[mode]
    assert ctx['data']['departure']['effect']==expected
    with session() as db:before_n=service.plan.snapshot(row_for(db,rid,n))
    result=execute(w,rid,ctx,personal=True)[1];valid('PersonalAck',result)
    d=result['data'];assert d['state']['actor_cycle_member_state']=='cancelled'
    assert d['state']==ctx['data']['expected_after']['state'] and d['departure']==ctx['data']['departure']
    assert d['impact']==ctx['data']['impact']
    if mode.startswith('last_'):
        assert d['leadership']['leader_cycle_member_id'] is None
        assert d['state']['generation_state']==('completed' if mode=='last_full' else 'cancelled')
    with session() as db:
        assert service.plan.snapshot(row_for(db,rid,n))==before_n
        assert db.get(service.life.Member,db.get(CycleMember,uuid.UUID(d['actor_cycle_member_id'])).membership_id).ended_at is None


@pytest.mark.parametrize('personal',[False,True])
def test_http_selection_profiles_and_ack(presence_db,personal):
    engine,a,b=presence_db;rid,c,n=bundle(a);ids=rounds(rid,c)
    suffix='batch-personal-completion-departure' if personal else 'batch-completion'
    url=f'/v2/raid-rooms/{rid}/{suffix}';params=Q|P|dict(target_cycle_key=c,round_ids=json.dumps(list(map(str,ids))))
    with client(a) as http:
        before=business(engine)
        for wrong in ('[]',json.dumps([str(ids[0])]*2),'null','[true]'):
            r=http.get(url+'-context',params=params|{'round_ids':wrong});assert r.status_code==400,r.json()
        assert http.get(url+'-context',params=list(params.items())+[('round_ids',params['round_ids'])]).status_code==400
        assert http.get(url+'-context',params=params|{'contract_profile':'beta-recruitment-wire-2'}).status_code==400
        assert business(engine)==before
        r=http.get(url+'-context',params=params);assert r.status_code==200,r.json()
        assert r.headers['cache-control']=='no-store'
        ctx=r.json();valid('PersonalContext' if personal else 'PartyContext',ctx)
        payload=body(ctx).model_dump(mode='json');headers={'Idempotency-Key':str(uuid.uuid4())}
        for query in (Q, Q|P|{'extra':'bad'}):
            r=http.post(url+'s',params=query,json=payload,headers=headers);assert r.status_code==400,r.json()
        bad=payload|{'extra':1};assert http.post(url+'s',params=Q|P,json=bad,headers=headers).status_code==400
        r=http.post(url+'s',params=Q|P,json=payload,headers=headers);assert r.status_code==200,r.json()
        valid('PersonalAck' if personal else 'PartyAck',r.json())
        assert http.post(url+'s',params=Q|P,json=payload,headers=headers).json()==r.json()


def test_denial_scope_cas_expiry_and_key_conflict(presence_db):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    denied=context(b,rid,c)
    assert not denied['data']['permission']['allowed']
    assert denied['data']['permission']['reason']=='TARGET_LEADER_REQUIRED'
    assert denied['data']['confirmation'] is None
    valid('PartyContext',denied)
    future=context(a,rid,n)
    assert future['data']['permission']['reason']=='TARGET_CYCLE_NOT_CURRENT'
    ctx=context(a,rid,c);before=business(engine)
    with profiles():
        for mutate in ('actor','scope','revision','selection','token','expired'):
            original=body(ctx);change=original.model_dump(mode='json')
            if mutate=='actor':change['actor_cycle_member_id']=str(uuid.uuid4())
            elif mutate=='scope':change['room_cycle_id']=str(uuid.uuid4())
            elif mutate=='revision':change['expected_target_revision']+=1
            elif mutate=='selection':change['round_ids']=change['round_ids'][:1]
            elif mutate=='token':change['context_token']='invalid'
            else:
                token=command_context.unseal(change['context_token']);token['expires']=(now_without_db()-timedelta(seconds=1)).isoformat()
                change['context_token']=command_context.seal(token)
            with pytest.raises(GameError) as error:
                service.execute(actor(a['uid']),rid,uuid.uuid4(),wire.BatchCommand.model_validate(change))
            assert error.value.code in ('CONTEXT_INVALID','TARGET_SCOPE_MISMATCH','COMMAND_CONTEXT_EXPIRED')
            assert business(engine)==before
        with pytest.raises(GameError):service.execute(actor(b['uid']),rid,uuid.uuid4(),body(ctx))
    key=uuid.uuid4();execute(a,rid,ctx,key=key)
    with profiles(),pytest.raises(GameError,match='IDEMPOTENCY_CONFLICT'):
        service.execute(actor(a['uid']),rid,key,body(ctx).model_copy(update={'expected_target_revision':body(ctx).expected_target_revision+1}))


def now_without_db():
    with session() as db:return now(db)


@pytest.mark.parametrize('personal',[False,True])
def test_full_rollback_at_middle_ack_and_commit_deadline(presence_db,monkeypatch,personal):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    ctx=context(a,rid,c,personal=personal);before=business(engine)
    for stage in ('middle','ack','deadline','week','proof'):
        with monkeypatch.context() as patch:
            if stage=='middle':
                original=service._apply_assignment;count=[0]
                def broken(*args,**kwargs):
                    original(*args,**kwargs);count[0]+=1
                    if count[0]==2:raise GameError('SYNTHETIC_ROLLBACK')
                patch.setattr(service,'_apply_assignment',broken)
            elif stage=='ack':
                original=cycles.commit_result
                def broken(*args,**kwargs):
                    original(*args,**kwargs);raise GameError('SYNTHETIC_ROLLBACK')
                patch.setattr(cycles,'commit_result',broken)
            elif stage in ('deadline','week'):
                original=cycles.now;count=[0]
                def clock(db):
                    count[0]+=1
                    return original(db)+((timedelta(days=7) if stage=='week' else timedelta(minutes=3)) if count[0]>1 else timedelta())
                patch.setattr(cycles,'now',clock)
            else:
                original=service.snapshots.preserved_completed;count=[0]
                def altered(*args,**kwargs):
                    value=original(*args,**kwargs);count[0]+=1
                    if count[0]==2:value['digest']='0'*64
                    return value
                patch.setattr(service.snapshots,'preserved_completed',altered)
            key=uuid.uuid4()
            with pytest.raises(GameError) as error:execute(a,rid,ctx,personal=personal,key=key)
            assert error.value.code in ('SYNTHETIC_ROLLBACK','COMMAND_CONTEXT_EXPIRED','CYCLE_CHANGED','TARGET_CONTEXT_STALE')
        assert business(engine)==before
        from app.game_accounts.models.models import RequestResult
        with session() as db:
            request=db.scalar(select(RequestResult).where(RequestResult.actor_id==a['uid'],RequestResult.key==key))
            assert request is None or request.completed_at is None
    assert execute(a,rid,ctx,personal=personal)[0]==200


@pytest.mark.parametrize('personal',[False,True])
def test_large_history_real_command_preserves_exact_originals(presence_db,personal):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    ids=rounds(rid,c)
    execute(a,rid,context(a,rid,c,ids[:1]))
    with session() as db,db.begin():
        row=row_for(db,rid,c)
        source=db.scalar(select(Assignment).where(Assignment.room_id==rid,Assignment.user_id==a['uid'],Assignment.state=='completed'))
        for i in range(45):clone_completed(db,source,character_id=uuid.UUID(a['ids'][i%2]))
        saved={x.id:service.life.assignment_snapshot(x) for x in db.scalars(select(Assignment).where(
            Assignment.room_id==rid,Assignment.state=='completed'))}
    ctx=context(a,rid,c,ids[1:],personal=personal)
    proof=ctx['data']['impact']['preserved_completed'];assert proof['assignment_count']>40
    result=execute(a,rid,ctx,personal=personal)[1]
    assert result['data']['impact']['preserved_completed']==proof
    with session() as db:
        assert {k:service.life.assignment_snapshot(db.get(Assignment,k)) for k in saved}==saved


@pytest.mark.parametrize('other',['batch','single','character','leave'])
def test_competing_commands_have_one_atomic_winner(presence_db,other):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    personal=other in ('character','leave')
    ctx=context(a,rid,c,personal=personal)
    if other=='single':
        from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import outcome_body
        rid0=rounds(rid,c)[0]
        with profiles():legacy=service.outcomes.get(actor(a['uid']),rid,c,'complete_item',rid0)
    elif other=='character':
        from app.raid_rooms.participation import cycle_character
        from tests.raid_rooms.participation.test_roster_public_contract import change
        with profiles():legacy=change(a,rid,c)
    elif other=='leave':
        from app.raid_rooms.participation import membership_actions
        from tests.raid_rooms.participation.test_membership_actions import body as member_body
        with profiles():legacy=member_body(membership_actions.get(actor(a['uid']),rid,c),'leave_target')
    def first():return execute(a,rid,ctx,personal=personal)
    def second():
        with profiles():
            if other=='batch':return execute(a,rid,ctx)
            if other=='single':return service.outcomes.execute(actor(a['uid']),None,rid0,uuid.uuid4(),outcome_body(legacy),'complete_item')
            if other=='character':return cycle_character.execute(actor(a['uid']),rid,uuid.uuid4(),legacy)
            return membership_actions.execute(actor(a['uid']),rid,uuid.uuid4(),legacy)
    def call(fn):
        try:return ('ok',fn())
        except GameError as error:return ('error',error.code)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(call,(first,second)))
    assert sum(r[0]=='ok' for r in results)==1,results
    assert next(r[1] for r in results if r[0]=='error') in (
        'ROUND_NOT_ACTIVE','REVISION_CONFLICT','TARGET_CONTEXT_STALE','WEEKLY_PARTICIPANT_REQUIRED',
        'SOURCE_PARTICIPATION_REQUIRED','ROOM_LEADER_REQUIRED','TARGET_LEADER_REQUIRED','TARGET_CYCLE_CLOSED')
    with session() as db:
        row=row_for(db,rid,c)
        active=service.snapshots.active_assignments(db,row)
        for assignment in active:
            item=db.get(service.graph.graph.Item,assignment.item_id)
            ledger=db.get(WeeklyState,(assignment.user_id,assignment.character_id,item.raid_id,row.cycle_key))
            assert ledger.active_party_id==rid and ledger.party_completed_at is None and ledger.manual_completed_at is None


def test_successor_unavailable_and_history_stale_never_apply(presence_db):
    engine,a,b=presence_db;rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    original=context(a,rid,c,personal=True)
    with session() as db,db.begin():
        row=row_for(db,rid,c);target=service.life.actual_member(db,row,b['uid'])
        target.state='review_required';target.revision+=1
    denied=context(a,rid,c,personal=True);valid('PersonalContext',denied)
    assert denied['data']['permission']['reason']=='SUCCESSOR_UNAVAILABLE'
    assert denied['data']['confirmation'] is None and denied['data']['expected_after'] is None
    before=business(engine)
    with pytest.raises(GameError,match='SUCCESSOR_UNAVAILABLE'):execute(a,rid,original,personal=True)
    assert business(engine)==before
    with session() as db,db.begin():
        row=row_for(db,rid,c);target=service.life.actual_member(db,row,b['uid'],states=('review_required',))
        target.state='participating';target.revision+=1
        prior=clone_completed(db,service.snapshots.active_assignments(db,row,user_id=a['uid'])[0])
        previous_id=prior.id
    current_ctx=context(a,rid,c)
    with session() as db,db.begin():db.get(Assignment,previous_id).revision+=1
    before=business(engine)
    with pytest.raises(GameError,match='TARGET_CONTEXT_STALE'):execute(a,rid,current_ctx)
    assert business(engine)==before


def test_group_visibility_and_successor_policy_fallback(presence_db,people,request):
    from tests.groups.test_group_admissions import group
    engine,a,b=presence_db
    gid=uuid.UUID(group(request.getfixturevalue('client'),a))
    rid,c,n=bundle(a)
    with profiles():beta_join(b,rid,c)
    with session() as db,db.begin():
        row=row_for(db,rid,c)
        policy.apply(db,row,dict(scope='group',group_id=gid))
        row.revision+=1
    outsider=people('batch-group-outsider')
    before=business(engine)
    with pytest.raises(GameError,match='ROOM_NOT_FOUND'):context(outsider,rid,c)
    assert business(engine)==before
    ctx=context(a,rid,c,personal=True)
    assert ctx['data']['departure']['effect']=='automatic_successor'
    assert ctx['group_policy_effect']['after']['scope']=='public'
    ack=execute(a,rid,ctx,personal=True)[1];valid('PersonalAck',ack)
    assert ack['group_policy']['scope']=='public' and ack['group_policy']['group_id'] is None
    assert ack['data']['leadership']['leader_cycle_member_id']==ctx['data']['departure']['successor']['cycle_member_id']
