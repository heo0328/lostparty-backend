"""Contract2: isolated restricted PostgreSQL; no development data or provider."""
import json
import uuid
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import event, select, inspect, func

from app.core.database import session, now
from app.game_accounts.models import Character, Activity
from app.game_accounts.support import GameError
from app.raid_rooms import admission_candidates as candidates, cycle_character as changes, cycle_member_reads
from app.raid_rooms import admission_eligibility as eligibility
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment
from app.raid_weekly.models import WeeklyState
from tests.test_application_composition import (current,candidate,ready,sources,imported,people,worlds,
    room,change_class,leader_class,apply,approve,occupancy,commands,context,admission_request,denied,actor)
from tests.test_recruitment_cycle_lifecycle import change_body
from tests.test_recruitment_participation import write_power
from tests.test_raid_room_migrations import table_digests

SCHEMA=json.loads(Path('docs/features/recruitment/participation/examples/candidate-contract-v2.schema.json').read_text())


def page(w,rid,key,intent='apply',**kw):
    value=candidates.get(actor(w['uid']),rid,key,intent,**kw)
    Draft202012Validator(SCHEMA,format_checker=FormatChecker()).validate(value)
    return value['data']


def picked(p,w,index=0):
    return next((x for x in p['items'] if x['character_id']==w['ids'][index]),None)


def minimum(rid,key,dealer,support=None):
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        settings=deepcopy(row.settings_snapshot);settings['combat_requirement'].update(dealer_min=dealer,support_min=support,input_mode='per_role');row.settings_snapshot=settings


def test_readonly_closed_roles_counts_and_context_agree(current):
    engine,a,b=current;rid,c,n=room(a);before=table_digests(engine,set(inspect(engine).get_table_names()))
    p=page(b,rid,c);item=picked(p,b);assert item and item['roles']['dealer']['allowed']
    assert item['roles']['support']==dict(supported=False,allowed=False,reason='ROLE_NOT_SUPPORTED',comparison=None)
    assert table_digests(engine,set(before))==before
    change_class(b,leader_class(a));p=page(b,rid,c)
    assert picked(p,b) is None
    assert context(b,rid,c,'apply')['data']['permissions']['apply']['reason']=='ROOM_COMPOSITION_CONFLICT'
    assert any(x['reason']=='ROOM_COMPOSITION_CONFLICT' for x in p['exclusion_summary'])
    assert sum(x['character_count'] for x in p['exclusion_summary'])==p['raw_candidate_count']-p['eligible_candidate_count']


def test_role_power_precision_retained_success_and_no_minimum(current):
    _,a,b=current;rid,c,n=room(a);change_class(b,'바드');minimum(rid,c,'100','100')
    p=page(b,rid,c);assert picked(p,b) is None
    assert any(x['reason']=='COMBAT_POWER_REQUIRED' and x['detail']=='missing' for x in p['exclusion_summary'])
    assert context(b,rid,c,'apply')['data']['permissions']['apply']['reason']=='COMBAT_POWER_REQUIRED'
    write_power(b,'support','100','2026-10-10T00:00:00Z')
    item=picked(page(b,rid,c),b);assert item['roles']['support']['allowed'] and not item['roles']['dealer']['allowed']
    write_power(b,'dealer','99.999999999999999999999999999','2026-10-11T00:00:00Z',3)
    item=picked(page(b,rid,c),b);assert item['roles']['dealer']['comparison']['state']=='below'
    write_power(b,'dealer','100','2026-10-12T00:00:00Z',4);write_power(b,'dealer',None,None,5)
    comp=picked(page(b,rid,c),b)['roles']['dealer']['comparison']
    assert comp['state']=='meets' and comp['actual']=='100' and comp['current_summary_version']==5 and comp['success_summary_version']==4 and comp['success_issues']
    assert context(b,rid,c,'apply')['data']['permissions']['apply']['allowed']
    assert picked(page(b,rid,n),b)['roles']['dealer']['comparison']['state']=='unrestricted'


