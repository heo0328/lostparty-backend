"""First group connection and opt-in display; disposable PostgreSQL only."""
import uuid
import json
from pathlib import Path
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,event,inspect,text
from app.core.database import session,now
from app.groups.models import Group,GroupMembership,GroupDirectoryHead
from app.groups.feature_models import GroupActivityHead
from app.member_limits.models import MemberUsageLimits
from app.game_accounts.support import GameError
from app.raid_rooms import (beta_profile,cycle_common as common,cycle_schemas,cycles,cycle_member_reads,
    cycle_queries,cycle_wire,group_list_display,cycle_leadership,group_connection)
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.integrated_models import RecruitmentRoom as Room
from tests.test_group_raid_lifecycle import (group_beta,beta,current,candidate,ready,sources,imported,people,worlds,create_group_room,beta_join)
from tests.test_beta_recruitment import create_beta,PROFILE
from tests.test_groups_http import create,fresh_body
from tests.test_group_display import add
from tests.test_group_foundation import actor
from tests.test_recruitment_cycle_management import global_body,transfer_body
from tests.test_recruitment_cycle_http import client as raid_client
from tests.test_recruitment_cycle_times import fingerprints
from tests.test_raid_room_migrations import table_digests


def group(client,w):
    response=create(client,w,fresh_body(client,w))
    assert response.status_code==201,response.text
    return response.json()['group']['group_id']


def ctx(a,rid,gid):
    with beta_profile.using():return common.get(actor(a['uid']),rid,'edit_common_settings',uuid.UUID(gid))


def body(value,gid):
    return global_body(value,group_id=gid,scope='group',expected_group_revision=value['target_group']['group_revision'])


def connect(a,rid,value,gid,key=None):
    with beta_profile.using():return common.execute(actor(a['uid']),rid,key or uuid.uuid4(),body(value,gid),'edit_common_settings')


def error(code,fn,*args,**kwargs):
    with pytest.raises(GameError) as caught:fn(*args,**kwargs)
    assert caught.value.code==code


def test_atomic_initial_connection_preserves_ledger_cn_and_original_ack(group_beta,client):
    engine,a,b=group_beta;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True);beta_join(b,rid,c)
    protected={'recruitment_memberships','recruitment_assignments','recruitment_cycle_members','recruitment_cycle_assignments',
        'recruitment_sessions','recruitment_session_participations','recruitment_time_reservations','recruitment_weekly_occupancies','raid_weekly_states'}
    protected&=set(inspect(engine).get_table_names());before=table_digests(engine,protected)
    value=ctx(a,rid,gid);assert value['data']['permission']['allowed']
    assert value['target_group']['membership_id'] and len(value['data']['impact_cycles'])==2
    key=uuid.uuid4();ack=connect(a,rid,value,gid,key)
    assert ack[1]['data']['outcome']=='applied' and len(ack[1]['data']['affected_cycle_keys'])==2
    assert table_digests(engine,protected)==before
    with session() as db:
        room=db.get(Room,rid);assert room.group_id==uuid.UUID(gid) and room.scope=='group'
        assert db.get(GroupActivityHead,uuid.UUID(gid)) is not None
    with beta_profile.using():
        assert cycle_member_reads.detail(actor(b['uid']),rid,c)['data']['my_membership']['group_member'] is False
        fresh=common.get(actor(a['uid']),rid,'edit_common_settings')
        common.execute(actor(a['uid']),rid,uuid.uuid4(),global_body(fresh,scope='public'),'edit_common_settings')
    assert connect(a,rid,value,gid,key)==ack
    with session() as db:assert db.get(Room,rid).scope=='public'
    with beta_profile.using():
        fresh=common.get(actor(a['uid']),rid,'edit_common_settings')
        assert common.execute(actor(a['uid']),rid,uuid.uuid4(),global_body(fresh,scope='group'),'edit_common_settings')[1]['data']['outcome']=='applied'
        error('GROUP_LINK_IMMUTABLE',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(common.get(actor(a['uid']),rid,'edit_common_settings'),group_id=None),'edit_common_settings')


