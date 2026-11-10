"""HTTP, snapshot and crash recovery checks against disposable PostgreSQL only."""
import copy
import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.database import engine
from app.core.database import session
from app.core.database import now
from app.game_accounts.rosters import batches
from app.game_accounts.character_profiles import profiles
from app.game_accounts.schemas.batch_schemas import RoleSummaryBatchIn
from app.game_accounts.models.models import Account
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import Registration
from app.game_accounts.models.models import NameClaim
from app.game_accounts.models.models import CharacterRoleSummary
from app.game_accounts.models.models import RequestResult
from tests.game_accounts.test_role_summaries import owned
from tests.game_accounts.test_role_summaries import world
from tests.game_accounts.test_role_summaries import data
from tests.game_accounts.test_role_summaries import get
from tests.game_accounts.test_role_summaries import put
from tests.game_accounts.test_game_accounts import another_user
from tests.game_accounts.test_account_bootstrap import fingerprints

GET = '/v2/me/characters/personal-profiles'
POST = '/v2/me/role-summary-batches'


def command(cid, role='dealer', key=None, body=None):
    return dict(character_id=str(cid), role=role, command_id=str(key or uuid.uuid4()),
                **(body or data()))


def read(client, h, ids):
    return client.get(GET, headers=h, params=[('character_id', str(cid)) for cid in ids])


def write(client, h, commands):
    return client.post(POST, headers=h, json={'items': commands})


def expand(cid, count):
    ids = [str(cid)]
    with session() as db, db.begin():
        original = db.get(Character, uuid.UUID(cid))
        for i in range(1, count):
            c = Character(account_id=original.account_id, server_name=original.server_name,
                character_name='Batch'+str(i), summary=copy.deepcopy(original.summary),
                fetched_at=original.fetched_at, confirmed_at=original.confirmed_at)
            db.add(c); db.flush()
            db.add(NameClaim(server_name=c.server_name, character_name=c.character_name, character_id=c.id))
            ids.append(str(c.id))
    return ids


def rows(model):
    with session() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_nine_success_preserves_single_profiles_no_activity_and_bootstrap(client, owned, monkeypatch):
    from app.game_accounts.provider_io.provider import LostArkProvider
    from app.lostark_keys import service as credentials
    h, _, cid = owned
    ids = expand(cid, 9)
    def forbidden(*args, **kw): raise AssertionError('provider or credential access')
    monkeypatch.setattr(LostArkProvider, '_fetch', forbidden)
    monkeypatch.setattr(credentials, 'capture', forbidden)
    before = fingerprints()
    response = read(client, h, ids)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    assert fingerprints() == before

    assert len(response.json()['items']) == 9
    for item in response.json()['items']:
        assert item['profile'] == get(client, h, item['character_id']).json()
        assert item['status'] == 200 and item['error'] is None
    out = write(client, h, [command(c) for c in ids])
    assert out.status_code == 200 and out.headers['cache-control'] == 'no-store'
    assert len(out.json()['items']) == 9
    for item in out.json()['items']:
        assert item['status'] == 200 and item['error'] is None
        profile = get(client, h, item['character_id']).json()
        assert item['result'] == dict(character_id=item['character_id'], role='dealer',
            ownership_revision=1, lifecycle_revision=1, **profile['dealer'])
        assert profile['support']['version'] == 1
    assert client.get('/v2/me/account-bootstrap', headers=h).status_code == 200


def test_partial_two_failures_and_all_failure_correlations(client, owned):
    h, _, cid = owned
    ids = expand(cid, 9)
    commands = [command(c) for c in ids]
    commands[3]['expected_version'] = 99
    commands[7]['role'] = 'other'
    out = write(client, h, commands)
    assert out.status_code == 200
    items = out.json()['items']
    assert [x['status'] for x in items] == [200, 200, 200, 409, 200, 200, 200, 400, 200]
    for source, item in zip(commands, items):
        assert all(item[k] == source[k] for k in ('character_id', 'role', 'command_id'))
    assert rows(CharacterRoleSummary) == 7
    assert items[3]['error']['code'] == 'REVISION_CONFLICT'
    assert items[7]['error']['code'] == 'INVALID_ROLE'
    assert write(client, h, [commands[3], commands[7]]).json()['items'][0]['status'] == 409


