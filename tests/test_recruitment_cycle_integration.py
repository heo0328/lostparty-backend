"""W5 non-empty legacy upgrade through 0029; all data is disposable."""
import os,subprocess
from sqlalchemy import inspect,select,text
from app.core.database import session
from app.raid_rooms import readiness,cycle_worker,admission_service
from app.raid_rooms.cycle_models import RoomCycle
from tests.test_recruitment_cycles import migrated
from tests.test_recruitment_cycle_outcomes import outcomes,planning,consent,lifecycle,candidate,ready,sources,imported,people,worlds
from tests.test_raid_room_migrations import table_digests
from tests.test_group_foundation import actor


def test_nonempty_legacy_upgrade_full_chain_preserves_all_columns_ack_and_review(migrated):
    engine,a,b,rid,current,key,request,ack,*_=migrated
    old=set(inspect(engine).get_table_names())-{'alembic_version'}
    before=table_digests(engine,old)
    result=subprocess.run(['alembic','upgrade','0029_cycle_outcomes'],env={**os.environ,
        'DATABASE_URL':engine.url.render_as_string(hide_password=False)},capture_output=True,timeout=90)
    assert result.returncode==0,'Restricted-role full two-cycle migration failed'
    assert table_digests(engine,old)==before
    with session() as db,db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        assert db.scalar(text('SELECT NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole FROM pg_roles WHERE rolname=current_user'))
        readiness.require_two_cycle_active(db)
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid)))
        assert rows and all(r.provenance=='legacy_unknown' and r.state=='review_required' and r.generation is None for r in rows)
    tables=set(inspect(engine).get_table_names())-{'alembic_version'}
    preserved=table_digests(engine,tables)
    cycle_worker.process_due()
    assert table_digests(engine,tables)==preserved
    replay=admission_service.execute(actor(a['uid']),'w1-preserve',key,request,
        lambda *args:(_ for _ in ()).throw(AssertionError('Must recover original ACK')))
    assert replay==ack
    assert table_digests(engine,old)==before


def test_prepared_app_real_jwt_create_join_read_and_member_isolation(outcomes):
    import json,uuid
    from fastapi.testclient import TestClient
    from app.main import create_two_cycle_app
    from app.auth.models import User
    from tests.test_recruitment_cycle_http import validate
    from tests.test_recruitment_cycle_creation import preflight,request
    from tests.test_recruitment_cycle_commands import admission_request
    engine,a,b=outcomes
    ctx=preflight(a,continuation=True,bundle=True)
    params=dict(target_cycle_key=ctx['data']['target_cycle_key'],character_id=a['ids'][0],selected_role='dealer',
        continuation_enabled='true',items=json.dumps([{k:t[k] for k in ('raid_id','difficulty_id')} for t in ctx['data']['targets']]))
    with TestClient(create_two_cycle_app()) as http:
        response=http.get('/v2/me/raid-room-creation-context',params=params,headers=a['headers'])
        assert response.status_code==200,response.json().get('error')
        ctx=response.json();command=request(ctx).model_dump(mode='json');key=str(uuid.uuid4())
        headers={**a['headers'],'Idempotency-Key':key}
        response=http.post('/v2/raid-rooms',json=command,headers=headers)
        assert response.status_code==201,response.json().get('error')
        ack=response.json();validate('/v2/raid-rooms','post',201,ack)
        assert http.post('/v2/raid-rooms',json=command,headers=headers).json()==ack
        rid=ack['data']['room_id'];c,n=[r['target_cycle_key'] for r in ack['data']['created_cycles']]
        response=http.get(f'/v2/raid-rooms/{rid}/admission-context',params=dict(target_cycle_key=n,
            character_id=b['ids'][0],selected_role='dealer',intent='join'),headers=b['headers'])
        assert response.status_code==200,response.json().get('error')
        body=admission_request(response.json()).model_dump(mode='json')
        response=http.post(f'/v2/raid-rooms/{rid}/join',json=body,headers={**b['headers'],'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json().get('error')
        for who in (a,b,a):
            response=http.get(f'/v2/raid-rooms/{rid}',params=dict(target_cycle_key=n),headers=who['headers'])
            assert response.status_code==200,response.json().get('error')
            assert response.headers['cache-control']=='no-store'
            assert response.json()['data']['my_target_role']==('leader' if who is a else 'member')
        response=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=dict(target_cycle_key=c),headers=b['headers'])
        assert response.status_code==403,response.json().get('error')
        for who in (a,b):
            response=http.post('/v2/me/raid-weekly-summary',json=dict(character_ids=[who['ids'][0]],target_cycle_keys=[c,n]),headers=who['headers'])
            assert response.status_code==200,response.json().get('error')
            assert response.headers['cache-control']=='no-store'
            validate('/v2/me/raid-weekly-summary','post',200,response.json())
            assert {e['character_id'] for e in response.json()['entries']}=={who['ids'][0]}
        with session() as db,db.begin():db.get(User,b['uid']).status='disabled'
        response=http.get(f'/v2/raid-rooms/{rid}',params=dict(target_cycle_key=n),headers=b['headers'])
        assert response.status_code==403,response.json().get('error')
        assert response.headers['cache-control']=='no-store'