@pytest.mark.parametrize('change',['member_revision','members_revision','ended','left','limit'])
def test_target_group_context_rejects_changed_authority_and_capacity(group_beta,client,change):
    _,a,b=group_beta;gid=group(client,a);rid,*_=create_beta(a);value=ctx(a,rid,gid)
    with session() as db,db.begin():
        g=db.get(Group,uuid.UUID(gid));member=db.get(GroupMembership,g.leader_membership_id)
        if change=='member_revision':member.revision+=1
        elif change=='members_revision':g.members_revision+=1
        elif change=='ended':g.ended_at=now(db)
        elif change=='left':member.ended_at=now(db)
        else:
            limit=db.get(MemberUsageLimits,a['uid'])
            if limit is None:db.add(MemberUsageLimits(user_id=a['uid'],revision=2,group_capacity=0,joined_groups=5,raid_rooms=10,updated_at=now(db)))
            else:limit.group_capacity=0;limit.revision+=1
    with pytest.raises(GameError):connect(a,rid,value,gid)
    with session() as db:assert db.get(Room,rid).group_id is None


def test_token_binds_selected_group_and_rejects_wrong_scope_and_legacy_context(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);other=group(client,a);rid,*_=create_beta(a);value=ctx(a,rid,gid)
    error('TARGET_SCOPE_MISMATCH',connect,a,rid,value,other)
    with beta_profile.using():
        error('TARGET_SCOPE_MISMATCH',common.execute,actor(a['uid']),rid,uuid.uuid4(),body(value,gid).model_copy(update={'scope':cycle_wire.Scope1('public')}),'edit_common_settings')
        legacy=common.get(actor(a['uid']),rid,'edit_common_settings');assert 'target_group' not in legacy
        error('GROUP_LINK_IMMUTABLE',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(legacy,group_id=gid,expected_group_revision=1,scope='group'),'edit_common_settings')
        error('INVALID_REQUEST',common.get,actor(a['uid']),rid,'leave',uuid.UUID(gid))
    connect(a,rid,value,gid)
    with beta_profile.using():error('GROUP_LINK_IMMUTABLE',common.get,actor(a['uid']),rid,'edit_common_settings',uuid.UUID(other))


def test_ack_and_final_expiry_failures_roll_back_group_link_activity_and_directories(group_beta,client,monkeypatch):
    engine,a,b=group_beta;gid=group(client,a);rid,*_=create_beta(a);value=ctx(a,rid,gid)
    before=fingerprints(engine)
    with monkeypatch.context() as patch:
        def broken(*args,**kwargs):raise RuntimeError('Synthetic ACK failure')
        patch.setattr(cycles,'commit_result',broken)
        with pytest.raises(RuntimeError):connect(a,rid,value,gid)
    assert fingerprints(engine)==before
    real=cycles.now;calls=[]
    with monkeypatch.context() as patch:
        def expired(db):calls.append(1);return real(db) if len(calls)==1 else real(db)+timedelta(minutes=3)
        patch.setattr(cycles,'now',expired)
        error('COMMAND_CONTEXT_EXPIRED',connect,a,rid,value,gid)
    assert fingerprints(engine)==before
    assert connect(a,rid,value,gid)[1]['data']['outcome']=='applied'


def test_cn_different_leaders_keep_g1_authority_and_no_fallback(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);add(client,a,b,gid);rid,c,_,_,_=create_beta(a,combined=True)
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat();beta_join(b,rid,n)
    with beta_profile.using():cycle_leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),transfer_body(a,rid,n,b))
    denied=ctx(b,rid,gid);assert denied['data']['permission']['reason']=='COMMON_LEADER_REQUIRED'
    error('COMMON_LEADER_REQUIRED',connect,b,rid,denied,gid)
    with session() as db,db.begin():
        current=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)));current.state='review_required'
    assert not ctx(b,rid,gid)['data']['permission']['allowed']


def test_concurrent_initial_connections_have_one_effect(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);other=group(client,a);rid,*_=create_beta(a);first=ctx(a,rid,gid);second=ctx(a,rid,other)
    def run(v,g):
        try:return connect(a,rid,v,g)[1]['data']['outcome']
        except GameError:return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda pair:run(*pair),[(first,gid),(second,other)]))
    assert sorted(results)==['applied','rejected']


