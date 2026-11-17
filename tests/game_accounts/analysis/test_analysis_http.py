"""Real PostgreSQL/HTTP command tests; provider responses are synthetic."""
import copy
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select, func
from app.core.database import session, now
from app.game_accounts.models.models import Character, CharacterRoleSummary, RequestResult
from app.game_accounts.analysis import service
from app.game_accounts.provider_io.provider import LostArkProvider, ProviderUnavailable
from app.game_accounts.common.support import GameError
from tests.game_accounts.test_role_summaries import owned
from tests.game_accounts.test_game_accounts import world
from tests.game_accounts.analysis.test_analyzer import fixture, CASES

URL='/v2/me/character-analysis/refresh'


@pytest.fixture
def subject(owned,monkeypatch):
    h,r,cid=owned
    with session() as db,db.begin():
        c=db.get(Character,uuid.UUID(cid));c.summary={**c.summary,'class_name':'바드'}
        name,server=c.character_name,c.server_name
    raw=fixture(CASES[0]);raw['ArmoryProfile'].update(CharacterName=name,ServerName=server)
    monkeypatch.setattr(LostArkProvider,'armory',lambda self,name:copy.deepcopy(raw))
    return h,uuid.UUID(cid),raw


def command(cid,**changes):
    body=dict(command_id=str(uuid.uuid4()),character_id=str(cid),expected_ownership_revision=1,
              expected_lifecycle_revision=1,expected_summary_versions=dict(dealer=1,support=1),trigger='manual')
    body.update(changes);return body


def post(client,h,body):
    response=client.post(URL,headers=h,json={'items':[body]})
    assert response.status_code==200,response.text
    from jsonschema import Draft202012Validator, FormatChecker
    schema=json.loads(Path('docs/features/rosters/power-and-profiles/analysis-refresh.schema.json').read_text())
    Draft202012Validator({**schema,'$ref':'#/$defs/Response'},format_checker=FormatChecker()).validate(response.json())
    return response.json()['items'][0]


def head(cid,role='support'):
    with session() as db:
        row=db.scalar(select(CharacterRoleSummary).where(CharacterRoleSummary.character_id==cid,CharacterRoleSummary.role==role))
        return None if row is None else dict(version=row.version,summary=copy.deepcopy(row.summary),detail=copy.deepcopy(row.detail),saved_at=row.saved_at)


def test_detected_role_setting_error_and_stored_detail(client,subject):
    h,cid,raw=subject
    result=post(client,h,command(cid))
    assert result['state']=='saved' and result['detected_role']=='support'
    assert result['result']['analysis']['summary']['integrity_status']=='error'
    stored=head(cid)
    assert stored['version']==2 and stored['detail']['detection']['detected_role']=='support'
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('GET must not fetch')):
        response=client.get(f'/v2/me/characters/{cid}/personal-profile',headers=h)
        assert response.status_code==200,response.text
        assert response.json()['support']==result['result']['analysis']
        response=client.get('/v2/me/account-bootstrap',headers=h)
        assert response.status_code==200,response.text
        for r in response.json()['registrations']:
            for profile in r['personal_profiles']:
                assert 'detail' not in profile['support']


def test_lower_power_null_and_failure_do_not_share_a_success_fallback(client,subject,monkeypatch):
    from app.raid_rooms.participation.participation_core import power_value
    h,cid,raw=subject
    assert post(client,h,command(cid))['state']=='saved'
    raw['ArmoryProfile']['CombatPower']='10.00'
    assert post(client,h,command(cid,expected_summary_versions=dict(dealer=99,support=2)))['state']=='saved'
    assert head(cid)['summary']['combat_power']=='10.00'
    raw['ArmoryProfile']['CombatPower']=None
    assert post(client,h,command(cid,expected_summary_versions=dict(dealer=99,support=3)))['state']=='saved'
    saved=head(cid)
    with session() as db:
        row=db.scalar(select(CharacterRoleSummary).where(CharacterRoleSummary.character_id==cid))
        assert power_value('support','100',row,1)['state']=='missing'
    monkeypatch.setattr(LostArkProvider,'armory',lambda *a:(_ for _ in ()).throw(ProviderUnavailable()))
    assert post(client,h,command(cid,expected_summary_versions=dict(dealer=1,support=4)))['state']=='failed'
    assert head(cid)==saved


