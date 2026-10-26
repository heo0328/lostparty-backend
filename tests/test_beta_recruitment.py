"""Agreed beta operations against disposable PostgreSQL; no development data."""
import json
import os
from pathlib import Path
import subprocess
import uuid
from datetime import date,datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func,inspect
from app.core.database import session,now
from app.game_accounts.support import GameError
from app.raid_rooms import beta_profile,beta_text,beta_schemas,beta_schedule,cycle_creation,cycle_commands,cycle_member_reads
from app.raid_rooms.beta_models import BetaSchedule,ApplicationMessagePresets,BetaAvailabilityCopy,BetaApplicationMemo
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleSubmission
from app.raid_rooms.source_models import TimeReservation,PersonalAvailability
from app.raid_rooms.integrated_models import RecruitmentRoom
from app.raid_rooms import application_presets
from app.raids import service as raids
from tests.test_application_composition import current,candidate,ready,sources,imported,people,worlds
from tests.test_recruitment_cycle_creation import preflight,request
from tests.test_recruitment_cycle_commands import context,admission_request
from tests.test_recruitment_cycle_http import client
from tests.test_group_foundation import actor
from tests.test_raid_room_migrations import table_digests

PROFILE={'contract_profile':beta_profile.PROFILE}


@pytest.fixture
def beta(current):
    engine,a,b=current
    tables=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0032_beta_recruitment'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-2000:]
    assert table_digests(engine,tables)==before
    from app.raid_rooms.readiness import require_two_cycle_active
    with session() as db:require_two_cycle_active(db)
    return engine,a,b


def create_beta(w,*,enabled=False,combined=False,mode='direct_join'):
    with session() as db:
        stamp=now(db)
        base=beta_schedule.time_policy.ceil_tick(stamp+timedelta(hours=2)).astimezone(timezone.utc)
        key=raids.cycle(base).cycle_key
    params=dict(base_starts_at=base.isoformat(),early_coordination_enabled='true' if enabled else 'false')
    if enabled:params['early_additional_members']='1'
    if combined:
        params.update(next_base_starts_at=(base+timedelta(days=7,hours=1)).isoformat(),next_early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=preflight(w,key=key,continuation=combined)
        body=request(ctx,admission_mode=mode).model_dump(mode='json')
        body.pop('schedule_groups');body['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        data=beta_schemas.BetaCreateRequest.model_validate(body)
        command=uuid.uuid4();status,ack=cycle_creation.create(actor(w['uid']),command,data)
        assert status==201
        assert cycle_creation.create(actor(w['uid']),command,data)==(status,ack)
    return uuid.UUID(ack['data']['room_id']),key,base,body,command


def beta_join(w,rid,key):
    with beta_profile.using():
        ctx=context(w,rid,key)
        data=admission_request(ctx)
        return cycle_commands.admit(actor(w['uid']),rid,uuid.uuid4(),data)


def test_shared_character_vectors():
    from pydantic import TypeAdapter, ValidationError
    from jsonschema import Draft202012Validator
    stored=TypeAdapter(beta_schemas.MemoStored)
    schema=json.loads(Path('docs/features/recruitment/weekly-cycles/proposals/beta-recruitment-v1.schema.json').read_text())['$defs']['MemoStored']
    for value in ['가\n','가\r','가\t','가\x7f',' 가','가 ']:
        with pytest.raises((GameError,ValidationError)):
            stored.validate_python(value)
        assert list(Draft202012Validator(schema).iter_errors(value))
    vectors=json.loads(Path('docs/features/recruitment/weekly-cycles/proposals/beta-recruitment-v1.examples.json').read_text())['character_vectors']
    for case in vectors:
        if case['valid']:
            assert beta_text.normalize(case['input'],preset=case['preset'])==case['normalized']
            if case['normalized'] is not None:
                assert stored.validate_python(case['normalized'])==case['normalized']
                Draft202012Validator(schema).validate(case['normalized'])
        else:
            with pytest.raises(GameError):beta_text.normalize(case['input'],preset=case['preset'])


def test_creation_promise_copy_identity_and_original_ack(beta):
    engine,a,b=beta
    rid,key,base,body,command=create_beta(a)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        saved=db.get(BetaSchedule,row.id);cm=db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id))
        assert saved.confirmation_kind is None and not saved.early_enabled
        assert db.get(BetaAvailabilityCopy,cm.id).state=='unset'
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.room_id==rid,TimeReservation.released_at.is_(None)))==1
    with beta_profile.using():
        result=cycle_member_reads.detail(actor(a['uid']),rid,key)
        assert result['data']['beta_schedule']['coordination_state']=='base_committed'
        assert result['data']['recruitment_identity']['number']>=1
        assert len(result['data']['recruitment_identity']['password'])==5
        other=cycle_member_reads.detail(actor(b['uid']),rid,key)
        assert other['data']['recruitment_identity'] is None
    beta_join(b,rid,key)
    with beta_profile.using():
        result=cycle_member_reads.plan(actor(b['uid']),rid,key)
        assert result['data']['recruitment_identity'] is not None
    with client(b) as http:
        assert http.get(f'/v2/raid-rooms/{rid}',params={**PROFILE,'target_cycle_key':key}).status_code==200
    with session() as db:
        assert db.scalar(select(func.count()).select_from(BetaAvailabilityCopy))==2


