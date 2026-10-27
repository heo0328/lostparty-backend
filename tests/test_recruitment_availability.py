"""R2-A isolated HTTP + real restricted-role PostgreSQL transactions."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text, event
from app.core.database import session
from app.core.errors import register
from app.raid_rooms import availability
from app.raid_rooms.availability_router import router
from app.raid_rooms.availability_schemas import PersonalIn
from app.raid_rooms.source_models import PersonalAvailability
from tests.test_recruitment_sources import sources, imported, people, worlds
from tests.test_group_foundation import actor
from tests.test_raid_room_http import err

PERSONAL = '/v1/me/play-availability'
RAW = [dict(weekday=7,start='23:00',end='01:00',end_day_offset=1),
       dict(weekday=1,start='00:30',end='02:00',end_day_offset=0)]


def body(intervals=None, version=1):
    return dict(expected_version=version, timezone='Asia/Seoul', intervals=RAW if intervals is None else intervals)


def put(client, person, data=None, path=PERSONAL, key=None):
    return client.put(path, json=body() if data is None else data,
        headers={**person['headers'], 'Idempotency-Key': str(key or uuid.uuid4())})


@pytest.fixture
def http():
    from app.main import no_store
    app = FastAPI()
    app.include_router(router)
    app.middleware('http')(no_store)
    register(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_raw_union_empty_noop_and_original_ack(sources, http):
    target,rid,second,third,a,b,*_ = sources
    before = http.get(PERSONAL,headers=a['headers'])
    assert before.status_code==200
    assert before.json()==dict(exists=False,version=1,timezone='Asia/Seoul',intervals=[],normalized_intervals=[],updated_at=None)
    key=uuid.uuid4()
    saved=put(http,a,key=key)
    assert saved.status_code==200,saved.text
    assert saved.json()['intervals']==RAW and saved.json()['version']==2
    assert saved.json()['normalized_intervals']==[dict(start_minute=0,end_minute=120),dict(start_minute=10020,end_minute=10080)]
    assert put(http,a,body(version=2)).json()==saved.json()
    empty=put(http,a,body([],2))
    assert empty.json()['exists'] and empty.json()['version']==3 and empty.json()['intervals']==[]
    assert put(http,a,key=key).json()==saved.json()
    err(put(http,a),409,'REVISION_CONFLICT')
    assert http.get(PERSONAL,headers=b['headers']).json()['exists'] is False
    assert saved.headers['cache-control']=='no-store'


def test_submission_snapshot_cas_no_get_copy_and_legacy_gate(sources,http):
    target,rid,second,third,a,b,*_=sources
    from tests.test_raid_room_migrations import table_digests
    protected={'raid_weekly_states','recruitment_reservations','recruitment_sessions','recruitment_participations'}
    before=table_digests(target,protected)
    path=f'/v1/me/raid-rooms/{rid}/availability-submission'
    missing=http.get(path,headers=a['headers'])
    assert missing.status_code==200 and missing.json()['state']=='missing'
    data=dict(expected_personal_version=1,expected_submission_revision=1,expected_membership_revision=1)
    err(put(http,a,data,path),409,'ROOM_REVIEW_REQUIRED')
    # Explicit synthetic reviewed fixture, not a production migration/approval.
    with target.begin() as c:
        c.execute(text("UPDATE recruitment_rooms SET migration_state='ready' WHERE id=:id"),dict(id=rid))
    err(put(http,a,data,path),409,'PERSONAL_AVAILABILITY_REQUIRED')
    assert put(http,a).status_code==200
    data['expected_personal_version']=2
    key=uuid.uuid4(); saved=put(http,a,data,path,key)
    assert saved.status_code==200,saved.text
    assert saved.json()['revision']==2 and saved.json()['source_personal_version']==2
    assert put(http,a,dict(data,expected_submission_revision=2),path).json()==saved.json()
    assert put(http,a,body([],2)).status_code==200
    assert http.get(path,headers=a['headers']).json()==saved.json()
    err(put(http,a,dict(data,expected_submission_revision=2),path),409,'REVISION_CONFLICT')
    refreshed=put(http,a,dict(data,expected_personal_version=3,expected_submission_revision=2),path)
    assert refreshed.json()['revision']==3 and refreshed.json()['intervals']==[]
    assert put(http,a,data,path,key).json()==saved.json()
    assert table_digests(target,protected)==before
    err(http.get(f'/v1/me/raid-rooms/{second}/availability-submission',headers=b['headers']),404,'ROOM_NOT_FOUND')
    with target.begin() as c:
        c.execute(text('UPDATE recruitment_memberships SET ended_at=clock_timestamp() WHERE room_id=:id AND user_id=:uid'),dict(id=rid,uid=a['uid']))
    err(put(http,a,data,path,key),404,'ROOM_NOT_FOUND')
    with target.begin() as c:
        c.execute(text('''INSERT INTO recruitment_memberships
            (id,room_id,user_id,revision,joined_at) VALUES (:id,:rid,:uid,1,clock_timestamp())'''),
            dict(id=uuid.uuid4(),rid=rid,uid=a['uid']))
    err(put(http,a,data,path,key),409,'REVISION_CONFLICT')


@pytest.mark.parametrize('changes',[
    {'expected_version':True},{'expected_version':'1'},{'expected_version':2147483648},
    {'timezone':'UTC'},{'unexpected':1},{'intervals':[dict(RAW[0],weekday=True)]},
    {'intervals':[dict(RAW[0],start='23:01')]},{'intervals':[dict(RAW[0],end_day_offset=2)]},
    {'intervals':[dict(RAW[0],start='23:00',end='23:00',end_day_offset=0)]},
    {'intervals':[dict(RAW[0],start='22:00',end='23:00',end_day_offset=1)]},
])
def test_strict_schema(changes):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):PersonalIn.model_validate(body()|changes)


def test_strict_http_readonly_scope_and_bound(sources,http):
    target,rid,second,third,a,b,*_=sources
    headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4()),'Content-Type':'application/json'}
    for value in ('{"expected_version":1,"expected_version":1}',
                  '{"expected_version":NaN}', '{"intervals":[{"weekday":1,"weekday":2}]}'):
        err(http.put(PERSONAL,content=value,headers=headers),400,'INVALID_REQUEST')
    err(http.put(PERSONAL,content=' '*32769,headers=headers),413,'REQUEST_TOO_LARGE')
    err(http.request('GET',PERSONAL,content='{}',headers=a['headers']),400,'INVALID_REQUEST')
    err(http.get(PERSONAL+'?x=1',headers=a['headers']),400,'INVALID_REQUEST')
    err(http.get(PERSONAL),401,'ACCESS_INVALID')
    assert put(http,a,body([])).json()['version']==2
    with target.begin() as c:
        c.execute(text('UPDATE game_account_registrations SET deleted_at=clock_timestamp() WHERE user_id=:uid'),dict(uid=a['uid']))
    assert http.get(PERSONAL,headers=a['headers']).json()['version']==2
    err(put(http,a,body([],2)),403,'OWNERSHIP_REQUIRED')


def test_concurrent_cas_and_rollback(sources,monkeypatch):
    target,rid,second,third,a,b,*_=sources
    principal=actor(a['uid'])
    def save(_):
        try:return availability.put(principal,uuid.uuid4(),body())[0]
        except Exception as error:return getattr(error,'code',type(error).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(map(str,pool.map(save,range(2))))==['200','REVISION_CONFLICT']
    key=uuid.uuid4(); original=availability.commit_result
    def fail_commit(*args):raise RuntimeError('synthetic failure')
    monkeypatch.setattr(availability,'commit_result',fail_commit)
    with pytest.raises(RuntimeError):availability.put(principal,key,body([],2))
    with session() as db:assert db.get(PersonalAvailability,a['uid']).revision==2
    monkeypatch.setattr(availability,'commit_result',original)
    assert availability.put(principal,key,body([],2))[1]['version']==3


def test_normalization_exact_week_coverage():
    rows=[dict(weekday=d,start='00:00',end='00:00',end_day_offset=1) for d in range(7,0,-1)]
    assert availability.normalize(rows)==[dict(start_minute=0,end_minute=10080)]
    assert availability.normalize([])==[]


def test_get_transactions_are_readonly_and_body_boundary(sources,http):
    target,rid,second,third,a,b,*_=sources
    statements=[]
    def record(conn,cursor,statement,parameters,context,many):
        statements.append(statement.strip().upper())
    event.listen(target,'before_cursor_execute',record)
    try:
        assert http.get(PERSONAL,headers=a['headers']).status_code==200
        assert http.get(f'/v1/me/raid-rooms/{rid}/availability-submission',headers=a['headers']).status_code==200
    finally:event.remove(target,'before_cursor_execute',record)
    assert statements.count('SET TRANSACTION READ ONLY')==2
    assert not any(s.startswith(('INSERT','UPDATE','DELETE')) for s in statements)
    payload=json.dumps(body([]),separators=(',',':'))
    headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4()),'Content-Type':'application/json'}
    exact=payload+' '*(32768-len(payload))
    assert http.put(PERSONAL,content=exact,headers=headers).status_code==200
    err(http.put(PERSONAL,content=exact+' ',headers=headers),413,'REQUEST_TOO_LARGE')


def test_draft_http_contract_and_production_contract_remain_separate(http):
    from app.main import app
    from pathlib import Path
    from app.raid_rooms.availability_contract import draft_openapi
    draft=draft_openapi()
    assert draft==json.loads(Path('openapi/recruitment-availability.draft.json').read_text())
    assert set(draft['paths'])==set(http.app.openapi()['paths'])
    assert app.openapi()==json.loads(Path('openapi/openapi.yaml').read_text())
    assert any(route.path==PERSONAL for route in app.routes)
