"""Actual-T group policy under the new schema, using disposable app-role PostgreSQL."""
import os
import subprocess
import uuid
from datetime import date, datetime, time, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, inspect
from app.core.database import session, now
from app.raids.service import KST
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_group_policy as policy, cycle_management, cycle_schemas, cycle_leadership
from app.raid_rooms import cycle_queries, cycle_member_reads, beta_profile, membership_actions, membership_action_schemas
from app.raid_rooms.cycle_models import RoomCycle, CycleMember, CycleGeneration
from app.raid_rooms.cycle_group_models import CycleGroupPolicy
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from tests.test_group_raid_lifecycle import group_beta, beta, current, candidate, ready, sources, imported, people, worlds, create_group_room, group, add
from tests.test_beta_recruitment import create_beta, beta_join
from tests.test_group_foundation import actor
from tests.test_recruitment_cycle_management import settings, transfer_body
from tests.test_raid_room_migrations import table_digests


@pytest.fixture
def policy_db(group_beta):
    engine,a,b=group_beta
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'alembic_version'})
    result=subprocess.run(['alembic','upgrade','0035_cycle_group_policy'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,'group policy migration failed'
    assert table_digests(engine,set(before))==before
    from app.raid_rooms import readiness
    with session() as db:
        readiness.require_two_cycle_active(db)
        readiness.require_cycle_worker(db)
    with policy.using(), beta_profile.using():
        yield engine,a,b


def state(rid,key):
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        return policy.state(policy.get(db,row))


def change(w,rid,key,gid):
    ctx=cycle_management.group_context(actor(w['uid']),rid,key,uuid.UUID(gid) if gid else None)
    body=settings(w,rid,key,context_token=ctx['data']['context_token'],
        group_policy=dict(scope='group' if gid else 'public',group_id=gid,expected_revision=ctx['group_policy']['revision']))
    return cycle_management.command(actor(w['uid']),rid,uuid.uuid4(),body,'settings')


def test_target_switches_preserve_other_target_and_participation(policy_db,client):
    engine,a,b=policy_db
    ga=group(client,a);gb=group(client,b);add(client,b,a,gb)
    rid,c,_,_,_=create_beta(a,combined=True)
    from datetime import timedelta
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    protected={'recruitment_memberships','recruitment_assignments','recruitment_cycle_members','recruitment_cycle_assignments',
        'recruitment_sessions','recruitment_session_participations','recruitment_time_reservations','raid_weekly_states'}
    protected &= set(inspect(engine).get_table_names())
    before=table_digests(engine,protected)
    original=state(rid,n)
    for gid in (ga,gb,None):
        ack=change(a,rid,c,gid)[1]
        assert ack['group_policy_effects'][0]['target_cycle_key']==c
        assert state(rid,c)['group_id']==(uuid.UUID(gid) if gid else None)
        assert state(rid,n)==original
        assert table_digests(engine,protected)==before
    with session() as db:assert db.get(Room,rid).revision==1


def test_transfer_to_external_is_atomic_public_and_original_ack(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a)
    rid,c,_,_,_=create_beta(a,combined=True);beta_join(b,rid,c)
    change(a,rid,c,gid)
    with session() as db:
        n=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key!=date.fromisoformat(c)))
        n_before=policy.state(policy.get(db,n))
    body=transfer_body(a,rid,c,b);command=uuid.uuid4()
    ack=cycle_leadership.transfer(actor(a['uid']),rid,command,body)
    assert state(rid,c)['scope']=='public'
    assert ack[1]['group_policy_effects'][0]['after']['group_id'] is None
    with policy.using(False):assert cycle_leadership.transfer(actor(a['uid']),rid,command,body)==ack
    with session() as db:assert policy.state(policy.get(db,n))==n_before


def test_stale_group_context_rollback_and_old_request_rejection(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a)
    old=settings(a,rid,c)
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    with policy.using(False),pytest.raises(GameError) as caught:
        cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),old,'settings')
    assert caught.value.code=='CLIENT_UPGRADE_REQUIRED'
    assert table_digests(engine,set(before))==before
    ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(gid))
    body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1))
    change(a,rid,c,None)  # noop has unchanged revision, then a real intervening change
    change(a,rid,c,gid)
    with pytest.raises(GameError) as caught:cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),body,'settings')
    assert caught.value.code in ('TARGET_CONTEXT_STALE','REVISION_CONFLICT')


