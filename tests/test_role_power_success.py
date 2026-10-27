"""Exercise unchanged public P1 writes and the new transaction-local evidence."""
import uuid
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from app.core.database import session
from app.game_accounts import profiles
from app.game_accounts.models import Account, Character
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.support import GameError
from tests.test_role_summaries import owned, world, put, get, data


def success(cid, role='dealer', ownership=1):
    with session() as db:
        row = db.scalar(select(RolePowerSuccess).where(
            RolePowerSuccess.character_id == uuid.UUID(cid),
            RolePowerSuccess.role == role, RolePowerSuccess.ownership_revision == ownership))
        if row is None:
            return None
        return {key:deepcopy(getattr(row,key)) for key in (
            'combat_power','observed_at','source_summary_version','source_saved_at',
            'source_summary','power_revision','record_created_at','record_updated_at')}


def changed(expected, value, stamp='2026-10-15T13:00:00Z'):
    body=data();body['expected_version']=expected
    body['summary'].update(combat_power=value,combat_power_observed_at=stamp if value is not None else None,
                           analyzed_at=stamp)
    return body


def test_build_error_still_retains_precise_value_and_exact_observation(client,owned):
    h,_,cid=owned;body=data()
    body['summary'].update(combat_power='100.4999',integrity_status='error',
                           issues=[{'code':'GEM_SLOT_COUNT','severity':'error'}])
    response=put(client,h,cid,body)
    assert response.status_code==200
    evidence=success(cid)
    assert evidence['combat_power']=='100.4999' and evidence['source_summary']==response.json()['summary']
    assert evidence['source_summary_version']==2 and evidence['power_revision']==2
    assert evidence['source_saved_at'].isoformat()==response.json()['saved_at'].replace('Z','+00:00')


def test_null_head_never_fabricates_or_erases_success(client,owned):
    h,_,cid=owned
    assert get(client,h,cid).status_code==200 and success(cid) is None
    assert put(client,h,cid,changed(1,None)).status_code==200 and success(cid) is None
    assert put(client,h,cid,changed(2,'100.50')).status_code==200
    before=success(cid)
    assert put(client,h,cid,changed(3,None,'2026-10-15T14:00:00Z')).status_code==200
    assert get(client,h,cid).json()['dealer']['summary']['combat_power'] is None
    assert success(cid)==before


def test_new_lower_observation_wins_delayed_max_and_replay_do_not(client,owned):
    h,_,cid=owned;key=uuid.uuid4()
    original=put(client,h,cid,key=key)
    assert original.status_code==200
    assert put(client,h,cid,changed(2,'100.4999')).status_code==200
    before=success(cid)
    delayed=changed(3,'999999','2026-10-15T12:00:00Z')
    assert put(client,h,cid,delayed).status_code==200
    assert get(client,h,cid).json()['dealer']['summary']['combat_power']=='999999'
    assert success(cid)==before
    delayed['expected_version']=4
    assert put(client,h,cid,delayed).json()['version']==4  # no-op
    assert put(client,h,cid,key=key).json()==original.json()
    assert success(cid)==before
    assert put(client,h,cid,changed(4,'99.9')).status_code==200  # same observation, higher head version
    assert success(cid)['combat_power']=='99.9' and success(cid)['source_summary_version']==5
    assert success(cid)['power_revision']==4


def test_concurrent_head_cas_has_one_success_snapshot(client,owned):
    h,_,cid=owned
    assert put(client,h,cid).status_code==200
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda value:put(client,h,cid,changed(2,value)),['100.11','100.12']))
    assert sorted(r.status_code for r in responses)==[200,409]
    current=get(client,h,cid).json()['dealer']
    assert success(cid)['combat_power']==current['summary']['combat_power']
    assert success(cid)['source_summary_version']==current['version']==3
    assert success(cid)['power_revision']==3


def test_commit_failure_rolls_back_head_and_success_then_same_key_recovers(client,owned,monkeypatch):
    h,_,cid=owned
    assert put(client,h,cid).status_code==200
    before=success(cid);key=uuid.uuid4();commit=profiles.commit_result
    def fail(*args,**kwargs):raise GameError('REQUEST_IN_PROGRESS',409,2)
    monkeypatch.setattr(profiles,'commit_result',fail)
    assert put(client,h,cid,changed(2,'50'),key=key).status_code==409
    assert get(client,h,cid).json()['dealer']['version']==2 and success(cid)==before
    monkeypatch.setattr(profiles,'commit_result',commit)
    assert put(client,h,cid,changed(2,'50'),key=key).status_code==200
    assert success(cid)['combat_power']=='50' and success(cid)['power_revision']==3


def test_role_and_owner_generations_do_not_borrow_values(client,owned):
    h,_,cid=owned
    assert put(client,h,cid).status_code==200 and success(cid,'support') is None
    assert put(client,h,cid,changed(1,'5'),role='support').status_code==200
    assert success(cid,'dealer')['combat_power']=='12345.00' and success(cid,'support')['combat_power']=='5'
    with session() as db,db.begin():
        character=db.get(Character,uuid.UUID(cid));account=db.get(Account,character.account_id)
        account.ownership_revision+=1
    assert get(client,h,cid).json()['dealer']['summary'] is None and success(cid,ownership=2) is None
    body=changed(1,'2');body['expected_ownership_revision']=2
    assert put(client,h,cid,body).status_code==200
    assert success(cid,ownership=2)['combat_power']=='2'
    assert success(cid,ownership=1)['combat_power']=='12345.00'


def test_retirement_cleanup_and_rollback_are_targeted(client,owned):
    from sqlalchemy import func
    from app.game_accounts import lifecycle
    from app.game_accounts.support import lock
    from tests.test_game_accounts import page
    import pytest
    h,r,cid=owned
    other=page(client,h,r['registration_id'])['characters']['items'][1]['character_id']
    assert put(client,h,cid).status_code==200 and put(client,h,other).status_code==200
    before,other_before=success(cid),success(other)
    with pytest.raises(RuntimeError),session() as db,db.begin():
        lock(db,'game-mutations-v1');character=db.get(Character,uuid.UUID(cid));account=db.get(Account,character.account_id)
        lifecycle.retire(db,account,character,lifecycle.evidence(db,account,complete=True))
        assert db.scalar(select(func.count()).select_from(RolePowerSuccess).where(RolePowerSuccess.character_id==character.id))==0
        raise RuntimeError('rollback synthetic retirement')
    assert success(cid)==before and success(other)==other_before
    with session() as db,db.begin():
        lock(db,'game-mutations-v1');character=db.get(Character,uuid.UUID(cid));account=db.get(Account,character.account_id)
        lifecycle.retire(db,account,character,lifecycle.evidence(db,account,complete=True))
    assert success(cid) is None and success(other)==other_before