@pytest.mark.parametrize('kind,status,code', [
    ('missing',404,'CHARACTER_NOT_FOUND'), ('deleted',404,'CHARACTER_NOT_FOUND'),
    ('foreign',404,'CHARACTER_NOT_FOUND'), ('lost',403,'OWNERSHIP_REQUIRED'),
    ('retired',409,'CHARACTER_UNUSABLE'), ('claim',409,'IDENTITY_CONFLICT'),
    ('suspect',200,None),
])
def test_read_guards_match_single(client, owned, login, monkeypatch, kind, status, code):
    h, r, cid = owned
    if kind == 'foreign': h = another_user(login, monkeypatch, client)
    with session() as db, db.begin():
        c = db.get(Character, uuid.UUID(cid))
        if kind == 'deleted': db.get(Registration, uuid.UUID(r['registration_id'])).deleted_at = now(db)
        if kind == 'lost': db.get(Account, c.account_id).owner_id = None
        if kind == 'retired': c.lifecycle_state = 'retired'
        if kind == 'suspect': c.lifecycle_state, c.status = 'suspect', 'suspect'
        if kind == 'claim': db.delete(db.get(NameClaim, (c.server_name, c.character_name)))
    if kind == 'missing': cid = str(uuid.uuid4())
    before = fingerprints()
    out = read(client, h, [cid]).json()['items'][0]
    assert out['status'] == status
    assert get(client, h, cid).status_code == status
    if code:
        assert out['profile'] is None and out['error']['code'] == code
        assert set(out) == {'character_id', 'status', 'profile', 'error'}
    assert fingerprints() == before
    count = rows(CharacterRoleSummary)
    out = write(client, h, [command(cid)]).json()['items'][0]
    assert out['status'] == (409 if kind == 'suspect' else status)
    assert rows(CharacterRoleSummary) == count


def test_read_query_rules_and_fifty_limit(client, owned):
    h, _, cid = owned
    for params in ([], [('character_id',cid)]*2, [('character_id','bad')],
                   [('character_id',cid),('extra','1')], [('character_id',str(uuid.uuid4()))]*51):
        assert client.get(GET, headers=h, params=params).status_code == 400
    assert client.request('GET', GET, params={'character_id':cid}, headers=h, content=b'{}').status_code == 400
    ids = expand(cid, 50)
    assert len(read(client, h, ids).json()['items']) == 50
    assert write(client, h, [command(c) for c in ids]).status_code == 200


@pytest.mark.parametrize('kind', ['empty','count','duplicate_key','duplicate_target','bad_uuid',
    'bad_role_type','bad_version','bad_summary','extra','missing','duplicate_json','nested_duplicate'])
def test_global_preflight_no_writes(client, owned, kind):
    h, _, cid = owned
    a = command(cid); b = command(str(uuid.uuid4()))
    body = {'items':[a,b]}
    if kind == 'empty': body['items'] = []
    if kind == 'count': body['items'] = [command(str(uuid.uuid4())) for _ in range(51)]
    if kind == 'duplicate_key': b['command_id'] = a['command_id']
    if kind == 'duplicate_target': b['character_id'] = cid
    if kind == 'bad_uuid': b['command_id'] = str(uuid.uuid1())
    if kind == 'bad_role_type': b['role'] = 4
    if kind == 'bad_version': b['expected_version'] = True
    if kind == 'bad_summary': b['summary']['observed_lifecycle_revision'] = 2
    if kind == 'extra': b['unknown'] = 1
    if kind == 'missing': del b['role']
    raw = json.dumps(body)
    if kind == 'duplicate_json': raw = raw.replace('"items":', '"items":[],"items":',1)
    if kind == 'nested_duplicate': raw = raw.replace('"source":', '"source":"x","source":',1)
    before = fingerprints()
    out = client.post(POST, headers={**h,'Content-Type':'application/json'}, content=raw)
    assert out.status_code == 400, out.text
    assert fingerprints() == before


