"""Group/raid lifetimes remain independent on current and next actual targets."""
import os
import subprocess
import uuid
from datetime import date, timedelta, timezone
import pytest
from sqlalchemy import select, delete
from app.core.database import session, now
from app.groups import management, raid_state
from app.groups.models import Group, GroupMembership
from app.game_accounts.models import Activity
from app.game_accounts.support import GameError
from app.raid_rooms import beta_profile, beta_schedule, beta_schemas, cycle_creation, cycle_commands, cycle_member_reads, cycle_common, cycle_lifecycle
from app.raid_rooms.cycle_models import RoomCycle
from app.raids import service as raids
from tests.test_beta_recruitment import beta, current, candidate, ready, sources, imported, people, worlds, beta_join
from tests.test_recruitment_cycle_creation import preflight, request
from tests.test_recruitment_cycle_commands import context, admission_request
from tests.test_group_admissions import group
from tests.test_group_display import get, add
from tests.test_group_management import command
from tests.test_group_foundation import actor


@pytest.fixture
def group_beta(beta):
    engine,a,b=beta
    result=subprocess.run(['alembic','upgrade','0034_group_features'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,'restricted group migration failed'
    from app.raid_rooms import readiness
    with session() as db:
        readiness.require_two_cycle_active(db)
        readiness.require_cycle_worker(db)
    return engine,a,b


def create_group_room(w,gid):
    with session() as db:base=beta_schedule.time_policy.ceil_tick(now(db)+timedelta(hours=2)).astimezone(timezone.utc)
    key=raids.cycle(base).cycle_key
    params=dict(base_starts_at=base.isoformat(),early_coordination_enabled='false',
        next_base_starts_at=(base+timedelta(days=7,hours=1)).isoformat(),next_early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=preflight(w,key=key,continuation=True,gid=uuid.UUID(gid))
        body=request(ctx,scope='group',group_id=gid).model_dump(mode='json')
        body.pop('schedule_groups');body['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        value=cycle_creation.create(actor(w['uid']),uuid.uuid4(),beta_schemas.BetaCreateRequest.model_validate(body))[1]['data']
    return uuid.UUID(value['room_id']),*[c['target_cycle_key'] for c in value['created_cycles']]


def qualify(w,rid,key):
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        member=cycle_lifecycle.actual_member(db,row,w['uid'])
        return cycle_lifecycle.qualify(db,db.get(cycle_creation.Room,rid),row,member)


def test_regular_group_member_creates_leader_transfer_does_not_change_raid(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);add(client,a,b,gid)
    rid,c,n=create_group_room(b,gid)
    from tests.test_recruitment_cycle_http import client as raid_client
    with beta_profile.using(),pytest.raises(GameError) as exc:
        cycle_common.get(actor(a['uid']),rid,'edit_common_settings')
    assert exc.value.code=='ROOM_MEMBERSHIP_REQUIRED'
    before=[]
    with beta_profile.using():
        for key in (c,n):
            value=cycle_member_reads.detail(actor(b['uid']),rid,key)
            before.append(value['data']['leadership'])
    management.transfer(actor(a['uid']),uuid.UUID(gid),uuid.uuid4(),command(a,gid,b))
    with beta_profile.using():
        for i,key in enumerate((c,n)):
            assert cycle_member_reads.detail(actor(b['uid']),rid,key)['data']['leadership']==before[i]
    # A group leader alone gets no authority over a nonparticipant raid.
    with beta_profile.using(),pytest.raises(GameError) as exc:
        cycle_common.get(actor(a['uid']),rid,'edit_common_settings')
    assert exc.value.code=='ROOM_MEMBERSHIP_REQUIRED'


def test_group_leave_preserves_actual_c_but_does_not_admit_new_n(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);add(client,a,b,gid);rid,c,n=create_group_room(a,gid)
    beta_join(b,rid,c)
    management.leave(actor(b['uid']),uuid.UUID(gid),uuid.uuid4(),command(b,gid))
    with beta_profile.using():
        qualify(b,rid,c)
        value=cycle_member_reads.detail(actor(b['uid']),rid,c)['data']
        assert value['my_membership']['group_member'] is False
        ctx=context(b,rid,n)
        assert not ctx['data']['permissions']['join']['allowed']
        with pytest.raises(GameError) as exc:
            cycle_commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(ctx))
        assert exc.value.code=='GROUP_MEMBERSHIP_REQUIRED'
    with session() as db,db.begin():
        db.execute(delete(Activity).where(Activity.settings_id==b['cid']))
    with beta_profile.using(),pytest.raises(GameError):qualify(b,rid,c)


def test_group_ended_retains_actual_leadership_plan_and_blocks_new_access(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);add(client,a,b,gid);rid,c,n=create_group_room(a,gid)
    with session() as db,db.begin():
        db.get(Group,uuid.UUID(gid)).ended_at=now(db)
        for m in db.scalars(select(GroupMembership).where(GroupMembership.group_id==uuid.UUID(gid))):m.ended_at=now(db)
    with beta_profile.using():
        for key in (c,n):
            qualify(a,rid,key)
            view=cycle_member_reads.plan(actor(a['uid']),rid,key)
            assert view['data']['my_membership']['group_member'] is False
        ctx=cycle_common.get(actor(a['uid']),rid,'edit_common_settings')
        assert ctx['data']['permission']['allowed'],ctx['data']['permission']
        with pytest.raises(GameError) as exc:context(b,rid,c)
        assert exc.value.code in ('ROOM_NOT_FOUND','GROUP_NOT_ACTIVE')
    from tests.test_recruitment_cycle_http import client as raid_client
    with raid_client(a) as http:
        params={'target_cycle_key':c,'contract_profile':beta_profile.PROFILE,'include_group_state':'true'}
        response=http.get(f'/v2/raid-rooms/{rid}/detail',params=params)
        assert response.status_code==200,response.text
        assert response.json()['group_state']['state']=='ended'
        params['reader_profile']='membership-actions-1'
        response=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=params)
        assert response.status_code==200,response.text
        assert response.json()['group_state']['group_id']==gid
        params.pop('reader_profile');params.pop('include_group_state')
        response=http.get(f'/v2/raid-rooms/{rid}/detail',params=params)
        assert response.status_code==200 and 'group_state' not in response.json()
    assert client.get('/v1/groups/'+gid+'/raid-rooms',headers=b['headers']).status_code==404


def test_same_room_blocker_set_includes_cn_and_unknown_never_zero(group_beta,client):
    _,a,b=group_beta;gid=group(client,a);add(client,a,b,gid);rid,c,n=create_group_room(a,gid)
    from app.groups import extended_management
    with beta_profile.using():
        page=raid_state.listing(actor(b['uid']),uuid.UUID(gid),20,None)
        value=extended_management.get(actor(a['uid']),uuid.UUID(gid))
    assert page['blocking_room_count']==value['blocking_room_count']==1
    assert {str(t['target_cycle_key']) for t in page['items'][0]['targets']}=={c,n}
    assert all(t['leader_display'] is not None for t in page['items'][0]['targets'])
    with session() as db,db.begin():db.get(cycle_creation.Room,rid).migration_state='legacy_review_required'
    page=raid_state.listing(actor(a['uid']),uuid.UUID(gid),20,None)
    assert page['state']=='unavailable' and page['blocking_room_count'] is None and len(page['items'])==1
    from app.raid_rooms.cycle_models import CycleGeneration
    with session() as db,db.begin():
        db.get(cycle_creation.Room,rid).migration_state='ready'
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key))
        db.get(CycleGeneration,(row.id,row.generation)).state='review_required'
    page=raid_state.listing(actor(a['uid']),uuid.UUID(gid),20,None)
    assert page['state']=='unavailable' and page['blocking_room_count'] is None



def test_public_link_allows_normal_group_disband_and_raid_survives(group_beta,client):
    from app.groups import extended_management
    from app.groups.management_schemas import DisbandGroupIn
    from tests.test_recruitment_cycle_management import global_body
    from tests.test_group_features_management import body
    _,a,b=group_beta;gid=group(client,a);rid,c,n=create_group_room(a,gid)
    with beta_profile.using():
        ctx=cycle_common.get(actor(a['uid']),rid,'edit_common_settings')
        value=global_body(ctx,scope='public')
        cycle_common.execute(actor(a['uid']),rid,uuid.uuid4(),value,'edit_common_settings')
        assert raid_state.listing(actor(a['uid']),uuid.UUID(gid),20,None)['blocking_room_count']==0
        data=DisbandGroupIn(**body(client,a,gid))
        assert extended_management.command(actor(a['uid']),uuid.UUID(gid),uuid.uuid4(),data,'disband')[0]==200
        for key in (c,n):
            qualify(a,rid,key)
            assert cycle_member_reads.plan(actor(a['uid']),rid,key)['data']['my_membership'] is not None
        assert context(b,rid,c)['data']['permissions']['join']['allowed']