@pytest.mark.parametrize('scope',['group','public'])
def test_migration_current_generations_normalize_without_rewriting_history(group_beta,client,scope):
    engine,a,b=group_beta;gid=group(client,a);rid,c,n=create_group_room(a,gid)
    with session() as db,db.begin():db.get(Room,rid).scope=scope
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0035_cycle_group_policy'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0
    assert table_digests(engine,tables)==before
    with session() as db:
        values=list(db.scalars(select(CycleGroupPolicy)))
        assert len(values)==2 and all(v.scope==scope for v in values)
        assert all(v.group_id==(uuid.UUID(gid) if scope=='group' else None) for v in values)


def test_private_target_visibility_search_and_group_metadata(policy_db,client,monkeypatch):
    engine,a,b=policy_db;ga=group(client,a);gb=group(client,b);add(client,b,a,gb)
    rid,c,_,_,_=create_beta(a,combined=True)
    from datetime import timedelta
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    change(a,rid,c,ga);change(a,rid,n,gb)
    from tests.test_recruitment_cycle_queries import search_request
    from app.game_accounts import observations
    calls=[]
    def unexpected_provider(*args,**kwargs):
        calls.append(True);raise AssertionError('Provider must not be called by reads')
    monkeypatch.setattr(observations,'fetch',unexpected_provider)
    before=table_digests(engine,set(inspect(engine).get_table_names()))
    with pytest.raises(GameError) as caught:cycle_member_reads.detail(actor(b['uid']),rid,c)
    assert caught.value.code=='ROOM_NOT_FOUND'
    assert cycle_member_reads.detail(actor(b['uid']),rid,n)['data']['settings']['group_id']==gb
    assert not cycle_queries.search(None,search_request(c))['data']['items']
    page=cycle_queries.search(actor(b['uid']),search_request(n),include_group_state=True)
    assert page['data']['items'][0]['group_id']==gb
    assert 'room_groups' not in page
    assert page['cycle_groups'][0]['group_id']==gb and page['cycle_groups'][0]['target_cycle_key']==n
    from app.groups import raid_state
    from app.groups.models import Group
    with session() as db:
        for gid,key in ((ga,c),(gb,n)):
            blocked,items=raid_state.evaluate(db,db.get(Group,uuid.UUID(gid)),now(db))
            assert blocked['blocking_room_count']==1
            assert [v['target_cycle_key'].isoformat() for v in items[0]['targets']]==[key]
    assert table_digests(engine,set(before))==before
    assert not calls
    with session() as db,db.begin():
        opposite=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        db.delete(policy.get(db,opposite))
    with session() as db:
        blocked,items=raid_state.evaluate(db,db.get(Group,uuid.UUID(ga)),now(db))
        assert blocked['state']=='unavailable' and blocked['blocking_room_count'] is None
        assert [v['target_cycle_key'].isoformat() for v in items[0]['targets']]==[c]


def test_settings_exception_rolls_back_policy_and_revision(policy_db,client,monkeypatch):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a)
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    from app.raid_rooms import cycle_lifecycle
    ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(gid))
    body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1))
    command=uuid.uuid4()
    original=cycle_lifecycle.ack
    def broken(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('synthetic policy interruption')
    monkeypatch.setattr(cycle_lifecycle,'ack',broken)
    with pytest.raises(RuntimeError):cycle_management.command(actor(a['uid']),rid,command,body,'settings')
    assert table_digests(engine,set(before))==before
    monkeypatch.setattr(cycle_lifecycle,'ack',original)
    assert cycle_management.command(actor(a['uid']),rid,command,body,'settings')[1]['data']['outcome']=='applied'
    assert state(rid,c)['group_id']==uuid.UUID(gid)


def action(w,rid,key,name):
    ctx=membership_actions.get(actor(w['uid']),rid,key)
    command=membership_action_schemas.Command.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],
        view_cycle_key=key,actor_membership_id=ctx['data']['actor']['membership_id'],
        expected_actor_membership_revision=ctx['data']['actor']['membership_revision'],action=name,
        context_token=ctx['data']['options'][name]['confirmation']['context_token']))
    return ctx,command