def test_bytes_chunked_envelope_boundary_and_input_command_size(client, owned):
    h, _, cid = owned
    raw = json.dumps({'items':[command(cid)]}, ensure_ascii=False, separators=(',',':')).encode()
    padded = raw + b' '*(524288-len(raw))
    assert client.post(POST, headers={**h,'Content-Type':'application/json'}, content=padded).status_code == 200
    before = fingerprints()
    for body in (padded+b' ', iter([padded,b' '])):
        assert client.post(POST, headers=h, content=body).status_code == 413
        assert fingerprints() == before
    # Valid timestamp parses to a short datetime, but limits use its raw input representation.
    a = command(cid, 'support')
    a['summary']['analyzed_at'] = '2026-10-15T12:00:00.'+'0'*33000+'Z'
    assert write(client, h, [a]).status_code == 413
    assert fingerprints() == before
    a['summary']['analyzed_at'] = '2026-10-15T12:00:00.0Z'
    subset = {k:a[k] for k in ('expected_version','expected_ownership_revision','expected_lifecycle_revision','summary')}
    length = len(json.dumps(subset,ensure_ascii=False,separators=(',',':')).encode())
    a['summary']['analyzed_at'] = '2026-10-15T12:00:00.'+'0'*(32768-length+1)+'Z'
    out=write(client,h,[a])
    assert out.status_code==200 and out.json()['items'][0]['status']==200
    assert client.post(POST+'?extra=1',headers=h,json={'items':[command(cid)]}).status_code == 400


@pytest.mark.parametrize('kind', ['utf16','surrogate','nan','malformed'])
def test_non_utf8_or_invalid_json_no_write(client, owned, kind):
    h, _, cid = owned
    a=command(cid)
    if kind=='surrogate': a['role']='\ud800'
    if kind=='nan': a['expected_version']=float('nan')
    raw=json.dumps({'items':[a]})
    if kind=='utf16': raw=raw.encode('utf-16')
    if kind=='malformed': raw='{"items":'
    before=fingerprints()
    assert client.post(POST,headers={**h,'Content-Type':'application/json'},content=raw).status_code==400
    assert fingerprints()==before


def test_single_batch_both_directions_historical_and_fingerprint_conflict(client, owned):
    h, _, cid = owned
    a = command(cid)
    original = put(client,h,cid,key=a['command_id'])
    replay = write(client,h,[a]).json()['items'][0]
    assert replay['result'] == original.json()
    b = command(cid,'support')
    original_batch = write(client,h,[b]).json()['items'][0]['result']
    assert put(client,h,cid,role='support',key=b['command_id']).json() == original_batch
    newer = data(); newer['expected_version']=2; newer['summary']['combat_power']='999'
    assert put(client,h,cid,newer).json()['version'] == 3
    assert write(client,h,[a]).json()['items'][0]['result'] == original.json()
    changed = copy.deepcopy(a); changed['summary']['combat_power']='888'
    assert write(client,h,[changed]).json()['items'][0]['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert get(client,h,cid).json()['dealer']['version'] == 3


def test_same_key_concurrent_and_expiry_lease(client, owned):
    h, _, cid = owned
    a = command(cid)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: write(client,h,[a]).json()['items'][0],range(2)))
    assert any(r['status']==200 for r in results)
    assert all(r['status']==200 or r['error']['code']=='REQUEST_IN_PROGRESS' for r in results)
    assert get(client,h,cid).json()['dealer']['version']==2
    assert write(client,h,[a]).json()['items'][0]['status']==200
    with session() as db, db.begin():
        row=db.scalar(select(RequestResult).where(RequestResult.key==uuid.UUID(a['command_id'])))
        row.completed_at=now(db)-timedelta(hours=25)
    assert write(client,h,[a]).json()['items'][0]['error']['code']=='IDEMPOTENCY_EXPIRED'
    pending=command(cid,'support')
    with session() as db:
        from app.auth.models import User
        from app.auth.models import Session
        principal=(db.scalar(select(User)),db.scalar(select(Session)))
    ticket,_=profiles.reserve(principal,'role-summary',uuid.UUID(pending['command_id']),
        {'target':cid,'role':'support','body':data()})
    out=write(client,h,[pending]).json()['items'][0]
    assert out['error']['code']=='REQUEST_IN_PROGRESS' and out['error']['retry_after_seconds']==2
    with session() as db,db.begin(): db.get(RequestResult,ticket[0]).lease_expires_at=now(db)-timedelta(seconds=1)
    assert write(client,h,[pending]).json()['items'][0]['status']==200