def test_early_confirmation_excludes_own_promise(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a,enabled=True)
    beta_join(b,rid,key)
    with beta_profile.using():
        value=cycle_member_reads.detail(actor(a['uid']),rid,key)['data']['beta_schedule']
        assert value['coordination_state']=='early_confirmed'
        assert datetime.fromisoformat(value['confirmed_starts_at'].replace('Z','+00:00'))<base


def test_base_fallback_and_delayed_review_read_has_no_effect(beta):
    engine,a,b=beta;rid,key,base,_,_=create_beta(a)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));room=db.get(RecruitmentRoom,rid)
        beta_schedule.reconcile(db,room,row,base-timedelta(minutes=20))
        assert db.get(BetaSchedule,row.id).confirmation_kind=='base_confirmed'
        beta_schedule.reconcile(db,room,row,base+timedelta(hours=1))
        assert not db.get(BetaSchedule,row.id).needs_review
    rid2,key2,base2,_,_=create_beta(b)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid2))
        before=beta_schedule.get(db,row).revision
        assert beta_schedule.view(db,row,base2+timedelta(minutes=20))['coordination_state']=='deadline_pending'
        assert beta_schedule.get(db,row).revision==before
        beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid2),row,base2+timedelta(minutes=20))
        assert beta_schedule.get(db,row).needs_review
        assert beta_schedule.view(db,row,base2+timedelta(minutes=21))['confirmed_starts_at'] is None


def test_presets_cas_raw_replay_account_isolation_and_no_get_write(beta):
    engine,a,b=beta
    before=table_digests(engine,set(inspect(engine).get_table_names()))
    assert application_presets.get(actor(a['uid']))==dict(version=1,items=[],saved_at=None)
    assert table_digests(engine,set(before))==before
    raw=dict(expected_version=1,items=[dict(id=str(uuid.uuid4()),text='  가  ')])
    data=application_presets.PresetPut.model_validate(raw);key=uuid.uuid4()
    result=application_presets.put(actor(a['uid']),key,data)
    assert result[1]['version']==2 and result[1]['items'][0]['text']=='가'
    assert application_presets.put(actor(a['uid']),key,data)==result
    changed={**raw,'items':[dict(raw['items'][0],text='가')]}
    with pytest.raises(GameError,match='IDEMPOTENCY_CONFLICT'):
        application_presets.put(actor(a['uid']),key,application_presets.PresetPut.model_validate(changed))
    with pytest.raises(GameError,match='REVISION_CONFLICT'):
        application_presets.put(actor(a['uid']),uuid.uuid4(),data)
    assert application_presets.get(actor(b['uid']))['items']==[]
    assert data.items[0].text=='  가  '


