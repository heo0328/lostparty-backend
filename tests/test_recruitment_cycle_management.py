"""W4-C restricted PostgreSQL: target isolation and explicit global impact."""
import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_management as service,cycle_common as common,cycle_schemas as inputs,cycle_leadership
from app.raid_rooms.cycle_models import ParticipationEvent
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentRoom as Room
from app.raid_rooms.participation_core import room_count
from tests.test_recruitment_cycle_outcomes import (outcomes,planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,plan,actor,add_member,cancel_member,fingerprints,denied,commands,cycles,preflight,request,creation,
    scoped,complete,propose_resume,vote,make_proposal,respond,confirm,CycleMember,RoomCycle,Reservation,Assignment)
from tests.test_recruitment_cycle_times_http import client
from tests.test_recruitment_cycle_http import validate


def transfer_body(a,rid,key,b):
    ctx=cycle_leadership.get_transfer(actor(a['uid']),rid,key);candidate=next(c for c in ctx['data']['candidates'] if str(c['character_id'])==str(b['ids'][0]))
    return inputs.Transfer.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=ctx['scope']['target_revision'],context_token=ctx['data']['context_token'],
        expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
        candidate_cycle_member_id=candidate['cycle_member_id'],expected_candidate_revision=candidate['revision']))


def settings(w,rid,key,**updates):
    view=service.get(actor(w['uid']),rid,key);data=view['data']
    return inputs.TargetSettings.model_validate(dict(expected_cycle_key=view['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=view['scope']['target_revision'],expected_leadership_revision=data['leadership']['leadership_revision'],
        expected_room_revision=data['room_revision'],expected_settings_revision=data['revision'],experience_level=data['experience_level'],
        combat_requirement=data['combat_requirement'],admission_mode=data['admission_mode'])|updates)


def formation(w,rid,key):
    view=plan(w,rid,key);members={}
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(view['scope']['room_cycle_id']))
        for cm in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id)):members[cm.membership_id]=cm
        placements=[dict(item_id=a.item_id,party_no=a.party_no,slot_no=a.slot_no,cycle_member_id=members[a.membership_id].id,
            expected_cycle_member_revision=members[a.membership_id].revision) for a in service.outcomes.assignments(db,row) if a.state=='active']
    return inputs.Formation.model_validate({k:v for k,v in scoped(w,rid,key).items() if k!='expected_room_revision'}|dict(placements=placements))


def removal(w,other,rid,key):
    own=plan(w,rid,key);target=plan(other,rid,key)['data']['my_membership']
    return inputs.Removal.model_validate(scoped(w,rid,key)|dict(expected_room_revision=service.get(actor(w['uid']),rid,key)['data']['room_revision'],
        expected_cycle_member_revision=own['data']['my_membership']['cycle_member_revision'],target_cycle_member_id=target['cycle_member_id'],
        expected_removed_cycle_member_revision=target['cycle_member_revision']))


def global_body(ctx,**updates):
    c=ctx['data'];values=dict(expected_cycle_key=c['expected_cycle_key'],expected_room_revision=c['room_revision'],context_token=c['context_token'])
    if c['command']=='edit_common_settings':
        values.update(c['current_settings']);values['expected_group_revision']=values.pop('group_revision');dto=inputs.CommonSettings
    else:values['expected_persistent_membership_revision']=c['persistent_membership_revision'];dto=inputs.GlobalMembership
    return dto.model_validate(values|updates)


def global_run(w,rid,kind,command=None,**updates):
    body=global_body(common.get(actor(w['uid']),rid,kind),**updates)
    return common.execute(actor(w['uid']),rid,command or uuid.uuid4(),body,kind)


def test_settings_target_only_noop_and_original_ack(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);before=plan(a,rid,c);body=settings(a,rid,n,experience_level='experienced')
    command=uuid.uuid4();result=service.command(actor(a['uid']),rid,command,body,'settings')
    assert service.get(actor(a['uid']),rid,n)['data']['experience_level']=='experienced'
    assert plan(a,rid,c)['data']['revision']==before['data']['revision']
    with session() as db,db.begin():assert db.get(Room,rid).revision==body.expected_room_revision
    noop=settings(a,rid,n);stable=fingerprints(engine)
    assert service.command(actor(a['uid']),rid,uuid.uuid4(),noop,'settings')[1]['data']['outcome']=='noop'
    assert fingerprints(engine)==stable
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',lambda db:commands.raids.cycle(now(db)).ends_at+timedelta(days=1))
        assert service.command(actor(a['uid']),rid,command,body,'settings')==result


