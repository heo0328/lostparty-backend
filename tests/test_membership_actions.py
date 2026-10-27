"""Ordinary departure/dissolution and profile boundaries on disposable PostgreSQL."""
import os, subprocess, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta,date
import pytest
from sqlalchemy import select, inspect, func, text
from app.core.database import session, now
from app.raid_rooms import membership_actions as service, membership_readers as readers, membership_action_schemas as schema
from app.raid_rooms.membership_action_models import LeadershipRecovery, MembershipActionAudit
from app.game_accounts.models import Character
from tests.test_completion_corrections import corrected
from tests.test_recruitment_cycle_outcomes import (
    outcomes,planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,plan,actor,add_member,complete,fingerprints,denied,commands,cycles,life,graph,
    RoomCycle,CycleMember,CycleGeneration,Assignment,cancel_member,
)
from tests.test_recruitment_cycle_times_http import client
from tests.test_raid_room_migrations import table_digests


@pytest.fixture
def membership_ready(corrected):
    engine,a,b=corrected
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    result=subprocess.run(['alembic','upgrade','0031_membership_actions'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,result.stderr.decode()[-1800:]
    assert table_digests(engine,tables)==before
    from app.raid_rooms import readiness
    with session() as db,db.begin():readiness.require_two_cycle_active(db)
    return engine,a,b


def validate_contract(name,value):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    contract=json.loads(Path('docs/features/recruitment/membership-actions/examples/membership-actions.schema.json').read_text())
    legacy_schema=json.loads(Path('openapi/two-cycle.openapi.yaml').read_text())
    legacy_schema['$schema']='https://json-schema.org/draft/2020-12/schema'
    registry=Registry().with_resource('urn:lostparty:two-cycle-0eed67c',Resource.from_contents(legacy_schema))
    Draft202012Validator({'$ref':'#/$defs/'+name,'$defs':contract['$defs']},registry=registry,format_checker=FormatChecker()).validate(value)


def export(name,value):
    directory=os.environ.get('MEMBERSHIP_EXAMPLES_DIR')
    if not directory:return
    import json
    from pathlib import Path
    def sanitized(v):
        if isinstance(v,dict):return {k:('<redacted-context-token>' if k=='context_token' else sanitized(x)) for k,x in v.items()}
        if isinstance(v,list):return [sanitized(x) for x in v]
        return v
    path=Path(directory);path.mkdir(parents=True,exist_ok=True);(path/(name+'.json')).write_text(json.dumps(sanitized(value),indent=2)+'\n')


def menu(w,rid,key):
    value=service.get(actor(w['uid']),rid,key);validate_contract('Context',value);return value


def body(value,action):
    return schema.Command.model_validate(dict(expected_cycle_key=value['scope']['current_cycle_key'],view_cycle_key=value['scope']['view_cycle_key'],
        actor_membership_id=value['data']['actor']['membership_id'],expected_actor_membership_revision=value['data']['actor']['membership_revision'],
        action=action,context_token=value['data']['options'][action]['confirmation']['context_token']))


def run(w,rid,key,action,*,value=None,command=None):
    value=value or menu(w,rid,key)
    result=service.execute(actor(w['uid']),rid,command or uuid.uuid4(),body(value,action))
    validate_contract('Result',result[1]);return result


def assert_rules(impact,result):
    out=result['data'];room=impact['room_effect']
    def match(rule,actual):
        if rule['comparison']=='equal':assert actual==rule['before']
        else:assert actual>rule['before']
        if rule['exact_after'] is not None:assert actual==rule['exact_after']
    match(room['room_revision_rule'],out['room_revision']);match(room['actor_membership_revision_rule'],out['actor_membership_revision'])
    assert out['actor_membership_ended']==room['actor_membership_will_end']
    assert out['ended_persistent_membership_count']==room['ended_persistent_membership_count']
    assert out['affected_cycle_keys']==impact['affected_cycle_keys']
    for before,after in zip(impact['targets'],out['effects']):
        assert before['planned_target_state']==after['target_state']
        assert before['planned_generation_state']==after['generation_state']
        for name,field in [('target','target_revision'),('members','members_revision'),('plan','plan_revision')]:match(before['revision_rules'][name],after[field])
        match(before['revision_rules']['leadership'],after['leadership']['leadership_revision'])
        assert {k:v for k,v in before['leadership_after'].items() if k in after['leadership']}==after['leadership']
        for b,a in zip(before['affected_members'],after['members']):match(b['revision_rule'],a['cycle_member_revision']);assert a['state']==b['planned_state']


@pytest.mark.parametrize('leader',[False,True])
def test_target_departure_succession_other_cycle_ack_readonly(membership_ready,leader,monkeypatch):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c)
    w=a if leader else b;before_n=plan(a,rid,n)['data'];before=fingerprints(engine)
    value=menu(w,rid,c);assert fingerprints(engine)==before
    selected=value['data']['options']['leave_target'];assert selected['permission']['allowed']
    command=uuid.uuid4();request=body(value,'leave_target');status,result=service.execute(actor(w['uid']),rid,command,request)
    assert status==200;assert_rules(selected['impact'],result)
    assert result['data']['effects'][0]['members'][0]['state']=='cancelled'
    assert result['data']['room_ended'] is False and not result['data']['actor_membership_ended']
    assert {k:v for k,v in plan(a,rid,n)['data'].items() if k not in ('server_time','permissions')}=={k:v for k,v in before_n.items() if k not in ('server_time','permissions')}
    before=fingerprints(engine);real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(days=7))
    assert service.execute(actor(w['uid']),rid,command,request)==(status,result)
    assert fingerprints(engine)==before


