"""Candidate authority and lifetime tests on disposable PostgreSQL; no live API."""
import copy
import uuid
from datetime import timedelta
from unittest.mock import patch
import pytest
from sqlalchemy import select,delete
from app.core.database import session,now
from app.game_accounts.models.models import Character,Account,Registration,Configuration,Activity,RequestResult,CharacterRoleSummary
from app.game_accounts.models.analysis_candidates import AnalysisCandidate,CandidatePolicy
from app.game_accounts.analysis import candidates
from app.game_accounts.common.support import GameError
from app.game_accounts.provider_io.provider import LostArkProvider,ProviderUnavailable
from tests.game_accounts.analysis.test_analysis_http import subject,command,post
from tests.game_accounts.test_role_summaries import owned
from tests.game_accounts.test_game_accounts import world

BOOT='/v2/me/account-bootstrap'
URL='/v2/me/character-analysis/refresh'

def read(client,h):
    r=client.get(BOOT+'?include_analysis_candidates=true',headers=h)
    assert r.status_code==200,r.text
    return next(v['analysis_candidates'] for v in r.json()['registrations'] if v['analysis_candidates'])

def ctx(proj,f,purpose='automatic_candidate'):
    return dict(candidate_id=f['candidate_id'],expected_generation=f['generation'],
        expected_policy_revision=proj['policy_revision'],expected_settings_version=proj['settings_version'],purpose=purpose)

@pytest.fixture
def candidate_subject(subject):
    h,cid,raw=subject
    with session() as db,db.begin():
        c=db.get(Character,cid);a=db.get(Account,c.account_id)
        conf=db.scalar(select(Configuration).where(Configuration.account_id==a.id))
        db.execute(delete(Activity).where(Activity.settings_id==conf.id,Activity.character_id==cid))
        p=candidates.policy(db,a.owner_id,a);f=candidates.fact_for(db,p,cid)
        assert f.reason=='initial_verification'
    return h,cid,raw

def send(client,h,b):
    r=client.post(URL,headers=h,json={'items':[b]})
    assert r.status_code==200,r.text
    return r.json()['items'][0]

def find(proj,cid):
    return next(v for v in proj['candidates'] if v['character_id']==str(cid))

def test_projection_no_side_effect_false_omits_and_strict_query(client,candidate_subject):
    h,cid,_=candidate_subject
    plain=client.get(BOOT,headers=h);assert plain.status_code==200
    assert all('analysis_candidates' not in v for v in plain.json()['registrations'])
    first=read(client,h);assert first==read(client,h)
    assert find(first,cid)['state']=='pending'
    assert client.get(BOOT+'?include_analysis_candidates=true&include_analysis_candidates=true',headers=h).status_code==400

def test_unselected_candidate_saved_ack_and_no_activity(client,candidate_subject):
    h,cid,_=candidate_subject;p=read(client,h);f=find(p,cid)
    b=command(cid,trigger='automatic',candidate_context=ctx(p,f))
    result=send(client,h,b);assert result['state']=='saved',result
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('no replay fetch')):
        assert send(client,h,b)==result
    assert find(read(client,h),cid)['state']=='succeeded'
    with session() as db:
        assert db.scalar(select(Activity).where(Activity.character_id==cid)) is None
    newer=command(cid,trigger='automatic',candidate_context=ctx(read(client,h),find(read(client,h),cid)))
    assert send(client,h,newer)['error']['code']=='ANALYSIS_CANDIDATE_COMPLETED'

@pytest.mark.parametrize('excluded',[False,True])
def test_failed_candidate_blocks_automatic_manual_retry_allowed(client,candidate_subject,monkeypatch,excluded):
    h,cid,raw=candidate_subject;p=read(client,h);f=find(p,cid)
    monkeypatch.setattr(LostArkProvider,'armory',lambda *a: (_ for _ in ()).throw(ProviderUnavailable()))
    b=command(cid,trigger='automatic',candidate_context=ctx(p,f))
    assert send(client,h,b)['state']=='failed'
    p=read(client,h);f=find(p,cid);assert f['state']=='blocked' and f['last_error']
    denied=send(client,h,command(cid,trigger='automatic',candidate_context=ctx(p,f)))
    assert (denied['state'],denied['retry'],denied['error']['code'])==('skipped','none','ANALYSIS_CANDIDATE_RETRY_REQUIRED')
    if excluded:
        with session() as db,db.begin():
            c=db.get(Character,cid);a=db.get(Account,c.account_id);p0,f0=candidates.row(db,a.owner_id,a,c)
            f0.excluded=True;p0.revision+=1
    p=read(client,h);f=find(p,cid)
    monkeypatch.setattr(LostArkProvider,'armory',lambda *a:copy.deepcopy(raw))
    result=send(client,h,command(cid,candidate_context=ctx(p,f,'manual_retry')))
    assert result['state']=='saved',result
    assert find(read(client,h),cid)['state']=='succeeded'