def test_real_http_profile_creation_presets_and_closed_queries(beta):
    engine,a,b=beta
    rid,key,base,body,command=create_beta(a)
    with client(a) as http:
        http.app.include_router(application_presets.router)
        replay=http.post('/v2/raid-rooms',params=PROFILE,json=body,headers={'Idempotency-Key':str(command)})
        assert replay.status_code==201,replay.json()
        assert 'recruitment_identity' not in replay.json()['data']
        detail=http.get(f'/v2/raid-rooms/{rid}/detail',params={**PROFILE,'target_cycle_key':key})
        assert detail.status_code==200,detail.json()
        assert detail.json()['data']['beta_schedule']['coordination_state']=='base_committed'
        assert http.get(f'/v2/raid-rooms/{rid}/detail',params={'contract_profile':'unknown','target_cycle_key':key}).status_code==400
        assert http.get('/v2/me/application-message-presets',params=PROFILE).status_code==400
        path='/v2/me/application-message-presets'
        saved=http.put(path,json=dict(expected_version=1,items=[dict(id=str(uuid.uuid4()),text='같이 가요!')]),headers={'Idempotency-Key':str(uuid.uuid4())})
        assert saved.status_code==200,saved.json()
        assert saved.json()['items'][0]['text']=='같이 가요!'
        invalid=http.put(path,json=dict(expected_version=2,items=[dict(id=str(uuid.uuid4()),text='😀')]),headers={'Idempotency-Key':str(uuid.uuid4())})
        assert invalid.status_code==400 and invalid.json()['error']['code']=='INVALID_REQUEST'
        assert invalid.json()['error']['details'] is None
        assert invalid.headers['Cache-Control']=='no-store'


def test_application_memo_snapshot_pending_no_copy_approval_atomic(beta):
    from tests.test_recruitment_cycle_commands import decision
    from app.raid_rooms.cycle_application_models import CycleApplication
    _,a,b=beta;rid,key,base,_,_=create_beta(a,mode='leader_only')
    with beta_profile.using():
        ctx=context(b,rid,key,'apply')
        raw=admission_request(ctx).model_dump(mode='json')|{'application_memo':'  가 함께:[]!  '}
        body=beta_schemas.BetaApplyRequest.model_validate(raw);command=uuid.uuid4()
        status,ack=cycle_commands.admit(actor(b['uid']),rid,command,body,applying=True)
        assert status==201
        aid=uuid.UUID(ack['data']['application_id'])
        assert cycle_commands.admit(actor(b['uid']),rid,command,body,applying=True)==(status,ack)
        own=cycle_commands.application(actor(b['uid']),aid)
        assert own['data']['application_memo']=='가 함께:[]!'
        leader=cycle_commands.application(actor(a['uid']),aid)
        assert leader['data']['application']['application_memo']=='가 함께:[]!'
        with session() as db:
            assert db.scalar(select(func.count()).select_from(BetaAvailabilityCopy))==1
            assert db.get(BetaApplicationMemo,aid).memo=='가 함께:[]!'
        cycle_commands.process(actor(a['uid']),aid,uuid.uuid4(),decision(ack['data'],context(a,rid,key,'apply')))
        with session() as db:
            assert db.get(CycleApplication,aid).state=='accepted'
            assert db.scalar(select(func.count()).select_from(BetaAvailabilityCopy))==2
            assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.released_at.is_(None)))==2


def test_two_actual_targets_unique_identity_and_opposite_privacy(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a,combined=True)
    with session() as db:
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid).order_by(RoomCycle.cycle_key)))
        identities=[db.get(BetaSchedule,r.id).number for r in rows]
        assert len(identities)==2 and identities[0]<identities[1]
        next_key=rows[1].cycle_key.isoformat()
    beta_join(b,rid,next_key)
    with beta_profile.using():
        assert cycle_member_reads.detail(actor(b['uid']),rid,key)['data']['recruitment_identity'] is None
        assert cycle_member_reads.detail(actor(b['uid']),rid,next_key)['data']['recruitment_identity']['number']==identities[1]


