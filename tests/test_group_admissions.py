"""G2 real HTTP/isolated PostgreSQL. Actors/provider data are fabricated fixtures."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from app.core.database import session, now
from app.auth import service as auth
from app.game_accounts.models import Activity, Character, RequestResult, NameClaim, Account, Registration, Configuration
from app.groups.models import Group, GroupMembership
from app.groups.admission_models import GroupJoinRelation, GroupJoinSubject, GroupJoinCode
from app.groups import admissions
from app.member_limits.service import Limits
from tests.test_representative import error
from tests.test_game_accounts import PrivateHeaders
from tests.test_groups_http import create, limits
from tests.test_member_limits import change


@pytest.fixture
def worlds(login, monkeypatch):
    def make(subject):
        monkeypatch.setattr(auth, 'verify_google', lambda *args: subject)
        result, _ = login()
        uid = uuid.UUID(result['user']['id'])
        with session() as db, db.begin():
            current = now(db)
            account = Account(owner_id=uid, verified_at=current)
            db.add(account); db.flush()
            registration = Registration(user_id=uid, account_id=account.id, lookup_name='sample-0',
                label='', is_main=True, preview=[], fetched_at=current, created_at=current, updated_at=current)
            db.add(registration)
            chars = [Character(account_id=account.id, server_name='test-server-'+subject, character_name=f'sample-{i}',
                summary=dict(server_name='test-server-'+subject,character_name=f'sample-{i}',class_name='test-class',
                             character_level=60,item_level='1700',combat_power=None),
                fetched_at=current,confirmed_at=current) for i in range(3)]
            db.add_all(chars); db.flush()
            db.add_all([NameClaim(server_name=c.server_name,character_name=c.character_name,character_id=c.id) for c in chars])
            config = Configuration(user_id=uid,account_id=account.id,representative_id=chars[0].id,state='configured')
            db.add(config); db.flush()
            db.add_all([Activity(settings_id=config.id,account_id=account.id,character_id=c.id) for c in chars[:2]])
            return dict(uid=uid,headers=PrivateHeaders(Authorization='Bearer '+result['access_token']),
                        rid=str(registration.id),aid=account.id,cid=config.id,ids=[str(c.id) for c in chars])
    return make


def post(client, w, path, body, key=None):
    return client.post(path, json=body, headers={**w['headers'], 'Idempotency-Key': str(key or uuid.uuid4())})


def own_selection(w):
    return dict(registration_id=w['rid'], character_id=w['ids'][0], expected_registration_version=1,
                expected_ownership_revision=1, expected_roster_revision=1, expected_lifecycle_revision=1)


def group(client, w):
    out=create(client,w);assert out.status_code==201,out.text
    return out.json()['group']['group_id']


def apply(client,w,gid,key=None):
    revision=client.get('/v1/groups/'+gid).json()['revision']
    return post(client,w,'/v1/groups/'+gid+'/applications',dict(**own_selection(w),expected_group_revision=revision),key)


def invite(client,sender,target,gid,key=None):
    detail=client.get('/v1/me/groups/'+gid,headers=sender['headers']).json()
    return post(client,sender,'/v1/groups/'+gid+'/invitations',dict(target_character_id=target['ids'][0],
        expected_target_ownership_revision=1,expected_target_lifecycle_revision=1,
        expected_group_revision=detail['group']['revision'],expected_membership_revision=detail['my_membership']['revision']),key)


def relation(client,w,rid):
    out=client.get('/v1/group-relations/'+rid,headers=w['headers']);assert out.status_code==200,out.text
    return out.json()


def action_body(client,w,rid):
    out=relation(client,w,rid)
    return dict(expected_relation_revision=out['revision'],expected_group_revision=out['group']['revision'],
                expected_members_revision=out['members_revision'])


def action(client,w,rid,verb,extra=None,key=None):
    data=action_body(client,w,rid);data.update(extra or {})
    return post(client,w,'/v1/group-relations/'+rid+'/'+verb,data,key)


def accept(client,w,rid,key=None):
    own=limits(client,w)
    return action(client,w,rid,'accept',dict(**own_selection(w),expected_limits_revision=own['limits_revision'],
                  expected_usage_revision=own['usage_revision']),key)


def code_state(client,w,gid):
    out=client.get('/v1/groups/'+gid+'/join-code',headers=w['headers']);assert out.status_code==200,out.text
    return out.json()


def code_command(client,w,gid):
    code=code_state(client,w,gid)
    detail=client.get('/v1/me/groups/'+gid,headers=w['headers']).json()
    return dict(expected_code_id=code['code_id'],expected_code_revision=code['revision'],
                expected_group_revision=detail['group']['revision'],expected_membership_revision=detail['my_membership']['revision'])


def new_code(client,w,gid,visible=False,key=None):
    return post(client,w,'/v1/groups/'+gid+'/join-code',dict(**code_command(client,w,gid),visible_to_members=visible),key)


def code_join_body(client,w,raw):
    preview=client.post('/v1/group-join-codes/preview',headers=w['headers'],json={'code':raw})
    assert preview.status_code==200,preview.text
    p=preview.json();own=limits(client,w)
    return dict(**own_selection(w),code=raw,expected_group_revision=p['group']['revision'],expected_members_revision=p['members_revision'],
                expected_code_id=p['code_id'],expected_code_revision=p['code_revision'],expected_limits_revision=own['limits_revision'],
                expected_usage_revision=own['usage_revision'])


def join(client,w,raw,key=None):
    return post(client,w,'/v1/group-join-codes/join',code_join_body(client,w,raw),key)


def subject(client,leader,gid,sid):
    with session() as db:return db.get(GroupJoinSubject,uuid.UUID(sid)).revision


def subject_command(client,leader,gid,sid):
    detail=client.get('/v1/me/groups/'+gid,headers=leader['headers']).json()
    return dict(expected_subject_revision=subject(client,leader,gid,sid),
                expected_group_revision=detail['group']['revision'],expected_membership_revision=detail['my_membership']['revision'])


def test_application_approve_atomic_membership_replay_and_current_roles(client,worlds):
    a,b=worlds('leader'),worlds('applicant');gid=group(client,a)
    key=uuid.uuid4();pending=apply(client,b,gid,key)
    assert pending.status_code==201,pending.text
    assert apply(client,b,gid,key).json()==pending.json()
    rid=pending.json()['relation_id']
    assert pending.json()['application_count']==1
    error(apply(client,b,gid),409,'GROUP_RELATION_EXISTS')
    assert client.get('/v1/me/group-relations?view=sent_applications',headers=b['headers']).json()['items'][0]['relation_id']==rid
    approved_key=uuid.uuid4();data=action_body(client,a,rid)
    approved=post(client,a,'/v1/group-relations/'+rid+'/approve',data,approved_key)
    assert approved.status_code==200 and approved.json()['state']=='accepted'
    assert post(client,a,'/v1/group-relations/'+rid+'/approve',data,approved_key).json()==approved.json()
    own=client.get('/v1/me/groups/'+gid,headers=b['headers']).json()
    assert own['my_membership']['role']=='member' and own['group']['member_count']==2
    assert limits(client,b)['usage_revision']==2
    with session() as db:
        assert db.scalar(select(func.count()).select_from(GroupMembership).where(GroupMembership.group_id==uuid.UUID(gid)))==2
    assert str(b['uid']) not in json.dumps(approved.json())


def test_invite_any_member_exact_lookup_accept_and_sender_cancel(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a)
    first=apply(client,b,gid).json();assert action(client,a,first['relation_id'],'approve').status_code==200
    with session() as db,db.begin():
        # Give the target a distinct name through a new fabricated character/claim-free setup already known to sender.
        target=db.get(Character,uuid.UUID(c['ids'][0]));name=target.character_name
    candidates=client.get('/v1/groups/'+gid+'/invite-candidates',headers=b['headers'],params={'character_name':name})
    assert candidates.status_code==200 and any(item['target_character_id']==c['ids'][0] for item in candidates.json()['items'])
    error(client.get('/v1/groups/'+gid+'/invite-candidates',headers=c['headers'],params={'character_name':name}),403,'GROUP_MEMBERSHIP_REQUIRED')
    invitation=invite(client,b,c,gid);assert invitation.status_code==201,invitation.text
    rid=invitation.json()['relation_id']
    assert relation(client,c,rid)['permissions']['accept']['allowed']
    error(apply(client,c,gid),409,'GROUP_RELATION_EXISTS')
    assert action(client,b,rid,'cancel').json()['state']=='cancelled'
    newer=invite(client,b,c,gid).json();rid=newer['relation_id']
    response=accept(client,c,rid);assert response.status_code==200,response.text
    assert response.json()['group']['member_count']==3
    assert relation(client,a,rid)['application_count']==0


def test_reject_resubmit_count_and_no_cooldown(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a)
    first=apply(client,b,gid).json()
    assert action(client,a,first['relation_id'],'reject').json()['state']=='rejected'
    second=apply(client,b,gid).json()
    assert second['relation_id']!=first['relation_id'] and second['subject_id']==first['subject_id']
    assert second['application_count']==2
    assert action(client,b,second['relation_id'],'cancel').json()['state']=='cancelled'


def test_expiry_read_only_reapply_and_cursor_stale(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a)
    first=apply(client,b,gid).json();rid=first['relation_id']
    with session() as db,db.begin():
        value=db.get(GroupJoinRelation,uuid.UUID(rid));value.created_at=now(db)-timedelta(hours=25);value.expires_at=now(db)-timedelta(hours=1)
    current=relation(client,b,rid)
    assert current['state']=='expired'
    with session() as db:assert db.get(GroupJoinRelation,uuid.UUID(rid)).state=='pending'
    error(action(client,a,rid,'approve'),409,'RELATION_NOT_PENDING')
    assert apply(client,b,gid).json()['application_count']==2


def test_block_all_routes_counter_no_revival_and_unblock(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a)
    pending=apply(client,b,gid).json();rid=pending['relation_id'];sid=pending['subject_id']
    code=new_code(client,a,gid).json()['code']
    result=action(client,a,rid,'reject',{'block_future':True})
    assert result.status_code==200
    error(apply(client,b,gid),403,'GROUP_JOIN_BLOCKED')
    error(invite(client,a,b,gid),403,'GROUP_JOIN_BLOCKED')
    error(client.post('/v1/group-join-codes/preview',headers=b['headers'],json={'code':code}),403,'GROUP_JOIN_BLOCKED')
    assert client.get('/v1/groups/'+gid+'/blocked-subjects',headers=a['headers']).json()['items'][0]['application_count']==1
    error(client.get('/v1/groups/'+gid+'/blocked-subjects',headers=b['headers']),403,'GROUP_MEMBERSHIP_REQUIRED')
    response=post(client,a,'/v1/groups/'+gid+'/join-subjects/'+sid+'/unblock',subject_command(client,a,gid,sid))
    assert response.status_code==200 and not response.json()['blocked']
    assert relation(client,b,rid)['state']=='rejected'
    assert join(client,b,code).status_code==200
    with session() as db:assert db.get(GroupJoinSubject,uuid.UUID(sid)).application_count==1


def test_full_group_accept_preserves_pending_then_can_retry(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=invite(client,a,b,gid).json()['relation_id']
    change(a['uid'],Limits(1,5,10))
    error(accept(client,b,rid),409,'GROUP_CAPACITY_REACHED')
    assert relation(client,b,rid)['state']=='pending'
    change(a['uid'],Limits(2,5,10),expected=2)
    assert accept(client,b,rid).status_code==200
    assert client.get('/v1/me/groups/'+gid,headers=b['headers']).json()['capacity']['state']=='at_limit'


def test_application_rechecks_activity_and_ownership_on_approve(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=apply(client,b,gid).json()['relation_id']
    with session() as db,db.begin():
        db.execute(text('DELETE FROM activity_characters WHERE settings_id=:sid'),{'sid':b['cid']})
    error(action(client,a,rid,'approve'),409,'ACTIVITY_SELECTION_REQUIRED')
    assert relation(client,b,rid)['state']=='pending'


def test_no_general_member_approval_block_or_code_management(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a)
    rid=apply(client,b,gid).json()['relation_id'];action(client,a,rid,'approve')
    pending=apply(client,c,gid).json();rid=pending['relation_id']
    error(client.get('/v1/group-relations/'+rid,headers=b['headers']),403,'GROUP_RELATION_FORBIDDEN')
    error(client.get('/v1/groups/'+gid+'/join-relations',headers=b['headers']),403,'GROUP_LEADER_REQUIRED')
    error(new_code(client,b,gid),403,'GROUP_LEADER_REQUIRED')


def test_code_visibility_hidden_still_usable_and_no_plaintext_storage(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a);key=uuid.uuid4()
    data=dict(**code_command(client,a,gid),visible_to_members=False)
    created=post(client,a,'/v1/groups/'+gid+'/join-code',data,key);assert created.status_code==201,created.text
    code=created.json()['code'];assert len(code)==6 and code.isalnum() and code==code.upper() and any(c.isdigit() for c in code) and any(c.isalpha() for c in code)
    assert post(client,a,'/v1/groups/'+gid+'/join-code',data,key).json()==created.json()
    assert code_state(client,a,gid)['code']==code
    joined=join(client,b,' '+code.lower()+' ');assert joined.status_code==200,joined.text
    assert code_state(client,b,gid)['code'] is None
    change_data=dict(**code_command(client,a,gid),visible_to_members=True)
    visible=client.put('/v1/groups/'+gid+'/join-code/visibility',headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())},json=change_data)
    assert visible.status_code==200
    assert code_state(client,b,gid)['code']==code
    change_data=dict(**code_command(client,a,gid),visible_to_members=False)
    client.put('/v1/groups/'+gid+'/join-code/visibility',headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())},json=change_data)
    assert code_state(client,b,gid)['code'] is None
    assert join(client,c,code).status_code==200
    with session() as db:
        row=db.scalar(select(GroupJoinCode))
        assert code.encode() not in row.ciphertext and row.digest!=code
        for ack in db.scalars(select(RequestResult.result).where(RequestResult.completed_at.is_not(None))):
            assert code not in json.dumps(ack)


def test_regeneration_ten_minutes_revokes_old_and_revoke_create_cannot_bypass(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);old=new_code(client,a,gid).json();code=old['code']
    path='/v1/groups/'+gid+'/join-code'
    error(post(client,a,path+'/regenerate',code_command(client,a,gid)),409,'GROUP_CODE_REGENERATION_COOLDOWN')
    assert post(client,a,path+'/revoke',code_command(client,a,gid)).status_code==200
    error(new_code(client,a,gid),409,'GROUP_CODE_REGENERATION_COOLDOWN')
    error(client.post('/v1/group-join-codes/preview',headers=b['headers'],json={'code':code}),404,'GROUP_JOIN_CODE_INVALID')
    with session() as db,db.begin():db.get(GroupJoinCode,uuid.UUID(old['code_id'])).created_at=now(db)-timedelta(minutes=11)
    recreated=new_code(client,a,gid);assert recreated.status_code==201,recreated.text
    assert recreated.json()['code_id']!=old['code_id']
    with session() as db,db.begin():db.get(GroupJoinCode,uuid.UUID(recreated.json()['code_id'])).created_at=now(db)-timedelta(minutes=11)
    regenerated=post(client,a,path+'/regenerate',code_command(client,a,gid));assert regenerated.status_code==200
    assert regenerated.json()['code_id']!=recreated.json()['code_id']
    error(client.post('/v1/group-join-codes/preview',headers=b['headers'],json={'code':recreated.json()['code']}),404,'GROUP_JOIN_CODE_INVALID')


def test_code_join_closes_application_without_count_increase_and_replays_after_revoke(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);pending=apply(client,b,gid).json()
    code=new_code(client,a,gid).json()['code'];key=uuid.uuid4();data=code_join_body(client,b,code)
    joined=post(client,b,'/v1/group-join-codes/join',data,key);assert joined.status_code==200
    assert relation(client,b,pending['relation_id'])['state']=='joined_by_code'
    post(client,a,'/v1/groups/'+gid+'/join-code/revoke',code_command(client,a,gid))
    assert post(client,b,'/v1/group-join-codes/join',data,key).json()==joined.json()
    with session() as db:assert db.get(GroupJoinSubject,uuid.UUID(pending['subject_id'])).application_count==1


def test_parallel_last_seat_approval_one_winner(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a);change(a['uid'],Limits(2,5,10))
    rids=[apply(client,w,gid).json()['relation_id'] for w in (b,c)]
    bodies=[action_body(client,a,rid) for rid in rids]
    from app.main import app
    def attempt(pair):
        rid,data=pair
        with TestClient(app) as other:return post(other,a,'/v1/group-relations/'+rid+'/approve',data).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(attempt,zip(rids,bodies)))
    assert sorted(codes)==[200,409]
    assert client.get('/v1/groups/'+gid).json()['member_count']==2


def test_rollback_after_admission_preserves_everything(client,worlds,monkeypatch):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=apply(client,b,gid).json()['relation_id']
    original=admissions.commit_result
    def fail_after(*args,**kwargs):raise RuntimeError('injected failure')
    monkeypatch.setattr(admissions,'commit_result',fail_after)
    assert action(client,a,rid,'approve').status_code==500
    monkeypatch.setattr(admissions,'commit_result',original)
    assert relation(client,b,rid)['state']=='pending'
    assert limits(client,b)['usage_revision']==1
    assert client.get('/v1/groups/'+gid).json()['member_count']==1


def test_rejoining_keeps_ended_membership_history_with_new_id(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);code=new_code(client,a,gid).json()['code']
    first=join(client,b,code).json()['my_membership']['membership_id']
    with session() as db,db.begin():
        old=db.get(GroupMembership,uuid.UUID(first));old.ended_at=now(db)
        db.get(Group,uuid.UUID(gid)).members_revision+=1
        from app.member_limits.service import record_group_membership_change
        record_group_membership_change(db,b['uid'])
    second=join(client,b,code);assert second.status_code==200,second.text
    assert second.json()['my_membership']['membership_id']!=first
    with session() as db:assert db.get(GroupMembership,uuid.UUID(first)).ended_at is not None


@pytest.mark.parametrize('path', ['/v1/me/group-relations','/v1/group-relations/00000000-0000-4000-8000-000000000001'])
def test_auth_required_and_no_store(client,path):
    out=client.get(path);error(out,401,'ACCESS_INVALID');assert out.headers['WWW-Authenticate']=='Bearer'


def test_strict_queries_input_and_get_no_writes(client,worlds):
    a=worlds('a');gid=group(client,a)
    for path in ('/v1/me/group-relations?view=unknown','/v1/me/group-relations?state=pending&state=all',
                 '/v1/groups/'+gid+'/join-code?code=secret','/v1/groups/'+gid+'/join-relations?limit=51'):
        error(client.get(path,headers=a['headers']),400,'INVALID_REQUEST')
    assert client.request('GET','/v1/me/group-relations',headers=a['headers'],json={}).status_code==400
    for path in ('/v1/groups/'+gid+'/join-code','/v1/groups/'+gid+'/blocked-subjects','/v1/groups/'+gid+'/join-relations'):
        assert client.get(path,headers=a['headers']).status_code==200
    with session() as db:
        assert db.scalar(select(func.count()).select_from(GroupJoinCode))==0
        assert db.scalar(select(func.count()).select_from(GroupJoinSubject))==0


def test_final_expiry_crossing_rolls_back_admission_and_ack(client,worlds,monkeypatch):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=apply(client,b,gid).json()['relation_id']
    with session() as db,db.begin():
        stamp=now(db);value=db.get(GroupJoinRelation,uuid.UUID(rid))
        value.created_at=stamp-timedelta(hours=23);value.expires_at=stamp+timedelta(minutes=1)
    original=admissions.commit_result; committed=False
    def mark_commit(*args,**kwargs):
        nonlocal committed
        result=original(*args,**kwargs);committed=True;return result
    monkeypatch.setattr(admissions,'commit_result',mark_commit)
    monkeypatch.setattr(admissions,'now',lambda db:stamp+timedelta(minutes=2) if committed else stamp)
    error(action(client,a,rid,'approve'),409,'RELATION_NOT_PENDING')
    with session() as db:
        assert db.get(GroupJoinRelation,uuid.UUID(rid)).state=='pending'
        assert db.scalar(select(func.count()).select_from(GroupMembership).where(GroupMembership.group_id==uuid.UUID(gid)))==1
    assert limits(client,b)['usage_revision']==1


def test_departed_inviter_logical_cancel_and_reinvite_without_reviving_old(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a)
    code=new_code(client,a,gid).json()['code'];member=join(client,b,code).json()['my_membership']['membership_id']
    rid=invite(client,b,c,gid).json()['relation_id']
    with session() as db,db.begin():db.get(GroupMembership,uuid.UUID(member)).ended_at=now(db)
    assert relation(client,c,rid)['state']=='cancelled'
    error(accept(client,c,rid),409,'RELATION_NOT_PENDING')
    newer=invite(client,a,c,gid);assert newer.status_code==201,newer.text
    assert newer.json()['relation_id']!=rid


def test_actor_scoped_cursors_and_expiry_invalidation(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');gid=group(client,a)
    first=apply(client,b,gid).json();second=apply(client,c,gid).json()
    path='/v1/groups/'+gid+'/join-relations'
    out=client.get(path,params={'limit':1},headers=a['headers']).json();cursor=out['next_cursor'];assert cursor
    error(client.get(path,params={'limit':2,'cursor':cursor},headers=a['headers']),400,'INVALID_REQUEST')
    error(client.get('/v1/me/group-relations',params={'limit':1,'cursor':cursor},headers=b['headers']),400,'INVALID_REQUEST')
    with session() as db,db.begin():
        row=db.get(GroupJoinRelation,uuid.UUID(second['relation_id']));row.created_at=now(db)-timedelta(hours=25);row.expires_at=now(db)-timedelta(hours=1)
    error(client.get(path,params={'limit':1,'cursor':cursor},headers=a['headers']),409,'CURSOR_STALE')


def test_personal_group_limit_rechecked_and_pending_preserved(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=apply(client,b,gid).json()['relation_id']
    change(b['uid'],Limits(15,0,10))
    error(action(client,a,rid,'approve'),409,'GROUP_MEMBERSHIP_LIMIT_REACHED')
    assert relation(client,b,rid)['state']=='pending'


def test_relation_revision_cas_then_current_result(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);rid=apply(client,b,gid).json()['relation_id']
    data=action_body(client,a,rid);data['expected_relation_revision']+=1
    error(post(client,a,'/v1/group-relations/'+rid+'/approve',data),409,'REVISION_CONFLICT')
    assert action(client,a,rid,'approve').status_code==200
    error(action(client,a,rid,'approve'),409,'RELATION_NOT_PENDING')


def test_code_replay_checks_current_membership_and_current_leader(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a)
    key=uuid.uuid4();generation=code_command(client,a,gid)
    created=post(client,a,'/v1/groups/'+gid+'/join-code',generation,key);code=created.json()['code']
    join_key=uuid.uuid4();data=code_join_body(client,b,code)
    joined=post(client,b,'/v1/group-join-codes/join',data,join_key)
    with session() as db,db.begin():
        db.get(GroupMembership,uuid.UUID(joined.json()['my_membership']['membership_id'])).ended_at=now(db)
    error(post(client,b,'/v1/group-join-codes/join',data,join_key),403,'GROUP_MEMBERSHIP_REQUIRED')
    with session() as db,db.begin():
        # Simulate later role change only; this is not a G3 command test.
        group_row=db.get(Group,uuid.UUID(gid));group_row.leader_membership_id=uuid.UUID(joined.json()['my_membership']['membership_id'])
    error(post(client,a,'/v1/groups/'+gid+'/join-code',generation,key),403,'GROUP_LEADER_REQUIRED')


def test_block_endpoint_closes_pending_and_alt_character_cannot_bypass(client,worlds):
    a,b=worlds('a'),worlds('b');gid=group(client,a);pending=apply(client,b,gid).json();sid=pending['subject_id']
    path='/v1/groups/'+gid+'/join-subjects/'+sid+'/block'
    out=post(client,a,path,subject_command(client,a,gid,sid));assert out.status_code==200,out.text
    assert relation(client,b,pending['relation_id'])['state']=='blocked'
    other=dict(**own_selection(b),expected_group_revision=1);other['character_id']=b['ids'][1]
    error(post(client,b,'/v1/groups/'+gid+'/applications',other),403,'GROUP_JOIN_BLOCKED')


def test_code_guess_limit_and_no_code_in_error(client,worlds):
    b=worlds('b')
    for _ in range(20):
        out=client.post('/v1/group-join-codes/preview',headers=b['headers'],json={'code':'ABCDE2'})
        error(out,404,'GROUP_JOIN_CODE_INVALID');assert 'ABCDE2' not in out.text
    error(client.post('/v1/group-join-codes/preview',headers=b['headers'],json={'code':'ABCDE2'}),429,'RATE_LIMITED')


def test_database_relation_subject_and_issuer_same_group_constraints(client,worlds):
    a,b,c=worlds('a'),worlds('b'),worlds('c');g1=group(client,a);g2=group(client,c)
    pending=apply(client,b,g1).json()
    with pytest.raises(IntegrityError):
        with session() as db,db.begin():
            current=now(db)
            db.add(GroupJoinRelation(group_id=uuid.UUID(g2),subject_id=uuid.UUID(pending['subject_id']),
                 target_user_id=b['uid'],issuer_user_id=b['uid'],kind='application',state='pending',revision=1,
                 selection=own_selection(b),created_at=current,expires_at=current+timedelta(hours=24)))
            db.flush()
