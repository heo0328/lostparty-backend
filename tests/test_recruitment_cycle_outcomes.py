"""W4-B actual PostgreSQL target outcomes; no development data/server mutation."""
import os,subprocess,uuid
from datetime import timedelta,datetime
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func,inspect,text
from sqlalchemy.exc import DBAPIError
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import cycle_outcomes as service,cycle_resume as resume,cycle_schedule_service as schedules,cycle_schemas as inputs
from app.raid_rooms import cycle_schedule as graph,cycle_lifecycle as life,cycle_wire as wire,readiness
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleRound,CycleGeneration,CycleSubmission
from app.raid_rooms.cycle_outcome_models import CycleOutcome,CycleResume
from app.raid_rooms.cycle_planning_models import CycleVote,CycleProposal
from app.raid_rooms.cycle_consent_models import CycleConsent
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round
from app.raid_rooms.source_models import TimeReservation as Reservation,ScheduleProposal as Proposal
from app.raid_weekly.models import WeeklyState
from tests.test_recruitment_cycle_planning import (planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    upgrade_planning,scheduled,plan,preflight,request,creation,actor,add_member,cancel_member,save_personal,submit,confirm,fingerprints,
    denied,commands,cycles,next_key,change_body,character,create_room,scoped,coordinated,make_proposal,response,respond)
from tests.test_raid_room_migrations import table_digests