def test_ack_and_id_conflict_do_not_fetch_or_write(client,subject):
    h,cid,raw=subject;body=command(cid)
    first=post(client,h,body)
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('ACK must not fetch')):
        assert post(client,h,body)==first
    different={**body,'trigger':'automatic'}
    assert post(client,h,different)['error']['code']=='IDEMPOTENCY_CONFLICT'
    assert head(cid)['version']==2


def test_detected_role_cas_conflict(client,subject):
    h,cid,raw=subject
    assert post(client,h,command(cid))['state']=='saved'
    saved=head(cid)
    response=post(client,h,command(cid))
    assert response['state']=='failed' and response['error']['code']=='REVISION_CONFLICT'
    assert head(cid)==saved


@pytest.mark.parametrize('bad', ['bool','duplicate','role','empty','too_many','non_uuid4','noncanonical_command','noncanonical_character','query','oversize','duplicate_json'])
def test_preflight_rejects_before_reservation(client,subject,bad):
    h,cid,raw=subject;body=command(cid);payload={'items':[body]}
    with session() as db:before=db.scalar(select(func.count()).select_from(RequestResult))
    status=400
    if bad=='bool':body['expected_ownership_revision']=True
    if bad=='duplicate':payload['items'].append({**body,'command_id':str(uuid.uuid4())})
    if bad=='role':body['role']='dealer'
    if bad=='empty':payload['items']=[]
    if bad=='too_many':payload['items']=[body]*51
    if bad=='non_uuid4':body['command_id']=str(uuid.uuid1())
    if bad=='noncanonical_command':body['command_id']=uuid.uuid4().hex
    if bad=='noncanonical_character':body['character_id']=cid.hex
    if bad=='query':response=client.post(URL+'?x=1',headers=h,json=payload)
    elif bad=='oversize':
        status=413;response=client.post(URL,headers={**h,'Content-Type':'application/json'},content=b' '*524289)
    elif bad=='duplicate_json':response=client.post(URL,headers={**h,'Content-Type':'application/json'},content=b'{"items":[],"items":[]}')
    else:response=client.post(URL,headers=h,json=payload)
    assert response.status_code==status,response.text
    with session() as db:assert db.scalar(select(func.count()).select_from(RequestResult))==before


def test_budget_missed_commands_are_unreserved_and_resubmittable(client,subject,monkeypatch):
    h,cid,raw=subject;body=command(cid)
    monkeypatch.setattr(service,'BUDGET_SECONDS',0)
    response=post(client,h,body)
    assert response['state']=='not_processed' and response['retry']=='same_command'
    with session() as db:assert db.scalar(select(RequestResult.id).where(RequestResult.key==uuid.UUID(body['command_id']))) is None
    monkeypatch.setattr(service,'BUDGET_SECONDS',20)
    assert post(client,h,body)['state']=='saved'


def test_key_not_configured_terminal_failure(client,subject,monkeypatch):
    h,cid,raw=subject
    monkeypatch.setattr(service.credentials,'capture',lambda:(_ for _ in ()).throw(GameError('UPSTREAM_NOT_CONFIGURED',503)))
    body=command(cid)
    response=post(client,h,body)
    assert response['state']=='failed' and response['error']['code']=='UPSTREAM_NOT_CONFIGURED'
    assert post(client,h,body)==response
    assert head(cid) is None


def test_lifecycle_changed_during_fetch_blocks_commit(client,subject,monkeypatch):
    h,cid,raw=subject
    def fetch(self,name):
        with session() as db,db.begin():db.get(Character,cid).lifecycle_revision+=1
        return copy.deepcopy(raw)
    monkeypatch.setattr(LostArkProvider,'armory',fetch)
    response=post(client,h,command(cid))
    assert response['error']['code']=='REVISION_CONFLICT' and head(cid) is None


def test_removed_writers_and_member_keys_are_absent(client,subject):
    h,cid,raw=subject
    assert client.put('/v1/me/lostark-api-key',headers=h,json={}).status_code==404
    assert client.put(f'/v2/me/characters/{cid}/role-summaries/dealer',headers=h,json={}).status_code==404
    assert client.post('/v2/me/role-summary-batches',headers=h,json={}).status_code==404


