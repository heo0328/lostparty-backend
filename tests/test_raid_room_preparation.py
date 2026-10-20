"""F3-A internal preparation; no production routes/source/config activated."""
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import event, select, text, func
from sqlalchemy.exc import OperationalError
from app.core.database import session, engine, now
from app.game_accounts.support import fail
from app.member_limits import service as limits
from app.member_limits.models import MemberUsageHead
from app.raid_rooms import core, service, usage, runtime, readiness, policies
from app.raid_rooms.models import Room, Round, Membership, Application, DirectoryHead
from app.raid_rooms.commands import Withdraw
from tests.test_raid_room_foundation import (people, worlds, create, create_command, selection,
    join, admission, recover, decision, denied)
from tests.test_group_foundation import actor
from tests.test_member_limits import change, rows


def snapshot(w):
    with session() as db, db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        return usage.limits_snapshot(db,w['uid'])


def test_explicit_and_public_usage_sources_are_ready(people):
    a=people('a'); before=rows()
    assert snapshot(a)['usage']['raid_rooms']==dict(used=0,remaining=10,state='within',can_increase=True)
    assert limits.get(actor(a['uid']))['usage']['raid_rooms']==dict(used=0,remaining=10,state='within',can_increase=True)
    assert rows()==before


def test_usage_counts_memberships_not_characters_pending_or_cycle(people):
    a,b=people('a'),people('b')
    room=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    join(b,room,applying=True)
    assert snapshot(b)['usage']['raid_rooms']['used']==0
    second=uuid.UUID(create(a,create_command(a,offset=3,selection=selection(a,index=1)))[1]['room_id'])
    assert snapshot(a)['usage']['raid_rooms']['used']==2
    with session() as db, db.begin():
        round=db.get(Round,db.get(Room,second).round_id)
        round.cycle_key-=timedelta(days=7)
    assert snapshot(a)['usage']['raid_rooms']['used']==2
    recover(a,second,'end')
    assert snapshot(a)['usage']['raid_rooms']['used']==1


def test_explicit_usage_exact_exceeded_and_recovered(people):
    a=people('a'); room=uuid.UUID(create(a)[1]['room_id'])
    change(a['uid'],limits.Limits(15,5,1))
    out=snapshot(a)
    assert out['usage']['raid_rooms']==dict(used=1,remaining=0,state='at_limit',can_increase=False)
    assert out['issues']==[]
    change(a['uid'],limits.Limits(15,5,0),expected=2)
    out=snapshot(a)
    assert out['usage']['raid_rooms']['state']=='exceeded'
    assert out['issues']==[dict(code='MEMBER_RAID_LIMIT_EXCEEDED',dimension='raid_rooms',used=1,limit=0)]
    recover(a,room,'end')
    assert snapshot(a)['usage']['raid_rooms']['state']=='at_limit'
    assert snapshot(a)['issues']==[]


def test_usage_read_no_writes_locks_or_head_creation(people):
    a=people('a'); statements=[]
    def capture(conn,cursor,statement,*args):statements.append(statement.upper())
    event.listen(engine(),'before_cursor_execute',capture)
    try:snapshot(a)
    finally:event.remove(engine(),'before_cursor_execute',capture)
    assert not any(s.lstrip().startswith(('INSERT ','UPDATE ','DELETE ')) or 'FOR UPDATE' in s for s in statements)
    with session() as db: assert db.get(MemberUsageHead,a['uid']) is None


def test_usage_failure_and_invalid_counter_do_not_become_zero(people,monkeypatch):
    a=people('a')
    def unavailable(*args):raise OperationalError('test',{},Exception('injected'))
    monkeypatch.setattr(usage,'count',unavailable)
    with session() as db:
        with pytest.raises(OperationalError):usage.limits_snapshot(db,a['uid'])
        for invalid in (None,False,-1,'0'):
            denied('SERVICE_UNAVAILABLE',limits.snapshot,db,a['uid'],room_count=lambda *args:invalid)


@pytest.mark.parametrize('value,enabled',[(None,False),('false',False),('0',False),('true',True),('1',True)])
def test_admission_setting_default_and_explicit_values(monkeypatch,value,enabled):
    if value is None:monkeypatch.delenv(runtime.SETTING,raising=False)
    else:monkeypatch.setenv(runtime.SETTING,value)
    assert runtime.admissions_enabled() is enabled
    assert runtime.admission_reason()==(None if enabled else 'SERVICE_UNAVAILABLE')


def test_invalid_admission_configuration_fails_closed_without_value_leak(monkeypatch):
    monkeypatch.setenv(runtime.SETTING,'private-invalid-marker')
    with pytest.raises(ValueError) as exc:runtime.admissions_enabled()
    assert 'private-invalid-marker' not in str(exc.value)
    assert runtime.admission_reason()=='SERVICE_UNAVAILABLE'
    with pytest.raises(TypeError):runtime.admission_policy(None)


def test_paused_creation_preserves_original_ack_and_rejects_new_execution(people,monkeypatch):
    a=people('a'); command=create_command(a); key=uuid.uuid4()
    policy=runtime.admission_policy(policies.public_finite)
    monkeypatch.setenv(runtime.SETTING,'true')
    original=service.create(actor(a['uid']),key,command,policy=policy)
    monkeypatch.setenv(runtime.SETTING,'false')
    assert service.create(actor(a['uid']),key,command,policy=policy)==original
    fresh=create_command(a,offset=3,selection=selection(a,index=1))
    denied('SERVICE_UNAVAILABLE',service.create,actor(a['uid']),uuid.uuid4(),fresh,policy=policy)
    assert snapshot(a)['usage']['raid_rooms']['used']==1
    recover(a,uuid.UUID(original[1]['room_id']),'end')
    assert snapshot(a)['usage']['raid_rooms']['used']==0