@pytest.fixture
def outcomes(planning):
    target,a,b=planning
    before=table_digests(target,set(inspect(target).get_table_names())-{'alembic_version'})
    done=subprocess.run(['alembic','upgrade','0029_cycle_outcomes'],env={**os.environ,'DATABASE_URL':target.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert done.returncode==0,done.stderr.decode()[-1500:]
    assert table_digests(target,set(before))==before
    with session() as db,db.begin():
        readiness.require_ready(db,integrated=True)
        denied('SERVICE_UNAVAILABLE',readiness.require_active,db)
        denied('SERVICE_UNAVAILABLE',readiness.require_legacy_worker,db)
    return target,a,b


def context(w,rid,key,kind='personal_completion',index=0):
    rd=None if kind=='close_weekly' else uuid.UUID(plan(w,rid,key)['data']['game_items'][index]['round_id'])
    return service.get(actor(w['uid']),rid,key,kind,rd)


def stable(value):return {k:v for k,v in value.items() if k!='server_time'}


def outcome_body(ctx):
    return inputs.Outcome.model_validate(dict(expected_cycle_key=ctx['scope']['current_cycle_key'],target_cycle_key=ctx['scope']['target_cycle_key'],
        expected_target_revision=ctx['scope']['target_revision'],context_token=ctx['data']['context_token']))


def complete(w,rid,key,kind='personal_completion',index=0,command=None):
    ctx=context(w,rid,key,kind,index);rd=ctx['data']['target_round_id']
    return service.execute(actor(w['uid']),rid if kind=='close_weekly' else None,uuid.UUID(rd) if rd else None,
        command or uuid.uuid4(),outcome_body(ctx),kind)


def resume_body(w,rid,key,groups=[]):
    view=plan(w,rid,key)
    with session() as db,db.begin():room=commands.base.room(db,w['uid'],rid);rev=room.revision
    return inputs.Resume.model_validate(scoped(w,rid,key)|dict(expected_room_revision=rev,
        expected_cycle_member_revision=view['data']['my_membership']['cycle_member_revision'],schedule_groups=groups))


def propose_resume(w,rid,key,groups=[]):
    ack=resume.create(actor(w['uid']),rid,uuid.uuid4(),resume_body(w,rid,key,groups))[1]
    return uuid.UUID(next(v['id'] for v in ack['data']['revisions'] if v['resource']=='proposal'))


def resume_response(w,rid,key,pid,answer='accept'):
    view=plan(w,rid,key);p=next(p for p in view['data']['proposals'] if p['proposal_id']==str(pid))
    return inputs.Respond.model_validate(dict(expected_cycle_key=view['scope']['current_cycle_key'],target_cycle_key=key,
        expected_target_revision=view['scope']['target_revision'],expected_cycle_member_revision=view['data']['my_membership']['cycle_member_revision'],
        expected_proposal_revision=p['revision'],expected_proposal_plan_revision=p['proposal_plan_revision'],response=answer))


def vote(w,rid,key,pid,answer='accept'):
    return schedules.respond(actor(w['uid']),pid,uuid.uuid4(),resume_response(w,rid,key,pid,answer))


def test_personal_partial_completion_preserves_other_item_times_and_n(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);confirm(b,rid,c)
    n_before=plan(a,rid,n);c_before=plan(a,rid,c)['data'];ctx=context(a,rid,c)
    before=fingerprints(target);context(a,rid,c);assert fingerprints(target)==before
    rd=uuid.UUID(ctx['data']['target_round_id'])
    with session() as db,db.begin():
        old={r.id:(r.starts_at,r.ends_at,r.round_id) for r in db.scalars(select(Reservation).where(Reservation.user_id==a['uid']))}
    complete(a,rid,c)
    after=plan(a,rid,c)['data']
    assert after['sessions']==c_before['sessions']
    assert after['session_segments']==c_before['session_segments']
    assert stable(plan(a,rid,n)['data'])==stable(n_before['data'])
    assert sum(a['state']=='completed' for a in after['my_assignments'])==1
    assert sum(a['state']=='active' for a in after['my_assignments'])==1
    assert len(after['formation_history'])==1
    with session() as db,db.begin():
        assert all((db.get(Reservation,k).starts_at,db.get(Reservation,k).ends_at)==v[:2] for k,v in old.items())
        assert all((db.get(Reservation,k).released_at is not None)==(v[2]==rd) for k,v in old.items())
        assert db.get(Round,rd).state=='active'
        assert db.scalar(select(func.count()).select_from(CycleOutcome))==1


def test_last_personal_completion_keeps_persistent_and_n_source_authority(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c);complete(a,rid,c,index=1)
    value=plan(a,rid,c)['data'];assert value['target_state']=='completed'
    with session() as db,db.begin():
        room=commands.base.room(db,a['uid'],rid);cm=life.actual_member(db,db.get(RoomCycle,uuid.UUID(plan(a,rid,c)['scope']['room_cycle_id'])),a['uid'])
        assert cm.state=='completed' and db.get(life.Member,cm.membership_id).ended_at is None and room.ended_at is None
        assert life.source(db,a['uid'],room,now(db))[1].id==cm.id
    assert plan(a,rid,n)['data']['target_state']=='open'


def test_party_completion_requires_actual_t_leader_and_preserves_manual_source(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c)
    denied('TARGET_LEADER_REQUIRED',complete,b,rid,c,'complete_item')
    complete(b,rid,c)
    complete(a,rid,c,'complete_item')
    with session() as db,db.begin():
        rd=db.get(Round,uuid.UUID(plan(a,rid,c)['data']['game_items'][0]['round_id']))
        assert rd.state=='completed'
        values=list(db.scalars(select(Assignment).where(Assignment.round_id==rd.id)))
        assert all(v.state=='completed' for v in values)
        manual=next(v for v in values if v.user_id==b['uid']);item=db.get(graph.graph.Item,manual.item_id)
        state=db.get(WeeklyState,(b['uid'],manual.character_id,item.raid_id,rd.cycle_key))
        assert state.manual_completed_at is not None # personal result not erased by later leader completion


def test_weekly_close_by_member_preserves_completed_and_other_cycle(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);complete(a,rid,c)
    n_before=plan(a,rid,n)['data'];complete(b,rid,c,'close_weekly')
    value=plan(a,rid,c)['data'];assert value['target_state']=='stopped_incomplete'
    assert sorted(a['state'] for a in value['my_assignments'])==['completed','stopped_incomplete']
    assert stable(plan(a,rid,n)['data'])==stable(n_before)
    with session() as db,db.begin():
        assert all(r.released_at is not None for r in db.scalars(select(Reservation).where(Reservation.round_id.in_([uuid.UUID(i['round_id']) for i in value['game_items']]))))
        assert db.scalar(select(func.count()).select_from(CycleOutcome))==2


def test_n1_resume_needs_separate_vote_and_creates_fresh_rounds_assignments(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c,'close_weekly')
    before=plan(a,rid,c)['data'];pid=propose_resume(a,rid,c)
    value=plan(a,rid,c)['data']['proposals'][-1]
    assert value['kind']=='weekly_resume' and value['my_response']=='pending' and value['accepted_count']==0
    assert vote(a,rid,c,pid)[1]['data']['outcome']=='applied'
    after=plan(a,rid,c)['data'];assert after['target_state']=='open'
    assert after['proposals'][-1]['my_response']=='accept' and after['proposals'][-1]['accepted_count']==1
    assert {i['round_id'] for i in before['game_items']}.isdisjoint({i['round_id'] for i in after['game_items']})
    assert {i['assignment_id'] for i in before['my_assignments']}.isdisjoint({i['assignment_id'] for i in after['my_assignments']})
    assert after['sessions']==[]
    with session() as db,db.begin():
        assert all(db.get(Round,uuid.UUID(i['round_id'])).state=='stopped_incomplete' for i in before['game_items'])
        assert all(db.get(Assignment,uuid.UUID(i['assignment_id'])).state=='stopped_incomplete' for i in before['my_assignments'])
        assert db.scalar(select(func.count()).select_from(CycleResume))==1


def test_resume_only_unfinished_round_after_party_completion(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c,'complete_item');complete(a,rid,c,'close_weekly')
    before=plan(a,rid,c)['data'];completed=next(i for i in before['game_items'] if i['round_state']=='completed')
    pid=propose_resume(a,rid,c);vote(a,rid,c,pid)
    after=plan(a,rid,c)['data'];assert completed in after['game_items']
    assert sorted(v['state'] for v in after['my_assignments'])==['active','completed']
    with session() as db,db.begin():assert db.get(Round,uuid.UUID(completed['round_id'])).state=='completed'


def test_n2_resume_quorum_and_atomic_failure(outcomes,monkeypatch):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);complete(b,rid,c,'close_weekly')
    pid=propose_resume(a,rid,c);assert plan(b,rid,c)['data']['proposals'][-1]['accepted_count']==1
    before=fingerprints(target);real=graph.admission.admit_bundle;calls=[]
    def broken(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise GameError('SYNTHETIC_RESUME_FAILURE')
        return real(*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(graph.admission,'admit_bundle',broken)
        denied('SYNTHETIC_RESUME_FAILURE',vote,b,rid,c,pid)
    assert len(calls)==2 and fingerprints(target)==before
    assert vote(b,rid,c,pid)[1]['data']['outcome']=='applied'
    assert all(v['state']=='active' for v in plan(b,rid,c)['data']['my_assignments'])


def test_completion_expired_context_and_stale_snapshot_rollback(outcomes,monkeypatch):
    target,a,b=outcomes;rid,c,n=scheduled(a);ctx=context(a,rid,c);body=outcome_body(ctx);rd=uuid.UUID(ctx['data']['target_round_id'])
    before=fingerprints(target);real=cycles.now;calls=[]
    def expired(db):calls.append(1);return real(db) if len(calls)==1 else datetime.fromisoformat(ctx['data']['expires_at'])
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',expired)
        denied('COMMAND_CONTEXT_EXPIRED',service.execute,actor(a['uid']),None,rd,uuid.uuid4(),body,'personal_completion')
    assert fingerprints(target)==before
    add_member(b,rid,c);before=fingerprints(target)
    denied('TARGET_CONTEXT_STALE',service.execute,actor(a['uid']),None,rd,uuid.uuid4(),body,'personal_completion')
    assert fingerprints(target)==before


def test_completion_original_ack_after_week_and_authority_change(outcomes,monkeypatch):
    target,a,b=outcomes;rid,c,n=scheduled(a);ctx=context(a,rid,c);body=outcome_body(ctx);rd=uuid.UUID(ctx['data']['target_round_id']);command=uuid.uuid4()
    ack=service.execute(actor(a['uid']),None,rd,command,body,'personal_completion')
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=14));before=fingerprints(target)
    assert service.execute(actor(a['uid']),None,rd,command,body,'personal_completion')==ack
    assert fingerprints(target)==before


@pytest.mark.parametrize('kind',['personal_completion','complete_item','close_weekly'])
def test_future_completion_forbidden_and_get_is_readonly(outcomes,kind):
    target,a,b=outcomes;rid,c,n=scheduled(a);before=fingerprints(target);ctx=context(a,rid,n,kind)
    assert ctx['data']['permission']['reason']=='TARGET_CYCLE_NOT_CURRENT'
    rd=ctx['data']['target_round_id']
    denied('TARGET_CYCLE_NOT_CURRENT',service.execute,actor(a['uid']),rid if rd is None else None,uuid.UUID(rd) if rd else None,uuid.uuid4(),outcome_body(ctx),kind)
    assert fingerprints(target)==before


def test_partial_personal_completion_survives_multi_member_resume(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);complete(a,rid,c)
    old_completed=next(a for a in plan(a,rid,c)['data']['my_assignments'] if a['state']=='completed')
    complete(b,rid,c,'close_weekly');pid=propose_resume(a,rid,c)
    assert vote(b,rid,c,pid)[1]['data']['outcome']=='applied'
    view=plan(a,rid,c)['data']
    assert sorted(a['state'] for a in view['my_assignments'])==['active','completed']
    assert old_completed in view['my_assignments']
    assert any(h['assignment_id']==old_completed['assignment_id'] for h in view['formation_history'])


def manual_body(w,raid_id,key,*,completed=True,revision=None):
    from app.raids import service as raids
    from app.raid_weekly import service as weekly
    cid=uuid.UUID(w['ids'][1])
    with session() as db,db.begin():
        account,character=weekly.scope(db,w['uid'],cid);row=db.get(WeeklyState,(w['uid'],cid,raid_id,weekly.parse_cycle(key)))
        return inputs.Manual.model_validate(dict(completed=completed,difficulty_id=None,expected_cycle_key=raids.cycle(now(db)).cycle_key,
            target_cycle_key=key,expected_catalog_version=raids.catalog().catalog_version,expected_revision=revision or (row.revision if row else 1),
            expected_ownership_revision=account.ownership_revision,expected_lifecycle_revision=character.lifecycle_revision))


def test_manual_mark_correction_keeps_party_source_and_original_ack(outcomes,monkeypatch):
    target,a,b=outcomes;rid,c,n=scheduled(a);cid=uuid.UUID(a['ids'][1]);raid_id='horizon_cathedral';command=uuid.uuid4()
    body=manual_body(a,raid_id,c)
    ack=service.manual(actor(a['uid']),cid,raid_id,command,body)
    assert ack[1]['data']['state']=='completed'
    with session() as db,db.begin():
        state=db.get(WeeklyState,(a['uid'],cid,raid_id,graph.admission.core.weekly.parse_cycle(c)))
        state.party_completed_at=now(db);state.completed_party_id=rid;state.party_difficulty_id='stage1';state.revision+=1
    result=service.manual(actor(a['uid']),cid,raid_id,uuid.uuid4(),manual_body(a,raid_id,c,completed=False))[1]
    assert result['data']['state']=='completed' and [s['source'] for s in result['data']['completion_sources']]==['party']
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=14))
    assert service.manual(actor(a['uid']),cid,raid_id,command,body)==ack