def test_profileless_new_join_blocked_and_personal_revision_bound(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    legacy=admission_request(context(b,rid,key))
    with pytest.raises(GameError,match='CLIENT_UPGRADE_REQUIRED'):
        cycle_commands.admit(actor(b['uid']),rid,uuid.uuid4(),legacy)
    with beta_profile.using():
        body=admission_request(context(b,rid,key))
        with session() as db,db.begin():
            db.add(PersonalAvailability(user_id=b['uid'],revision=1,timezone='Asia/Seoul',intervals=[],normalized_intervals=[],saved_at=now(db)))
        with pytest.raises(GameError,match='SELECTION_CONTEXT_CHANGED'):
            cycle_commands.admit(actor(b['uid']),rid,uuid.uuid4(),body)
        assert beta_join(b,rid,key)[0]==200


def test_toggle_and_search_filter_before_pagination(beta):
    from app.raid_rooms import cycle_schedule_service
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    with beta_profile.using():
        plan=cycle_member_reads.plan(actor(a['uid']),rid,key)
        p=plan['data']
        body=beta_schemas.BetaScheduleEditRequest.model_validate(dict(expected_cycle_key=plan['scope']['current_cycle_key'],target_cycle_key=key,
            expected_target_revision=plan['scope']['target_revision'],expected_plan_revision=p['revision'],
            expected_members_revision=p['members_revision'],expected_leadership_revision=p['leadership']['leadership_revision'],
            early_coordination_enabled=True,early_additional_members=1,accept_immediate_confirmation=True))
        cycle_schedule_service.edit(actor(a['uid']),rid,uuid.uuid4(),body)
        assert cycle_member_reads.detail(actor(a['uid']),rid,key)['data']['beta_schedule']['coordination_state']=='coordinating'
    with client(b) as http:
        path='/v2/raid-rooms'
        windows=json.dumps([dict(starts_at=base.isoformat(),ends_at=(base+timedelta(minutes=5)).isoformat())])
        response=http.get(path,params={**PROFILE,'target_cycle_key':key,'departure_windows':windows,'schedule_states':'["coordinating"]','limit':1})
        assert response.status_code==200,response.json()
        assert [v['room_id'] for v in response.json()['data']['items']]==[str(rid)]
        windows=json.dumps([dict(starts_at=(base-timedelta(minutes=5)).isoformat(),ends_at=base.isoformat())])
        response=http.get(path,params={**PROFILE,'target_cycle_key':key,'departure_windows':windows})
        assert response.status_code==200,response.json()
        assert response.json()['data']['items']==[]


def test_join_copy_failure_rolls_back_all_business_effects(beta,monkeypatch):
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    original=beta_schedule.copy_personal
    def fail_after_copy(db,row,cm,stamp):
        original(db,row,cm,stamp)
        raise GameError('SERVICE_UNAVAILABLE',503)
    monkeypatch.setattr(beta_schedule,'copy_personal',fail_after_copy)
    with pytest.raises(GameError,match='SERVICE_UNAVAILABLE'):beta_join(b,rid,key)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(CycleMember).where(CycleMember.user_id==b['uid']))==0
        assert db.scalar(select(func.count()).select_from(BetaAvailabilityCopy))==1
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.released_at.is_(None)))==1


def test_independent_due_commits_when_stale_join_rejected(beta,monkeypatch):
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    with beta_profile.using():body=admission_request(context(b,rid,key))
    original=beta_schedule.reconcile
    def overdue(db,room,row,stamp):original(db,room,row,base-timedelta(minutes=20))
    monkeypatch.setattr(beta_schedule,'reconcile',overdue)
    with beta_profile.using():
        with pytest.raises(GameError,match='TARGET_CONTEXT_STALE'):
            cycle_commands.admit(actor(b['uid']),rid,uuid.uuid4(),body)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        assert db.get(BetaSchedule,row.id).confirmation_kind=='base_confirmed'
        assert db.scalar(select(func.count()).select_from(CycleMember).where(CycleMember.user_id==b['uid']))==0