def test_leave_group_priority_and_leave_all_atomic_public_fallback(policy_db,client,people):
    engine,a,b=policy_db;gid=group(client,a)
    rid,c,_,_,_=create_beta(a,combined=True)
    from datetime import timedelta
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    beta_join(b,rid,c);beta_join(b,rid,n)
    third=people('policy-third');add(client,a,third,gid);beta_join(third,rid,c)
    change(a,rid,c,gid);change(a,rid,n,gid)
    ctx,body=action(a,rid,c,'leave_all')
    plans=ctx['data']['options']['leave_all']['impact']['targets']
    assert plans[0]['successor']['membership_id']!=plans[1]['successor']['membership_id']
    result=membership_actions.execute(actor(a['uid']),rid,uuid.uuid4(),body)[1]
    assert [e['group_policy_effect']['after']['scope'] for e in result['data']['effects']]==['group','public']
    assert state(rid,c)['group_id']==uuid.UUID(gid) and state(rid,n)['group_id'] is None


def test_cn_different_leaders_change_without_g1_and_title_remains_common(policy_db,client):
    engine,a,b=policy_db;gid=group(client,b)
    rid,c,_,_,_=create_beta(a,combined=True)
    from datetime import timedelta
    from app.raid_rooms import cycle_common
    from app.raid_rooms.cycle_group_schemas import TitleCommand
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat();beta_join(b,rid,n)
    cycle_leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),transfer_body(a,rid,n,b))
    change(b,rid,n,gid)
    assert state(rid,c)['scope']=='public' and state(rid,n)['scope']=='group'
    ctx=cycle_common.get(actor(a['uid']),rid,'edit_common_settings')
    body=TitleCommand(expected_cycle_key=ctx['data']['expected_cycle_key'],expected_room_revision=ctx['data']['room_revision'],
        context_token=ctx['data']['context_token'],title='new common title')
    cycle_common.execute(actor(a['uid']),rid,uuid.uuid4(),body,'edit_common_settings')
    assert state(rid,n)['scope']=='group'
    with session() as db:assert db.get(Room,rid).title=='new common title'
    for kind in ('leave','end'):
        assert cycle_common.get(actor(a['uid']),rid,kind)['data']['current_settings']=={'title':'new common title'}


def test_opening_inherits_source_normalizes_nonmember_and_existing_n_unchanged(policy_db,client):
    engine,a,b=policy_db;gid=group(client,b);add(client,b,a,gid);rid,c,_,_,_=create_beta(a)
    from datetime import timedelta
    from app.raid_rooms import cycle_opening, beta_schemas, cycle_wire
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    beta_join(b,rid,c);change(a,rid,c,gid)
    # Leader leaves the group without changing the raid. Reopening derives public explicitly.
    from app.groups.models import GroupMembership
    with session() as db,db.begin():
        m=policy.member(db,uuid.UUID(gid),a['uid']);m.ended_at=now(db);m.revision+=1
    params=dict(base_starts_at=datetime.combine(date.fromisoformat(n),time(18),KST).astimezone(timezone.utc).isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=cycle_opening.get(actor(a['uid']),rid,n,'open')
        assert ctx['data']['group_policy_effect']['after']['scope']=='public'
        data=ctx['data']
        body=beta_schemas.BetaOpenRequest.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],
            target_cycle_key=n,expected_target_revision=ctx['scope']['target_revision'],context_token=data['context_token'],
            selection=data['selection'],target_items=data['targets'],target_session_ids=[],intent='open',
            beta_schedule=data['beta_schedule_config']))
        command=uuid.uuid4();cycle_opening.execute(actor(a['uid']),rid,command,body)
        saved=state(rid,n)
        assert saved['scope']=='public' and state(rid,c)['scope']=='group'
        ctx=cycle_opening.get(actor(a['uid']),rid,n,'open')
        assert ctx['data']['opening_effect']=='already_open'
        assert state(rid,n)==saved