def test_settings_uses_actual_leader_and_strict_cas(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n)
    from app.raid_rooms import cycle_leadership as leaders
    leaders.transfer(actor(a['uid']),rid,uuid.uuid4(),transfer_body(a,rid,n,b))
    denied('TARGET_LEADER_REQUIRED',service.command,actor(a['uid']),rid,uuid.uuid4(),settings(a,rid,n),'settings')
    denied('WEEKLY_PARTICIPANT_REQUIRED',service.command,actor(b['uid']),rid,uuid.uuid4(),settings(b,rid,c),'settings')


def test_formation_swaps_active_seats_preserves_completed_and_n(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);complete(a,rid,c,index=0)
    history=plan(a,rid,c)['data']['formation_history'];next_before=plan(a,rid,n)['data']['revision']
    body=formation(a,rid,c);placements=[p.model_copy(update={'slot_no':4 if p.slot_no==1 else p.slot_no}) for p in body.placements]
    body=body.model_copy(update={'placements':placements});service.command(actor(a['uid']),rid,uuid.uuid4(),body,'formation')
    assert plan(a,rid,c)['data']['formation_history']==history
    assert plan(a,rid,n)['data']['revision']==next_before
    assert any(s['slot_no']==4 and s['assignment_id'] for s in plan(a,rid,c)['data']['formation_slots'])


def test_formation_duplicate_seat_and_cross_target_have_no_effect(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n);body=formation(a,rid,n)
    invalid=body.model_copy(update={'placements':[p.model_copy(update={'slot_no':1}) for p in body.placements]})
    before=fingerprints(engine);denied('ROOM_COMPOSITION_CONFLICT',service.command,actor(a['uid']),rid,uuid.uuid4(),invalid,'formation')
    assert fingerprints(engine)==before
    invalid=inputs.Formation.model_validate(body.model_dump(mode='json')|{'target_cycle_key':c,'expected_target_revision':plan(a,rid,c)['scope']['target_revision']})
    denied('REVISION_CONFLICT',service.command,actor(a['uid']),rid,uuid.uuid4(),invalid,'formation')


def test_removal_only_target_keeps_persistent_n_and_completed_source(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n);confirm(b,rid,c);confirm(b,rid,n)
    complete(b,rid,c,index=0);before_n=plan(b,rid,n)['data'];history=plan(b,rid,c)['data']['formation_history']
    body=removal(a,b,rid,c);key=uuid.uuid4();result=service.command(actor(a['uid']),rid,key,body,'remove')
    assert service.command(actor(a['uid']),rid,key,body,'remove')==result
    assert plan(b,rid,n)['data']['revision']==before_n['revision']
    assert plan(a,rid,c)['data']['formation_history']==history
    with session() as db,db.begin():
        assert db.get(Member,uuid.UUID(before_n['my_membership']['membership_id'])).ended_at is None
        assert db.scalar(select(func.count()).select_from(ParticipationEvent).where(ParticipationEvent.action=='removed'))==1


def test_removal_reevaluates_proposal_without_reviving_old_votes(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n);pid,_=make_proposal(a,rid,n)
    service.command(actor(a['uid']),rid,uuid.uuid4(),removal(a,b,rid,n),'remove')
    proposal=next(p for p in plan(a,rid,n)['data']['proposals'] if p['proposal_id']==str(pid))
    assert proposal['state']=='applied'


def test_common_settings_exact_global_ack_noop_and_readonly_context(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);before=fingerprints(engine);ctx=common.get(actor(a['uid']),rid,'edit_common_settings')
    assert fingerprints(engine)==before and len(ctx['data']['impact_cycles'])==2
    old=[plan(a,rid,k)['data']['revision'] for k in (c,n)]
    result=global_run(a,rid,'edit_common_settings',title='renamed')[1]
    assert result['data']['affected_cycle_keys']==[c,n] and 'target_cycle_key' not in result['scope']
    assert [plan(a,rid,k)['data']['revision'] for k in (c,n)]==old
    before=fingerprints(engine);result=global_run(a,rid,'edit_common_settings')[1]
    assert result['data']['outcome']=='noop' and result['data']['affected_cycle_keys']==[] and fingerprints(engine)==before


def test_g1_completed_c_retains_authority_but_n_leader_does_not(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n)
    cycle_leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),transfer_body(a,rid,n,b))
    complete(a,rid,c,'complete_item',0);complete(a,rid,c,'complete_item',1)
    assert common.get(actor(a['uid']),rid,'edit_common_settings')['data']['permission']['allowed']
    assert not common.get(actor(b['uid']),rid,'edit_common_settings')['data']['permission']['allowed']
    global_run(a,rid,'edit_common_settings',title='completed leader')