def test_no_eligible_successor_departure_success_and_explicit_recovery(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c)
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.lifecycle_state='retired'
    value=menu(a,rid,c);selected=value['data']['options']['leave_target'];assert selected['permission']['allowed']
    result=run(a,rid,c,'leave_target',value=value)[1];assert_rules(selected['impact'],result)
    effect=result['data']['effects'][0];assert effect['leadership_status']=='pending_review' and effect['target_state']=='review_required'
    assert effect['leadership']['leader_cycle_member_id'] is None
    export('no-successor-context',value);export('no-successor-result',result)
    value=readers.get(actor(b['uid']),rid,c,'detail')
    assert value['data']['viewer']['role']=='member' and value['data']['content'] is None
    assert value['data']['recovery']['state']=='leadership_pending'
    m=menu(b,rid,c);assert m['data']['options']['leave_target']['permission']['allowed']
    assert m['data']['options']['recover_leadership']['permission']['allowed'] is False
    with session() as db,db.begin():
        char=db.get(Character,uuid.UUID(b['ids'][0]));char.lifecycle_state='active'
    m=menu(b,rid,c);impact=m['data']['options']['recover_leadership']['impact'];assert impact
    result=run(b,rid,c,'recover_leadership',value=m)[1];assert_rules(impact,result)
    assert result['data']['effects'][0]['target_state']=='open'
    assert readers.get(actor(b['uid']),rid,c,'detail')['data']['content'] is not None


def test_last_departure_only_target_then_room_end(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a)
    first=run(a,rid,c,'leave_target')[1];assert not first['data']['room_ended']
    m=menu(a,rid,n);impact=m['data']['options']['leave_target']['impact']
    last=run(a,rid,n,'leave_target',value=m)[1];assert_rules(impact,last)
    assert last['data']['room_ended'] and last['data']['ended_persistent_membership_count']==1
    page=readers.memberships(actor(a['uid']),c,'ended')
    loc=page['data']['items'][0]['viewer']['record_locator']
    record=readers.get(actor(a['uid']),rid,c,'plan',membership_id=uuid.UUID(loc['membership_id']),cycle_member_id=uuid.UUID(loc['cycle_member_id']))
    export('ended-own-record-plan',record)
    assert record['data']['viewer']['mode']=='record' and record['data']['access']['read_only']
    assert record['data']['record']['assignments'] and record['data']['content'] is None
    assert not record['data']['permissions']['read_action_menu']['allowed']
    denied('ROOM_NOT_FOUND',readers.get,actor(b['uid']),rid,c,'detail',membership_id=uuid.UUID(loc['membership_id']),cycle_member_id=uuid.UUID(loc['cycle_member_id']))