def test_concurrent_changes_one_commit_and_context_recheck_after_membership_change(policy_db,client):
    engine,a,b=policy_db;ga=group(client,a);gb=group(client,b);add(client,b,a,gb)
    rid,c,_,_,_=create_beta(a)
    bodies=[]
    for gid in (ga,gb):
        ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(gid))
        bodies.append(settings(a,rid,c,context_token=ctx['data']['context_token'],
            group_policy=dict(scope='group',group_id=gid,expected_revision=1)))
    def run(body):
        with policy.using(),beta_profile.using():
            try:return cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),body,'settings')[1]['data']['outcome']
            except GameError as e:return e.code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,bodies))
    assert results.count('applied')==1 and any(v in ('TARGET_CONTEXT_STALE','REVISION_CONFLICT') for v in results)
    target=ga if state(rid,c)['group_id']==uuid.UUID(gb) else gb
    ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(target))
    body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=target,expected_revision=2))
    with session() as db,db.begin():
        m=policy.member(db,uuid.UUID(target),a['uid']);m.ended_at=now(db);m.revision+=1
    with pytest.raises(GameError) as caught:cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),body,'settings')
    assert caught.value.code=='GROUP_MEMBERSHIP_REQUIRED'


def test_eight_participants_group_priority_then_external_and_last_member_close(policy_db,client,people):
    engine,a,b=policy_db;gid=group(client,a)
    from app.raid_rooms import cycle_creation,cycle_commands,cycle_wire,beta_schemas,beta_schedule
    from tests.test_recruitment_cycle_creation import request
    from tests.test_recruitment_cycle_commands import context,admission_request
    from app.raids import service as raids
    with session() as db:
        stamp=now(db);c=raids.cycle(stamp).cycle_key
    raid=next(r for r in raids.catalog().raids if r.raid_id=='kazeros_act4')
    params=dict(base_starts_at=(stamp+timedelta(hours=2)).replace(second=0,microsecond=0).isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=cycle_creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',[
            cycle_wire.BCreateTarget(raid_id=raid.raid_id,difficulty_id=raid.difficulties[0].difficulty_id,expected_weekly_revision=1)],None,c)
        raw=request(ctx).model_dump(mode='json');raw.pop('schedule_groups');raw['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        rid=uuid.UUID(cycle_creation.create(actor(a['uid']),uuid.uuid4(),beta_schemas.BetaCreateRequest.model_validate(raw))[1]['data']['room_id'])
        members=[]
        for i in range(7):
            from app.auth.router import _limits
            _limits.clear()
            w=people('policy-eight-'+str(i));members.append(w)
            cycle_commands.admit(actor(w['uid']),rid,uuid.uuid4(),admission_request(context(w,rid,c,role='support' if i in (2,6) else 'dealer')))
        add(client,a,members[3],gid);change(a,rid,c,gid)
        ctx,body=action(a,rid,c,'leave_target')
        successor=ctx['data']['options']['leave_target']['impact']['targets'][0]['successor']
        with session() as db:assert db.get(CycleMember,uuid.UUID(successor['cycle_member_id'])).user_id==members[3]['uid']
        membership_actions.execute(actor(a['uid']),rid,uuid.uuid4(),body)
        assert state(rid,c)['scope']=='group'
        ctx,body=action(members[3],rid,c,'leave_target')
        result=membership_actions.execute(actor(members[3]['uid']),rid,uuid.uuid4(),body)[1]
        assert result['data']['effects'][0]['group_policy_effect']['after']['scope']=='public'
        for w in [m for i,m in enumerate(members) if i!=3]:
            ctx,body=action(w,rid,c,'leave_target')
            membership_actions.execute(actor(w['uid']),rid,uuid.uuid4(),body)
        with session() as db:
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
            assert row.state=='closed'


def test_http_settings_confirmation_marker_and_original_ack(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a)
    from fastapi.testclient import TestClient
    from app.main import create_two_cycle_app
    params={'contract_profile':beta_profile.PROFILE,'group_policy_version':policy.VERSION}
    with TestClient(create_two_cycle_app(),raise_server_exceptions=False) as http:
        response=http.get(f'/v2/raid-rooms/{rid}/command-context',params={**params,'target_cycle_key':c,
            'command':'edit_group_policy','target_group_id':gid},headers=a['headers'])
        assert response.status_code==200,response.text
        ctx=response.json()
        body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1)).model_dump(mode='json',exclude_unset=True)
        headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())}
        response=http.put(f'/v2/raid-rooms/{rid}/settings',params=params,headers=headers,json=body)
        assert response.status_code==200,response.text
        assert response.json()['group_policy_effects'][0]['after']['group_id']==gid
        replay=http.put(f'/v2/raid-rooms/{rid}/settings',params={'contract_profile':beta_profile.PROFILE},headers=headers,json=body)
        assert replay.status_code==200 and replay.json()==response.json()