def test_g1_review_c_never_falls_back_to_n(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==commands.raids.cycle(now(db)).starts_at.astimezone(commands.raids.KST).date()));row.state='review_required'
    ctx=common.get(actor(a['uid']),rid,'edit_common_settings');assert ctx['data']['authorization_cycle_key']==c
    assert ctx['data']['permission']['reason']=='ROOM_REVIEW_REQUIRED'
    denied('ROOM_REVIEW_REQUIRED',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(ctx,title='no'),'edit_common_settings')


def test_n_only_common_ack_does_not_manufacture_c(outcomes):
    engine,a,b=outcomes
    with session() as db,db.begin():n=(cycles.target(now(db),commands.raids.cycle(now(db)).cycle_key).current+timedelta(days=7)).isoformat()
    made=creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,key=n,continuation=True),continuation=dict(enabled=True,next_selection=None)))[1]['data'];rid=uuid.UUID(made['room_id'])
    ctx=common.get(actor(a['uid']),rid,'edit_common_settings');assert ctx['data']['authorization_cycle_key']==n
    assert global_run(a,rid,'edit_common_settings',title='only N')[1]['data']['affected_cycle_keys']==[n]
    with session() as db,db.begin():assert db.scalar(select(func.count()).select_from(RoomCycle).where(RoomCycle.room_id==rid))==1


def test_global_leave_all_actual_targets_releases_one_room_unit(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n);confirm(b,rid,c);confirm(b,rid,n)
    with session() as db,db.begin():before_count=room_count(db,b['uid'])
    ctx=common.get(actor(b['uid']),rid,'leave');assert len(ctx['data']['impact_cycles'])==2
    result=common.execute(actor(b['uid']),rid,uuid.uuid4(),global_body(ctx),'leave')[1]
    assert result['data']['affected_cycle_keys']==[c,n]
    with session() as db,db.begin():
        assert room_count(db,b['uid'])==before_count-1
        assert not list(db.scalars(select(Reservation).where(Reservation.room_id==rid,Reservation.user_id==b['uid'],Reservation.released_at.is_(None))))
        assert len(list(db.scalars(select(Assignment).where(Assignment.room_id==rid,Assignment.user_id==a['uid'],Assignment.state=='active'))))==4


def test_persistent_only_leave_after_cancel_has_zero_target_effect(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n);cancel_member(b,rid,n)
    ctx=common.get(actor(b['uid']),rid,'leave');assert ctx['data']['impact_cycles']==[]
    assert common.execute(actor(b['uid']),rid,uuid.uuid4(),global_body(ctx),'leave')[1]['data']['affected_cycle_keys']==[]