def test_http_opt_in_search_membership_pages_and_nonmember_badges(group_beta,client):
    engine,a,b=group_beta;gid=group(client,a);rid,c,_,_,_=create_beta(a,combined=True);beta_join(b,rid,c)
    connect(a,rid,ctx(a,rid,gid),gid)
    with beta_profile.using():
        value=common.get(actor(a['uid']),rid,'edit_common_settings');common.execute(actor(a['uid']),rid,uuid.uuid4(),global_body(value,scope='public'),'edit_common_settings')
    expected={str(a['uid']):True,str(b['uid']):False}
    samples=[]
    for viewer in (a,b):
        with raid_client(viewer) as http:
            params={**PROFILE,'target_cycle_key':c}
            for reader in (None,'application-display-1','membership-actions-1'):
                for include in (False,True):
                    query=dict(params)
                    if reader:query['reader_profile']=reader
                    if include:query['include_group_state']='true'
                    response=http.get(f'/v2/raid-rooms/{rid}/detail',params=query)
                    assert response.status_code==200,response.text
                    value=response.json()['data'];value=value['content']['data'] if reader=='membership-actions-1' else value
                    flags={item['membership_id']:item['group_member'] for item in value['members']}
                    samples.append(flags)
            for reader in (None,'membership-actions-1'):
                query=dict(params,include_group_state='true')
                if reader:query['reader_profile']=reader
                page=http.get('/v2/me/raid-room-memberships',params=query)
                assert page.status_code==200,page.text
                assert page.json()['group_states']==[dict(group_id=gid,name=page.json()['group_states'][0]['name'],state='active')]
                assert page.json()['room_groups']==[dict(room_id=str(rid),group_id=gid)]
            page=http.get('/v2/me/raid-room-applications',params=dict(params,include_group_state='true'))
            assert page.status_code==200 and page.json()['group_states']==[]
    assert all(flags==samples[0] for flags in samples)
    examples=json.loads(Path('docs/features/groups/raid-link-examples.json').read_text())
    assert len(examples['badge_observations'])==len(samples)==12
    assert all(sorted(m['group_member'] for m in e['members'])==sorted(samples[0].values()) for e in examples['badge_observations'])
    assert sorted(samples[0].values())==[False,True]
    with session() as db,db.begin():
        g=db.get(Group,uuid.UUID(gid));g.ended_at=now(db);db.get(GroupDirectoryHead,1).revision+=1
    with raid_client(b) as http:
        page=http.get('/v2/me/raid-room-memberships',params={**PROFILE,'target_cycle_key':c,'include_group_state':'true'})
        assert page.status_code==200 and page.json()['group_states'][0]['state']=='ended'
        detail=http.get(f'/v2/raid-rooms/{rid}/detail',params={**PROFILE,'target_cycle_key':c})
        assert detail.status_code==200 and all(not m['group_member'] for m in detail.json()['data']['members'])


def test_page_metadata_bound_to_cursor_and_readonly_snapshot(group_beta,client,people,monkeypatch):
    engine,a,b=group_beta;gid=group(client,a);rid,c,_,_,_=create_beta(a)
    connect(a,rid,ctx(a,rid,gid),gid)
    with beta_profile.using():
        value=common.get(actor(a['uid']),rid,'edit_common_settings');common.execute(actor(a['uid']),rid,uuid.uuid4(),global_body(value,scope='public'),'edit_common_settings')
    # A second actual target makes a real paginated result without manufacturing a room row.
    other=people('group-link-card-other');other_gid=group(client,other)
    rid2,*_=create_group_room(other,other_gid)
    with beta_profile.using():
        value=common.get(actor(other['uid']),rid2,'edit_common_settings');common.execute(actor(other['uid']),rid2,uuid.uuid4(),global_body(value,scope='public'),'edit_common_settings')
    from app.game_accounts.provider import LostArkProvider
    def forbidden(*args,**kwargs):raise AssertionError('No provider during group display reads')
    monkeypatch.setattr(LostArkProvider,'_fetch',forbidden)
    search=dict(target_cycle_key=c,category='all',admission_scope='public',group_ids=[],filter_context_token=None,member_conditions=[],raid_ids=[],difficulty_ids=[],limit=1,cursor=None)
    statements=[]
    def record(conn,cursor,sql,params,context,many):statements.append(sql.lstrip().split()[0].upper())
    event.listen(engine,'before_cursor_execute',record)
    try:
        with raid_client(b) as http:
            page=http.post('/v2/raid-rooms/search',params={**PROFILE,'include_group_state':'true'},json=search)
            assert page.status_code==200,page.text
            value=page.json();assert len(value['group_states'])==1 and len(value['room_groups'])==1
            token=value['data']['next_cursor'];assert token
            ordinary=http.get('/v2/raid-rooms',params={**PROFILE,'target_cycle_key':c})
            assert ordinary.status_code==200 and 'group_states' not in ordinary.json()
            listed=http.get('/v2/raid-rooms',params={**PROFILE,'target_cycle_key':c,'include_group_state':'true'})
            assert listed.status_code==200 and len(listed.json()['group_states'])==2
    finally:event.remove(engine,'before_cursor_execute',record)
    assert set(statements)<={'SELECT','SET'}
    with session() as db,db.begin():
        db.get(Group,uuid.UUID(gid)).name='Renamed group';db.get(GroupDirectoryHead,1).revision+=1
    with raid_client(b) as http:
        stale=http.post('/v2/raid-rooms/search',params={**PROFILE,'include_group_state':'true'},json=dict(search,cursor=token))
        assert stale.status_code==409 and stale.json()['error']['code']=='CURSOR_STALE'
        invalid=http.get('/v2/raid-rooms',params=[('target_cycle_key',c),('include_group_state','true'),('include_group_state','false')])
        assert invalid.status_code==400