@pytest.mark.parametrize('failure', ['database','budget','session'])
def test_mid_batch_stops_preserves_results_and_recovers(client, owned, monkeypatch, failure):
    h, _, cid = owned
    ids=expand(cid,3); commands=[command(c) for c in ids]
    original=profiles.put; calls=[]
    def wrapped(*args):
        calls.append(args)
        if len(calls)==2 and failure=='database': raise OperationalError('private SQL',{},Exception('secret'))
        result=original(*args)
        if len(calls)==1:
            if failure=='budget': monkeypatch.setattr(batches,'BUDGET_SECONDS',0)
            if failure=='session':
                from app.auth.models import Session
                with session() as db,db.begin(): db.scalar(select(Session)).revoked_at=now(db)
        return result
    monkeypatch.setattr(profiles,'put',wrapped)
    response=write(client,h,commands)
    assert response.status_code==200
    out=response.json()['items']
    assert out[0]['status']==200 and out[2]['error']['code']=='BATCH_NOT_PROCESSED'
    assert rows(CharacterRoleSummary)==1
    if failure=='database':
        assert out[1]['error']['code']=='SERVICE_UNAVAILABLE'
        assert 'secret' not in response.text and 'private SQL' not in response.text
    if failure=='session': assert out[1]['status']==401
    monkeypatch.setattr(profiles,'put',original);monkeypatch.setattr(batches,'BUDGET_SECONDS',20)
    if failure!='session':
        assert all(i['status']==200 for i in write(client,h,commands).json()['items'])
        assert rows(CharacterRoleSummary)==3


def test_post_commit_response_loss_replays_without_increment(client, owned, monkeypatch):
    h, _, cid=owned
    a=command(cid); original=profiles.put
    def lost(*args):
        original(*args)
        raise OperationalError('lost commit ack',{},Exception('lost'))
    monkeypatch.setattr(profiles,'put',lost)
    assert write(client,h,[a]).json()['items'][0]['error']['code']=='SERVICE_UNAVAILABLE'
    monkeypatch.setattr(profiles,'put',original)
    assert write(client,h,[a]).json()['items'][0]['result']['version']==2
    assert rows(CharacterRoleSummary)==1


@pytest.mark.parametrize('kind,status', [('expired',401),('revoked',401),('disabled',403)])
def test_global_auth_rejects_before_reservation(client, owned, kind, status):
    from app.auth.models import User
    from app.auth.models import Session
    h, _, cid = owned
    with session() as db, db.begin():
        s = db.scalar(select(Session))
        if kind == 'expired': s.idle_expires_at = now(db)-timedelta(seconds=1)
        elif kind == 'revoked': s.revoked_at = now(db)
        else: db.scalar(select(User)).status = 'disabled'
    before = fingerprints()
    assert write(client,h,[command(cid)]).status_code == status
    assert read(client,h,[cid]).status_code == status
    assert fingerprints() == before


@pytest.mark.parametrize('kind', ['ownership','lifecycle','role'])
def test_read_does_not_bypass_current_write_fences(client, owned, kind):
    h, _, cid=owned
    a=command(cid)
    assert read(client,h,[cid]).json()['items'][0]['status']==200
    if kind=='role': assert put(client,h,cid).status_code==200
    else:
        with session() as db, db.begin():
            c=db.get(Character,uuid.UUID(cid))
            if kind=='ownership': db.get(Account,c.account_id).ownership_revision+=1
            else: c.lifecycle_revision+=1
    before=rows(CharacterRoleSummary)
    assert write(client,h,[a]).json()['items'][0]['error']['code']=='REVISION_CONFLICT'
    assert rows(CharacterRoleSummary)==before


