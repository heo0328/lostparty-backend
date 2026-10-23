"""W2 read slice: actor isolation, exact leases, RR preservation and contract parity."""
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import pytest
from sqlalchemy import event, inspect, select, text
from app.core.database import engine, session, now
from app.game_accounts.models import Account, Character, NameClaim, Registration
from app.raid_rooms import queries, weekly_summary as service, weekly_summary_schemas as s
from app.raid_rooms.integrated_models import RecruitmentMembership as Member, RecruitmentRoom as Room
from app.raid_rooms.source_models import ContinuationChoice
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState
from app.raids import service as raids
from tests.test_group_admissions import worlds
from tests.test_raid_room_foundation import people
from tests.test_recruitment_participation import make_room, admit
from tests.test_recruitment_cycles import add_next_bundle
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor

META='/v2/raid-cycles'
SUMMARY='/v2/me/raid-weekly-summary'


@pytest.fixture
def users(people,monkeypatch):
    a,b=people('summary-a'),people('summary-b')
    with session() as db:
        current=date.fromisoformat(raids.cycle(now(db)).cycle_key)
    stamp=datetime.combine(current,datetime.min.time(),raids.KST).astimezone(timezone.utc)+timedelta(hours=11)
    monkeypatch.setattr(queries,'now',lambda db:stamp)
    return a,b,current,stamp


def body(a,current,*,both=True):
    return dict(character_ids=[a['ids'][0]],target_cycle_keys=[current.isoformat()]+[(current+timedelta(days=7)).isoformat()] if both else [current.isoformat()])


def request(client,a,data):
    return client.post(SUMMARY,headers=a['headers'],json=data)


def entry(response,key,raid='horizon_cathedral'):
    return next(e for e in response.json()['entries'] if e['target_cycle_key']==key.isoformat() and e['raid_id']==raid)


def test_actual_main_routes_no_store_and_read_only_all_tables(client,users,monkeypatch):
    a,b,current,stamp=users
    from app.game_accounts.provider import LostArkProvider
    from app.lostark_keys import service as keys
    def forbidden(*args,**kwargs):raise AssertionError('Summary must not call provider or credential capture')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden)
    monkeypatch.setattr(keys,'capture',forbidden)
    tables=set(inspect(engine()).get_table_names())-{'alembic_version'}
    before=table_digests(engine(),tables)
    meta=client.get(META,headers=a['headers'])
    assert meta.status_code==200,meta.text
    assert meta.headers['Cache-Control']=='no-store'
    assert meta.json()['current']['cycle_key']==current.isoformat()
    assert meta.json()['next']['cycle_key']==(current+timedelta(days=7)).isoformat()
    out=request(client,a,body(a,current))
    assert out.status_code==200,out.text
    assert out.headers['Cache-Control']=='no-store'
    assert len(out.json()['entries'])==10
    assert all(e['weekly_revision']==1 and e['participation'] is None and e['completion_sources']==[]
               and e['continuation_state']=='not_selected' for e in out.json()['entries'])
    assert entry(out,current)['permissions']['mark_completed']['allowed']
    assert not entry(out,current+timedelta(days=7))['permissions']['mark_completed']['allowed']
    assert request(client,a,body(a,current)).json()==out.json()
    assert table_digests(engine(),tables)==before


@pytest.mark.parametrize('stamp,cycle,complete',[
    ('2026-10-20T20:59:59+00:00','2026-10-14',True),
    ('2026-10-20T21:00:00+00:00','2026-10-21',False),
    ('2026-10-21T00:59:59+00:00','2026-10-21',False),
    ('2026-10-21T01:00:00+00:00','2026-10-21',True),
])
def test_metadata_six_and_ten_hour_boundary(client,users,monkeypatch,stamp,cycle,complete):
    a,*_=users
    monkeypatch.setattr(queries,'now',lambda db:datetime.fromisoformat(stamp))
    out=client.get(META,headers=a['headers'])
    assert out.status_code==200,out.text
    data=out.json()
    assert data['current']['cycle_key']==cycle
    assert data['current']['permissions']['complete']['allowed']==complete
    assert data['current']['permissions']['complete']['next_change_at'] is not None
    assert all(data['next']['permissions'][k]['allowed'] for k in ('read','create','admit'))
    assert not data['next']['permissions']['complete']['allowed']
    assert datetime.fromisoformat(data['current']['playable_from'].replace('Z','+00:00')).astimezone(raids.KST).hour==10
    with session() as db:
        assert db.scalar(text('SELECT count(*) FROM raid_weekly_states'))==0