def test_unconfirmed_and_needs_review_use_existing_proposal_quorum(beta):
    from app.raid_rooms import cycle_schedule_service,cycle_schemas
    from tests.test_recruitment_cycle_planning import response
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid),row,base+timedelta(minutes=20))
    with beta_profile.using():
        view=cycle_member_reads.plan(actor(a['uid']),rid,key);p=view['data'];sess=p['sessions'][0]
        segments=p['session_segments'][0]['segments']
        body=cycle_schemas.Propose.model_validate(dict(expected_cycle_key=view['scope']['current_cycle_key'],target_cycle_key=key,
            expected_target_revision=view['scope']['target_revision'],expected_plan_revision=p['revision'],
            expected_members_revision=p['members_revision'],expected_leadership_revision=p['leadership']['leadership_revision'],
            targets=[dict(session_id=sess['session_id'],expected_schedule_revision=sess['schedule_revision'],
                starts_at=(base+timedelta(hours=1)).isoformat(),item_durations=[dict(item_id=s['item_id'],duration_minutes=None) for s in segments])]))
        ack=cycle_schedule_service.propose(actor(a['uid']),rid,uuid.uuid4(),body)[1]
        pid=uuid.UUID(next(v['id'] for v in ack['data']['revisions'] if v['resource']=='proposal'))
        assert cycle_member_reads.plan(actor(a['uid']),rid,key)['data']['beta_schedule']['coordination_state']=='needs_review'
        cycle_schedule_service.respond(actor(a['uid']),pid,uuid.uuid4(),response(a,rid,key,pid))
        final=cycle_member_reads.plan(actor(a['uid']),rid,key)['data']['beta_schedule']
        assert final['coordination_state']=='proposal_confirmed'
        assert datetime.fromisoformat(final['confirmed_starts_at'].replace('Z','+00:00'))==base+timedelta(hours=1)


def validate_beta_wire(path,method,status,value):
    from jsonschema import Draft202012Validator,FormatChecker
    bundle=json.loads(Path('docs/features/recruitment/weekly-cycles/proposals/beta-recruitment-v2.wire.json').read_text())
    operation=next(o for o in bundle['operations'] if o['path']==path and o['method']==method)
    schema=operation['responses'][str(status)]['content']['application/json']['schema']
    Draft202012Validator({'$defs':bundle['$defs'],**schema},format_checker=FormatChecker()).validate(value)


