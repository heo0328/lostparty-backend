import uuid
from sqlalchemy import inspect
from tests.test_recruitment_cycle_lifecycle import (lifecycle,candidate,ready,sources,imported,people,worlds,
    create_room,opening_body,continue_body,cancel_body,scoped,next_key,add_member,actor)
from tests.test_recruitment_cycle_lifecycle import change_body
from tests.test_recruitment_cycle_http import client,validate
from tests.test_raid_room_migrations import table_digests
from app.raid_rooms import cycle_wire as wire


def post(http,path,body,spec):
    value=body.model_dump(mode='json');validate(spec,'post',200,value,input=True)
    response=http.post(path,json=value,headers={'Idempotency-Key':str(uuid.uuid4())})
    assert response.status_code==200,response.json().get('error')
    validate(spec,'post',200,response.json())
    return response.json()


def get(http,rid,suffix,key):
    spec='/v2/me/raid-rooms/{room_id}/'+suffix
    query=dict(target_cycle_key=key)
    if suffix=='opening-context':query['intent']='open'
    response=http.get(f'/v2/me/raid-rooms/{rid}/{suffix}',params=query)
    assert response.status_code==200,response.json().get('error')
    validate(spec,'get',200,response.json())
    return response.json()


def test_w3_http_open_continue_transfer_cancel_reopen_contract(lifecycle):
    _,a,b=lifecycle
    room=create_room(a,combined=False);rid=uuid.UUID(room['room_id']);n=next_key()
    add_member(b,rid,room['created_cycles'][0]['target_cycle_key'])
    with client(a) as http:
        ctx=get(http,rid,'opening-context',n)
        post(http,f'/v2/raid-rooms/{rid}/recruitment-openings',opening_body(ctx),'/v2/raid-rooms/{room_id}/recruitment-openings')
    with client(b) as http:
        ctx=get(http,rid,'continuation-context',n)
        post(http,f'/v2/raid-rooms/{rid}/continuation-participations',continue_body(ctx),'/v2/raid-rooms/{room_id}/continuation-participations')
    with client(a) as http:
        ctx=get(http,rid,'leadership-transfer-context',n);candidate=ctx['data']['candidates'][0]
        body=wire.TransferCommand.model_validate(scoped(ctx)|dict(expected_leadership_revision=ctx['data']['leadership']['leadership_revision'],
            candidate_cycle_member_id=candidate['cycle_member_id'],expected_candidate_revision=candidate['revision']))
        post(http,f'/v2/raid-rooms/{rid}/leadership-transfers',body,'/v2/raid-rooms/{room_id}/leadership-transfers')
    for w in (b,a):
        with client(w) as http:
            ctx=get(http,rid,'participation-cancellation-context',n)
            post(http,f'/v2/raid-rooms/{rid}/participation-cancellations',cancel_body(ctx),'/v2/raid-rooms/{room_id}/participation-cancellations')
    with client(a) as http:
        response=http.get(f'/v2/me/raid-rooms/{rid}/opening-context',params=dict(target_cycle_key=n,intent='reopen'))
        assert response.status_code==200,response.json().get('error')
        validate('/v2/me/raid-rooms/{room_id}/opening-context','get',200,response.json())
        result=post(http,f'/v2/raid-rooms/{rid}/recruitment-openings',opening_body(response.json(),'reopen'),'/v2/raid-rooms/{room_id}/recruitment-openings')
        assert result['scope']['target_generation']==2


def test_w3_contexts_readonly_and_strict_query_body(lifecycle):
    engine,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key();add_member(b,rid,n)
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    with client(a) as http:
        for suffix in ('opening-context','continuation-context','participation-cancellation-context','leadership-transfer-context'):
            get(http,rid,suffix,n)
        assert table_digests(engine,tables)==before
        path=f'/v2/me/raid-rooms/{rid}/continuation-context'
        for query in ([('target_cycle_key',n),('character_id',a['ids'][1])],
                      [('target_cycle_key',n),('target_cycle_key',n)],
                      [('target_cycle_key',n),('unrelated','value')]):
            assert http.get(path,params=query).status_code==400
        ctx=get(http,rid,'participation-cancellation-context',n)
        body=cancel_body(ctx).model_dump(mode='json');body['expected_leadership_revision']=True
        response=http.post(f'/v2/raid-rooms/{rid}/participation-cancellations',json=body,
            headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==400
        validate('/v2/raid-rooms/{room_id}/participation-cancellations','post',400,response.json())


def test_http_same_character_role_change_keeps_exact_weekly_lease(lifecycle):
    from app.core.database import session
    from sqlalchemy import select
    from app.raid_rooms.weekly_links import WeeklyOccupancy
    _,a,b=lifecycle
    room=create_room(a);rid=uuid.UUID(room['room_id']);n=next_key()
    with client(a) as http:
        plan=http.get(f'/v2/me/raid-rooms/{rid}/plan',params={'target_cycle_key':n})
        assert plan.status_code==200,plan.json().get('error')
        response=http.get(f'/v2/raid-rooms/{rid}/admission-context',params=dict(target_cycle_key=n,
            character_id=a['ids'][0],selected_role='support',intent='change_character'))
        assert response.status_code==200,response.json().get('error')
        assert set(response.json()['data']['permissions'])=={'change_character'}
        validate('/v2/raid-rooms/{room_id}/admission-context','get',200,response.json())
        changed=post(http,f'/v2/raid-rooms/{rid}/character-changes',change_body(response.json(),plan.json()),
            '/v2/raid-rooms/{room_id}/character-changes')
        assert changed['scope']['target_revision']==2
    with session() as db,db.begin():
        leases=list(db.scalars(select(WeeklyOccupancy).where(WeeklyOccupancy.room_id==rid)))
        assert len(leases)==2 and {str(v.character_id) for v in leases}=={a['ids'][0]}