def test_public_pending_preserved_but_approval_uses_current_group(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a,mode='leader_only')
    from app.raid_rooms import cycle_commands as commands,beta_schemas
    from tests.test_recruitment_cycle_commands import context,admission_request,decision
    pending=commands.admit(actor(b['uid']),rid,uuid.uuid4(),beta_schemas.BetaApplyRequest.model_validate(
        admission_request(context(b,rid,c,intent='apply')).model_dump(mode='json')),applying=True)[1]
    aid=uuid.UUID(pending['data']['application_id'])
    from app.raid_rooms.cycle_application_models import CycleApplication
    before=table_digests(engine,{'recruitment_cycle_applications'})
    change(a,rid,c,gid)
    assert table_digests(engine,{'recruitment_cycle_applications'})==before
    with session() as db:
        app=db.get(CycleApplication,aid)
        assert app.state=='pending' and app.origin_scope=='public' and app.origin_group_id is None
    # The server can inspect the stored application, but cannot approve using its old public origin.
    with pytest.raises(GameError) as caught:
        commands.process(actor(a['uid']),aid,uuid.uuid4(),decision(pending['data'],context(a,rid,c,'apply')),action='approve')
    assert caught.value.code=='GROUP_MEMBERSHIP_REQUIRED'
    with session() as db:assert db.get(CycleApplication,aid).state=='pending'