@pytest.mark.parametrize('kind',['foreign','unknown','deleted_registration','transferred_owner','identity_conflict','retired'])
def test_entire_batch_rejects_inaccessible_or_unusable_character(client,users,kind):
    a,b,current,_=users
    cid=a['ids'][1]
    expected=403
    with session() as db,db.begin():
        if kind=='foreign':cid=b['ids'][0]
        elif kind=='unknown':cid=str(uuid.uuid4())
        elif kind=='deleted_registration':db.get(Registration,uuid.UUID(a['rid'])).deleted_at=now(db)
        elif kind=='transferred_owner':db.get(Account,a['aid']).owner_id=b['uid']
        elif kind=='identity_conflict':
            character=db.get(Character,uuid.UUID(cid));db.delete(db.get(NameClaim,(character.server_name,character.character_name)));expected=409
        elif kind=='retired':db.get(Character,uuid.UUID(cid)).lifecycle_state='retired';expected=409
    data=body(a,current);data['character_ids'].append(cid)
    out=request(client,a,data)
    assert out.status_code==expected,out.text
    assert 'entries' not in out.json() and out.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('change',[
    {'character_ids':[]},{'character_ids':None},{'character_ids':['bad']},{'target_cycle_keys':[]},
    {'target_cycle_keys':None},{'target_cycle_keys':['20261021']},{'target_cycle_keys':[True]},
    {'character_ids':[str(uuid.uuid4()) for _ in range(51)]},{'extra':'not allowed'},
])
def test_strict_request_shape(client,users,change):
    a,b,current,_=users
    out=request(client,a,body(a,current)|change)
    assert out.status_code==400,out.text


def test_duplicate_targets_ids_and_outside_current_next_rejected(client,users):
    a,b,current,_=users
    for change in (
        {'character_ids':[a['ids'][0],a['ids'][0].upper()]},
        {'target_cycle_keys':[current.isoformat(),current.isoformat()]},
        {'target_cycle_keys':[(current+timedelta(days=14)).isoformat()]},
        {'target_cycle_keys':[(current-timedelta(days=7)).isoformat()]},
        {'target_cycle_keys':[(current+timedelta(days=1)).isoformat()]},
    ):
        out=request(client,a,body(a,current)|change)
        assert out.status_code in (400,409),out.text


def test_auth_and_input_boundaries(client,users):
    a,b,current,_=users
    assert client.get(META).status_code==401
    assert client.post(SUMMARY,json=body(a,current)).status_code==401
    for path in (META+'?target_cycle_key='+current.isoformat(),META+'?x=1&x=2'):
        assert client.get(path,headers=a['headers']).status_code==400
    assert client.request('GET',META,headers=a['headers'],content=b'{}').status_code==400
    assert client.post(SUMMARY+'?target_cycle_key='+current.isoformat(),headers=a['headers'],json=body(a,current)).status_code==400
    raw=json.dumps(body(a,current))[:-1]+',"character_ids":[]} '
    assert client.post(SUMMARY,headers={**a['headers'],'Content-Type':'application/json'},content=raw).status_code==400
    assert client.post(SUMMARY,headers=a['headers'],content=b' '*32769).status_code==413


def test_completion_sources_remain_distinct_and_time_gated(client,users,monkeypatch):
    a,b,current,stamp=users
    with session() as db,db.begin():
        db.add(WeeklyState(user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),raid_id='horizon_cathedral',
            cycle_key=current,revision=7,manual_completed_at=stamp,manual_difficulty_id=None,
            party_completed_at=stamp,party_difficulty_id='stage1',completed_party_id=uuid.uuid4(),updated_at=stamp))
    out=request(client,a,body(a,current))
    row=entry(out,current)
    assert row['weekly_revision']==7
    assert [s['source'] for s in row['completion_sources']]==['manual','party']
    assert row['permissions']['clear_manual_completion']['allowed'] and row['participation'] is None
    before_ten=stamp-timedelta(hours=2)
    monkeypatch.setattr(queries,'now',lambda db:before_ten)
    row=entry(request(client,a,body(a,current)),current)
    assert not row['permissions']['mark_completed']['allowed']
    assert not row['permissions']['clear_manual_completion']['allowed']
    assert len(row['completion_sources'])==2