def test_pages_scope_stale_permission_and_query_count(current):
    engine,a,b=current;rid,c,n=room(a);counts=[]
    def count(*args):counts.append(1)
    event.listen(engine,'before_cursor_execute',count)
    try:
        p=page(b,rid,c,limit=1);query_count=len(counts);counts.clear()
        full=page(b,rid,c,limit=100);assert len(counts)==query_count
    finally:event.remove(engine,'before_cursor_execute',count)
    ids=[x['character_id'] for x in p['items']];token=p['snapshot_token'];cursor=p['next_cursor']
    while cursor:
        p=page(b,rid,c,limit=2,cursor=cursor);assert p['snapshot_token']==token
        ids.extend(x['character_id'] for x in p['items']);cursor=p['next_cursor']
    assert ids==[x['character_id'] for x in full['items']]
    cursor=page(b,rid,c,limit=1)['next_cursor'];assert cursor
    denied('INVALID_REQUEST',page,a,rid,c,cursor=cursor)
    denied('INVALID_REQUEST',page,b,rid,n,cursor=cursor)
    denied('INVALID_REQUEST',page,b,rid,c,cursor=cursor[:-2]+'xx')
    change_class(b,'changed-class');denied('CURSOR_STALE',page,b,rid,c,cursor=cursor)
    denied('WEEKLY_PARTICIPANT_REQUIRED',page,b,rid,c,'change_character')


def test_missing_data_and_completed_target_isolation(current):
    _,a,b=current;rid,c,n=room(a,bundle=True)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        item,rd=commands.admission.rounds(db,row)[-1]
        state=db.get(WeeklyState,(b['uid'],uuid.UUID(b['ids'][0]),item.raid_id,row.cycle_key))
        if state is None:
            state=WeeklyState(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),raid_id=item.raid_id,cycle_key=row.cycle_key,revision=1,updated_at=now(db));db.add(state)
        state.manual_completed_at=now(db);state.manual_difficulty_id=rd.difficulty_id
    assert picked(page(b,rid,c),b) is None and picked(page(b,rid,n),b)
    assert context(b,rid,c,'apply')['data']['permissions']['apply']['reason']=='WEEKLY_ALREADY_COMPLETED'
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.summary={**char.summary,'item_level':None}
    denied('CHARACTER_DATA_UNAVAILABLE',page,b,rid,c)


def test_empty_source_is_distinct_from_filtered(current):
    _,a,b=current;rid,c,n=room(a)
    with session() as db,db.begin():
        for cid in b['ids']:
            row=db.get(Activity,(b['cid'],uuid.UUID(cid)))
            if row:db.delete(row)
    p=page(b,rid,c);assert p['raw_candidate_count']==p['eligible_candidate_count']==0 and p['items']==p['exclusion_summary']==[] and p['next_cursor'] is None


def test_change_self_exclusion_opposite_party_consent_and_original_ack(current,people):
    _,a,b=current;rid,c,n=room(a,eight=True)
    # Join b in party1, then put b's proposed replacement class next to it.
    approve(a,apply(b,rid,c)[1]['data'],rid,c)
    w=people('opposite-party-class');
    with session() as db:newclass=db.get(Character,uuid.UUID(b['ids'][1])).summary['class_name']
    change_class(w,newclass);approve(a,apply(w,rid,c)[1]['data'],rid,c)
    p=page(b,rid,c,'change_character');assert p['actor'] and picked(p,b,0) and picked(p,b,1)
    plan=cycle_member_reads.plan(actor(b['uid']),rid,c)
    ctx=commands.get_context(actor(b['uid']),rid,c,uuid.UUID(b['ids'][1]),'dealer','change_character')
    assert ctx['data']['permissions']['change_character']['allowed'] and {t['party_no'] for t in ctx['data']['targets']}=={2}
    body=change_body(ctx,plan);tampered=body.model_copy(deep=True)
    for t in tampered.target_items:t.party_no=1
    denied('TARGET_SCOPE_MISMATCH',changes.execute,actor(b['uid']),rid,uuid.uuid4(),tampered)
    command=uuid.uuid4();result=changes.execute(actor(b['uid']),rid,command,body);assert result[0]==200
    assert changes.execute(actor(b['uid']),rid,command,body)==result
    with session() as db:
        active=list(db.scalars(select(Assignment).where(Assignment.room_id==rid,Assignment.user_id==b['uid'],Assignment.state=='active')))
        assert {x.character_id for x in active}=={uuid.UUID(b['ids'][1])} and {x.party_no for x in active}=={2}
    assert page(b,rid,n)['intent']=='apply'