def test_partial_commit_then_real_worker_exit_recovers(client, owned):
    h, _, cid=owned;ids=expand(cid,3);commands=[command(c) for c in ids]
    # Kill only an isolated test subprocess, after its first committed item.
    code="\nimport json\nimport os\nimport sys\nimport uuid\nfrom sqlalchemy import select\nfrom app.core.database import session\nfrom app.auth.models import User\nfrom app.auth.models import Session\nfrom app.game_accounts.rosters import batches\nfrom app.game_accounts.character_profiles import profiles\nfrom app.game_accounts.schemas.batch_schemas import RoleSummaryBatchIn\nwith session() as db:\n    principal=(db.get(User,uuid.UUID(sys.argv[1])),db.get(Session,uuid.UUID(sys.argv[2])))\noriginal=profiles.put\ndef terminate(*args):\n    original(*args)\n    os._exit(23)\nprofiles.put=terminate\nbatches.put(principal,RoleSummaryBatchIn.model_validate(json.loads(sys.stdin.read())),'crash-test')\n"
    from app.auth.models import User
    from app.auth.models import Session
    with session() as db: uid,sid=str(db.scalar(select(User.id))),str(db.scalar(select(Session.id)))
    process=subprocess.run([sys.executable,'-c',code,uid,sid],input=json.dumps({'items':commands}),
                           text=True,capture_output=True,timeout=30)
    assert process.returncode==23,process.stderr
    assert rows(CharacterRoleSummary)==1
    assert all(i['result']['version']==2 for i in write(client,h,commands).json()['items'])
    assert rows(CharacterRoleSummary)==3


def test_snapshot_and_constant_select_count(client, owned, monkeypatch):
    h, _, cid=owned;ids=expand(cid,50)
    counts=[]
    for size in (1,9,50):
        queries=[]
        def record(conn,cursor,statement,*args):
            if statement.lstrip().upper().startswith('SELECT'): queries.append(statement)
        event.listen(engine(),'before_cursor_execute',record)
        try: assert read(client,h,ids[:size]).status_code==200
        finally: event.remove(engine(),'before_cursor_execute',record)
        counts.append(len(queries))
    assert counts[0]==counts[1]==counts[2],counts
    original=batches.current_personal_rows;changed=[]
    def mutate(*args):
        if not changed:
            changed.append(True)
            with session() as db,db.begin(): db.get(Character,uuid.UUID(cid)).lifecycle_revision=2
        return original(*args)
    monkeypatch.setattr(batches,'current_personal_rows',mutate)
    assert read(client,h,[cid]).json()['items'][0]['profile']['lifecycle_revision']==1
    assert get(client,h,cid).json()['lifecycle_revision']==2
    print('BATCH_READ_SELECT_COUNTS',counts)


def test_nine_local_http_comparison(client, owned):
    h, _, cid=owned;ids=expand(cid,9)
    start=time.perf_counter();responses=[]
    for c in ids: responses.extend([get(client,h,c),put(client,h,c)])
    single=time.perf_counter()-start
    start=time.perf_counter()
    bulk=[read(client,h,ids),write(client,h,[command(c,'support') for c in ids])]
    batch=time.perf_counter()-start
    assert all(r.status_code==200 for r in responses+bulk)
    assert all(i['status']==200 for i in bulk[1].json()['items'])
    print('LOCAL_SYNTHETIC_COMPARISON',json.dumps(dict(
        characters=9,single_calls=18,batch_calls=2,
        single_seconds=round(single,4),batch_seconds=round(batch,4),
        single_response_bytes=sum(len(r.content) for r in responses),
        batch_response_bytes=sum(len(r.content) for r in bulk))))