def test_current_and_next_exact_leases_with_legacy_intent_separate(client,users):
    a,b,current,stamp=users
    rid=make_room(a)
    admit(a,rid)
    with session() as db,db.begin():
        from tests.test_recruitment_cycles import next_rounds
        next_rounds(db,rid,current+timedelta(days=7))
        add_next_bundle(db,rid,current,a['uid'])
        member=db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==a['uid']))
        from app.raid_rooms.integrated_models import RecruitmentItem as Item
        item=db.scalar(select(Item).where(Item.room_id==rid))
        db.add(ContinuationChoice(id=uuid.uuid4(),room_id=rid,item_id=item.id,membership_id=member.id,user_id=a['uid'],
            character_id=uuid.UUID(a['ids'][1]),raid_id=item.raid_id,selected_role='dealer',ownership_revision=1,
            target_cycle=current+timedelta(days=7),revision=1,state='selected'))
    data=body(a,current);data['character_ids'].append(a['ids'][1])
    out=request(client,a,data)
    assert out.status_code==200,out.text
    for key in (current,current+timedelta(days=7)):
        row=entry(out,key)
        assert row['participation']['status']=='confirmed' and row['participation']['room_id']==str(rid)
        assert not row['permissions']['mark_completed']['allowed']
    legacy=next(e for e in out.json()['entries'] if e['character_id']==a['ids'][1] and e['raid_id']=='horizon_cathedral' and e['target_cycle_key']!=(current.isoformat()))
    assert legacy['continuation_state']=='legacy_intent' and legacy['participation'] is None


def test_legacy_assignment_without_lease_is_review_only(client,users):
    a,b,current,_=users
    rid=make_room(a);admit(a,rid)
    with session() as db,db.begin():
        lease=db.scalar(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid));db.delete(lease)
    out=request(client,a,body(a,current))
    assert out.status_code==200,out.text
    assert entry(out,current)['participation']['status']=='review_required'
    assert entry(out,current)['continuation_state']=='blocked'


def test_hidden_title_and_review_occupancy_after_membership_ends(client,users):
    a,b,current,_=users
    rid=make_room(a);admit(a,rid)
    from tests.test_group_admissions import group
    gid=uuid.UUID(group(client,b))
    with session() as db,db.begin():
        room=db.get(Room,rid);room.scope='group';room.group_id=gid
        member=db.scalar(select(Member).where(Member.room_id==rid));member.ended_at=now(db)
    out=request(client,a,body(a,current))
    assert out.status_code==200,out.text
    part=entry(out,current)['participation']
    assert part['status']=='review_required' and part['room_title'] is None and not part['can_view_detail']


def test_orphan_ledger_is_not_misrepresented_as_no_participation(client,users):
    a,b,current,stamp=users
    with session() as db,db.begin():
        db.add(WeeklyState(user_id=a['uid'],character_id=uuid.UUID(a['ids'][0]),raid_id='horizon_cathedral',
            cycle_key=current,revision=2,active_party_id=uuid.uuid4(),active_difficulty_id='stage1',joined_at=stamp,updated_at=stamp))
    assert request(client,a,body(a,current)).status_code==503


def test_rr_snapshot_remains_consistent_during_concurrent_leave(client,users):
    a,b,current,_=users
    rid=make_room(a);admit(a,rid)
    changed=[]
    def after_select(connection,cursor,statement,parameters,context,many):
        if changed or 'from raid_weekly_states' not in statement.lower():return
        changed.append(True)
        # A second connection commits AFTER the summary ledger read and BEFORE
        # its lease/assignment reads. RR must still return the original snapshot.
        with engine().begin() as writer:
            writer.execute(text('''UPDATE raid_weekly_states SET active_party_id=NULL,
                active_difficulty_id=NULL,joined_at=NULL,revision=revision+1 WHERE user_id=:uid'''),{'uid':a['uid']})
            writer.execute(text('DELETE FROM recruitment_weekly_occupancies WHERE user_id=:uid'),{'uid':a['uid']})
            writer.execute(text("UPDATE recruitment_assignments SET state='left',ended_at=clock_timestamp(),revision=revision+1 WHERE user_id=:uid"),{'uid':a['uid']})
    event.listen(engine(),'after_cursor_execute',after_select)
    try:out=request(client,a,body(a,current))
    finally:event.remove(engine(),'after_cursor_execute',after_select)
    assert changed and out.status_code==200,out.text
    assert entry(out,current)['participation']['status']=='confirmed'
    assert entry(request(client,a,body(a,current)),current)['participation'] is None