def test_expired_ack_is_not_reexecuted(client,subject):
    h,cid,raw=subject;body=command(cid)
    assert post(client,h,body)['state']=='saved'
    with session() as db,db.begin():
        record=db.scalar(select(RequestResult).where(RequestResult.key==uuid.UUID(body['command_id'])))
        record.completed_at=now(db)-timedelta(hours=25)
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('Expired ACK must not refetch')):
        result=post(client,h,body)
    assert result['state']=='failed' and result['error']['code']=='IDEMPOTENCY_EXPIRED'
    assert head(cid)['version']==2


def test_fresh_concurrent_commands_reserve_one_candidate_owner(client,subject,monkeypatch):
    from app.game_accounts.models.analysis import AnalysisFetch
    h,cid,raw=subject;entered=Event();release=Event();calls=[]
    def fetch(self,name):
        calls.append(name);entered.set()
        assert release.wait(5)
        return copy.deepcopy(raw)
    monkeypatch.setattr(LostArkProvider,'armory',fetch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one=pool.submit(post,client,h,command(cid));assert entered.wait(5)
        two=pool.submit(post,client,h,command(cid))
        # Wait for both distinct commands to reserve while the owner fetch is blocked.
        import time
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with session() as db:
                n=db.scalar(select(func.count()).select_from(RequestResult).where(RequestResult.operation==service.OPERATION))
            if n==2:break
            time.sleep(.02)
        time.sleep(.1);release.set()
        results=[one.result(),two.result()]
    assert len(calls)==1
    assert sorted(r['state'] for r in results)==['failed','saved']
    assert next(r for r in results if r['state']=='failed')['error']['code']=='ANALYSIS_CANDIDATE_IN_PROGRESS'
    assert head(cid)['version']==2
    assert post(client,h,command(cid,expected_summary_versions=dict(dealer=1,support=2)))['state']=='saved'
    assert len(calls)==2 # a completed observation is not a new command's cache


def test_server_key_rotation_during_fetch_blocks_storage(client,subject,monkeypatch):
    h,cid,raw=subject
    from app.game_accounts.provider_io import credentials
    original=credentials.capture;first=original()
    rotated=credentials.Snapshot('0'*64,'0'*64,'synthetic.rotated.token')
    current=[first]
    monkeypatch.setattr(credentials,'capture',lambda *args:current[0])
    def fetch(self,name):current[0]=rotated;return copy.deepcopy(raw)
    monkeypatch.setattr(LostArkProvider,'armory',fetch)
    response=post(client,h,command(cid))
    assert response['state']=='failed' and response['error']['code']=='SERVER_KEY_CHANGED'
    assert head(cid) is None


def test_provider_rate_limit_is_terminal_and_retry_metadata_is_preserved(client,subject,monkeypatch):
    h,cid,raw=subject;body=command(cid)
    from app.game_accounts.provider_io import rate_limits
    calls=[]
    def fetch(self,name):
        calls.append(name)
        rate_limits.record(service.credentials.capture().fingerprint,datetime.now(timezone.utc)+timedelta(seconds=60))
        raise ProviderUnavailable('UPSTREAM_RATE_LIMITED',http_status=429)
    monkeypatch.setattr(LostArkProvider,'armory',fetch)
    result=post(client,h,body)
    assert result['state']=='failed' and result['retry']=='new_command'
    assert result['error']['retry_after_seconds']>=1 and result['error']['retry_at'] is not None
    assert post(client,h,body)==result and len(calls)==1
    assert head(cid) is None


@pytest.mark.parametrize('status,code',[(401,'LOSTARK_KEY_REJECTED'),(403,'LOSTARK_KEY_REJECTED'),
    (415,'UPSTREAM_UNAVAILABLE'),(429,'UPSTREAM_RATE_LIMITED'),(500,'UPSTREAM_UNAVAILABLE'),
    (502,'UPSTREAM_UNAVAILABLE'),(503,'UPSTREAM_UNAVAILABLE'),(504,'UPSTREAM_UNAVAILABLE')])
def test_official_failures_suppress_shared_new_fetches_but_leave_reads_available(client,subject,monkeypatch,status,code):
    from tests.game_accounts.test_game_account_primitives import transport
    from app.game_accounts.provider_io import provider
    from app.game_accounts.models.provider_limits import ProviderLimit
    h,cid,raw=subject
    monkeypatch.setattr(LostArkProvider,'armory',lambda self,name:self._fetch(name,'armories/characters',''))
    mock,_=transport(status=status)
    monkeypatch.setattr(provider.requests,'get',mock.get)
    first=post(client,h,command(cid))
    second=post(client,h,command(cid))
    assert first['state']==second['state']=='failed'
    assert first['error']['code']==second['error']['code']==code
    assert first['retry']==second['retry']=='new_command'
    assert mock.get.call_count==1 and head(cid) is None
    with session() as db:
        block=db.get(ProviderLimit,service.credentials.capture().fingerprint)
        assert block.upstream_status==status
    assert client.get(f'/v2/me/characters/{cid}/personal-profile',headers=h).status_code==200
    assert client.get('/v1/raid-catalog').status_code==200


@pytest.mark.parametrize('status',[404,302,418])
def test_target_missing_and_unexpected_status_never_become_success(client,subject,monkeypatch,status):
    from tests.game_accounts.test_game_account_primitives import transport
    from app.game_accounts.provider_io import provider
    h,cid,raw=subject
    monkeypatch.setattr(LostArkProvider,'armory',lambda self,name:self._fetch(name,'armories/characters',''))
    mock,_=transport(status=status)
    monkeypatch.setattr(provider.requests,'get',mock.get)
    result=post(client,h,command(cid))
    assert result['state']=='failed' and result['error']['code']=='UPSTREAM_UNAVAILABLE'
    assert head(cid) is None


@pytest.mark.parametrize('exception',['Timeout','ConnectionError'])
def test_transport_failure_is_terminal_and_shared_throttle_is_used(client,subject,monkeypatch,exception):
    import requests
    from unittest.mock import Mock
    from app.game_accounts.provider_io import provider
    h,cid,raw=subject
    monkeypatch.setattr(LostArkProvider,'armory',lambda self,name:self._fetch(name,'armories/characters',''))
    get=Mock(side_effect=getattr(requests,exception)('private token name'))
    monkeypatch.setattr(provider.requests,'get',get)
    for _ in range(2):
        result=post(client,h,command(cid))
        assert result['state']=='failed' and result['retry']=='new_command'
    assert get.call_count==1 and head(cid) is None


def test_timeout_unknown_never_commits_late_and_recovers_same_command(client,subject,monkeypatch):
    h,cid,raw=subject;release=Event();done=Event();body=command(cid)
    original=service.collect
    def blocked(self,name):
        assert release.wait(15)
        return copy.deepcopy(raw)
    def collect(*args):
        try:return original(*args)
        finally:done.set()
    monkeypatch.setattr(LostArkProvider,'armory',blocked)
    monkeypatch.setattr(service,'collect',collect)
    monkeypatch.setattr(service,'BUDGET_SECONDS',10)
    result=post(client,h,body)
    assert result['state']=='unknown' and result['retry']=='same_command'
    assert post(client,h,body)['state']=='in_progress'
    release.set();assert done.wait(5)
    assert head(cid) is None
    with session() as db,db.begin():
        row=db.scalar(select(RequestResult).where(RequestResult.key==uuid.UUID(body['command_id'])))
        row.lease_expires_at=now(db)-timedelta(seconds=1)
    monkeypatch.setattr(service,'BUDGET_SECONDS',20)
    assert post(client,h,body)['state']=='saved' and head(cid)['version']==2


def test_unfinished_command_expires_after_48_hours_without_reexecuting(client,subject,monkeypatch):
    h,cid,raw=subject;body=command(cid)
    principal=None
    from app.auth.service import principal as authenticated
    principal=authenticated(h['Authorization'].split()[1])
    from app.game_accounts.common.support import reserve
    reserve(principal,service.OPERATION,uuid.UUID(body['command_id']),{k:v for k,v in body.items() if k!='command_id'})
    from app.game_accounts.common import support
    monkeypatch.setattr(support,'now',lambda db:now(db)+timedelta(hours=49))
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('Expired command must not fetch')):
        result=post(client,h,body)
    assert result['error']['code']=='IDEMPOTENCY_EXPIRED' and head(cid) is None