def test_pre_upgrade_ack_replay_and_old_context_cannot_execute_after_migration(group_beta):
    engine,a,b=group_beta
    from app.raid_rooms import cycle_creation,beta_schemas
    rid,c,_,raw,command=create_beta(a)
    old=beta_schemas.BetaCreateRequest.model_validate(raw)
    with beta_profile.using():original=cycle_creation.create(actor(a['uid']),command,old)
    from app.raid_rooms import cycles
    original_settings=settings(a,rid,c)
    pending_key=uuid.uuid4()
    pending_payload=dict(room_id=str(rid),body=original_settings.model_dump(mode='json',exclude_unset=True))
    def interrupted(*args):raise RuntimeError('synthetic pre-cutover failure')
    with beta_profile.using(),pytest.raises(RuntimeError):
        cycles.execute(actor(a['uid']),'target-settings',pending_key,pending_payload,interrupted)
    result=subprocess.run(['alembic','upgrade','0035_cycle_group_policy'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    with beta_profile.using():
        assert cycle_creation.create(actor(a['uid']),command,old)==original
        with pytest.raises(GameError) as caught:cycle_creation.create(actor(a['uid']),uuid.uuid4(),old)
        assert caught.value.code=='CLIENT_UPGRADE_REQUIRED'
        with policy.using(),pytest.raises(GameError) as caught:cycle_creation.create(actor(a['uid']),uuid.uuid4(),old)
        assert caught.value.code=='CLIENT_UPGRADE_REQUIRED'
        with policy.using(),pytest.raises(GameError) as caught:
            cycle_management.command(actor(a['uid']),rid,pending_key,original_settings,'settings')
        assert caught.value.code=='CLIENT_UPGRADE_REQUIRED'
    assert table_digests(engine,set(before))==before


def test_leave_all_second_target_failure_rolls_back_everything(policy_db,client,monkeypatch):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True)
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    for key in (c,n):beta_join(b,rid,key);change(a,rid,key,gid)
    ctx,body=action(a,rid,c,'leave_all')
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    original=policy.apply;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(True)
        if len(calls)==2:raise RuntimeError('synthetic opposite target failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(policy,'apply',fail_second)
    with pytest.raises(RuntimeError):membership_actions.execute(actor(a['uid']),rid,uuid.uuid4(),body)
    assert len(calls)==2 and table_digests(engine,set(before))==before


def test_unavailable_successor_preserves_recovery_boundary(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a);beta_join(b,rid,c);change(a,rid,c,gid)
    from app.game_accounts.models import Character
    with session() as db,db.begin():db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_state='retired'
    ctx,body=action(a,rid,c,'leave_target')
    result=membership_actions.execute(actor(a['uid']),rid,uuid.uuid4(),body)[1]
    assert result['data']['effects'][0]['leadership_status']=='pending_review'
    assert state(rid,c)['scope']=='public'
    ctx=membership_actions.get(actor(b['uid']),rid,c)
    assert not ctx['data']['options']['recover_leadership']['permission']['allowed']
    with session() as db,db.begin():db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_state='active'
    ctx,body=action(b,rid,c,'recover_leadership')
    result=membership_actions.execute(actor(b['uid']),rid,uuid.uuid4(),body)[1]
    assert result['data']['effects'][0]['leadership_status']=='active'


def test_n_cancel_reopen_keeps_policy_history_and_current_target(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True)
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    change(a,rid,c,gid);change(a,rid,n,gid)
    from app.raid_rooms import cycle_opening,beta_schemas
    from tests.test_recruitment_cycle_lifecycle import cancel_body
    cycle_leadership.cancel(actor(a['uid']),rid,uuid.uuid4(),cancel_body(cycle_leadership.get_cancel(actor(a['uid']),rid,n)))
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(n)))
        previous=policy.state(policy.get(db,row,generation=1))
    gb=group(client,b);add(client,b,a,gb);change(a,rid,c,gb)
    params=dict(base_starts_at=datetime.combine(date.fromisoformat(n),time(18),KST).astimezone(timezone.utc).isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=cycle_opening.get(actor(a['uid']),rid,n,'reopen');data=ctx['data']
        body=beta_schemas.BetaOpenRequest.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],
            target_cycle_key=n,expected_target_revision=ctx['scope']['target_revision'],context_token=data['context_token'],
            selection=data['selection'],target_items=data['targets'],target_session_ids=[],intent='reopen',beta_schedule=data['beta_schedule_config']))
        result=cycle_opening.execute(actor(a['uid']),rid,uuid.uuid4(),body)[1]
        assert result['scope']['target_generation']==2
    with session() as db:
        row=db.get(RoomCycle,row.id)
        assert policy.state(policy.get(db,row,generation=1))==previous
        assert policy.get(db,row).group_id==uuid.UUID(gb)
        assert policy.metadata(db,row,generation=999)['state']=='unavailable'
    assert state(rid,c)['group_id']==uuid.UUID(gb)
    from app.raid_rooms import membership_readers
    page=membership_readers.memberships(actor(a['uid']),n,state='all',include_group_state=True)
    assert {v['generation']:v['group_id'] for v in page['cycle_groups']}=={1:gid,2:gb}


def test_group_change_final_context_expiry_rolls_back_ack(policy_db,client,monkeypatch):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a)
    from app.raid_rooms import cycles
    actual=cycles.now;calls=[]
    def delayed(db):
        calls.append(True)
        return actual(db)+(timedelta(minutes=3) if len(calls)>1 else timedelta())
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    monkeypatch.setattr(cycles,'now',delayed)
    with pytest.raises(GameError) as caught:change(a,rid,c,gid)
    assert caught.value.code=='COMMAND_CONTEXT_EXPIRED'
    assert table_digests(engine,set(before))==before


def test_n_cancellation_group_priority_then_public_fallback(policy_db,client,people):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True)
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    third=people('policy-n-successor');add(client,a,third,gid)
    beta_join(b,rid,n);beta_join(third,rid,n);change(a,rid,n,gid)
    from tests.test_recruitment_cycle_lifecycle import cancel_body
    ctx=cycle_leadership.get_cancel(actor(a['uid']),rid,n)
    with session() as db:assert db.get(CycleMember,uuid.UUID(ctx['data']['successor']['cycle_member_id'])).user_id==third['uid']
    cycle_leadership.cancel(actor(a['uid']),rid,uuid.uuid4(),cancel_body(ctx))
    assert state(rid,n)['scope']=='group'
    ctx=cycle_leadership.get_cancel(actor(third['uid']),rid,n)
    cycle_leadership.cancel(actor(third['uid']),rid,uuid.uuid4(),cancel_body(ctx))
    assert state(rid,n)['scope']=='public' and state(rid,c)['scope']=='public'


