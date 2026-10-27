import uuid
import pytest
from sqlalchemy import select,func,text
from app.core.database import session,now
from app.raid_rooms import cycle_times as times
from app.raid_rooms.source_models import TimeReservation as Reservation
from app.raid_rooms.cycle_consent_models import CycleConsent
from tests.test_recruitment_cycle_times import (consent,lifecycle,candidate,ready,sources,imported,people,worlds,
    scheduled,save_personal,submission,confirmation,plan,actor,add_member,fingerprints,confirm)
from tests.test_recruitment_cycle_http import client as candidate_client,validate


def client(w):
    # The isolated candidate app must use the real runtime's cache policy too.
    # Importing main does not run its lifespan or mount the candidate in main.
    from app.main import no_store
    http=candidate_client(w)
    http.app.middleware('http')(no_store)
    return http


def test_submission_context_confirmation_actual_http_contract(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);save_personal(a)
    route=f'/v2/me/raid-rooms/{rid}/availability-submission';spec='/v2/me/raid-rooms/{room_id}/availability-submission'
    with client(a) as http:
        for suffix,specpath in [('availability-submission',spec),('schedule-context','/v2/me/raid-rooms/{room_id}/schedule-context')]:
            response=http.get(f'/v2/me/raid-rooms/{rid}/{suffix}',params={'target_cycle_key':n})
            assert response.status_code==200,response.json()
            assert response.headers['cache-control']=='no-store'
            validate(specpath,'get',200,response.json())
        body=submission(a,rid,n).model_dump(mode='json');validate(spec,'put',200,body,input=True)
        headers={'Idempotency-Key':str(uuid.uuid4())}
        response=http.put(route,json=body,headers=headers)
        assert response.status_code==200,response.json()
        validate(spec,'put',200,response.json())
        assert http.put(route,json=body,headers=headers).json()==response.json()
        sid,data=confirmation(a,rid,n);body=data.model_dump(mode='json')
        path=f'/v2/raid-sessions/{sid}/participation-confirmations'
        spec='/v2/raid-sessions/{session_id}/participation-confirmations'
        validate(spec,'post',200,body,input=True)
        response=http.post(path,json=body,headers={'Idempotency-Key':str(uuid.uuid4())})
        assert response.status_code==200,response.json()
        validate(spec,'post',200,response.json())
        response=http.get('/v2/me/raid-schedule-overlaps',params={'target_cycle_key':n})
        assert response.status_code==200,response.json()
        validate('/v2/me/raid-schedule-overlaps','get',200,response.json())


def test_http_readonly_strict_query_body_and_cross_target(consent):
    engine,a,b=consent;rid,c,n=scheduled(a);sid,data=confirmation(a,rid,n)
    before=fingerprints(engine)
    with client(a) as http:
        for url,query in [(f'/v2/me/raid-rooms/{rid}/schedule-context',{'target_cycle_key':n,'target_session_id':str(sid)}),
            (f'/v2/me/raid-rooms/{rid}/availability-submission',{'target_cycle_key':n}),
            ('/v2/me/raid-schedule-overlaps',{'target_cycle_key':n})]:
            assert http.get(url,params=query).status_code==200
            assert http.get(url,params=list(query.items())+[('target_cycle_key',n)]).status_code==400
            assert http.get(url,params=query|{'extra':'bad'}).status_code==400
        for field in ('expected_target_revision','expected_schedule_revision','expected_cycle_member_revision','expected_participation_revision'):
            response=http.post(f'/v2/raid-sessions/{sid}/participation-confirmations',json=data.model_dump(mode='json')|{field:True},
                headers={'Idempotency-Key':str(uuid.uuid4())})
            assert response.status_code==400
            validate('/v2/raid-sessions/{session_id}/participation-confirmations','post',400,response.json())
        response=http.get(f'/v2/me/raid-rooms/{rid}/schedule-context',params={'target_cycle_key':c,'target_session_id':str(sid)})
        assert response.status_code==400
    with client(b) as http:
        assert http.get(f'/v2/me/raid-rooms/{rid}/availability-submission',params={'target_cycle_key':n}).status_code==403
    assert fingerprints(engine)==before


def test_c_confirmation_final_end_deadline_and_original_ack(consent,monkeypatch):
    engine,a,b=consent;rid,c,n=scheduled(a);add_member(b,rid,c)
    sid,body=confirmation(b,rid,c)
    from app.raid_rooms import cycles,cycle_schedule
    with session() as db,db.begin():end=db.get(cycle_schedule.Session,sid).ends_at
    before=fingerprints(engine);clock=cycles.now;calls=[]
    def boundary(db):calls.append(1);return clock(db) if len(calls)==1 else end
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',boundary)
        from tests.test_recruitment_cycle_times import denied
        denied('SCHEDULE_ENDED',times.confirm,actor(b['uid']),sid,uuid.uuid4(),body)
    assert fingerprints(engine)==before
    command=uuid.uuid4();original=times.confirm(actor(b['uid']),sid,command,body)
    with monkeypatch.context() as m:
        m.setattr(cycles,'now',lambda db:end)
        assert times.confirm(actor(b['uid']),sid,command,body)==original
    with session() as db,db.begin():
        assert db.scalar(select(func.count()).select_from(CycleConsent).where(CycleConsent.user_id==b['uid']))==1