def test_actual_beta_reader_matrix_matches_agreed_closed_wire(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    rows=[
        ('/v2/raid-rooms/{room_id}',{}),('/v2/raid-rooms/{room_id}/detail',{}),
        ('/v2/raid-rooms/{room_id}/detail',{'reader_profile':'application-display-1'}),
        ('/v2/raid-rooms/{room_id}/detail',{'reader_profile':'membership-actions-1'}),
        ('/v2/me/raid-rooms/{room_id}/plan',{}),
        ('/v2/me/raid-rooms/{room_id}/plan',{'reader_profile':'membership-actions-1'}),
        ('/v2/me/raid-room-memberships',{}),('/v2/me/raid-room-memberships',{'reader_profile':'membership-actions-1'}),
        ('/v2/me/raid-room-applications',{}),('/v2/me/raid-rooms/{room_id}/schedule-context',{}),
        ('/v2/me/raid-rooms/{room_id}/availability-submission',{}),('/v2/raid-rooms',{})]
    with client(a) as http:
        for path,extra in rows:
            response=http.get(path.replace('{room_id}',str(rid)),params={**PROFILE,'target_cycle_key':key,**extra})
            assert response.status_code==200,(path,extra,response.json())
            validate_beta_wire(path,'GET',200,response.json())
        params={**PROFILE,'target_cycle_key':key,'character_id':a['ids'][0],'selected_role':'dealer',
            'items':json.dumps([{'raid_id':v['raid_id'],'difficulty_id':v['difficulty_id']} for v in preflight(a)['data']['targets']]),
            'base_starts_at':base.isoformat(),'early_coordination_enabled':'false'}
        response=http.get('/v2/me/raid-room-creation-context',params=params)
        assert response.status_code==200,response.json()
        validate_beta_wire('/v2/me/raid-room-creation-context','GET',200,response.json())


def test_http_raw_presence_idempotency_and_profile_input_rejection(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a,mode='leader_only')
    with beta_profile.using():raw=admission_request(context(b,rid,key,'apply')).model_dump(mode='json')
    command=str(uuid.uuid4())
    with client(b) as http:
        path=f'/v2/raid-rooms/{rid}/applications'
        original=http.post(path,params=PROFILE,json=raw,headers={'Idempotency-Key':command})
        assert original.status_code==201,original.json()
        replay=http.post(path,params=PROFILE,json=raw,headers={'Idempotency-Key':command})
        assert replay.json()==original.json()
        conflict=http.post(path,params=PROFILE,json={**raw,'application_memo':None},headers={'Idempotency-Key':command})
        assert conflict.status_code==409 and conflict.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
        legacy_shape=request(preflight(b)).model_dump(mode='json')
        invalid=http.post('/v2/raid-rooms',params=PROFILE,json=legacy_shape,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert invalid.status_code==400,invalid.json()


def test_explicit_next_opening_has_its_own_base_and_identity(beta):
    from app.raid_rooms import cycle_opening,cycle_schemas
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    next_key=(datetime.fromisoformat(key)+timedelta(days=7)).date().isoformat()
    next_base=base+timedelta(days=7,hours=1)
    params=dict(base_starts_at=next_base.isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):
        value=cycle_opening.get(actor(a['uid']),rid,next_key,'open')
        d=value['data']
        validate_beta_wire('/v2/me/raid-rooms/{room_id}/opening-context','GET',200,value)
        body=beta_schemas.BetaOpenRequest.model_validate(dict(expected_cycle_key=value['scope']['current_cycle_key'],
            target_cycle_key=next_key,expected_target_revision=None,context_token=d['context_token'],selection=d['selection'],
            target_items=d['targets'],target_session_ids=[],intent='open',beta_schedule=d['beta_schedule_config']))
        status,ack=cycle_opening.execute(actor(a['uid']),rid,uuid.uuid4(),body)
        assert status==200
        view=cycle_member_reads.detail(actor(a['uid']),rid,next_key)['data']
        assert datetime.fromisoformat(view['beta_schedule']['base_starts_at'].replace('Z','+00:00'))==next_base
        current_view=cycle_member_reads.detail(actor(a['uid']),rid,key)['data']
        assert view['recruitment_identity']['number']!=current_view['recruitment_identity']['number']


def test_safe_legacy_leave_cleans_promise_and_record_stays_private(beta):
    from tests.test_membership_actions import run as membership_run
    _,a,b=beta;rid,key,base,_,_=create_beta(a);beta_join(b,rid,key)
    with session() as db:
        cm=db.scalar(select(CycleMember).where(CycleMember.user_id==b['uid']))
        mid,cid=cm.membership_id,cm.id
    membership_run(b,rid,key,'leave_target')
    with session() as db:
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.user_id==b['uid'],TimeReservation.released_at.is_(None)))==0
    with client(b) as http:
        response=http.get(f'/v2/raid-rooms/{rid}/detail',params={**PROFILE,'target_cycle_key':key,'reader_profile':'membership-actions-1','membership_id':str(mid),'cycle_member_id':str(cid)})
        assert response.status_code==200,response.json()
        data=response.json()['data']
        assert data['content'] is None and data['record'] is not None
        assert data['recruitment_identity'] is None and data['beta_schedule'] is None
        validate_beta_wire('/v2/raid-rooms/{room_id}/detail','GET',200,response.json())