def test_missing_current_policy_is_not_zero_group_blockers(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a);change(a,rid,c,gid)
    from app.groups import raid_state
    from app.groups.models import Group
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        db.delete(policy.get(db,row))
    with session() as db:
        blocked,items=raid_state.evaluate(db,db.get(Group,uuid.UUID(gid)),now(db))
        assert blocked['state']=='unavailable' and blocked['blocking_room_count'] is None


def test_settings_context_binds_membership_identity_after_rejoin(policy_db,client):
    engine,a,b=policy_db;gid=group(client,b);add(client,b,a,gid);rid,c,_,_,_=create_beta(a)
    ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(gid))
    body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1))
    from app.groups.models import GroupMembership
    with session() as db,db.begin():
        old=policy.member(db,uuid.UUID(gid),a['uid']);old.ended_at=now(db);old.revision+=1
        db.flush()
        db.add(GroupMembership(id=uuid.uuid4(),group_id=uuid.UUID(gid),user_id=a['uid'],revision=1,joined_at=now(db)))
    with pytest.raises(GameError) as caught:cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),body,'settings')
    assert caught.value.code=='TARGET_CONTEXT_STALE'
    assert state(rid,c)['scope']=='public'


def test_all_detail_profiles_share_target_badges_and_legacy_c_projection(policy_db,client):
    engine,a,b=policy_db;ga=group(client,a);gb=group(client,b);add(client,b,a,gb)
    rid,c,_,_,_=create_beta(a,combined=True);n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    for key in (c,n):beta_join(b,rid,key)
    change(a,rid,c,ga);change(a,rid,n,gb)
    from app.raid_rooms import group_link_display, membership_readers
    for key,gid,expected in ((c,ga,False),(n,gb,True)):
        for viewer in (a,b):
            for profile in (None,'application-display-1','membership-actions-1'):
                value=group_link_display.get(actor(viewer['uid']),rid,key,'detail',reader_profile=profile)
                members=value['data']['content']['data']['members'] if profile=='membership-actions-1' else value['data']['members']
                target=next(v for v in members if v['membership_id']==cycle_member_reads.detail(actor(b['uid']),rid,key)['data']['my_membership']['membership_id'])
                assert target['group_member'] is expected
                assert value['group_state']['group_id']==uuid.UUID(gid)
        old=cycle_queries.get_card(actor(a['uid']),rid,key)
        assert old['data']['group_id']==gid
    from app.raid_rooms import v1_compat
    value=v1_compat.dispatch('card',{'principal':actor(a['uid']),'rid':rid})
    assert value['group_id']==ga


def test_group_context_rejects_actor_and_opposite_target_forgery(policy_db,client):
    engine,a,b=policy_db;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True);beta_join(b,rid,c)
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    ctx=cycle_management.group_context(actor(a['uid']),rid,c,uuid.UUID(gid))
    body=settings(a,rid,c,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1))
    before=table_digests(engine,set(inspect(engine).get_table_names())-{'game_account_requests'})
    with pytest.raises(GameError):cycle_management.command(actor(b['uid']),rid,uuid.uuid4(),body,'settings')
    other=settings(a,rid,n,context_token=ctx['data']['context_token'],group_policy=dict(scope='group',group_id=gid,expected_revision=1))
    with pytest.raises(GameError) as caught:cycle_management.command(actor(a['uid']),rid,uuid.uuid4(),other,'settings')
    assert caught.value.code=='TARGET_SCOPE_MISMATCH'
    assert table_digests(engine,set(before))==before


def test_closed_null_leader_settings_are_readable_with_edit_denied(policy_db,client):
    engine,a,b=policy_db;rid,c,_,_,_=create_beta(a)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        generation=db.get(CycleGeneration,(row.id,row.generation))
        row.state='closed';generation.state='completed';generation.closed_at=now(db)
        generation.leader_cycle_member_id=None
    value=cycle_member_reads.detail(actor(a['uid']),rid,c)
    assert value['data']['settings']['permissions']['edit_settings']==dict(allowed=False,reason='ROUND_NOT_ACTIVE',next_change_at=None)
    value=cycle_management.get(actor(a['uid']),rid,c)
    assert value['data']['permissions']['edit_settings']['reason']=='ROUND_NOT_ACTIVE'
