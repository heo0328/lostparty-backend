"""Current ownership gates for commands, late results and retained private cache."""
import uuid
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts import power_service, service, lifecycle, observations
from app.game_accounts.models import Account, Registration, ScopedPowerCache, RequestResult
from tests.test_game_accounts import world, register, verify, change, page, BASE
from tests.test_combat_power import endpoint, body, seed_provider


def lose_ownership(registration):
    with session() as db, db.begin():
        r=db.get(Registration,uuid.UUID(registration['registration_id']))
        account=db.get(Account,r.account_id)
        account.owner_id=None
        account.ownership_revision+=1


@pytest.mark.parametrize('lost', [False,True])
def test_unowned_rejected_before_credentials_and_provider(client,world,monkeypatch,lost):
    h,state=world;r=register(client,h)
    if lost:
        verify(client,h,state,r['registration_id']);lose_ownership(r)
    def forbidden(*args):pytest.fail('unowned command must not access credential or provider')
    monkeypatch.setattr(power_service.credentials,'capture',forbidden)
    monkeypatch.setattr(power_service,'fetch_power',forbidden)
    for _ in range(2):
        response=change(client,h,'post',endpoint(r),body('a0'))
        assert response.status_code==403 and response.json()['error']['code']=='OWNERSHIP_REQUIRED'
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ScopedPowerCache))==0


@pytest.mark.parametrize('lost', [False,True])
def test_retained_preview_and_cache_are_masked_not_erased(client,world,lost):
    h,state=world;r=register(client,h)
    if lost:
        verify(client,h,state,r['registration_id']);lose_ownership(r)
    with session() as db,db.begin():
        registration=db.get(Registration,uuid.UUID(r['registration_id']))
        registration.preview=[dict(row,combat_power='9876') for row in registration.preview]
        cache=ScopedPowerCache(actor_id=registration.user_id,scope_key='retained-old-preview',
            **lifecycle.power_scope(registration),credential_version=1,server_name='sample-server',
            character_name='a0',value='8765',fetched_at=now(db),checked_at=now(db),
            status='available',generation=1)
        db.add(cache)
    pages=[page(client,h,r['registration_id'])['characters']['items'],
           client.get('/v2/me/game-accounts/'+r['registration_id']+'/characters',headers=h).json()['items']]
    for items in pages:
        for row in items:
            assert row['combat_power'] is row['power_fetched_at'] is row['power_checked_at'] is row['power_reason'] is None
            assert row['power_status']=='unknown' and row['power_stale'] is True
    assert client.get(BASE,headers=h).json()['items'][0]['representative_summary'] is None
    with session() as db:
        registration=db.get(Registration,uuid.UUID(r['registration_id']))
        assert registration.preview[0]['combat_power']=='9876'
        assert db.scalar(select(ScopedPowerCache)).value=='8765'


def test_success_replay_rechecks_current_ownership(client,world,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    calls=seed_provider(monkeypatch,'111');key=uuid.uuid4()
    first=change(client,h,'post',endpoint(r),body('a0'),key)
    assert first.status_code==200
    with session() as db:
        stored_before=db.scalar(select(RequestResult).where(RequestResult.operation=='power')).result
    lose_ownership(r)
    replay=change(client,h,'post',endpoint(r),body('a0'),key)
    assert replay.status_code==403 and replay.json()['error']['code']=='OWNERSHIP_REQUIRED'
    assert len(calls)==1
    with session() as db:
        assert db.scalar(select(ScopedPowerCache)).value=='111'
        result=db.scalar(select(RequestResult).where(RequestResult.operation=='power'))
        assert result.result==stored_before # compare stored history without wire datetime normalization


def test_ownership_loss_after_replay_reservation_is_rechecked(client,world,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    seed_provider(monkeypatch);key=uuid.uuid4()
    assert change(client,h,'post',endpoint(r),body('a0'),key).status_code==200
    original=power_service.reserve
    def racing(*args):
        result=original(*args);lose_ownership(r);return result
    monkeypatch.setattr(power_service,'reserve',racing)
    response=change(client,h,'post',endpoint(r),body('a0'),key)
    assert response.status_code==403 and response.json()['error']['code']=='OWNERSHIP_REQUIRED'


def test_ownership_lost_during_provider_never_commits_private_result(client,world,monkeypatch):
    h,state=world;r=register(client,h);verify(client,h,state,r['registration_id'])
    def racing(*args):
        lose_ownership(r);return 'available','999',None
    monkeypatch.setattr(power_service,'fetch_power',racing)
    response=change(client,h,'post',endpoint(r),body('a0'))
    assert response.status_code==403 and response.json()['error']['code']=='OWNERSHIP_REQUIRED'
    with session() as db:
        assert all(c.value is None and c.lease_expires_at is None for c in db.scalars(select(ScopedPowerCache)))
        assert db.scalar(select(RequestResult).where(RequestResult.operation=='power')).completed_at is None


def test_direct_preview_projects_old_observation_without_mutation(client,world,monkeypatch):
    from datetime import datetime,timezone
    h,_=world
    rows=[dict(server_name='sample-server',character_name='a0',class_name='sample-class',
               character_level=60,item_level='1700',combat_power='123')]
    monkeypatch.setattr(service,'lookup',lambda *a,**kw:observations.Observation(rows,datetime.now(timezone.utc)))
    response=client.post('/v1/game-accounts/preview',headers=h,json={'character_name':'a0'})
    assert response.status_code==200 and response.json()['characters'][0]['combat_power'] is None
    assert rows[0]['combat_power']=='123'


@pytest.mark.parametrize('operation', ['patch','refresh'])
def test_registration_success_replay_masks_old_representative(client,world,monkeypatch,operation):
    from tests.test_game_accounts import save_data
    h,state=world;r=register(client,h,main=True);verify(client,h,state,r['registration_id'])
    current=page(client,h,r['registration_id'])
    assert change(client,h,'put',BASE+'/'+r['registration_id']+'/character-settings',save_data(current)).status_code==200
    seed_provider(monkeypatch,'777')
    assert change(client,h,'post',endpoint(r),body('a0')).status_code==200
    latest=client.get(BASE,headers=h).json()['items'][0]
    key=uuid.uuid4()
    url=BASE+'/'+r['registration_id']+('/refresh' if operation=='refresh' else '')
    data={} if operation=='refresh' else {'label':'new-label','expected_version':latest['version']}
    method='post' if operation=='refresh' else 'patch'
    first=change(client,h,method,url,data,key)
    assert first.status_code==200
    first_reg=first.json()['registration'] if operation=='refresh' else first.json()
    assert first_reg['representative_summary']['combat_power']=='777'
    with session() as db:
        stored_before=db.scalar(select(RequestResult).where(RequestResult.operation==operation,RequestResult.key==key)).result
    lose_ownership(r)
    replay=change(client,h,method,url,data,key)
    assert replay.status_code==200
    replay_reg=replay.json()['registration'] if operation=='refresh' else replay.json()
    assert replay_reg['representative_summary'] is None
    with session() as db:
        result=db.scalar(select(RequestResult).where(RequestResult.operation==operation,RequestResult.key==key))
        assert result.result==stored_before