def test_preset_concurrent_versions_only_one_writer_wins(beta):
    _,a,b=beta
    def write(text):
        data=application_presets.PresetPut.model_validate(dict(expected_version=1,items=[dict(id=str(uuid.uuid4()),text=text)]))
        try:return application_presets.put(actor(a['uid']),uuid.uuid4(),data)[0]
        except GameError as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(write,['첫 문구','둘째 문구']))
    assert sorted(map(str,results))==sorted(['200','REVISION_CONFLICT'])
    assert application_presets.get(actor(a['uid']))['version']==2


def test_rolled_back_identity_number_is_not_reused(beta,monkeypatch):
    _,a,b=beta
    original=beta_schedule.copy_personal
    def reject(db,row,cm,stamp):
        original(db,row,cm,stamp)
        raise GameError('SERVICE_UNAVAILABLE',503)
    monkeypatch.setattr(beta_schedule,'copy_personal',reject)
    with pytest.raises(GameError,match='SERVICE_UNAVAILABLE'):create_beta(a)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(BetaSchedule))==0
    monkeypatch.setattr(beta_schedule,'copy_personal',original)
    rid,key,base,_,_=create_beta(a)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        assert db.get(BetaSchedule,row.id).number==2


def test_existing_member_next_participation_copies_current_table_atomically(beta):
    from app.raid_rooms import cycle_continuation,cycle_schemas
    _,a,b=beta;rid,key,base,_,_=create_beta(a,combined=True);beta_join(b,rid,key)
    next_key=(datetime.fromisoformat(key)+timedelta(days=7)).date().isoformat()
    with beta_profile.using():
        value=cycle_continuation.get(actor(b['uid']),rid,next_key)
        d=value['data']
        validate_beta_wire('/v2/me/raid-rooms/{room_id}/continuation-context','GET',200,value)
        body=cycle_schemas.Continue.model_validate(dict(expected_cycle_key=value['scope']['current_cycle_key'],
            target_cycle_key=next_key,expected_target_revision=value['scope']['target_revision'],
            context_token=d['context_token'],selection=d['selection'],target_items=d['targets'],target_session_ids=[]))
        status,ack=cycle_continuation.execute(actor(b['uid']),rid,uuid.uuid4(),body)
        assert status==200
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==datetime.fromisoformat(next_key).date()))
        cm=db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.user_id==b['uid']))
        assert cm.state=='participating' and db.get(BetaAvailabilityCopy,cm.id).state=='unset'
        assert db.scalar(select(func.count()).select_from(TimeReservation).where(TimeReservation.user_id==b['uid'],TimeReservation.released_at.is_(None)))==2


def test_fallback_crossing_departure_rolls_back_then_reviews(beta,monkeypatch):
    from app.core import database
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    monkeypatch.setattr(database,'now',lambda db:base+timedelta(seconds=1))
    with pytest.raises(GameError,match='SERVICE_UNAVAILABLE'):
        with session() as db,db.begin():
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
            beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid),row,base-timedelta(minutes=20))
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid))
        assert db.get(BetaSchedule,row.id).confirmation_kind is None
        beta_schedule.reconcile(db,db.get(RecruitmentRoom,rid),row,base+timedelta(seconds=1))
        assert db.get(BetaSchedule,row.id).needs_review


def test_creation_context_binds_changed_own_reservation_evidence(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a);beta_join(b,rid,key)
    next_key=(datetime.fromisoformat(key)+timedelta(days=7)).date().isoformat()
    params=dict(base_starts_at=(base+timedelta(days=7)).isoformat(),early_coordination_enabled='false')
    with beta_profile.using(params):
        ctx=preflight(b,key=next_key)
        assert ctx['data']['permissions']['create']['allowed']
        raw=request(ctx).model_dump(mode='json');raw.pop('schedule_groups')
        raw['beta_schedule_targets']=ctx['data']['beta_schedule_targets']
        data=beta_schemas.BetaCreateRequest.model_validate(raw)
        with session() as db,db.begin():
            reservation=db.scalar(select(TimeReservation).where(TimeReservation.user_id==b['uid'],TimeReservation.released_at.is_(None)))
            reservation.released_at=now(db);reservation.released_reason='schedule_changed'
        with pytest.raises(GameError,match='SELECTION_CONTEXT_CHANGED'):
            cycle_creation.create(actor(b['uid']),uuid.uuid4(),data)