def test_mixed_roles_opposite_only_dissolve_and_empty_effects_end(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,n)
    # Ordinary actor departs N, making b the N leader while keeping C.
    run(a,rid,n,'leave_target')
    m=menu(b,rid,c);opts=m['data']['options']
    assert not opts['leave_target']['visible'] and opts['leave_all']['permission']['allowed']
    assert opts['dissolve_led_targets']['impact']['affected_cycle_keys']==[n]
    before_c=plan(a,rid,c)['data']
    result=run(b,rid,c,'dissolve_led_targets',value=m)[1];assert_rules(opts['dissolve_led_targets']['impact'],result)
    assert not result['data']['room_ended'] and not result['data']['actor_membership_ended']
    assert {k:v for k,v in plan(a,rid,c)['data'].items() if k not in ('server_time','permissions')}=={k:v for k,v in before_c.items() if k not in ('server_time','permissions')}
    m=menu(b,rid,c);impact=m['data']['options']['leave_all']['impact'];assert impact['targets']==[]
    result=run(b,rid,c,'leave_all',value=m)[1];assert_rules(impact,result)
    assert result['data']['effects']==[] and result['data']['actor_membership_ended']
    export('empty-effects-context',m);export('empty-effects-result',result)


def test_both_targets_dissolve_members_room_completion_preserved(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    complete(a,rid,c,index=1)
    m=menu(a,rid,n);impact=m['data']['options']['dissolve_led_targets']['impact']
    assert impact['affected_cycle_keys']==[c,n] and all(len(t['affected_members'])==2 for t in impact['targets'])
    completed=[x for t in impact['targets'] for m in t['affected_members'] for x in m['preserved_completed_assignment_ids']]
    assert completed
    result=run(a,rid,n,'dissolve_led_targets',value=m)[1];assert_rules(impact,result)
    assert result['data']['room_ended'] and result['data']['ended_persistent_membership_count']==2
    with session() as db:
        assert all(db.get(Assignment,uuid.UUID(x)).state=='completed' for x in completed)
        assert db.scalar(select(func.count()).select_from(MembershipActionAudit).where(MembershipActionAudit.room_id==rid))==1


def test_context_stale_all_or_nothing_and_duplicate_command(membership_ready,people):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c)
    m=menu(a,rid,c);request=body(m,'dissolve_led_targets')
    add_member(b,rid,n);before=fingerprints(engine)
    denied('TARGET_CONTEXT_STALE',service.execute,actor(a['uid']),rid,uuid.uuid4(),request)
    assert fingerprints(engine)==before
    m=menu(a,rid,c);request=body(m,'leave_all');command=uuid.uuid4()
    def attempt(_):
        from app.game_accounts.support import GameError
        try:return service.execute(actor(a['uid']),rid,command,request)
        except GameError as error:
            assert error.code=='REQUEST_IN_PROGRESS';return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    saved=service.execute(actor(a['uid']),rid,command,request)
    assert any(results) and all(r is None or r==saved for r in results)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(MembershipActionAudit).where(MembershipActionAudit.command_id==command))==1


def test_normal_profile_preserves_legacy_content_and_profile_cursor(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a)
    old=plan(a,rid,c);profile=readers.get(actor(a['uid']),rid,c,'plan')
    def normalize(v):
        if isinstance(v,dict):return {k:normalize(x) for k,x in v.items() if k not in ('server_now','server_time','evaluated_at')}
        if isinstance(v,list):return [normalize(x) for x in v]
        return v
    assert normalize(profile['data']['content'])==normalize(old)
    assert profile['data']['viewer']['mode']=='participant'
    assert profile['data']['permissions']['resume_weekly']['allowed'] is False
    from app.raid_rooms import cycle_lists
    old_page=cycle_lists.memberships(actor(a['uid']),c)
    page=readers.memberships(actor(a['uid']),c)
    assert page['data']['items'][0]['content']==old_page['data']['items'][0]
    denied('INVALID_REQUEST',readers.get,actor(a['uid']),rid,c,'detail',membership_id=uuid.uuid4())


def test_leave_all_independent_successions_and_n_rollback(membership_ready,monkeypatch):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    m=menu(a,rid,n);impact=m['data']['options']['leave_all']['impact'];request=body(m,'leave_all')
    assert [t['transition'] for t in impact['targets']]==['automatic_successor','automatic_successor']
    original=service.cleanup;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('synthetic N failure')
        return original(*args,**kwargs)
    before=fingerprints(engine);monkeypatch.setattr(service,'cleanup',fail_second)
    with pytest.raises(RuntimeError):service.execute(actor(a['uid']),rid,uuid.uuid4(),request)
    assert fingerprints(engine)==before
    monkeypatch.setattr(service,'cleanup',original)
    result=run(a,rid,n,'leave_all',value=m)[1];assert_rules(impact,result)
    assert result['data']['actor_membership_ended'] and not result['data']['room_ended']
    assert all(e['leadership']['leader_membership_id']!=result['data']['actor_membership_id'] for e in result['data']['effects'])