def test_change_context_change_requires_reconfirmation_and_rollback(current,monkeypatch):
    engine,a,b=current;rid,c,n=room(a,bundle=True)
    plan=cycle_member_reads.plan(actor(a['uid']),rid,n)
    ctx=commands.get_context(actor(a['uid']),rid,n,uuid.UUID(a['ids'][1]),'dealer','change_character');body=change_body(ctx,plan)
    tables=set(inspect(engine).get_table_names())-{'game_account_requests'};before=table_digests(engine,tables)
    original=commands.admission.core.release_assignment;calls=[]
    def failed(db,row,stamp):
        calls.append(1)
        if len(calls)==2:raise GameError('SYNTHETIC_RELEASE_FAILURE')
        return original(db,row,stamp)
    with monkeypatch.context() as m:
        m.setattr(commands.admission.core,'release_assignment',failed)
        denied('SYNTHETIC_RELEASE_FAILURE',changes.execute,actor(a['uid']),rid,uuid.uuid4(),body)
    assert table_digests(engine,tables)==before
    with session() as db,db.begin():
        ch=db.get(Character,uuid.UUID(a['ids'][1]));ch.summary={**ch.summary,'class_name':'new-confirmation-class'}
    denied('TARGET_CONTEXT_STALE',changes.execute,actor(a['uid']),rid,uuid.uuid4(),body)


def test_approval_failure_pending_no_business_writes_and_stored_party(current,people):
    engine,a,b=current;rid,c,n=room(a)
    app=apply(b,rid,c)[1]['data'];w=people('same-class-approve');change_class(w,leader_class(b));approve(a,apply(w,rid,c)[1]['data'],rid,c)
    tables=set(inspect(engine).get_table_names())-{'game_account_requests'};before=table_digests(engine,tables)
    denied('ROOM_COMPOSITION_CONFLICT',approve,a,app,rid,c)
    assert table_digests(engine,tables)==before
    with session() as db:assert db.get(CycleApplication,uuid.UUID(app['application_id'])).state=='pending'


def test_candidate_http_closed_queries_contract_and_no_store(current,monkeypatch):
    from tests.test_recruitment_cycle_times_http import client
    _,a,b=current;rid,c,n=room(a);route=f'/v2/raid-rooms/{rid}/admission-character-candidates';query=dict(target_cycle_key=c,intent='apply')
    with client(b) as http:
        response=http.get(route,params=query);assert response.status_code==200,response.text
        assert response.headers['cache-control']=='no-store';Draft202012Validator(SCHEMA,format_checker=FormatChecker()).validate(response.json())
        for params in (query|dict(extra='x'),query|dict(intent='invented'),list(query.items())+[('intent','apply')],query|dict(limit=0)):
            assert http.get(route,params=params).status_code==400
        assert http.request('GET',route,params=query,json={}).status_code==400
        monkeypatch.setattr(candidates,'MAX_RESPONSE_BYTES',1)
        response=http.get(route,params=query);assert response.status_code==413 and response.headers['cache-control']=='no-store'