def test_expired_unresolved_original_body_reconciles_without_fetch_even_stale_cas(client,candidate_subject):
    h,cid,_=candidate_subject;p=read(client,h);f=find(p,cid)
    b=command(cid,trigger='automatic',candidate_context=ctx(p,f))
    with session() as db,db.begin():
        c=db.get(Character,cid);a=db.get(Account,c.account_id);p0,f0=candidates.row(db,a.owner_id,a,c)
        f0.state='running';f0.command_id=uuid.UUID(b['command_id']);f0.command_body=b
        f0.lease_until=now(db)-timedelta(hours=50)
        p0.revision+=1;c.lifecycle_revision+=1
    projected=find(read(client,h),cid)
    assert projected['unresolved_command']['recovery']=='reconcile_required'
    assert projected['unresolved_command']['command']==b
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('reconcile cannot fetch')):
        result=send(client,h,b)
        assert (result['state'],result['status'],result['retry'],result['error']['code'])==('failed',409,'new_command','ANALYSIS_CANDIDATE_RECONCILED')
        assert send(client,h,b)['error']['code']=='ANALYSIS_CANDIDATE_RECONCILED'
    assert find(read(client,h),cid)['state']=='blocked'

def test_delta_only_explicit_removed_reselect_and_registration_lifetime(client,candidate_subject):
    h,cid,_=candidate_subject
    with session() as db,db.begin():
        c=db.get(Character,cid);a=db.get(Account,c.account_id);uid=a.owner_id
        p,f=candidates.row(db,uid,a,c)
        candidates.delta(db,uid,a,[],[]);assert not f.excluded
        candidates.delta(db,uid,a,[cid],[]);assert f.excluded
        rev=p.revision
        with pytest.raises(GameError):candidates.delta(db,uid,a,[],[cid],rev-1)
        candidates.delta(db,uid,a,[],[cid],rev);assert not f.excluded
        r=db.scalar(select(Registration).where(Registration.account_id==a.id));r.deleted_at=now(db)
        candidates.delta(db,uid,a,[cid],[]);f.state='succeeded';f.completed_at=now(db)
        aid=a.id;fid=f.id
    with session() as db:
        f=db.get(AnalysisCandidate,fid);assert f.excluded and f.state=='succeeded'
        assert db.get(CandidatePolicy,f.policy_id).account_id==aid

@pytest.mark.parametrize('legacy,values,expected',[
    (False,[None,'1699','1700'],'first_threshold'),
    (False,[None,'1700'],'new_at_threshold'),
    (True,[None,'1700'],None),
    (True,['1699',None,'1700'],'first_threshold'),
])
def test_observation_baseline_and_null(client,candidate_subject,legacy,values,expected):
    _,cid,_=candidate_subject
    with session() as db,db.begin():
        c=db.get(Character,cid);a=db.get(Account,c.account_id);p,f=candidates.row(db,a.owner_id,a,c)
        f.legacy=legacy;f.reason=None;f.below_threshold=False
        for value in values:
            candidates.observe(db,a,[{**c.summary,'server_name':c.server_name,'character_name':c.character_name,'item_level':value}],False)
        assert f.reason==expected

def test_two_commands_single_candidate_and_lease_recovery(client,candidate_subject):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    h,cid,raw=candidate_subject;p=read(client,h);f=find(p,cid)
    entered,release=Event(),Event()
    def fetch(*args):
        entered.set()
        assert release.wait(10)
        return copy.deepcopy(raw)
    first=command(cid,trigger='automatic',candidate_context=ctx(p,f))
    second=command(cid,trigger='automatic',candidate_context=ctx(p,f))
    with patch.object(LostArkProvider,'armory',side_effect=fetch) as calls,ThreadPoolExecutor(2) as pool:
        running=pool.submit(send,client,h,first)
        assert entered.wait(10)
        try:
            denied=send(client,h,second)
            assert (denied['state'],denied['status'],denied['retry'],denied['error']['code'])==('failed',409,'none','ANALYSIS_CANDIDATE_IN_PROGRESS')
            # This ID owns its rejection ACK, not the other execution.
            assert send(client,h,second)==denied
            owner=find(read(client,h),cid)['unresolved_command']['command']
            assert owner==first
        finally:release.set()
        assert running.result()['state']=='saved'
        assert calls.call_count==1

def test_selection_delta_wins_during_provider_call(client,candidate_subject):
    h,cid,raw=candidate_subject;p=read(client,h);f=find(p,cid)
    def fetch(*args):
        with session() as db,db.begin():
            c=db.get(Character,cid);a=db.get(Account,c.account_id)
            candidates.delta(db,a.owner_id,a,[cid],[])
        return copy.deepcopy(raw)
    with patch.object(LostArkProvider,'armory',side_effect=fetch):
        result=send(client,h,command(cid,trigger='automatic',candidate_context=ctx(p,f)))
    assert result['error']['code']=='REVISION_CONFLICT',result
    with session() as db:
        assert db.scalar(select(CharacterRoleSummary).where(CharacterRoleSummary.character_id==cid)) is None
    assert find(read(client,h),cid)['eligibility']=='explicitly_excluded'