def test_automatic_excludes_inactive_but_manual_does_not_change_preferences(client,subject):
    from app.game_accounts.models.models import CharacterPersonalPreferences
    h,cid,raw=subject
    with session() as db,db.begin():
        uid=db.scalar(select(RequestResult.actor_id).limit(1))
        db.add(CharacterPersonalPreferences(user_id=uid,character_id=cid,ownership_revision=1,
            preferred_role='dealer',visible=True,display_order=None,version=1,saved_at=now(db)))
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('Excluded automatic command must not fetch')):
        result=post(client,h,command(cid,trigger='automatic'))
    assert result['state']=='skipped' and result['error']['code']=='AUTOMATIC_TARGET_EXCLUDED'
    assert post(client,h,command(cid))['detected_role']=='support'
    with session() as db:
        assert db.get(CharacterPersonalPreferences,(uid,cid,1)).preferred_role=='dealer'


def test_nice_group_uses_whole_owned_roster_and_setting_is_rechecked(client,subject,monkeypatch):
    from app.game_accounts.models.models import Configuration, Activity, Registration
    from app.member_settings.models import MemberSettings
    h,cid,raw=subject
    with session() as db,db.begin():
        character=db.get(Character,cid)
        registration=db.scalar(select(Registration).where(Registration.account_id==character.account_id))
        uid=registration.user_id
        for row in db.scalars(select(Character).where(Character.account_id==character.account_id)):
            row.summary=dict(row.summary,class_name='바드',item_level='1700')
        config=db.scalar(select(Configuration).where(Configuration.user_id==uid,Configuration.account_id==character.account_id,Configuration.ended_at.is_(None)))
        config.representative_id=cid;config.state='configured'
        db.flush()
        # Other high-level same-class characters are outside activity selection.
        db.add(Activity(settings_id=config.id,account_id=character.account_id,character_id=cid))
        settings=db.get(MemberSettings,uid)
        if settings is None:db.add(MemberSettings(user_id=uid,nice_group_auto_refresh_enabled=False,updated_at=now(db)))
        else:settings.nice_group_auto_refresh_enabled=False
    excluded=command(cid,trigger='automatic')
    assert post(client,h,excluded)['state']=='skipped'
    with session() as db,db.begin():db.get(MemberSettings,uid).nice_group_auto_refresh_enabled=True
    assert post(client,h,excluded)['state']=='skipped' # terminal ACK, no automatic new ID
    assert post(client,h,command(cid,trigger='automatic'))['state']=='saved'