def test_bulk_query_count_does_not_grow_with_characters(current):
    from app.game_accounts.models import Account, NameClaim
    engine,a,b=current;rid,c,n=room(a);queries=[]
    def count(*args):queries.append(1)
    event.listen(engine,'before_cursor_execute',count)
    try:
        p=page(b,rid,c,limit=100);initial=len(queries)
        with session() as db,db.begin():
            original=db.get(Character,uuid.UUID(b['ids'][0]));stamp=now(db)
            for i in range(20):
                name='synthetic-bulk-'+str(i);summary={**original.summary,'character_name':name,'class_name':'bulk-class-'+str(i)}
                char=Character(id=uuid.uuid4(),account_id=original.account_id,server_name=original.server_name,character_name=name,
                    summary=summary,fetched_at=stamp,confirmed_at=stamp)
                db.add(char);db.flush();db.add(NameClaim(server_name=char.server_name,character_name=name,character_id=char.id))
                db.add(Activity(settings_id=b['cid'],character_id=char.id,account_id=original.account_id))
            db.get(Account,original.account_id).roster_revision+=1
        queries.clear();after=page(b,rid,c,limit=100)
        assert after['raw_candidate_count']==p['raw_candidate_count']+20 and len(queries)==initial
    finally:event.remove(engine,'before_cursor_execute',count)


def test_same_room_other_assignment_lease_not_self_excluded(current):
    from app.raid_rooms.integrated_models import RecruitmentRound as Round
    from app.raid_rooms.weekly_links import WeeklyOccupancy
    _,a,b=current;rid,c,n=room(a)
    with session() as db,db.begin():
        target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        cm=changes.life.actual_member(db,target,a['uid'],states=('participating',));old=changes.life.assignments(db,target,cm)[0]
        rd=db.get(Round,old.round_id);new_round=Round(id=uuid.uuid4(),room_id=rid,item_id=old.item_id,cycle_key=rd.cycle_key,
            difficulty_id=rd.difficulty_id,catalog_version=rd.catalog_version,game_party_size=rd.game_party_size,state='active',revision=1,created_at=now(db))
        db.add(new_round);db.flush()
        char=db.get(Character,uuid.UUID(a['ids'][1]));extra=Assignment(id=uuid.uuid4(),room_id=rid,item_id=old.item_id,round_id=new_round.id,
            membership_id=old.membership_id,user_id=a['uid'],character_id=char.id,selected_role='dealer',party_no=1,slot_no=2,
            display=dict(server_name=char.server_name,character_name=char.character_name,class_name=char.summary['class_name']),build={},
            ownership_revision=1,lifecycle_revision=1,state='active',revision=1,joined_at=now(db))
        db.add(extra);db.flush()
        item=next(i for i,r in commands.admission.rounds(db,target) if i.id==old.item_id)
        state=WeeklyState(user_id=a['uid'],character_id=char.id,raid_id=item.raid_id,cycle_key=target.cycle_key,revision=1,
            active_party_id=rid,active_difficulty_id=rd.difficulty_id,joined_at=extra.joined_at,updated_at=now(db));db.add(state);db.flush()
        db.add(WeeklyOccupancy(user_id=a['uid'],character_id=char.id,raid_id=item.raid_id,cycle_key=target.cycle_key,
            room_id=rid,item_id=item.id,round_id=new_round.id,assignment_id=extra.id,joined_at=extra.joined_at))
    p=page(a,rid,c,'change_character');assert picked(p,a,1) is None
    ctx=commands.get_context(actor(a['uid']),rid,c,uuid.UUID(a['ids'][1]),'dealer','change_character')
    assert ctx['data']['permissions']['change_character']['reason']=='WEEKLY_ALREADY_PARTICIPATING'