@pytest.mark.parametrize('completed',[True,False])
def test_manual_and_completion_before_wednesday_ten_forbidden(outcomes,monkeypatch,completed):
    from datetime import datetime,time,timezone
    target,a,b=outcomes;rid,c,n=scheduled(a)
    body=manual_body(a,'horizon_cathedral',c,completed=completed)
    stamp=datetime.combine(graph.admission.core.weekly.parse_cycle(c),time(9,59),commands.raids.KST).astimezone(timezone.utc)
    before=fingerprints(target)
    monkeypatch.setattr(cycles,'now',lambda db:stamp)
    denied('PLAY_NOT_STARTED',service.manual,actor(a['uid']),uuid.UUID(a['ids'][1]),'horizon_cathedral',uuid.uuid4(),body)
    assert fingerprints(target)==before


def test_partial_completion_remaining_schedule_proposal_and_confirmation(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);confirm(b,rid,c)
    complete(a,rid,c)
    pid,_=make_proposal(a,rid,c)
    assert respond(b,rid,c,pid)[1]['data']['outcome']=='applied'
    assert confirm(a,rid,c)[1]['data']['outcome']=='noop'
    with session() as db,db.begin():
        active=list(db.scalars(select(Reservation).where(Reservation.user_id==a['uid'],Reservation.released_at.is_(None))))
        assert len(active)==1
        assert db.get(Assignment,active[0].assignment_id).state=='active'


