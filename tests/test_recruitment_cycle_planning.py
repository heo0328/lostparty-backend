"""W4-A2 scheduling under restricted PostgreSQL with synthetic actors."""
import os,subprocess,uuid
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,inspect,func,text
from sqlalchemy.exc import DBAPIError
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_schedule_service as service,cycle_planning as engine,cycle_proposals as proposals
from app.raid_rooms import cycle_schemas as inputs,cycle_schedule as graph,cycle_times as times,cycle_wire as wire
from app.raid_rooms.cycle_models import RoomCycle,CycleMember
from app.raid_rooms.cycle_planning_models import CycleProposal,CycleVote,CycleScheduleEvent,CycleAlternative
from app.raid_rooms.cycle_consent_models import CycleConsent
from app.raid_rooms.source_models import TimeReservation as Reservation,ScheduleGroup,ScheduleAlternative,ScheduleProposal as Proposal
from tests.test_recruitment_cycle_times import (consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,plan,preflight,request,creation,actor,add_member,cancel_member,save_personal,submit,confirm,fingerprints,
    denied,commands,cycles,next_key,change_body,character)
from tests.test_recruitment_cycle_commands import create_room
from tests.test_raid_room_migrations import table_digests
from app.raid_rooms import readiness


def upgrade_planning(target):
    old=set(inspect(target).get_table_names())-{'alembic_version'};before=table_digests(target,old)
    result=subprocess.run(['alembic','upgrade','0028_cycle_planning'],env={**os.environ,
        'DATABASE_URL':target.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-2200:]
    assert table_digests(target,old)==before
    with session() as db,db.begin():
        readiness.require_ready(db,integrated=True)
        with pytest.raises(GameError):readiness.require_active(db)


@pytest.fixture
def planning(consent):
    target,a,b=consent;upgrade_planning(target)
    return target,a,b


def scoped(w,rid,key):
    view=plan(w,rid,key)
    return dict(expected_cycle_key=view['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=view['scope']['target_revision'],expected_plan_revision=view['data']['revision'],
        expected_members_revision=view['data']['members_revision'],expected_leadership_revision=view['data']['leadership']['leadership_revision'])


def coordinated(w,rid,key,**changes):
    value=dict(client_group_key='coordinated',existing_group_id=None,expected_group_revision=None,
        occurrence_mode='one_of',planning_mode='coordinated',day_scope='any_current_cycle',required=True,
        auto_confirm_additional_members=1,alternatives=[])
    value.update(changes)
    return inputs.EditGroups.model_validate(scoped(w,rid,key)|dict(groups=[value]))


def make_proposal(w,rid,key,*,indexes=None,shift=60):
    view=plan(w,rid,key)['data'];sessions=[s for s in view['sessions'] if s['state']=='confirmed']
    if indexes is not None:sessions=[sessions[i] for i in indexes]
    targets=[]
    for sess in sessions:
        segments=next(v['segments'] for v in view['session_segments'] if v['session_id']==sess['session_id'])
        targets.append(dict(session_id=sess['session_id'],expected_schedule_revision=sess['schedule_revision'],
            starts_at=(datetime.fromisoformat(sess['starts_at'])+timedelta(minutes=shift)).isoformat(),
            item_durations=[dict(item_id=s['item_id'],duration_minutes=None) for s in segments]))
    body=inputs.Propose.model_validate(scoped(w,rid,key)|dict(targets=targets))
    ack=service.propose(actor(w['uid']),rid,uuid.uuid4(),body)[1]
    pid=uuid.UUID(next(r['id'] for r in ack['data']['revisions'] if r['resource']=='proposal'))
    return pid,ack


def response(w,rid,key,pid,answer='accept'):
    view=plan(w,rid,key);p=next(p for p in view['data']['proposals'] if p['proposal_id']==str(pid))
    return inputs.Respond.model_validate(dict(expected_cycle_key=view['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=view['scope']['target_revision'],expected_cycle_member_revision=view['data']['my_membership']['cycle_member_revision'],
        expected_proposal_revision=p['revision'],expected_proposal_plan_revision=p['proposal_plan_revision'],response=answer))


def respond(w,rid,key,pid,answer='accept'):
    return service.respond(actor(w['uid']),pid,uuid.uuid4(),response(w,rid,key,pid,answer))


def test_target_initial_coordination_after_explicit_submissions(planning):
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    service.edit(actor(a['uid']),rid,uuid.uuid4(),coordinated(a,rid,n))
    view=plan(a,rid,n);gid=uuid.UUID(view['data']['schedule_groups'][0]['group_id'])
    before=fingerprints(target)
    assert service.candidates(actor(a['uid']),gid,n)['data']['state']=='no_candidate'
    assert fingerprints(target)==before
    save_personal(a);save_personal(b);submit(a,rid,n)
    assert plan(a,rid,n)['data']['sessions']==[]
    submit(b,rid,n)
    view=plan(a,rid,n)
    assert len(view['data']['sessions'])==1 and view['data']['sessions'][0]['state']=='confirmed'
    assert view['data']['my_participations'][0]['confirmation_state']=='confirmed'
    assert plan(b,rid,n)['data']['my_participations'][0]['confirmation_state']=='confirmed'
    c=room['created_cycles'][0]['target_cycle_key']
    assert plan(a,rid,c)['data']['sessions']==[]
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleConsent))==2
        assert db.scalar(select(func.count()).select_from(CycleScheduleEvent).where(CycleScheduleEvent.kind=='initial_confirmed'))==1


def test_n1_requires_separate_explicit_vote_and_preserves_old_reservations(planning):
    target,a,b=planning;rid,c,n=scheduled(a);confirm(a,rid,n)
    pid,ack=make_proposal(a,rid,n)
    assert ack['data']['outcome']=='recorded'
    assert plan(a,rid,n)['data']['proposals'][0]['my_response']['response']=='pending'
    with session() as db,db.begin():
        original={r.id:(r.starts_at,r.ends_at) for r in db.scalars(select(Reservation).where(Reservation.user_id==a['uid']))}
    ack=respond(a,rid,n,pid)[1]
    assert ack['data']['outcome']=='applied'
    view=plan(a,rid,n)
    assert view['data']['sessions'][0]['schedule_revision']==2
    assert view['data']['proposals'][0]['state']=='applied'
    with session() as db,db.begin():
        for k,value in original.items():
            r=db.get(Reservation,k);assert (r.starts_at,r.ends_at)==value
        assert db.scalar(select(func.count()).select_from(CycleVote))==1


def test_n2_vote_quorum_concurrent_response_and_original_ack(planning):
    target,a,b=planning;rid,c,n=scheduled(a);add_member(b,rid,n)
    pid,_=make_proposal(a,rid,n)
    view=plan(b,rid,n)['data']['proposals'][0]
    assert view['votes'][0]['eligible_count']==view['votes'][0]['required_votes']==2
    assert view['votes'][0]['accepted_count']==1
    body=response(b,rid,n,pid);command=uuid.uuid4()
    def attempt(_):
        try:return service.respond(actor(b['uid']),pid,command,body)
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    original=service.respond(actor(b['uid']),pid,command,body)
    assert all(r==original or r=='REQUEST_IN_PROGRESS' for r in results)
    assert original[1]['data']['outcome']=='applied'
    assert plan(a,rid,n)['data']['proposals'][0]['state']=='applied'
    cancel_member(b,rid,n)
    before=fingerprints(target)
    assert service.respond(actor(b['uid']),pid,command,body)==original
    assert fingerprints(target)==before
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleVote))==2