def test_saved_application_party_does_not_auto_relocate_on_approval(current,people):
    _,a,b=current;rid,c,n=room(a,eight=True);app=apply(b,rid,c)[1]['data']
    w=people('saved-party-same-class');change_class(w,leader_class(b));approve(a,apply(w,rid,c)[1]['data'],rid,c)
    # Current fresh context could use party2, but the stored party1 application is not rewritten.
    assert {t['party_no'] for t in context(b,rid,c,'apply')['data']['targets']}=={2}
    denied('ROOM_COMPOSITION_CONFLICT',approve,a,app,rid,c)
    with session() as db:
        row=db.get(CycleApplication,uuid.UUID(app['application_id']));assert row.state=='pending' and {t['party_no'] for t in row.targets}=={1}


def test_tampered_application_party_and_unsupported_role_rejected(current):
    _,a,b=current;rid,c,n=room(a,eight=True);ctx=context(b,rid,c,'apply');body=admission_request(ctx).model_copy(deep=True)
    for t in body.target_items:t.party_no=2
    denied('TARGET_SCOPE_MISMATCH',commands.admit,actor(b['uid']),rid,uuid.uuid4(),body,applying=True)
    ctx=context(b,rid,c,'apply','support')
    assert ctx['data']['permissions']['apply']['reason']=='ROLE_NOT_SUPPORTED'
    denied('ROLE_NOT_SUPPORTED',commands.admit,actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx),applying=True)


def test_candidate_actual_bearer_unauthenticated_foreign_and_revoked(current):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth.models import User,Session
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    _,a,b=current;rid,c,n=room(a);app=FastAPI();register(app);app.include_router(router);app.middleware('http')(no_store)
    route=f'/v2/raid-rooms/{rid}/admission-character-candidates';query=dict(target_cycle_key=c,intent='apply')
    with session() as db:
        user=db.get(User,b['uid']);auth=actor(b['uid'])[1]
        # Synthetic test identity/session only, never development credentials.
        bearer=b['headers']['Authorization']
    with TestClient(app) as http:
        for headers in ({},{'Authorization':'Bearer invalid'}):
            r=http.get(route,params=query,headers=headers);assert r.status_code==401 and r.headers['cache-control']=='no-store'
        r=http.get(route,params=query,headers={'Authorization':bearer});assert r.status_code==200,r.text
        r=http.get(route,params=query|dict(intent='change_character'),headers={'Authorization':bearer});assert r.status_code==403
        with session() as db,db.begin():db.get(Session,auth.id).revoked_at=now(db)
        r=http.get(route,params=query,headers={'Authorization':bearer});assert r.status_code==401


@pytest.mark.parametrize('kind,code',[('power','COMBAT_POWER_REQUIRED'),('completed','WEEKLY_ALREADY_COMPLETED'),('occupied','WEEKLY_ALREADY_PARTICIPATING')])
def test_approval_rechecks_latest_qualification_pending_preserved(current,kind,code):
    from tests.test_recruitment_cycle_commands import create_room
    engine,a,b=current;rid,c,n=room(a);app=apply(b,rid,c)[1]['data']
    if kind=='power':minimum(rid,c,'100')
    elif kind=='occupied':create_room(b,combined=False)
    else:
        with session() as db,db.begin():
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
            item,rd=commands.admission.rounds(db,row)[0];state=db.get(WeeklyState,(b['uid'],uuid.UUID(b['ids'][0]),item.raid_id,row.cycle_key))
            if state is None:
                state=WeeklyState(user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),raid_id=item.raid_id,cycle_key=row.cycle_key,revision=1,updated_at=now(db));db.add(state)
            state.party_completed_at=now(db);state.completed_party_id=uuid.uuid4();state.party_difficulty_id=rd.difficulty_id
    tables=set(inspect(engine).get_table_names())-{'game_account_requests'};before=table_digests(engine,tables)
    denied(code,approve,a,app,rid,c)
    assert table_digests(engine,tables)==before
    with session() as db:assert db.get(CycleApplication,uuid.UUID(app['application_id'])).state=='pending'