def test_recovery_review_remaining_and_existing_leader_revision_preserved(membership_ready,people):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);d=people('recovery-other');add_member(b,rid,c);add_member(d,rid,c)
    with session() as db,db.begin():
        for person in (b,d):db.get(Character,uuid.UUID(person['ids'][0])).lifecycle_state='retired'
    run(a,rid,c,'leave_target')
    with session() as db,db.begin():db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_state='active'
    m=menu(b,rid,c);impact=m['data']['options']['recover_leadership']['impact']
    assert impact['targets'][0]['planned_target_state']=='review_required'
    result=run(b,rid,c,'recover_leadership',value=m)[1];assert_rules(impact,result)
    leader=result['data']['effects'][0]['leadership'];assert leader['leader_cycle_member_id']
    with session() as db,db.begin():db.get(Character,uuid.UUID(d['ids'][0])).lifecycle_state='active'
    m=menu(b,rid,c);impact=m['data']['options']['recover_leadership']['impact']
    assert impact['targets'][0]['revision_rules']['leadership']['comparison']=='equal'
    result=run(b,rid,c,'recover_leadership',value=m)[1];assert_rules(impact,result)
    assert result['data']['effects'][0]['target_state']=='open'
    assert result['data']['effects'][0]['leadership']==leader


def test_unknown_generation_reader_visible_no_fabrication(membership_ready):
    engine,a,b=membership_ready
    from tests.test_recruitment_participation import make_room
    rid=make_room(b)
    with session() as db,db.begin():
        key=life.raids.cycle(now(db)).cycle_key
        member=db.scalar(select(life.Member).where(life.Member.room_id==rid,life.Member.user_id==b['uid']))
        row=RoomCycle(id=uuid.uuid4(),room_id=rid,cycle_key=key,state='review_required',generation=None,revision=1,
            settings_revision=1,members_revision=1,plan_revision=1,settings_snapshot=None,provenance='legacy_unknown',created_at=now(db))
        db.add(row);db.flush()
        db.add(CycleMember(id=uuid.uuid4(),room_id=rid,cycle_id=row.id,generation=None,membership_id=member.id,
            user_id=b['uid'],state='review_required',revision=1,joined_order=None,joined_at=None))
    value=readers.get(actor(b['uid']),rid,key,'detail');validate_contract('DetailProfile',value)
    assert value['data']['viewer']['mode']=='recovery' and value['data']['viewer']['role']=='none'
    assert value['data']['target']['target_generation'] is None and value['data']['target']['leadership'] is None
    assert value['data']['recovery']['state']=='unverified'
    denied('ROOM_REVIEW_REQUIRED',readers.get,actor(b['uid']),rid,key,'plan')
    page=readers.memberships(actor(b['uid']),key);validate_contract('MembershipPage',page)
    assert any(x['target']['room_id']==str(rid) for x in page['data']['items'])
    value=menu(b,rid,key)
    assert value['data']['options']['leave_target']['visible'] and not value['data']['options']['leave_target']['permission']['allowed']


def test_expiry_current_cycle_scope_and_tampered_body_no_write(membership_ready,monkeypatch):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);m=menu(a,rid,c);request=body(m,'leave_target')
    before=fingerprints(engine)
    wrong=request.model_copy(update={'view_cycle_key':n})
    denied('CONTEXT_INVALID',service.execute,actor(a['uid']),rid,uuid.uuid4(),wrong)
    real=cycles.now;monkeypatch.setattr(cycles,'now',lambda db:real(db)+timedelta(seconds=121))
    denied('COMMAND_CONTEXT_EXPIRED',service.execute,actor(a['uid']),rid,uuid.uuid4(),request)
    assert fingerprints(engine)==before


