"""Current-owned roster policy, using the real collector with fake HTTP."""
import json
import uuid
from urllib.parse import unquote
import pytest
from sqlalchemy import select, func, delete
from app.core.database import session, now
from app.game_accounts import observations, provider, lifecycle
from app.game_accounts.models import Account, Character, Registration, NameClaim, Configuration, Audit, LimitEvent, CharacterRetirement, CharacterRoleSummary
from tests.test_game_accounts import world, register, verify, page, change, save_data, BASE
from tests.test_game_account_primitives import transport

LIVE_FETCH = observations.fetch


@pytest.fixture
def roster(world, client, monkeypatch):
    h, state = world
    r = register(client, h, main=True)
    verify(client, h, state, r['registration_id'])
    state['binding'] = False
    wire = dict(names=['a0','a1','a2'], status={}, calls=[], malformed=None, server='sample-server')
    monkeypatch.setattr(observations, 'fetch', LIVE_FETCH)
    def get(url, **kwargs):
        assert url.endswith('/siblings')
        name = unquote(url.split('/')[-2])
        wire['calls'].append(name)
        code = wire['status'].get(name, 200)
        body = [dict(ServerName=wire['server'], CharacterName=n, CharacterClassName='sample-class',
                     CharacterLevel=60, ItemAvgLevel='1700.00') for n in wire['names']]
        if wire['malformed'] == 'duplicate': body.append(dict(body[0]))
        elif wire['malformed'] == 'entry': body.append(None)
        elif wire['malformed'] == 'empty': body = []
        _, response = transport(status=code, body=json.dumps(body).encode())
        return response
    monkeypatch.setattr(provider.requests, 'get', get)
    return h, r, wire


def refresh(client, h, r, key=None):
    return change(client, h, 'post', BASE+'/'+r['registration_id']+'/refresh', {}, key)


def clear_quota():
    with session() as db, db.begin(): db.execute(delete(LimitEvent))


def names(client, h, r):
    return {c['character_name']: c for c in page(client,h,r['registration_id'])['characters']['items']}


def test_owned_api_roster_adds_new_ids_blocks_missing_and_preserves_selection(client, roster):
    h, r, wire = roster
    p = page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(p)).status_code == 200
    old = names(client,h,r)
    with session() as db:
        a = db.scalar(select(Account)); before = (a.owner_id,a.ownership_revision,a.verified_at,a.roster_revision)
    wire['names'] = ['a0','a1','a3']
    key = uuid.uuid4()
    response = refresh(client,h,r,key)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result['added_count'],result['suspect_count'],result['requires_refresh']) == (1,1,True)
    current = names(client,h,r)
    assert current['a0']['character_id'] == old['a0']['character_id']
    assert current['a2']['roster_status'] == 'suspect' and not current['a2']['eligible']
    assert current['a3']['character_id'] not in {c['character_id'] for c in old.values()}
    settings = result['registration']['settings']
    assert set(settings['activity_character_ids']) == {c['character_id'] for c in old.values()}
    assert settings['representative_character_id'] == old['a0']['character_id']
    assert settings['configuration_state'] == 'needs_reconfiguration'
    with session() as db:
        a = db.scalar(select(Account))
        assert (a.owner_id,a.ownership_revision,a.verified_at) == before[:3]
        assert a.roster_revision == before[3]+1
        assert db.scalar(select(func.count()).select_from(Audit)) == 1
        assert db.scalar(select(func.count()).select_from(CharacterRoleSummary)) == 0
        assert db.scalar(select(func.count()).select_from(CharacterRetirement)) == 0
    assert refresh(client,h,r,key).json() == result
    assert wire['calls'] == ['a0']
    # All stored-list reads remain independent of provider calls.
    client.get(BASE,headers=h)
    client.get('/v2/me/game-accounts/'+r['registration_id']+'/characters',headers=h)
    assert wire['calls'] == ['a0']


def test_explicit_404_recovers_lookup_but_preserves_verification_and_owner(client, roster):
    h, r, wire = roster
    with session() as db:
        a = db.scalar(select(Account)); owner, verified_at = a.owner_id,a.verified_at
    wire['names'] = ['a1','a2','new-name']
    wire['status']['a0'] = 404
    response = refresh(client,h,r)
    assert response.status_code == 200, response.text
    assert wire['calls'] == ['a0','a1']
    assert response.json()['registration']['ownership_status'] == 'owned'
    with session() as db:
        saved = db.get(Registration,uuid.UUID(r['registration_id']))
        assert saved.lookup_name == 'a1'
        a = db.get(Account,saved.account_id)
        assert (a.owner_id,a.verified_at) == (owner,verified_at)
        from app.game_accounts.models import Verification
        assert db.scalar(select(Verification.lookup_name)) == 'a0'
    assert names(client,h,r)['a0']['roster_status'] == 'suspect'
    clear_quota(); wire['calls'].clear()
    assert refresh(client,h,r).status_code == 200
    assert wire['calls'] == ['a1']