def test_printable_ascii_preset_storage_and_original_payload_replay(beta):
    _,a,b=beta
    text='  :;[]{}<>\\|`"\'=$%^*  '
    expected=text.strip(' ')
    key=str(uuid.uuid4());item=str(uuid.uuid4())
    body=dict(expected_version=1,items=[dict(id=item,text=text)])
    with client(a) as http:
        http.app.include_router(application_presets.router)
        path='/v2/me/application-message-presets'
        first=http.put(path,json=body,headers={'Idempotency-Key':key})
        assert first.status_code==200,first.json()
        assert first.json()['items']==[dict(id=item,text=expected)]
        validate_beta_wire(path,'PUT',200,first.json())
        assert http.put(path,json=body,headers={'Idempotency-Key':key}).json()==first.json()
        assert http.get(path).json()==first.json()
        # Equivalent normalized text is still a different original body.
        changed={**body,'items':[dict(id=item,text=expected)]}
        conflict=http.put(path,json=changed,headers={'Idempotency-Key':key})
        assert conflict.status_code==409 and conflict.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
        assert http.get(path).json()==first.json()


def test_ended_membership_without_selected_cycle_member_remains_readable(beta):
    from tests.test_membership_actions import run
    _,a,b=beta
    rid,c,_,_,_=create_beta(a,combined=True)
    beta_join(b,rid,c)
    with beta_profile.using():run(b,rid,c,'leave_all')
    n=(date.fromisoformat(c)+timedelta(days=7)).isoformat()
    with client(b) as http:
        path='/v2/me/raid-room-memberships'
        for key in [c,n]:
            for state in ['ended','all']:
                result=http.get(path,params={**PROFILE,'reader_profile':'membership-actions-1',
                    'target_cycle_key':key,'state':state})
                assert result.status_code==200,result.json()
                validate_beta_wire(path,'GET',200,result.json())
                item=next(v for v in result.json()['data']['items'] if v['target']['room_id']==str(rid))
                assert item['content'] is None
                assert item['beta_schedule'] is None
                assert 'recruitment_identity' not in item
                if key==n:
                    assert item['viewer']['cycle_member_id'] is None
                    assert item['viewer']['mode']=='relation_only'


def test_explicit_beta_copy_increments_same_personal_version_and_replays_once(beta):
    from app.raid_rooms import cycle_times
    _,a,b=beta
    rid,key,_,_,_=create_beta(a)
    with beta_profile.using():
        initial=cycle_times.get_submission(actor(a['uid']),rid,key)
        assert initial['data']['revision']==1
        assert initial['data']['availability_copy']['state']=='unset'
        from app.raid_rooms import cycle_wire as wire
        # Use the same existing explicit submission request as native clients.
        value=initial['data'];scope=initial['scope']
        request=wire.InputContract3PutV2MeRaidRoomsRoomIdAvailabilitySubmission.model_validate(dict(
            expected_cycle_key=scope['current_cycle_key'],target_cycle_key=key,
            expected_target_revision=scope['target_revision'],
            expected_cycle_member_revision=value['cycle_member_revision'],
            expected_submission_revision=value['revision'],expected_personal_version=value['source_personal_version']))
        command=uuid.uuid4()
        status,ack=cycle_times.put_submission(actor(a['uid']),rid,command,request)
        assert status==200 and ack['data']['revision']==2
        assert ack['data']['source_personal_version']==initial['data']['source_personal_version']==1
        assert ack['data']['availability_copy']['state']=='unset'
        assert cycle_times.put_submission(actor(a['uid']),rid,command,request)==(status,ack)
        assert cycle_times.get_submission(actor(a['uid']),rid,key)['data']==ack['data']