def test_pending_application_survives_first_link_and_page_uses_current_group(group_beta,client):
    engine,a,b=group_beta;gid=group(client,a);rid,c,*_=create_beta(a,mode='leader_only')
    from tests.test_application_composition import apply
    from app.raid_rooms.cycle_application_models import CycleApplication
    with beta_profile.using():pending=apply(b,rid,c)[1]['data']
    before=table_digests(engine,{'recruitment_cycle_applications'})
    connect(a,rid,ctx(a,rid,gid),gid)
    assert table_digests(engine,{'recruitment_cycle_applications'})==before
    with raid_client(b) as http:
        page=http.get('/v2/me/raid-room-applications',params={**PROFILE,'target_cycle_key':c,'include_group_state':'true'})
        assert page.status_code==200,page.text
        value=page.json();assert value['data']['items'][0]['admission_origin']['group_id'] is None
        assert value['room_groups']==[dict(room_id=str(rid),group_id=gid)]
        assert value['group_states'][0]['group_id']==gid
        assert value['data']['items'][0]['state']=='pending'


def test_target_group_default_limits_without_override_row(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);rid,*_=create_beta(a)
    with session() as db,db.begin():
        row=db.get(MemberUsageLimits,a['uid'])
        if row is not None:db.delete(row)
    value=ctx(a,rid,gid);assert value['target_group']['permission']['allowed']
    assert connect(a,rid,value,gid)[1]['data']['outcome']=='applied'


def test_first_connection_and_real_group_leave_share_write_lock(group_beta,client):
    _,a,b=group_beta;gid=group(client,b);add(client,b,a,gid);rid,c,*_=create_beta(a);value=ctx(a,rid,gid)
    from app.groups import management
    from tests.test_group_management import command
    leave=command(a,gid)
    def link():
        try:return connect(a,rid,value,gid)[1]['data']['outcome']
        except GameError:return 'rejected'
    def depart():return management.leave(actor(a['uid']),uuid.UUID(gid),uuid.uuid4(),leave)
    with ThreadPoolExecutor(max_workers=2) as pool:
        f=pool.submit(link);g=pool.submit(depart);outcome=f.result();assert g.result()[0]==200
    with session() as db:
        row=db.get(Room,rid);assert (row.group_id is not None)==(outcome=='applied')
    with beta_profile.using():assert cycle_member_reads.detail(actor(a['uid']),rid,c)['data']['my_membership'] is not None


def test_display_database_failure_is_503_and_not_empty_success(group_beta,client,monkeypatch):
    _,a,b=group_beta;rid,c,*_=create_beta(a)
    from sqlalchemy.exc import OperationalError
    with monkeypatch.context() as patch:
        def unavailable(*args,**kwargs):raise OperationalError('Synthetic group read failure',{},None)
        patch.setattr(group_list_display,'attach',unavailable)
        with raid_client(b) as http:
            result=http.get('/v2/raid-rooms',params={**PROFILE,'target_cycle_key':c,'include_group_state':'true'})
            assert result.status_code==503 and result.json()['error']['code']=='SERVICE_UNAVAILABLE'


def test_pre34_keeps_default_but_rejects_opt_in(beta,client):
    _,a,b=beta;rid,c,*_=create_beta(a)
    with raid_client(b) as http:
        params={**PROFILE,'target_cycle_key':c}
        assert http.get('/v2/raid-rooms',params=params).status_code==200
        response=http.get('/v2/raid-rooms',params=dict(params,include_group_state='true'))
        assert response.status_code==503 and response.json()['error']['code']=='GROUP_FEATURE_NOT_READY'