@pytest.mark.parametrize('kind',[500,429,401,'duplicate','entry','empty','missing_target','wrong_server'])
def test_failed_refresh_is_atomic_and_never_revokes_ownership(client, roster, kind):
    h, r, wire = roster
    before = page(client,h,r['registration_id'])
    if isinstance(kind,int): wire['status']['a0'] = kind
    elif kind == 'missing_target': wire['names'] = ['a1','a2']
    elif kind == 'wrong_server': wire['server'] = 'foreign-server'
    else: wire['malformed'] = kind
    response = refresh(client,h,r)
    assert response.status_code in (409,503), response.text
    assert wire['calls'] == ['a0']
    assert page(client,h,r['registration_id']) == before
    assert client.get(BASE,headers=h).json()['items'][0]['ownership_status'] == 'owned'


def test_recovery_is_bounded_and_no_anchor_does_not_revoke_owner(client, roster):
    h, r, wire = roster
    before = page(client,h,r['registration_id'])
    wire['status'] = dict.fromkeys(['a0','a1','a2'],404)
    assert refresh(client,h,r).status_code == 503
    assert wire['calls'] == ['a0','a1','a2']
    assert page(client,h,r['registration_id']) == before
    clear_quota(); wire['calls'].clear()
    with session() as db,db.begin():
        for c in db.scalars(select(Character)): c.status,c.lifecycle_state = 'suspect','suspect'
    assert refresh(client,h,r).json()['error']['code'] == 'ACCOUNT_BINDING_EVIDENCE_PENDING'
    assert wire['calls'] == []
    assert client.get(BASE,headers=h).json()['items'][0]['ownership_status'] == 'owned'


def test_normal_owned_api_reappearance_recovers_current_suspect_not_retired(client, roster):
    h, r, wire = roster
    old = names(client,h,r)
    wire['names'] = ['a0','a1']
    assert refresh(client,h,r).status_code == 200
    clear_quota(); wire['names'] = ['a0','a1','a2']
    response = refresh(client,h,r)
    assert response.status_code == 200 and response.json()['suspect_count'] == 0
    assert names(client,h,r)['a2']['eligible']
    assert names(client,h,r)['a2']['character_id'] == old['a2']['character_id']
    clear_quota()
    with session() as db, db.begin():
        c = db.get(Character,uuid.UUID(old['a2']['character_id']))
        a = db.get(Account,c.account_id)
        lifecycle.retire(db,a,c,lifecycle.evidence(db,a,complete=True))
    response = refresh(client,h,r)
    assert response.status_code == 200
    assert names(client,h,r)['a2']['character_id'] != old['a2']['character_id']
    with session() as db:
        assert db.get(Character,uuid.UUID(old['a2']['character_id'])).lifecycle_state == 'retired'


def test_foreign_claim_cannot_enter_current_owned_roster(client, roster):
    h, r, wire = roster
    with session() as db,db.begin():
        original = db.scalar(select(Account))
        foreign = Account(owner_id=original.owner_id,verified_at=now(db))
        db.add(foreign);db.flush()
        c = Character(account_id=foreign.id,server_name='sample-server',character_name='foreign',
            summary=dict(server_name='sample-server',character_name='foreign',class_name='sample-class',character_level=60,item_level='1700',combat_power=None),fetched_at=now(db),confirmed_at=now(db))
        db.add(c);db.flush()
        db.add(NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id))
    before = page(client,h,r['registration_id'])
    wire['names'] += ['foreign']
    response = refresh(client,h,r)
    assert response.status_code == 409 and response.json()['error']['code'] == 'IDENTITY_CONFLICT'
    assert page(client,h,r['registration_id']) == before


@pytest.mark.parametrize('change_kind',['version','owner','key','deleted'])
def test_registration_change_during_network_rejects_late_observation(client, roster, monkeypatch, change_kind):
    h, r, wire = roster
    original = provider.requests.get
    def changed(*args,**kwargs):
        result = original(*args,**kwargs)
        with session() as db,db.begin():
            saved=db.get(Registration,uuid.UUID(r['registration_id']))
            if change_kind == 'owner':
                a=db.get(Account,saved.account_id);a.owner_id=None;a.ownership_revision += 1
            elif change_kind == 'key':
                from app.lostark_keys.models import Credential
                db.scalar(select(Credential)).version += 1
            else:
                saved.version += 1
                if change_kind == 'deleted': saved.deleted_at=now(db)
        return result
    monkeypatch.setattr(provider.requests,'get',changed)
    wire['names'] += ['new-name']
    response=refresh(client,h,r)
    expected = 'LOSTARK_KEY_CHANGED' if change_kind == 'key' else 'REGISTRATION_NOT_FOUND' if change_kind == 'deleted' else 'REVISION_CONFLICT'
    assert response.status_code == (404 if change_kind == 'deleted' else 409)
    assert response.json()['error']['code'] == expected
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Character).where(Character.character_name == 'new-name')) == 0
