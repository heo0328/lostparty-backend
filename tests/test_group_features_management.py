"""Atomic group management, restricted PostgreSQL, fabricated memberships."""
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, func
from app.core.database import session
from app.groups import extended_management as service, admissions
from app.groups.models import Group, GroupMembership
from app.groups.feature_models import GroupActivityHead
from app.groups.admission_models import GroupJoinCode, GroupJoinSubject
from app.member_limits.models import MemberUsageHead
from app.game_accounts.support import GameError
from tests.test_group_display import group_features, get, add
from tests.test_group_admissions import worlds, apply, action, post, own_selection, invite, new_code, join
from tests.test_group_foundation import actor
from tests.test_group_management import command

MANAGEMENT = {'management_profile':'group-management-1'}


def state(client,w,gid):
    return get(client,w,f'/v1/groups/{gid}/management',**MANAGEMENT)


def body(client,w,gid):
    value=state(client,w,gid);m=value['my_membership']
    return dict(expected_group_revision=value['group_revision'],expected_members_revision=value['members_revision'],
        expected_membership_id=m['membership_id'],expected_membership_revision=m['revision'])


def test_disband_atomic_code_history_and_ack(group_features,client):
    _,a,b,gid=group_features
    new_code(client,a,gid)
    data=body(client,a,gid);key=uuid.uuid4()
    result=post(client,a,f'/v1/groups/{gid}/disband',data,key)
    assert result.status_code==200,result.text
    assert post(client,a,f'/v1/groups/{gid}/disband',data,key).json()==result.json()
    assert post(client,a,f'/v1/groups/{gid}/disband',data).status_code==404
    with session() as db:
        g=db.get(Group,uuid.UUID(gid));m=db.get(GroupMembership,uuid.UUID(data['expected_membership_id']))
        assert g.ended_at==m.ended_at and g.leader_membership_id==m.id
        assert db.scalar(select(GroupJoinCode).where(GroupJoinCode.group_id==g.id)).revoked_at is not None
        assert db.get(GroupActivityHead,g.id).last_activity_at is not None


def test_pending_disband_and_self_remove_rejected(group_features,client):
    _,a,b,gid=group_features;assert apply(client,b,gid).status_code==201
    value=state(client,a,gid)
    assert value['permissions']['disband']['reason']=='GROUP_PENDING_RELATIONS_EXIST'
    response=post(client,a,f'/v1/groups/{gid}/disband',body(client,a,gid))
    assert response.status_code==409
    data=body(client,a,gid);data['expected_target_membership_revision']=data['expected_membership_revision']
    assert post(client,a,f'/v1/groups/{gid}/members/{data["expected_membership_id"]}/remove',data).status_code==409


def test_remove_invites_usage_rejoin_and_historical_ack(group_features,client,worlds):
    _,a,b,gid=group_features;mid=add(client,a,b,gid)
    other=worlds('invited-by-removed');invitation=invite(client,b,other,gid).json();code=new_code(client,a,gid).json()['code']
    data=body(client,a,gid);data['expected_target_membership_revision']=1;key=uuid.uuid4()
    result=post(client,a,f'/v1/groups/{gid}/members/{mid}/remove',data,key)
    assert result.status_code==200,result.text
    assert get(client,other,'/v1/me/group-request-counts')['action_required']==0
    with session() as db:
        subject=db.scalar(select(GroupJoinSubject).where(GroupJoinSubject.group_id==uuid.UUID(gid),GroupJoinSubject.user_id==b['uid']))
        assert subject.blocked_at is None
    rejoined=join(client,b,code);assert rejoined.status_code==200,rejoined.text
    assert rejoined.json()['my_membership']['membership_id']!=mid
    assert post(client,a,f'/v1/groups/{gid}/members/{mid}/remove',data,key).json()==result.json()
    assert get(client,b,'/v1/me/groups/'+gid)['my_membership']['membership_id']!=mid


def test_representative_owned_activity_and_noop(group_features,client):
    _,a,b,gid=group_features;add(client,a,b,gid)
    data={**body(client,a,gid),**own_selection(a),'character_id':a['ids'][1]}
    def put(w, value):return client.put('/v1/groups/'+gid+'/representative',headers={**w['headers'],'Idempotency-Key':str(uuid.uuid4())},json=value)
    assert put(b,data).status_code==403
    changed=put(a,data);assert changed.status_code==200,changed.text
    assert changed.json()['outcome']=='applied'
    with session() as db:stamp=db.get(GroupActivityHead,uuid.UUID(gid)).last_activity_at
    data.update(body(client,a,gid));noop=put(a,data);assert noop.status_code==200,noop.text
    assert noop.json()['outcome']=='noop' and noop.json()['changed_at'] is None
    with session() as db:assert db.get(GroupActivityHead,uuid.UUID(gid)).last_activity_at==stamp
    data.update(character_id=a['ids'][2]);assert put(a,data).status_code==409
    assert get(client,a,'/v1/me/groups/'+gid)['group']['name']!=''