def test_runtime_schema_uses_closed_models_and_preserves_base_contract(membership_ready):
    import json
    from pathlib import Path
    from app.main import app,create_two_cycle_app
    original=json.loads(Path('openapi/openapi.yaml').read_text())
    assert app.openapi()==original
    runtime=create_two_cycle_app().openapi()
    assert '/v2/raid-rooms/{room_id}/membership-actions' in runtime['paths']
    command=runtime['components']['schemas']['MembershipActionCommand']
    assert command['additionalProperties'] is False and len(command['required'])==6
    assert runtime['components']['schemas']['BMembership']==json.loads(Path('openapi/two-cycle.openapi.yaml').read_text())['components']['schemas']['BMembership']


def test_eight_members_both_targets_dissolve_with_exact_cleanup(membership_ready,people):
    engine,a,b=membership_ready
    from app.raid_rooms import cycle_creation as creation,cycle_wire
    from tests.test_recruitment_cycle_creation import request
    from tests.test_recruitment_cycle_commands import context,admission_request
    raid=next(r for r in life.raids.catalog().raids if r.raid_id=='kazeros_act4')
    with session() as db:key=life.raids.cycle(now(db)).cycle_key
    ctx=creation.get(actor(a['uid']),uuid.UUID(a['ids'][0]),'dealer',[
        cycle_wire.BCreateTarget(raid_id=raid.raid_id,difficulty_id=raid.difficulties[0].difficulty_id,expected_weekly_revision=1)],None,key,True,None,None)
    result=creation.create(actor(a['uid']),uuid.uuid4(),request(ctx))[1]['data'];rid=uuid.UUID(result['room_id'])
    c,n=[x['target_cycle_key'] for x in result['created_cycles']]
    for i in range(7):
        from app.auth.router import _limits
        _limits.clear();w=people(f'membership-eight-{i}')
        for key in (c,n):commands.admit(actor(w['uid']),rid,uuid.uuid4(),admission_request(context(w,rid,key,role='support' if i in (2,6) else 'dealer')))
    value=menu(a,rid,n);impact=value['data']['options']['dissolve_led_targets']['impact']
    assert [len(t['affected_members']) for t in impact['targets']]==[8,8]
    result=run(a,rid,n,'dissolve_led_targets',value=value)[1];assert_rules(impact,result)
    assert result['data']['ended_persistent_membership_count']==8
    export('eight-members-two-targets-context',value);export('eight-members-two-targets-result',result)
    with session() as db:
        assert not db.scalar(select(life.WeeklyOccupancy.assignment_id).where(life.WeeklyOccupancy.room_id==rid).limit(1))


def test_historical_group_departure_rejoin_identity_and_readonly(membership_ready):
    engine,a,b=membership_ready
    from app.groups.models import Group,GroupMembership
    from tests.test_group_foundation import create as group_create
    from tests.test_recruitment_cycle_creation import preflight,request
    from app.raid_rooms import cycle_creation as creation
    from tests.test_recruitment_cycle_commands import context,admission_request
    gid=uuid.UUID(group_create(a)[1]['group']['group_id']);gmid=uuid.uuid4()
    with session() as db,db.begin():
        db.add(GroupMembership(id=gmid,group_id=gid,user_id=b['uid'],character_id=uuid.UUID(b['ids'][0]),display=None,revision=1,joined_at=now(db)))
        db.get(Group,gid).members_revision+=1
    created=creation.create(actor(a['uid']),uuid.uuid4(),request(preflight(a,continuation=True,gid=gid),scope='group',group_id=str(gid)))[1]['data']
    rid=uuid.UUID(created['room_id']);c,n=[x['target_cycle_key'] for x in created['created_cycles']]
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,c)))
    run(b,rid,c,'leave_all')
    old=readers.memberships(actor(b['uid']),c,'ended')['data']['items'][0]['viewer']['record_locator']
    commands.admit(actor(b['uid']),rid,uuid.uuid4(),admission_request(context(b,rid,c)))
    current=readers.get(actor(b['uid']),rid,c,'detail')['data']['viewer']
    assert current['membership_id']!=old['membership_id'] and current['cycle_member_id']!=old['cycle_member_id']
    with session() as db,db.begin():db.get(GroupMembership,gmid).ended_at=now(db)
    # Existing active room membership remains an independent visibility basis.
    assert readers.get(actor(b['uid']),rid,c,'detail')['data']['viewer']['membership_id']==current['membership_id']
    value=readers.get(actor(b['uid']),rid,c,'plan',membership_id=uuid.UUID(old['membership_id']),cycle_member_id=uuid.UUID(old['cycle_member_id']))
    validate_contract('PlanProfile',value)
    assert value['data']['viewer']['membership_id']==old['membership_id']
    assert value['data']['access']['read_only'] and value['data']['content'] is None
    assert all(not value['data']['permissions'][k]['allowed'] for k in ('manage_target','resume_weekly','read_action_menu'))
    assert {x['character_id'] for x in value['data']['record']['assignments']}=={b['ids'][0]}
    denied('INVALID_REQUEST',readers.get,actor(b['uid']),rid,c,'plan',membership_id=uuid.UUID(old['membership_id']),cycle_member_id=uuid.UUID(old['cycle_member_id']),include_resume_display=True)