def test_summary_does_not_load_closed_generations(client,users):
    a,b,current,stamp=users
    rid=make_room(a);admit(a,rid)
    from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round
    with session() as db,db.begin():
        original=db.scalar(select(Assignment).where(Assignment.room_id==rid))
        original_round=db.get(Round,original.round_id)
        for _ in range(25):
            rd=Round(id=uuid.uuid4(),room_id=rid,item_id=original.item_id,cycle_key=current,
                difficulty_id=original_round.difficulty_id,catalog_version=original_round.catalog_version,
                game_party_size=original_round.game_party_size,revision=1,state='completed',created_at=stamp,ended_at=stamp)
            db.add(rd);db.flush()
            fields={c.name:getattr(original,c.name) for c in Assignment.__table__.columns
                    if c.name not in ('record_created_at','record_updated_at')}
            fields.update(id=uuid.uuid4(),round_id=rd.id,state='left',ended_at=stamp)
            db.add(Assignment(**fields))
    with session() as db:
        ids,candidates=service.graphs(db,a['uid'],[uuid.UUID(a['ids'][0])],[current],[])
        assert len(ids)==1 and len(candidates[(uuid.UUID(a['ids'][0]),'horizon_cathedral',current)])==1
    out=request(client,a,body(a,current))
    assert out.status_code==200 and entry(out,current)['participation']['status']=='confirmed'


@pytest.mark.parametrize('change,status',[('disabled',403),('revoked',401)])
def test_current_session_and_member_state_is_checked(client,users,change,status):
    a,b,current,_=users
    from app.auth.models import User,Session
    with session() as db,db.begin():
        if change=='disabled':db.get(User,a['uid']).status='disabled'
        else:db.scalar(select(Session).where(Session.user_id==a['uid'])).revoked_at=now(db)
    for out in (client.get(META,headers=a['headers']),request(client,a,body(a,current))):
        assert out.status_code==status,out.text
        assert out.headers['Cache-Control']=='no-store'


def test_maximum_500_entries_constant_query_count_and_unchanged_data(client,users):
    a,b,current,stamp=users
    with session() as db,db.begin():
        for i in range(47):
            character=Character(id=uuid.uuid4(),account_id=a['aid'],server_name='summary-scale',character_name=f'char-{i}',
                summary={},status='confirmed',lifecycle_state='active',lifecycle_revision=1,fetched_at=stamp,confirmed_at=stamp)
            db.add(character);db.flush()
            db.add(NameClaim(server_name=character.server_name,character_name=character.character_name,character_id=character.id))
        ids=list(db.scalars(select(Character.id).where(Character.account_id==a['aid']).order_by(Character.id)))
    principal=actor(a['uid'])
    counts=[]
    for subset in (ids[:1],ids):
        calls=[]
        def executed(connection,cursor,statement,parameters,context,many):
            if statement.lstrip().lower().startswith('select'):calls.append(statement)
        event.listen(engine(),'before_cursor_execute',executed)
        try:
            result=service.summary(principal,s.SummaryRequest(character_ids=subset,target_cycle_keys=body(a,current)['target_cycle_keys']))
        finally:event.remove(engine(),'before_cursor_execute',executed)
        counts.append(len(calls))
        assert len(result['entries'])==len(subset)*10
    assert counts[0]==counts[1] and counts[1]<=12
    out=request(client,a,dict(character_ids=list(map(str,ids)),target_cycle_keys=body(a,current)['target_cycle_keys']))
    assert out.status_code==200 and len(out.json()['entries'])==500
    print('WEEKLY_SUMMARY_MAX characters=50 entries=500 select_statements='+str(counts[1])+' bytes='+str(len(out.content)))
    with session() as db:
        assert db.scalar(text('SELECT count(*) FROM raid_weekly_states'))==0


def expand(schema,document):
    if isinstance(schema,list):return [expand(v,document) for v in schema]
    if not isinstance(schema,dict):return schema
    if '$ref' in schema:return expand(document['components']['schemas'][schema['$ref'].rsplit('/',1)[1]],document)
    result={k:expand(v,document) for k,v in schema.items() if k not in ('title','description')}
    if result.get('type')=='array':result.setdefault('minItems',0)
    if 'required' in result:result['required']=sorted(result['required'])
    return result


def test_runtime_slice_matches_agreed_contract_and_canonical_source():
    from app.main import app
    runtime=app.openapi()
    assert runtime==json.loads(Path('openapi/openapi.yaml').read_text())
    contract=json.loads(Path('docs/features/recruitment/artifacts/issue13-two-cycle.full.openapi.json').read_text())
    for path,method in ((META,'get'),(SUMMARY,'post')):
        actual=runtime['paths'][path][method];agreed=contract['paths'][path][method]
        assert actual['operationId']==agreed['operationId']
        assert actual['security']==agreed['security']
        assert expand(actual['responses']['200']['content']['application/json']['schema'],runtime)==expand(agreed['responses']['200']['content']['application/json']['schema'],contract)
        if method=='post':
            assert expand(actual['requestBody']['content']['application/json']['schema'],runtime)==expand(agreed['requestBody']['content']['application/json']['schema'],contract)
