"""Current stored analysis reads; no old client summary producer."""
import copy
import uuid
import pytest
from sqlalchemy import event
from app.core.database import engine, session, now
from app.game_accounts.rosters import batches
from app.game_accounts.provider_io import credentials
from app.game_accounts.provider_io.provider import LostArkProvider
from app.game_accounts.models.models import Account, Character, Registration, NameClaim
from tests.game_accounts.test_role_summaries import owned, world, get, put
from tests.game_accounts.test_game_accounts import another_user
from tests.game_accounts.test_account_bootstrap import fingerprints

GET='/v2/me/characters/personal-profiles'


def read(client, h, ids):
    return client.get(GET, headers=h, params=[('character_id', str(cid)) for cid in ids])


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


def test_read_query_rules_and_fifty_limit(client, owned):
    h, _, cid = owned
    for params in ([], [('character_id',cid)]*2, [('character_id','bad')],
                   [('character_id',cid),('extra','1')], [('character_id',str(uuid.uuid4()))]*51):
        assert client.get(GET, headers=h, params=params).status_code == 400
    assert client.request('GET', GET, params={'character_id':cid}, headers=h, content=b'{}').status_code == 400
    ids = expand(cid, 50)
    assert len(read(client, h, ids).json()['items']) == 50


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


def test_saved_and_unset_profiles_match_single_reads_without_provider_or_writes(client,owned,monkeypatch):
    h,_,cid=owned;ids=expand(cid,9)
    put(client,h,cid)
    def forbidden(*args,**kwargs):raise AssertionError('Stored reads cannot access provider or credentials')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden)
    monkeypatch.setattr(credentials,'capture',forbidden)
    before=fingerprints()
    response=read(client,h,ids)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    for item in response.json()['items']:
        assert item['status']==200 and item['error'] is None
        assert item['profile']==get(client,h,item['character_id']).json()
    assert response.json()['items'][0]['profile']['dealer']['detail'] is not None
    assert response.json()['items'][1]['profile']['dealer']['detail'] is None
    assert fingerprints()==before