def test_http_menu_command_profile_validation_and_no_store(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a)
    path=f'/v2/raid-rooms/{rid}/membership-action-context'
    with client(a) as http:
        response=http.get(path,params={'target_cycle_key':c});assert response.status_code==200,response.json()
        value=response.json();validate_contract('Context',value);assert response.headers['cache-control']=='no-store'
        request=body(value,'leave_target').model_dump(mode='json');command=str(uuid.uuid4())
        route=f'/v2/raid-rooms/{rid}/membership-actions'
        rejected=http.post(route,json=request|{'extra':True},headers={'Idempotency-Key':command});assert rejected.status_code==400
        result=http.post(route,json=request,headers={'Idempotency-Key':command});assert result.status_code==200,result.json()
        validate_contract('Result',result.json());assert result.headers['cache-control']=='no-store'
        assert http.post(route,json=request,headers={'Idempotency-Key':command}).json()==result.json()
        page=http.get('/v2/me/raid-room-memberships',params={'target_cycle_key':c,'state':'ended','reader_profile':readers.PROFILE})
        assert page.status_code==200,page.json();validate_contract('MembershipPage',page.json())
        loc=page.json()['data']['items'][0]['viewer']['record_locator']
        params={'target_cycle_key':c,'reader_profile':readers.PROFILE,'membership_id':loc['membership_id'],'cycle_member_id':loc['cycle_member_id']}
        record=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=params)
        assert record.status_code==200,record.json();validate_contract('PlanProfile',record.json())
        assert record.headers['cache-control']=='no-store'
        params['reader_profile']='typo'
        assert http.get(f'/v2/me/raid-rooms/{rid}/plan',params=params).status_code==400


def test_same_persistent_membership_rejoin_keeps_old_record_cm_and_assignments(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c)
    before=readers.get(actor(b['uid']),rid,c,'plan')['data'];old=before['viewer']['record_locator']
    run(b,rid,c,'leave_target')
    old_record=readers.get(actor(b['uid']),rid,c,'plan',membership_id=uuid.UUID(old['membership_id']),cycle_member_id=uuid.UUID(old['cycle_member_id']))['data']
    old_ids={x['assignment_id'] for x in old_record['record']['assignments']}
    add_member(b,rid,c)
    current_plan=readers.get(actor(b['uid']),rid,c,'plan')['data']
    assert not old_ids & {x['assignment_id'] for x in current_plan['content']['data']['my_assignments']}
    new=current_plan['viewer']
    assert new['membership_id']==old['membership_id'] and new['cycle_member_id']!=old['cycle_member_id']
    again=readers.get(actor(b['uid']),rid,c,'plan',membership_id=uuid.UUID(old['membership_id']),cycle_member_id=uuid.UUID(old['cycle_member_id']))['data']
    assert again['viewer']['cycle_member_state']=='cancelled' and again['viewer']['role']=='none'
    assert again['record']==old_record['record']
    current=readers.memberships(actor(b['uid']),c)['data']['items']
    assert sum(x['viewer']['cycle_member_id']==new['cycle_member_id'] for x in current)==1
    ended=readers.memberships(actor(b['uid']),c,'ended')['data']['items']
    assert any(x['viewer']['cycle_member_id']==old['cycle_member_id'] for x in ended)
    # A later completion must not rewrite the older cancelled CM.
    complete(b,rid,c,index=0)
    with session() as db:assert db.get(CycleMember,uuid.UUID(old['cycle_member_id'])).state=='cancelled'