def test_ack_failure_rolls_back_disband_and_activity(group_features,client,monkeypatch):
    _,a,b,gid=group_features;data=body(client,a,gid);key=uuid.uuid4()
    with session() as db:
        before=db.get(Group,uuid.UUID(gid)).revision
        head=db.get(GroupActivityHead,uuid.UUID(gid));stamp=head.last_activity_at if head else None
    with monkeypatch.context() as patch:
        def fail(*args):raise RuntimeError('synthetic ACK failure')
        patch.setattr(admissions,'commit_result',fail)
        assert post(client,a,f'/v1/groups/{gid}/disband',data,key).status_code==500
    with session() as db:
        g=db.get(Group,uuid.UUID(gid));head=db.get(GroupActivityHead,g.id)
        assert g.ended_at is None and g.revision==before
        assert (head.last_activity_at if head else None)==stamp
    assert post(client,a,f'/v1/groups/{gid}/disband',data,key).status_code==200


def test_concurrent_disband_application_no_partial_success(group_features,client):
    _,a,b,gid=group_features;data=body(client,a,gid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(post,client,a,f'/v1/groups/{gid}/disband',data)
        second=pool.submit(apply,client,b,gid)
        responses=[first.result(),second.result()]
    assert sum(r.status_code in (200,201) for r in responses)==1
    with session() as db:
        g=db.get(Group,uuid.UUID(gid))
        active=db.scalar(select(func.count()).select_from(GroupMembership).where(GroupMembership.group_id==g.id,GroupMembership.ended_at.is_(None)))
        assert active==(0 if g.ended_at else 1)


def test_current_members_share_empty_room_listing_and_no_group_commands(group_features,client):
    _,a,b,gid=group_features;add(client,a,b,gid)
    for w in (a,b):
        value=get(client,w,f'/v1/groups/{gid}/raid-rooms')
        assert value['state']=='clear' and value['blocking_room_count']==0 and value['items']==[]
        assert client.post(f'/v1/groups/{gid}/raid-rooms/{uuid.uuid4()}/make-public',headers=w['headers'],json={}).status_code==404
    assert not state(client,b,gid)['permissions']['remove_member']['allowed']


def test_database_failure_not_zero_and_unknown_schema_rejected(group_features,client,monkeypatch):
    from app.groups import raid_state
    from sqlalchemy.exc import OperationalError
    from sqlalchemy import text
    _,a,b,gid=group_features
    with monkeypatch.context() as patch:
        def unavailable(*args):raise OperationalError('synthetic source unavailable',{},None)
        patch.setattr(raid_state,'evaluate',unavailable)
        response=client.get('/v1/groups/'+gid+'/raid-rooms',headers=a['headers'])
        assert response.status_code==503
    with session() as db,db.begin():db.execute(text("UPDATE alembic_version SET version_num='9999_unknown'"))
    assert client.get('/v1/groups/'+gid+'/management',headers=a['headers'],params=MANAGEMENT).status_code==503
    assert client.get('/v1/groups/'+gid+'/members',headers=a['headers']).status_code==200


def test_concurrent_remove_transfer_has_one_owner_and_no_partial_relation(group_features,client):
    from tests.test_group_management import command
    _,a,b,gid=group_features;mid=add(client,a,b,gid)
    removal={**body(client,a,gid),'expected_target_membership_revision':1}
    transfer=command(a,gid,b).model_dump(mode='json')
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(post,client,a,f'/v1/groups/{gid}/members/{mid}/remove',removal)
        second=pool.submit(post,client,a,f'/v1/groups/{gid}/leadership-transfer',transfer)
        responses=[first.result(),second.result()]
    assert sum(r.status_code==200 for r in responses)==1
    assert all(r.status_code in (200,403,409) for r in responses)
    with session() as db:
        g=db.get(Group,uuid.UUID(gid));leader=db.get(GroupMembership,g.leader_membership_id)
        assert leader.ended_at is None
        target=db.get(GroupMembership,uuid.UUID(mid))
        assert (target.ended_at is not None)==(leader.user_id==a['uid'])


def test_code_join_updates_display_provenance_with_selected_character(group_features,client):
    from tests.test_group_admissions import code_join_body
    from app.groups.feature_models import SubjectCharacterReference
    _,a,b,gid=group_features
    original=invite(client,a,b,gid).json();assert action(client,a,original['relation_id'],'cancel').status_code==200
    code=new_code(client,a,gid).json()['code'];data=code_join_body(client,b,code);data['character_id']=b['ids'][1]
    response=post(client,b,'/v1/group-join-codes/join',data);assert response.status_code==200,response.text
    with session() as db:
        subject=db.scalar(select(GroupJoinSubject).where(GroupJoinSubject.group_id==uuid.UUID(gid),GroupJoinSubject.user_id==b['uid']))
        ref=db.get(SubjectCharacterReference,subject.id)
        assert ref.character_id==uuid.UUID(b['ids'][1])