def test_commit_response_loss_replays_saved_ack_without_duplicate_fetch(client,subject,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    h,cid,raw=subject;body=command(cid);original=service.save
    def lost(*args):
        original(*args)
        raise SQLAlchemyError('synthetic commit response lost')
    monkeypatch.setattr(service,'save',lost)
    first=post(client,h,body)
    assert first['state']=='unknown' and first['retry']=='same_command'
    assert head(cid)['version']==2
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('Recovery must not fetch twice')):
        replay=post(client,h,body)
    assert replay['state']=='saved' and replay['result']['analysis']['version']==2



def test_identity_changed_while_fetching_requires_new_command(client,subject,monkeypatch):
    h,cid,raw=subject
    def fetch(self,name):
        with session() as db,db.begin():
            c=db.get(Character,cid);c.summary=dict(c.summary,class_name='홀리나이트')
        return copy.deepcopy(raw)
    monkeypatch.setattr(LostArkProvider,'armory',fetch)
    result=post(client,h,command(cid))
    assert result['state']=='failed' and result['error']['code']=='REVISION_CONFLICT'
    assert head(cid) is None



def test_unknown_stored_class_is_a_terminal_item_failure_without_fetch(client,subject):
    h,cid,raw=subject
    with session() as db,db.begin():
        c=db.get(Character,cid);c.summary={k:v for k,v in c.summary.items() if k!='class_name'}
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('Unknown identity class must not fetch')):
        result=post(client,h,command(cid))
    assert result['state']=='failed' and result['error']['code']=='ROLE_DETECTION_UNAVAILABLE'
    assert head(cid) is None