def test_global_leader_leave_and_other_target_participant_end_blocked(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    assert common.get(actor(a['uid']),rid,'leave')['data']['permission']['reason']=='LEADERSHIP_RESOLUTION_REQUIRED'
    assert common.get(actor(a['uid']),rid,'end')['data']['permission']['reason']=='ROOM_LAST_MEMBER_REQUIRED'


def test_global_end_safe_last_member_preserves_completion_and_original_ack(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c,index=0)
    with session() as db,db.begin():done=db.scalar(select(Assignment).where(Assignment.room_id==rid,Assignment.state=='completed'));saved=(done.id,done.party_no,done.slot_no,done.build)
    ctx=common.get(actor(a['uid']),rid,'end');body=global_body(ctx);key=uuid.uuid4()
    result=common.execute(actor(a['uid']),rid,key,body,'end')
    with session() as db,db.begin():
        assert db.get(Room,rid).ended_at is not None
        done=db.get(Assignment,saved[0]);assert (done.id,done.party_no,done.slot_no,done.build)==saved
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',lambda db:now(db)+timedelta(days=7))
        assert common.execute(actor(a['uid']),rid,key,body,'end')==result


def test_common_context_stale_and_expired_protect_all_effects(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);ctx=common.get(actor(a['uid']),rid,'edit_common_settings');body=global_body(ctx,title='old')
    service.command(actor(a['uid']),rid,uuid.uuid4(),settings(a,rid,n,experience_level='experienced'),'settings')
    before=fingerprints(engine);denied('TARGET_CONTEXT_STALE',common.execute,actor(a['uid']),rid,uuid.uuid4(),body,'edit_common_settings');assert fingerprints(engine)==before
    ctx=common.get(actor(a['uid']),rid,'edit_common_settings');body=global_body(ctx)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',lambda db:now(db)+timedelta(minutes=3))
        denied('COMMAND_CONTEXT_EXPIRED',common.execute,actor(a['uid']),rid,uuid.uuid4(),body,'edit_common_settings')


def test_global_leave_second_target_failure_rolls_back_both(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    ctx=common.get(actor(b['uid']),rid,'leave');before=fingerprints(engine);real=service.remove_member;calls=[]
    def failed(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise GameError('ROOM_REVIEW_REQUIRED')
        return real(*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(service,'remove_member',failed)
        denied('ROOM_REVIEW_REQUIRED',common.execute,actor(b['uid']),rid,uuid.uuid4(),global_body(ctx),'leave')
    assert len(calls)==2 and fingerprints(engine)==before


def test_http_settings_common_commands_contract_and_strict_scope(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a)
    with client(a) as http:
        response=http.get(f'/v2/me/raid-rooms/{rid}/settings',params={'target_cycle_key':n});assert response.status_code==200,response.json()
        validate('/v2/me/raid-rooms/{room_id}/settings','get',200,response.json())
        body=settings(a,rid,n,experience_level='experienced').model_dump(mode='json')
        validate('/v2/raid-rooms/{room_id}/settings','put',200,body,input=True)
        response=http.put(f'/v2/raid-rooms/{rid}/settings',json=body,headers={'Idempotency-Key':str(uuid.uuid4())});assert response.status_code==200,response.json()
        validate('/v2/raid-rooms/{room_id}/settings','put',200,response.json())
        path=f'/v2/me/raid-rooms/{rid}/common-context';query={'command':'edit_common_settings'}
        assert http.get(path,params=query|{'target_cycle_key':c}).status_code==400
        response=http.get(path,params=query);assert response.status_code==200,response.json();assert response.headers['cache-control']=='no-store'
        validate('/v2/me/raid-rooms/{room_id}/common-context','get',200,response.json());body=global_body(response.json(),title='HTTP').model_dump(mode='json')
        validate('/v2/raid-rooms/{room_id}/common-settings','put',200,body,input=True)
        response=http.put(f'/v2/raid-rooms/{rid}/common-settings',json=body,headers={'Idempotency-Key':str(uuid.uuid4())});assert response.status_code==200,response.json()
        validate('/v2/raid-rooms/{room_id}/common-settings','put',200,response.json())
        assert http.put(f'/v2/raid-rooms/{rid}/common-settings',json=body|{'expected_room_revision':True},headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==400


def test_http_formation_removal_and_global_leave_contract(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    with client(a) as http:
        body=formation(a,rid,n).model_dump(mode='json')
        spec='/v2/raid-rooms/{room_id}/formation';validate(spec,'put',200,body,input=True)
        response=http.put(f'/v2/raid-rooms/{rid}/formation',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json();validate(spec,'put',200,response.json())
        body=removal(a,b,rid,n).model_dump(mode='json');spec='/v2/raid-rooms/{room_id}/removals';validate(spec,'post',200,body,input=True)
        response=http.post(f'/v2/raid-rooms/{rid}/removals',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json();validate(spec,'post',200,response.json())
    with client(b) as http:
        ctx=http.get(f'/v2/me/raid-rooms/{rid}/common-context',params={'command':'leave'}).json()
        body=global_body(ctx).model_dump(mode='json');spec='/v2/raid-rooms/{room_id}/leave';validate(spec,'post',200,body,input=True)
        headers={'Idempotency-Key':str(uuid.uuid4())}
        response=http.post(f'/v2/raid-rooms/{rid}/leave',json=body,headers=headers)
        assert response.status_code==200,response.json();validate(spec,'post',200,response.json())
        assert http.post(f'/v2/raid-rooms/{rid}/leave',json=body,headers=headers).json()==response.json()


def test_http_global_end_contract_and_scope(outcomes):
    _,a,b=outcomes;rid,c,n=scheduled(a)
    with client(a) as http:
        ctx=http.get(f'/v2/me/raid-rooms/{rid}/common-context',params={'command':'end'}).json()
        body=global_body(ctx).model_dump(mode='json');spec='/v2/raid-rooms/{room_id}/end';validate(spec,'post',200,body,input=True)
        response=http.post(f'/v2/raid-rooms/{rid}/end',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json();validate(spec,'post',200,response.json())
        assert 'target_revision' not in response.json()['scope']


def test_common_group_link_is_immutable_and_group_cas_is_required(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);ctx=common.get(actor(a['uid']),rid,'edit_common_settings')
    before=fingerprints(engine)
    denied('GROUP_LINK_IMMUTABLE',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(ctx,group_id=uuid.uuid4()),'edit_common_settings')
    denied('INVALID_REQUEST',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(ctx,expected_group_revision=2),'edit_common_settings')
    denied('GROUP_MEMBERSHIP_REQUIRED',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(ctx,scope='group'),'edit_common_settings')
    assert fingerprints(engine)==before


def test_common_final_expiry_and_week_boundary_roll_back(outcomes,monkeypatch):
    engine,a,b=outcomes;rid,c,n=scheduled(a);ctx=common.get(actor(a['uid']),rid,'edit_common_settings');body=global_body(ctx,title='expired final')
    before=fingerprints(engine);real=cycles.now;calls=[]
    def expired(db):
        calls.append(1);return real(db) if len(calls)==1 else real(db)+timedelta(minutes=3)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',expired)
        denied('COMMAND_CONTEXT_EXPIRED',common.execute,actor(a['uid']),rid,uuid.uuid4(),body,'edit_common_settings')
    assert fingerprints(engine)==before
    calls=[]
    def rolled(db):
        calls.append(1);return real(db) if len(calls)==1 else real(db)+timedelta(days=7)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',rolled)
        denied('CYCLE_CHANGED',common.execute,actor(a['uid']),rid,uuid.uuid4(),body,'edit_common_settings')
    assert fingerprints(engine)==before


def test_concurrent_global_leave_has_one_effect(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    ctx=common.get(actor(b['uid']),rid,'leave');body=global_body(ctx);key=uuid.uuid4()
    def attempt(_):
        try:return common.execute(actor(b['uid']),rid,key,body,'leave')
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    original=common.execute(actor(b['uid']),rid,key,body,'leave')
    assert all(r==original or r=='REQUEST_IN_PROGRESS' for r in results)
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(ParticipationEvent).where(ParticipationEvent.command_id==key))==2


def test_removal_after_resume_keeps_new_and_old_completion_sources(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);complete(b,rid,c,index=0)
    complete(a,rid,c,'close_weekly');pid=propose_resume(a,rid,c);vote(b,rid,c,pid)
    history=plan(a,rid,c)['data']['formation_history']
    service.command(actor(a['uid']),rid,uuid.uuid4(),removal(a,b,rid,c),'remove')
    assert plan(a,rid,c)['data']['formation_history']==history


def test_target_removal_rejects_foreign_cycle_member(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    body=removal(a,b,rid,c).model_copy(update={'target_cycle_member_id':uuid.UUID(plan(b,rid,n)['data']['my_membership']['cycle_member_id'])})
    before=fingerprints(engine);denied('TARGET_SCOPE_MISMATCH',service.command,actor(a['uid']),rid,uuid.uuid4(),body,'remove')
    assert fingerprints(engine)==before


def test_other_member_leave_keeps_completed_c_leadership(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    complete(a,rid,c,index=0);complete(a,rid,c,index=1)
    leader=plan(a,rid,c)['data']['leadership']
    global_run(b,rid,'leave')
    assert plan(a,rid,c)['data']['target_state']=='completed'
    assert plan(a,rid,c)['data']['leadership']==leader
    assert common.get(actor(a['uid']),rid,'edit_common_settings')['data']['permission']['allowed']


def test_linked_group_common_settings_requires_current_group_revision(outcomes):
    engine,a,b=outcomes
    from tests.test_group_foundation import create as group_create
    gid=uuid.UUID(group_create(a)[1]['group']['group_id'])
    ctx=preflight(a,continuation=True,gid=gid)
    room=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx,group_id=gid))[1]['data'];rid=uuid.UUID(room['room_id'])
    ctx=common.get(actor(a['uid']),rid,'edit_common_settings');rev=ctx['data']['current_settings']['group_revision']
    denied('REVISION_CONFLICT',common.execute,actor(a['uid']),rid,uuid.uuid4(),global_body(ctx,title='stale group',expected_group_revision=rev+1),'edit_common_settings')
    result=global_run(a,rid,'edit_common_settings',title='linked')[1]
    assert result['data']['affected_cycle_keys']


def test_http_common_unauthorized_actor_and_binding(outcomes):
    engine,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,n)
    ctx=common.get(actor(b['uid']),rid,'edit_common_settings');assert not ctx['data']['permission']['allowed']
    body=global_body(ctx,title='unauthorized').model_dump(mode='json');before=fingerprints(engine)
    with client(b) as http:
        response=http.put(f'/v2/raid-rooms/{rid}/common-settings',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==403,response.json();validate('/v2/raid-rooms/{room_id}/common-settings','put',403,response.json())
    assert fingerprints(engine)==before
    ctx=common.get(actor(a['uid']),rid,'edit_common_settings')
    denied('TARGET_SCOPE_MISMATCH',common.execute,actor(b['uid']),rid,uuid.uuid4(),global_body(ctx,title='wrong actor'),'edit_common_settings')