def test_fenced_ack_rolls_back_summary_and_candidate(client,candidate_subject):
    from app.game_accounts.analysis import service
    h,cid,_=candidate_subject;p=read(client,h);f=find(p,cid)
    real=service.commit_result
    def fail_saved(db,ticket,status,result):
        if result['state']=='saved':
            raise RuntimeError('synthetic loss before commit')
        return real(db,ticket,status,result)
    with patch.object(service,'commit_result',side_effect=fail_saved):
        result=send(client,h,command(cid,trigger='automatic',candidate_context=ctx(p,f)))
    assert result['state']=='unknown'
    assert find(read(client,h),cid)['state']=='running'
    with session() as db:
        assert db.scalar(select(CharacterRoleSummary).where(CharacterRoleSummary.character_id==cid)) is None

def test_nice_group_off_skips_candidate_and_manual_allowed(client,candidate_subject):
    h,cid,raw=candidate_subject
    with session() as db,db.begin():
        c=db.get(Character,cid)
        other=db.scalar(select(Character).where(Character.account_id==c.account_id,Character.id!=cid))
        other.summary={**other.summary,'class_name':'바드','item_level':'1700'}
    p=read(client,h);f=find(p,cid);assert f['eligibility']=='nice_group_disabled'
    with patch.object(LostArkProvider,'armory',side_effect=AssertionError('must not fetch')):
        result=send(client,h,command(cid,trigger='automatic',candidate_context=ctx(p,f)))
        assert result['state']=='skipped' and result['error']['code']=='AUTOMATIC_TARGET_EXCLUDED'
    assert find(read(client,h),cid)['state']=='pending'
    assert send(client,h,command(cid))['state']=='saved'

def test_fixed_examples_and_outcome_matrix():
    import json
    from pathlib import Path
    from app.game_accounts.schemas.analysis_schemas import AnalysisRequest,AnalysisResponse
    value=json.loads(Path('docs/features/rosters/activity-and-presentation/refresh-candidate.examples.json').read_text())
    AnalysisRequest.model_validate(value['reconcile']['body'])
    AnalysisRequest.model_validate(value['manual_retry_excluded_or_nice_off']['body'])
    AnalysisResponse.model_validate(value['manual_retry_excluded_or_nice_off']['response'])
    for example in value['outcomes']:
        AnalysisRequest.model_validate(example['request'])
        AnalysisResponse.model_validate(example['response'])
        bad=copy.deepcopy(example['response']);bad['items'][0]['retry']='same_command'
        with pytest.raises(ValueError):AnalysisResponse.model_validate(bad)

def test_new_owner_generation_never_inherits_candidates(client,candidate_subject):
    h,cid,_=candidate_subject
    with session() as db,db.begin():
        c=db.get(Character,cid);a=db.get(Account,c.account_id);p,f=candidates.row(db,a.owner_id,a,c)
        f.excluded=True;f.state='succeeded'
        a.ownership_revision+=1
    new=read(client,h)
    assert new['baseline']=='not_initialized' and new['candidates']==[]

def test_0038_baseline_preserves_existing_rows():
    from sqlalchemy import text
    from tests.raid_rooms.common.test_raid_room_migrations import isolated_app_database
    from tests.game_accounts.analysis.test_analysis_migrations import seed_user
    with isolated_app_database() as (engine,role,migrate):
        migrate('0037_server_analysis');uid=seed_user(engine);aid,cid=uuid.uuid4(),uuid.uuid4()
        with engine.begin() as db:
            db.execute(text("INSERT INTO game_accounts(id,owner_id,ownership_revision,roster_revision,verified_at) VALUES(:a,:u,1,1,now())"),dict(a=aid,u=uid))
            db.execute(text("""INSERT INTO game_characters(id,account_id,server_name,character_name,summary,status,fetched_at,confirmed_at,lifecycle_state,lifecycle_revision)
                VALUES(:c,:a,'synthetic','synthetic','{"item_level":"1700"}','confirmed',now(),now(),'active',1)"""),dict(c=cid,a=aid))
            before=dict(db.execute(text('SELECT * FROM game_characters WHERE id=:c'),dict(c=cid)).mappings().one())
        migrate('0038_analysis_candidates')
        with engine.connect() as db:
            after=dict(db.execute(text('SELECT * FROM game_characters WHERE id=:c'),dict(c=cid)).mappings().one())
            assert before==after
            assert db.scalar(text("SELECT baseline FROM analysis_candidate_policies WHERE account_id=:a"),dict(a=aid))=='legacy'
            fact=db.execute(text("SELECT legacy,reason FROM analysis_candidates WHERE character_id=:c"),dict(c=cid)).one()
            assert fact==(True,None)