def test_paused_join_retry_resume_replay_and_cleanup(people,monkeypatch):
    a,b=people('a'),people('b'); room=uuid.UUID(create(a)[1]['room_id'])
    cmd=admission(b,room); key=uuid.uuid4(); policy=runtime.admission_policy(policies.public_finite)
    monkeypatch.setenv(runtime.SETTING,'false')
    denied('SERVICE_UNAVAILABLE',service.admit,actor(b['uid']),room,key,cmd,policy=policy)
    assert snapshot(b)['usage']['raid_rooms']['used']==0
    monkeypatch.setenv(runtime.SETTING,'true')
    first=service.admit(actor(b['uid']),room,key,cmd,policy=policy)
    monkeypatch.setenv(runtime.SETTING,'false')
    assert service.admit(actor(b['uid']),room,key,cmd,policy=policy)==first
    recover(b,room)
    assert snapshot(b)['usage']['raid_rooms']['used']==0


def test_paused_pending_approve_reject_withdraw_and_usage(people,monkeypatch):
    a,b,c,d=[people(x) for x in 'abcd']; room=uuid.UUID(create(a,create_command(a,mode='leader_only'))[1]['room_id'])
    b_app=uuid.UUID(join(b,room,applying=True)[1]['application_id'])
    c_app=uuid.UUID(join(c,room,applying=True)[1]['application_id'])
    cmd=decision(b_app); key=uuid.uuid4(); policy=runtime.admission_policy(policies.public_finite)
    monkeypatch.setenv(runtime.SETTING,'false')
    denied('SERVICE_UNAVAILABLE',service.admit,actor(d['uid']),room,uuid.uuid4(),admission(d,room),applying=True,policy=policy)
    denied('SERVICE_UNAVAILABLE',service.decide,actor(a['uid']),b_app,key,cmd,approve=True,policy=policy)
    with session() as db:assert db.get(Application,b_app).state=='pending'
    assert snapshot(b)['usage']['raid_rooms']['used']==0
    assert service.decide(actor(a['uid']),c_app,uuid.uuid4(),decision(c_app))[1]['state']=='rejected'
    assert service.withdraw(actor(b['uid']),b_app,uuid.uuid4(),Withdraw(expected_application_revision=1))[1]['state']=='withdrawn'


def test_enabled_admission_still_runs_explicit_policy(people,monkeypatch):
    a=people('a');monkeypatch.setenv(runtime.SETTING,'true')
    def reject(*args):fail('COMBAT_REQUIREMENT_UNAVAILABLE')
    denied('COMBAT_REQUIREMENT_UNAVAILABLE',service.create,actor(a['uid']),uuid.uuid4(),create_command(a),
           policy=runtime.admission_policy(reject))
    assert snapshot(a)['usage']['raid_rooms']['used']==0


def test_readiness_passes_read_only_under_current_role_without_creating_rows():
    with session() as db,db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        readiness.require_ready(db)
        assert db.scalar(select(func.count()).select_from(Membership))==0


@pytest.mark.parametrize('alter',[
    "UPDATE alembic_version SET version_num='unknown_future_revision'",
    "ALTER TABLE raid_room_applications RENAME COLUMN build TO missing_build",
    "ALTER TABLE raid_room_memberships DISABLE TRIGGER record_timestamps_before_write",
    "DROP INDEX uq_room_current_slot",
    "DELETE FROM raid_room_directory_head",
    "ALTER TABLE raid_rooms DROP CONSTRAINT fk_room_current_round",
])
def test_readiness_rejects_missing_or_incompatible_prerequisites(alter):
    with session() as db:
        db.execute(text(alter))
        try:denied('SERVICE_UNAVAILABLE',readiness.require_ready,db)
        finally:db.rollback()
    with session() as db:readiness.require_ready(db)


def test_readiness_verifies_runtime_privileges_without_superuser_assumption():
    role='room_prep_'+uuid.uuid4().hex
    with session() as db:
        # Fabricated isolated-test role; the entire DDL/GRANT transaction is rolled back.
        db.execute(text(f'CREATE ROLE {role} NOLOGIN'))
        db.execute(text(f'GRANT USAGE ON SCHEMA public TO {role}'))
        db.execute(text(f'GRANT SELECT ON public.alembic_version TO {role}'))
        names=', '.join('public.'+m.__tablename__ for m in readiness.MODELS)
        db.execute(text(f'GRANT SELECT, INSERT, UPDATE ON {names} TO {role}'))
        db.execute(text(f'SET LOCAL ROLE {role}'))
        readiness.require_ready(db)
        db.execute(text('RESET ROLE'))
        db.execute(text(f'REVOKE UPDATE ON public.raid_room_applications FROM {role}'))
        db.execute(text(f'SET LOCAL ROLE {role}'))
        try:denied('SERVICE_UNAVAILABLE',readiness.require_ready,db)
        finally:db.rollback()


def test_preparation_does_not_install_routes_or_change_openapi():
    import json
    from app.main import app
    assert app.openapi()==json.loads(open('openapi/openapi.yaml').read())
    assert all(getattr(route.endpoint,'__module__','')!='app.raid_rooms.router' for route in app.routes)