def test_review_pending_expiry_does_not_assign_leader(membership_ready,monkeypatch):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c)
    with session() as db,db.begin():db.get(Character,uuid.UUID(b['ids'][0])).lifecycle_state='retired'
    run(a,rid,c,'leave_target')
    from app.raid_rooms import cycle_worker
    real=cycle_worker.now;monkeypatch.setattr(cycle_worker,'now',lambda db:real(db)+timedelta(days=7))
    cycle_worker.process_room(rid)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(c)))
        gen=db.get(CycleGeneration,(row.id,row.generation));recovery=db.get(LeadershipRecovery,(row.id,row.generation))
        assert row.state=='closed' and gen.state=='stopped' and gen.leader_cycle_member_id is None
        assert recovery.state=='closed'
        assert not db.scalar(select(life.WeeklyOccupancy.assignment_id).where(life.WeeklyOccupancy.room_id==rid,life.WeeklyOccupancy.cycle_key==date.fromisoformat(c)).limit(1))


def test_existing_atomic_commands_keep_wire_and_replay_on0031(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a);add_member(b,rid,c);add_member(b,rid,n)
    from app.raid_rooms import atomic_members
    from tests.test_atomic_members import removal,removal_body,departure,depart_body
    value=removal(a,b,rid,n);old_removal=atomic_members.execute(actor(a['uid']),rid,uuid.uuid4(),removal_body(value))
    assert old_removal[1]['data']['action']=='member_removal'
    value=departure(a,rid,c);request=depart_body(value);command=uuid.uuid4()
    original=atomic_members.execute(actor(a['uid']),rid,command,request,departure=True)
    assert original[1]['data']['action']=='personal_completion_departure'
    # A later ordinary command never reinterprets the old durable ACK.
    run(b,rid,c,'leave_target')
    assert atomic_members.execute(actor(a['uid']),rid,command,request,departure=True)==original


def test_actual_bearer_auth_foreign_actor_revoked_ack_and_request_limit(membership_ready):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    from app.auth.models import Session
    engine,a,b=membership_ready;rid,c,n=scheduled(a)
    app=FastAPI();register(app);app.include_router(router);app.middleware('http')(no_store)
    menu_path=f'/v2/raid-rooms/{rid}/membership-action-context';post_path=f'/v2/raid-rooms/{rid}/membership-actions'
    with TestClient(app,raise_server_exceptions=False) as http:
        for headers in ({},{'Authorization':'Bearer invalid'}):
            r=http.get(menu_path,params={'target_cycle_key':c},headers=headers)
            assert r.status_code==401 and r.headers['cache-control']=='no-store'
        r=http.get(menu_path,params={'target_cycle_key':c},headers=a['headers']);assert r.status_code==200,r.json()
        request=body(r.json(),'leave_target').model_dump(mode='json')
        assert http.get(menu_path,params={'target_cycle_key':c},headers=b['headers']).status_code==403
        assert http.post(post_path,json=request,headers=b['headers']|{'Idempotency-Key':str(uuid.uuid4())}).status_code==400
        headers=a['headers']|{'Idempotency-Key':str(uuid.uuid4())}
        assert http.post(post_path,content=' '*32769,headers=headers).status_code==413
        result=http.post(post_path,json=request,headers=headers);assert result.status_code==200,result.json()
        assert result.headers['cache-control']=='no-store'
        with session() as db,db.begin():db.scalar(select(Session).where(Session.user_id==a['uid'])).revoked_at=now(db)
        replay=http.post(post_path,json=request,headers=headers)
        assert replay.status_code==401 and replay.headers['cache-control']=='no-store'


def test_retained_stopped_reader_preserves_server_capability_without_app_reactivation(membership_ready):
    engine,a,b=membership_ready;rid,c,n=scheduled(a)
    complete(a,rid,c,kind='close_weekly')
    before=fingerprints(engine)
    value=readers.get(actor(a['uid']),rid,c,'plan');validate_contract('PlanProfile',value)
    assert value['data']['viewer']['mode']=='retained' and value['data']['content'] is not None
    assert value['data']['permissions']['resume_weekly']['allowed']
    assert value['data']['access']['read_only'] is False
    assert fingerprints(engine)==before  # no preview proposal/write/automatic resume