def test_multi_session_apply_is_atomic_and_one_command_records_each_consent(planning,monkeypatch):
    target,a,b=planning;rid,c,n=scheduled(a,alternatives=2)
    pid,_=make_proposal(a,rid,n)
    before=fingerprints(target);real=engine.consent;calls=[]
    def interrupted(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise GameError('ROOM_REVIEW_REQUIRED',409)
        return real(*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(engine,'consent',interrupted)
        denied('ROOM_REVIEW_REQUIRED',respond,a,rid,n,pid)
    assert len(calls)==2 and fingerprints(target)==before
    ack=respond(a,rid,n,pid)[1]
    assert ack['data']['outcome']=='applied'
    view=plan(a,rid,n)['data']
    assert len(view['sessions'])==2 and all(s['schedule_revision']==2 for s in view['sessions'])
    with session() as db,db.begin():
        values=list(db.scalars(select(CycleConsent)))
        assert len(values)==2 and values[0].command_id==values[1].command_id
        assert values[0].participation_id!=values[1].participation_id


def test_rejoin_discards_old_vote_and_requires_fresh_response(planning):
    target,a,b=planning;rid,c,n=scheduled(a);add_member(b,rid,n)
    pid,_=make_proposal(a,rid,n)
    respond(b,rid,n,pid,'reject')
    cancel_member(b,rid,n) # N falls to one; creator acceptance can now apply.
    assert plan(a,rid,n)['data']['proposals'][0]['state']=='applied'
    add_member(b,rid,n)
    pid,_=make_proposal(a,rid,n)
    respond(b,rid,n,pid,'reject');cancel_member(a,rid,n)
    # The remaining reject does not apply. Rejoining the old creator has a fresh CM revision.
    add_member(a,rid,n)
    view=plan(a,rid,n)['data']['proposals'][-1]
    assert view['state']=='pending' and view['my_response']['response']=='pending'
    assert view['votes'][0]['accepted_count']==0
    respond(a,rid,n,pid)
    assert respond(b,rid,n,pid)[1]['data']['outcome']=='applied'


def test_proposals_are_independent_and_stale_base_becomes_obsolete(planning):
    target,a,b=planning;rid,c,n=scheduled(a)
    first,_=make_proposal(a,rid,n);second,_=make_proposal(a,rid,n,shift=120)
    respond(a,rid,n,first)
    before=plan(a,rid,c)['data']['sessions']
    # An explicit response checks a changed base before changing any times.
    result=respond(a,rid,n,second)[1]
    assert result['data']['outcome']=='recorded'
    values={p['proposal_id']:p['state'] for p in plan(a,rid,n)['data']['proposals']}
    assert values[str(first)]=='applied' and values[str(second)]=='obsolete'
    assert plan(a,rid,c)['data']['sessions']==before


def test_target_authority_and_failed_cas_are_readonly(planning):
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();c=room['created_cycles'][0]['target_cycle_key']
    add_member(b,rid,c)
    body=coordinated(a,rid,n);before=fingerprints(target)
    denied('WEEKLY_PARTICIPANT_REQUIRED',service.edit,actor(b['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(target)==before
    add_member(b,rid,n);body=coordinated(b,rid,n);before=fingerprints(target)
    denied('TARGET_LEADER_REQUIRED',service.edit,actor(b['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(target)==before
    stale=coordinated(a,rid,n).model_dump(mode='json');stale['expected_plan_revision']+=1
    denied('REVISION_CONFLICT',service.edit,actor(a['uid']),rid,uuid.uuid4(),inputs.EditGroups.model_validate(stale))
    assert fingerprints(target)==before


def edit_unscheduled(w,rid,key,*,gid=None,revision=None,manual=False,choices=2):
    view=plan(w,rid,key)['data'];items=[i['item_id'] for i in view['game_items']]
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(plan(w,rid,key)['scope']['room_cycle_id']))
        start=engine.floor(db,row)+timedelta(hours=2)
    local=graph.graph.time.ceil_tick(start).astimezone(commands.raids.KST)
    group=dict(client_group_key='draft',existing_group_id=gid,expected_group_revision=revision,
        occurrence_mode='one_of',planning_mode='manual' if manual else 'unscheduled',day_scope='selected_weekdays',required=True,
        auto_confirm_additional_members=None,alternatives=[dict(client_alternative_key=f'alt-{i}',existing_session_id=None,
            expected_session_revision=None,weekday=local.isoweekday(),starts_local=local.strftime('%H:%M') if manual else None,
            leader_latest_start_local=None,item_ids=items) for i in range(choices)])
    return inputs.EditGroups.model_validate(scoped(w,rid,key)|dict(groups=[group]))


def test_draft_edit_preserves_id_and_old_alternatives_then_manual_selection(planning):
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key()
    service.edit(actor(a['uid']),rid,uuid.uuid4(),edit_unscheduled(a,rid,n))
    group=plan(a,rid,n)['data']['schedule_groups'][0];gid=uuid.UUID(group['group_id'])
    with session() as db,db.begin():old={a.id:engine.snapshot(a) for a in graph.alternatives(db,db.get(ScheduleGroup,gid))}
    service.edit(actor(a['uid']),rid,uuid.uuid4(),edit_unscheduled(a,rid,n,gid=gid,revision=group['revision'],manual=True))
    view=plan(a,rid,n);group=view['data']['schedule_groups'][0]
    assert group['group_id']==str(gid) and group['revision']==2 and view['data']['sessions']==[]
    assert len(group['alternatives'])==2
    with session() as db,db.begin():assert all(engine.snapshot(db.get(ScheduleAlternative,k))==v for k,v in old.items())
    body=inputs.SelectGroup.model_validate(scoped(a,rid,n)|dict(expected_group_revision=group['revision'],
        alternative_id=group['alternatives'][0]['alternative_id']))
    assert service.select_group(actor(a['uid']),gid,uuid.uuid4(),body)[1]['data']['outcome']=='applied'
    assert len(plan(a,rid,n)['data']['sessions'])==1
    before=fingerprints(target)
    denied('SCHEDULE_PROPOSAL_REQUIRED',service.edit,actor(a['uid']),rid,uuid.uuid4(),edit_unscheduled(a,rid,n))
    assert fingerprints(target)==before


def test_candidate_fixed_opening_floor_and_initial_exception(planning,monkeypatch):
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=room['created_cycles'][0]['target_cycle_key'];add_member(b,rid,n)
    service.edit(actor(a['uid']),rid,uuid.uuid4(),coordinated(a,rid,n))
    save_personal(a);save_personal(b);submit(a,rid,n)
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(plan(a,rid,n)['scope']['room_cycle_id']));fixed=engine.floor(db,row)
        # Later threshold fulfilment uses the stored opening floor, without another +30.
        stamp=fixed+timedelta(hours=6);start=graph.graph.time.ceil_tick(stamp+timedelta(minutes=1))
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',lambda db:stamp)
        submit(b,rid,n)
    view=plan(a,rid,n)['data'];sess=view['sessions'][0]
    assert datetime.fromisoformat(sess['starts_at'])>=fixed
    assert datetime.fromisoformat(sess['starts_at'])<stamp+timedelta(minutes=30)
    assert datetime.fromisoformat(sess['starts_at'])<=start
    assert all(p['confirmation_state']=='confirmed' for p in view['my_participations'])
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(plan(a,rid,n)['scope']['room_cycle_id']))
        denied('RECRUITMENT_CLOSED',graph.deadlines,db,row,[],stamp)



def test_append_only_planning_evidence_and_foreign_keys(planning):
    target,a,b=planning;rid,c,n=scheduled(a);pid,_=make_proposal(a,rid,n);respond(a,rid,n,pid)
    for model in (CycleProposal,CycleVote,CycleScheduleEvent):
        with session() as db,db.begin():
            row=db.scalar(select(model));pk=list(model.__table__.primary_key.columns)[0]
            for mutation in ('UPDATE','DELETE'):
                with pytest.raises(DBAPIError),db.begin_nested():
                    if mutation=='UPDATE':db.execute(text(f'UPDATE {model.__tablename__} SET record_updated_at=clock_timestamp() WHERE {pk.name}=:id'),dict(id=getattr(row,pk.name)))
                    else:db.execute(text(f'DELETE FROM {model.__tablename__} WHERE {pk.name}=:id'),dict(id=getattr(row,pk.name)))
    with session() as db,db.begin():
        row=db.scalar(select(CycleVote));values=engine.snapshot(row)|dict(id=uuid.uuid4(),cycle_member_id=uuid.uuid4(),revision=2)
        values.pop('record_created_at');values.pop('record_updated_at')
        with pytest.raises(DBAPIError),db.begin_nested():db.add(CycleVote(**values));db.flush()


@pytest.mark.parametrize('count,required',[(1,1),(2,2),(3,2),(4,2),(5,3),(6,3),(7,4),(8,4)])
def test_session_quorum_policy(count,required):
    assert graph.graph.time.quorum(count)==required


def test_http_groups_candidates_selection_and_strict_inputs(planning):
    from tests.test_recruitment_cycle_times_http import client
    from tests.test_recruitment_cycle_http import validate
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key()
    spec='/v2/raid-rooms/{room_id}/schedule-groups';body=edit_unscheduled(a,rid,n,manual=True).model_dump(mode='json')
    with client(a) as http:
        validate(spec,'put',200,body,input=True)
        headers={'Idempotency-Key':str(uuid.uuid4())}
        result=http.put(f'/v2/raid-rooms/{rid}/schedule-groups',json=body,headers=headers)
        assert result.status_code==200,result.json()
        validate(spec,'put',200,result.json())
        assert http.put(f'/v2/raid-rooms/{rid}/schedule-groups',json=body,headers=headers).json()==result.json()
        group=plan(a,rid,n)['data']['schedule_groups'][0];gid=group['group_id']
        body=inputs.SelectGroup.model_validate(scoped(a,rid,n)|dict(expected_group_revision=group['revision'],
            alternative_id=group['alternatives'][0]['alternative_id'])).model_dump(mode='json')
        spec='/v2/raid-schedule-groups/{group_id}/selections'
        validate(spec,'post',200,body,input=True)
        response=http.post(f'/v2/raid-schedule-groups/{gid}/selections',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json();validate(spec,'post',200,response.json())
        assert response.headers['cache-control']=='no-store'
        for field in ('expected_target_revision','expected_group_revision','expected_plan_revision'):
            invalid=http.post(f'/v2/raid-schedule-groups/{gid}/selections',json=body|{field:True},headers={'Idempotency-Key':str(uuid.uuid4())})
            assert invalid.status_code==400;validate(spec,'post',400,invalid.json())
    # Candidate GET remains a read under the actual target, including empty submissions.
    n=room['created_cycles'][0]['target_cycle_key']
    service.edit(actor(a['uid']),rid,uuid.uuid4(),coordinated(a,rid,n))
    gid=plan(a,rid,n)['data']['schedule_groups'][0]['group_id'];before=fingerprints(target)
    with client(a) as http:
        route=f'/v2/raid-schedule-groups/{gid}/candidates';spec='/v2/raid-schedule-groups/{group_id}/candidates'
        result=http.get(route,params={'target_cycle_key':n});assert result.status_code==200,result.json()
        validate(spec,'get',200,result.json())
        assert http.get(route,params=[('target_cycle_key',n),('target_cycle_key',n)]).status_code==400
        assert http.get(route,params={'target_cycle_key':n,'extra':'bad'}).status_code==400
    assert fingerprints(target)==before


def test_http_proposal_vote_and_plan_fixed_schema(planning):
    from tests.test_recruitment_cycle_times_http import client
    from tests.test_recruitment_cycle_http import validate
    target,a,b=planning;rid,c,n=scheduled(a)
    # Build a second proposal through HTTP without changing the first pending proposal.
    pid,_=make_proposal(a,rid,n)
    with session() as db,db.begin():binding=db.get(CycleProposal,pid);content=binding.content
    view=plan(a,rid,n)['data'];segments=view['session_segments'][0]['segments'];sess=view['sessions'][0]
    body=inputs.Propose.model_validate(scoped(a,rid,n)|dict(targets=[dict(session_id=sess['session_id'],
        expected_schedule_revision=sess['schedule_revision'],starts_at=content[0]['segments'][0]['starts_at'],
        item_durations=[dict(item_id=s['item_id'],duration_minutes=None) for s in segments])])).model_dump(mode='json')
    with client(a) as http:
        spec='/v2/raid-rooms/{room_id}/schedule-proposals';validate(spec,'post',200,body,input=True)
        result=http.post(f'/v2/raid-rooms/{rid}/schedule-proposals',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        pid=uuid.UUID(next(v['id'] for v in result.json()['data']['revisions'] if v['resource']=='proposal'))
        body=response(a,rid,n,pid).model_dump(mode='json');spec='/v2/raid-schedule-proposals/{proposal_id}/responses'
        validate(spec,'post',200,body,input=True)
        result=http.post(f'/v2/raid-schedule-proposals/{pid}/responses',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        result=http.get(f'/v2/me/raid-rooms/{rid}/plan',params={'target_cycle_key':n})
        assert result.status_code==200,result.json();validate('/v2/me/raid-rooms/{room_id}/plan','get',200,result.json())


def test_character_change_invalidates_acceptance_without_restoring_it(planning):
    target,a,b=planning;rid,c,n=scheduled(a);add_member(b,rid,n)
    pid,_=make_proposal(a,rid,n)
    assert plan(a,rid,n)['data']['proposals'][0]['votes'][0]['accepted_count']==1
    ctx=commands.get_context(actor(a['uid']),rid,n,uuid.UUID(a['ids'][1]),'dealer','change_character')
    character.execute(actor(a['uid']),rid,uuid.uuid4(),change_body(ctx,plan(a,rid,n)))
    view=plan(a,rid,n)['data']['proposals'][0]
    assert view['state']=='pending' and view['my_response']['response']=='pending'
    assert view['votes'][0]['accepted_count']==0
    assert respond(b,rid,n,pid)[1]['data']['outcome']=='recorded'
    assert respond(a,rid,n,pid)[1]['data']['outcome']=='applied'
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleVote))==3


def test_all_target_session_quorums_must_pass_before_any_apply(planning):
    from app.raid_rooms.source_models import SessionBinding,SessionParticipation
    target,a,b=planning;rid,c,n=scheduled(a,alternatives=2);add_member(b,rid,n)
    # Synthetic optional second time: B participates only in the first time.
    view=plan(b,rid,n)['data'];sid=uuid.UUID(view['sessions'][1]['session_id'])
    with session() as db,db.begin():
        binding=db.get(SessionBinding,sid);binding.required=False
        part=db.get(SessionParticipation,uuid.UUID(next(p['participation_id'] for p in view['my_participations'] if p['session_id']==str(sid))))
        part.state='ended';part.revision+=1
    pid,_=make_proposal(a,rid,n)
    votes=plan(a,rid,n)['data']['proposals'][0]['votes']
    assert sorted(v['eligible_count'] for v in votes)==[1,2]
    assert all(v['accepted_count']==0 for v in votes) # mixed N1 requires creator's separate response
    assert respond(b,rid,n,pid)[1]['data']['outcome']=='recorded'
    assert all(s['schedule_revision']==1 for s in plan(a,rid,n)['data']['sessions'])
    assert respond(a,rid,n,pid)[1]['data']['outcome']=='applied'
    assert all(s['schedule_revision']==2 for s in plan(a,rid,n)['data']['sessions'])


def test_final_clock_expiry_rolls_back_initial_confirmation_and_submission(planning,monkeypatch):
    from tests.test_recruitment_cycle_times import submission
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);key=room['created_cycles'][0]['target_cycle_key']
    add_member(b,rid,key);service.edit(actor(a['uid']),rid,uuid.uuid4(),coordinated(a,rid,key))
    save_personal(a);save_personal(b);submit(a,rid,key);body=submission(b,rid,key)
    with session() as db,db.begin():
        row=db.get(RoomCycle,uuid.UUID(plan(a,rid,key)['scope']['room_cycle_id']))
        stamp=engine.floor(db,row)+timedelta(hours=2)
    before=fingerprints(target);calls=[]
    def boundary(db):calls.append(1);return stamp if len(calls)==1 else stamp+timedelta(minutes=10)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',boundary)
        denied('SCHEDULE_IN_PAST',times.put_submission,actor(b['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(target)==before


def test_initial_candidates_avoid_other_session_reservations(planning):
    target,a,b=planning;room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    body=coordinated(a,rid,n).model_dump(mode='json');body['groups'].append(body['groups'][0]|dict(client_group_key='second'))
    service.edit(actor(a['uid']),rid,uuid.uuid4(),inputs.EditGroups.model_validate(body))
    save_personal(a);save_personal(b);submit(a,rid,n);submit(b,rid,n)
    values=sorted(plan(a,rid,n)['data']['sessions'],key=lambda s:s['starts_at'])
    assert len(values)==2 and all(s['state']=='confirmed' for s in values)
    assert datetime.fromisoformat(values[0]['ends_at'])<=datetime.fromisoformat(values[1]['starts_at'])
    with session() as db,db.begin():assert db.scalar(select(func.count()).select_from(CycleConsent))==4


def test_selected_weekday_coordination_preserves_item_order_and_latest_bound(planning):
    target,a,b=planning;room=create_room(a,bundle=True);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    item_ids=[i['item_id'] for i in plan(a,rid,n)['data']['game_items']][::-1]
    body=coordinated(a,rid,n,day_scope='selected_weekdays',alternatives=[dict(client_alternative_key='weekday',
        existing_session_id=None,expected_session_revision=None,weekday=4,starts_local=None,
        leader_latest_start_local='23:55',item_ids=item_ids)])
    service.edit(actor(a['uid']),rid,uuid.uuid4(),body)
    save_personal(a);save_personal(b);submit(a,rid,n);submit(b,rid,n)
    value=plan(a,rid,n)['data'];sess=value['sessions'][0]
    assert datetime.fromisoformat(sess['starts_at']).astimezone(commands.raids.KST).isoweekday()==4
    assert [s['item_id'] for s in value['session_segments'][0]['segments']]==item_ids
    assert value['schedule_groups'][0]['alternatives'][0]['session_id']==sess['session_id']


@pytest.mark.parametrize('invalid,code',[
    ('unaligned','INVALID_REQUEST'),('wrong_cycle','CYCLE_CHANGED'),
    ('before_floor','SCHEDULE_BEFORE_FLOOR'),('over_24h','INVALID_REQUEST'),
])
def test_proposed_time_bounds_reject_without_effect(planning,invalid,code):
    target,a,b=planning;rid,c,n=scheduled(a)
    if invalid=='before_floor':n=c
    view=plan(a,rid,n);sess=view['data']['sessions'][0];segments=view['data']['session_segments'][0]['segments']
    start=datetime.fromisoformat(sess['starts_at'])+timedelta(hours=1)
    durations=[dict(item_id=s['item_id'],duration_minutes=None) for s in segments]
    if invalid=='unaligned':start+=timedelta(minutes=1)
    elif invalid=='wrong_cycle':start+=timedelta(days=14)
    elif invalid=='before_floor':
        with session() as db,db.begin():
            row=db.get(RoomCycle,uuid.UUID(view['scope']['room_cycle_id']))
            start=graph.graph.time.ceil_tick(engine.floor(db,row))-timedelta(minutes=5)
    else:durations=[dict(item_id=s['item_id'],duration_minutes=1440) for s in segments]
    body=inputs.Propose.model_validate(scoped(a,rid,n)|dict(targets=[dict(session_id=sess['session_id'],
        expected_schedule_revision=sess['schedule_revision'],starts_at=start.isoformat(),item_durations=durations)]))
    before=fingerprints(target)
    denied(code,service.propose,actor(a['uid']),rid,uuid.uuid4(),body)
    assert fingerprints(target)==before


def test_newcomer_pending_and_nonacceptor_releases_only_old_target_reservations(planning,people):
    target,a,b=planning;rid,c,n=scheduled(a);confirm(a,rid,n);add_member(b,rid,n)
    pid,_=make_proposal(a,rid,n)
    newcomer=people('a2-newcomer');add_member(newcomer,rid,n);confirm(newcomer,rid,n)
    view=plan(newcomer,rid,n)['data']['proposals'][0]
    assert view['my_response']['response_set']=='newcomer' and view['my_response']['response']=='pending'
    assert (view['votes'][0]['eligible_count'],view['votes'][0]['required_votes'],view['votes'][0]['accepted_count'])==(3,2,1)
    with session() as db,db.begin():
        before={r.id:(r.starts_at,r.ends_at) for r in db.scalars(select(Reservation).where(Reservation.user_id==newcomer['uid']))}
        other={r.id:(r.starts_at,r.ends_at,r.released_at) for r in db.scalars(select(Reservation).where(Reservation.user_id==a['uid'],Reservation.session_id.not_in([uuid.UUID(s['session_id']) for s in plan(a,rid,n)['data']['sessions']])))}
    respond(b,rid,n,pid)
    part=plan(newcomer,rid,n)['data']['my_participations'][0]
    assert part['confirmation_state']=='confirmation_pending' and part['reservation_state']=='released'
    with session() as db,db.begin():
        assert before and all(db.get(Reservation,k).released_at is not None and (db.get(Reservation,k).starts_at,db.get(Reservation,k).ends_at)==v for k,v in before.items())
        assert db.scalar(select(func.count()).select_from(Reservation).where(Reservation.user_id==newcomer['uid'],Reservation.released_at.is_(None)))==0
        assert all((db.get(Reservation,k).starts_at,db.get(Reservation,k).ends_at,db.get(Reservation,k).released_at)==v for k,v in other.items())


def test_migration_preserves_existing_nonempty_consent_and_reservation_history(consent):
    target,a,b=consent;rid,c,n=scheduled(a);confirm(a,rid,n)
    with session() as db,db.begin():assert db.scalar(select(func.count()).select_from(CycleConsent))==1
    upgrade_planning(target)
    assert plan(a,rid,n)['data']['my_participations'][0]['confirmation_state']=='confirmed'
    assert respond(a,rid,n,make_proposal(a,rid,n)[0])[1]['data']['outcome']=='applied'