def test_outcome_resume_sql_immutability_and_exact_owner(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);complete(a,rid,c,'close_weekly');pid=propose_resume(a,rid,c)
    for model,field in ((CycleOutcome,'id'),(CycleResume,'proposal_id')):
        with session() as db,db.begin():
            row=db.scalar(select(model));value=getattr(row,field)
            for sql in (f'UPDATE {model.__tablename__} SET record_updated_at=clock_timestamp() WHERE {field}=:id',
                        f'DELETE FROM {model.__tablename__} WHERE {field}=:id'):
                with pytest.raises(DBAPIError),db.begin_nested():db.execute(text(sql),dict(id=value))
    with session() as db,db.begin():
        old=db.get(CycleResume,pid)
        with pytest.raises(DBAPIError),db.begin_nested():
            db.add(CycleResume(proposal_id=uuid.uuid4(),room_id=old.room_id,cycle_id=old.cycle_id,generation=old.generation,content={}))
            db.flush()


def test_http_fixed_context_completion_closure_resume_and_response(outcomes):
    from tests.test_recruitment_cycle_times_http import client
    from tests.test_recruitment_cycle_http import validate
    target,a,b=outcomes;rid,c,n=scheduled(a)
    with client(a) as http:
        ctx=http.get(f'/v2/raid-rooms/{rid}/command-context',params=dict(command='personal_completion',target_cycle_key=c,round_id=plan(a,rid,c)['data']['game_items'][0]['round_id']))
        assert ctx.status_code==200,ctx.json();validate('/v2/raid-rooms/{room_id}/command-context','get',200,ctx.json())
        assert ctx.headers['cache-control']=='no-store'
        body=outcome_body(ctx.json()).model_dump(mode='json');rd=ctx.json()['data']['target_round_id']
        spec='/v2/raid-rounds/{round_id}/personal-completion';validate(spec,'post',200,body,input=True)
        result=http.post(f'/v2/raid-rounds/{rd}/personal-completion',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        ctx=context(a,rid,c,'close_weekly');body=outcome_body(ctx).model_dump(mode='json');spec='/v2/raid-rooms/{room_id}/weekly-incomplete-closures'
        result=http.post(f'/v2/raid-rooms/{rid}/weekly-incomplete-closures',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        body=resume_body(a,rid,c).model_dump(mode='json');spec='/v2/raid-rooms/{room_id}/weekly-resume-proposals';validate(spec,'post',200,body,input=True)
        result=http.post(f'/v2/raid-rooms/{rid}/weekly-resume-proposals',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        pid=uuid.UUID(next(v['id'] for v in result.json()['data']['revisions'] if v['resource']=='proposal'))
        body=resume_response(a,rid,c,pid).model_dump(mode='json');spec='/v2/raid-schedule-proposals/{proposal_id}/responses'
        result=http.post(f'/v2/raid-schedule-proposals/{pid}/responses',json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        result=http.get(f'/v2/me/raid-rooms/{rid}/plan',params={'target_cycle_key':c})
        assert result.status_code==200,result.json();validate('/v2/me/raid-rooms/{room_id}/plan','get',200,result.json())


def test_http_party_completion_manual_and_strict_scope(outcomes):
    from tests.test_recruitment_cycle_times_http import client
    from tests.test_recruitment_cycle_http import validate
    target,a,b=outcomes;rid,c,n=scheduled(a);ctx=context(a,rid,c,'complete_item');rd=ctx['data']['target_round_id'];body=outcome_body(ctx).model_dump(mode='json')
    with client(a) as http:
        route=f'/v2/raid-rounds/{rd}/completion';spec='/v2/raid-rounds/{round_id}/completion'
        wrong=http.post(route,json=body|dict(expected_target_revision=True),headers={'Idempotency-Key':str(uuid.uuid4())})
        assert wrong.status_code==400;validate(spec,'post',400,wrong.json())
        result=http.post(route,json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'post',200,result.json())
        assert http.get(f'/v2/raid-rooms/{rid}/command-context',params=[('command','close_weekly'),('target_cycle_key',c),('target_cycle_key',c)]).status_code==400
        spec='/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion'
        body=manual_body(a,'horizon_cathedral',c).model_dump(mode='json');validate(spec,'put',200,body,input=True)
        route=f"/v2/me/characters/{a['ids'][1]}/raid-weekly-states/horizon_cathedral/manual-completion"
        result=http.put(route,json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code==200,result.json();validate(spec,'put',200,result.json())
    before=fingerprints(target)
    denied('WEEKLY_PARTICIPANT_REQUIRED',service.get,actor(b['uid']),rid,c,'close_weekly')
    assert fingerprints(target)==before


def test_manual_resume_allocates_only_new_consents_for_acceptors(outcomes,people):
    target,a,b=outcomes;rid,c,n=scheduled(a);add_member(b,rid,c);third=people('w4b-resume-third');add_member(third,rid,c);confirm(third,rid,c)
    complete(b,rid,c,'close_weekly')
    view=plan(a,rid,c)['data'];items=[i['item_id'] for i in view['game_items']]
    with session() as db,db.begin():start=graph.graph.time.ceil_tick(now(db)+timedelta(hours=2)).astimezone(commands.raids.KST)
    groups=[dict(client_group_key='new-manual',existing_group_id=None,expected_group_revision=None,occurrence_mode='each',
        planning_mode='manual',day_scope='selected_weekdays',required=True,auto_confirm_additional_members=None,
        alternatives=[dict(client_alternative_key='one',existing_session_id=None,expected_session_revision=None,
            weekday=start.isoweekday(),starts_local=start.strftime('%H:%M'),leader_latest_start_local=None,item_ids=items)])]
    pid=propose_resume(a,rid,c,groups);vote(third,rid,c,pid,'reject');vote(b,rid,c,pid)
    value=plan(third,rid,c)['data'];assert value['target_state']=='open'
    assert value['my_participations'][0]['confirmation_state']=='confirmation_pending'
    assert plan(a,rid,c)['data']['my_participations'][0]['confirmation_state']=='confirmed'
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(Reservation).where(Reservation.user_id==third['uid'],Reservation.released_at.is_(None)))==0
        new=[v for v in db.scalars(select(CycleConsent)) if v.evidence['authorization']['kind']=='weekly_resume']
        assert {v.user_id for v in new}=={a['uid'],b['uid']}


def test_duplicate_concurrent_completion_has_one_effect_and_original_receipt(outcomes):
    target,a,b=outcomes;rid,c,n=scheduled(a);ctx=context(a,rid,c);body=outcome_body(ctx);rd=uuid.UUID(ctx['data']['target_round_id']);key=uuid.uuid4()
    def attempt(_):
        try:return service.execute(actor(a['uid']),None,rd,key,body,'personal_completion')
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    original=service.execute(actor(a['uid']),None,rd,key,body,'personal_completion')
    assert all(v==original or v=='REQUEST_IN_PROGRESS' for v in results)
    with session() as db,db.begin():assert db.scalar(select(func.count()).select_from(CycleOutcome))==1


def test_manual_final_week_boundary_rolls_back_and_noop_is_readonly(outcomes,monkeypatch):
    target,a,b=outcomes;rid,c,n=scheduled(a);cid=uuid.UUID(a['ids'][1]);body=manual_body(a,'horizon_cathedral',c)
    before=fingerprints(target);real=cycles.now;calls=[]
    def boundary(db):calls.append(1);return real(db) if len(calls)==1 else real(db)+timedelta(days=7)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',boundary)
        denied('CYCLE_CHANGED',service.manual,actor(a['uid']),cid,'horizon_cathedral',uuid.uuid4(),body)
    assert fingerprints(target)==before
    service.manual(actor(a['uid']),cid,'horizon_cathedral',uuid.uuid4(),manual_body(a,'horizon_cathedral',c,completed=False))
    assert fingerprints(target)==before


def test_partial_resume_intent_can_copy_full_bundle_into_reopened_n(outcomes):
    from app.raid_rooms import cycle_opening as opening
    from tests.test_recruitment_cycle_lifecycle import opening_body
    target,a,b=outcomes;rid,c,n=scheduled(a);cancel_member(a,rid,n)
    complete(a,rid,c,'complete_item');complete(a,rid,c,'close_weekly')
    remaining=[i['item_id'] for i in plan(a,rid,c)['data']['game_items'] if i['round_state']=='stopped_incomplete']
    with session() as db,db.begin():start=graph.graph.time.ceil_tick(now(db)+timedelta(hours=2)).astimezone(commands.raids.KST)
    groups=[dict(client_group_key='remaining',existing_group_id=None,expected_group_revision=None,occurrence_mode='each',planning_mode='manual',
        day_scope='selected_weekdays',required=True,auto_confirm_additional_members=None,alternatives=[dict(client_alternative_key='one',
        existing_session_id=None,expected_session_revision=None,weekday=start.isoweekday(),starts_local=start.strftime('%H:%M'),
        leader_latest_start_local=None,item_ids=remaining)])]
    pid=propose_resume(a,rid,c,groups);vote(a,rid,c,pid)
    ctx=opening.get(actor(a['uid']),rid,n,'reopen')
    assert ctx['data']['permission']['allowed']
    opening.execute(actor(a['uid']),rid,uuid.uuid4(),opening_body(ctx,'reopen'))
    value=plan(a,rid,n)['data'];assert len(value['my_assignments'])==2
    assert all(p['reservation_state']=='none' for p in value['my_participations'])
    assert len(value['session_segments'][0]['segments'])==2


@pytest.mark.parametrize('kind',['complete_item','close_weekly'])
def test_closed_completed_and_stopped_leaders_can_transfer_without_n_effect(outcomes,kind):
    from app.raid_rooms import cycle_leadership as leadership
    from tests.test_recruitment_cycle_lifecycle import scoped as context_scoped
    target,a,b=outcomes;rid,c,n=scheduled(a,bundle=False);add_member(b,rid,c)
    complete(a,rid,c,kind);before=stable(plan(a,rid,n)['data']);view=plan(a,rid,c)['data']
    ctx=leadership.get_transfer(actor(a['uid']),rid,c);candidate=ctx['data']['candidates'][0]
    body=wire.TransferCommand.model_validate(context_scoped(ctx)|dict(expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
        candidate_cycle_member_id=candidate['cycle_member_id'],expected_candidate_revision=candidate['revision']))
    leadership.transfer(actor(a['uid']),rid,uuid.uuid4(),body)
    after=plan(a,rid,c)['data'];assert after['leadership']['leader_cycle_member_id']==candidate['cycle_member_id']
    assert after['my_assignments']==view['my_assignments']
    assert stable(plan(a,rid,n)['data'])==before