def test_change_missing_original_lease_is_not_a_valid_preview(current):
    from app.raid_rooms.weekly_links import WeeklyOccupancy
    _,a,b=current;rid,c,n=room(a)
    ctx=commands.get_context(actor(a['uid']),rid,c,uuid.UUID(a['ids'][1]),'dealer','change_character')
    plan=cycle_member_reads.plan(actor(a['uid']),rid,c);body=change_body(ctx,plan)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        cm=changes.life.actual_member(db,row,a['uid'],states=('participating',));assignment=changes.life.assignments(db,row,cm)[0]
        lease=db.scalar(select(WeeklyOccupancy).where(WeeklyOccupancy.assignment_id==assignment.id));db.delete(lease)
    denied('WEEKLY_OCCUPANCY_CHANGED',page,a,rid,c,'change_character')
    denied('WEEKLY_OCCUPANCY_CHANGED',changes.execute,actor(a['uid']),rid,uuid.uuid4(),body)


def test_corrupt_lease_not_hidden_by_a_filtered_low_level_character(current):
    from tests.test_recruitment_cycle_commands import create_room
    _,a,b=current;other=create_room(b,combined=False);rid,c,n=room(a)
    with session() as db,db.begin():
        assignment=db.scalar(select(Assignment).where(Assignment.room_id==uuid.UUID(other['room_id']),Assignment.user_id==b['uid'],Assignment.state=='active'))
        assignment.state,assignment.ended_at='left',now(db)
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.summary={**char.summary,'item_level':'1'}
    denied('WEEKLY_OCCUPANCY_CHANGED',page,b,rid,c)


def test_join_candidates_exclude_low_level_and_match_context_without_writes(current):
    from tests.test_recruitment_cycle_commands import create_room
    _,a,b=current;rid=uuid.UUID(create_room(a)['room_id'])
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key))
        key=row.cycle_key.isoformat();item,rd=commands.admission.rounds(db,row)[0]
        difficulty=commands.raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version)
    p=page(b,rid,key,'join');assert p['intent']=='join' and p['actor'] is None and picked(p,b)
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.summary={**char.summary,'item_level':str(int(difficulty.min_item_level)-1)}
    before=occupancy()
    result=page(b,rid,key,'join');assert picked(result,b) is None
    assert any(v['reason']=='RAID_ITEM_LEVEL_REQUIRED' for v in result['exclusion_summary'])
    assert context(b,rid,key,'join')['data']['permissions']['join']['reason']=='RAID_ITEM_LEVEL_REQUIRED'
    assert occupancy()==before
    denied('ADMISSION_MODE_CHANGED',page,b,rid,key,'apply')


def test_join_candidates_cursor_scope_and_existing_intents(current):
    from tests.test_recruitment_cycle_commands import create_room
    _,a,b=current;ack=create_room(a);rid=uuid.UUID(ack['room_id']);c,n=[v['target_cycle_key'] for v in ack['created_cycles']]
    p=page(b,rid,c,'join',limit=1);assert p['next_cursor']
    full=page(b,rid,c,'join',limit=100);ids=[v['character_id'] for v in p['items']]
    while p['next_cursor']:
        p=page(b,rid,c,'join',limit=1,cursor=p['next_cursor']);ids.extend(v['character_id'] for v in p['items'])
    assert ids==[v['character_id'] for v in full['items']]
    cursor=page(b,rid,c,'join',limit=1)['next_cursor']
    denied('INVALID_REQUEST',page,b,rid,n,'join',cursor=cursor)
    denied('INVALID_REQUEST',page,a,rid,c,'join',cursor=cursor)
    denied('WEEKLY_PARTICIPANT_REQUIRED',page,b,rid,c,'change_character')
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        row.settings_snapshot={**row.settings_snapshot,'admission_mode':'leader_only'}
        row.settings_revision+=1
    denied('ADMISSION_MODE_CHANGED',page,b,rid,c,'join')
    assert page(b,rid,c,'apply')['intent']=='apply'
