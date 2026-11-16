"""Minute personal inputs preserve snapshots and five-minute scheduling boundaries."""
import uuid
from datetime import datetime,timedelta,timezone
import pytest
from pydantic import TypeAdapter,ValidationError
from app.raid_rooms.schemas.availability_schemas import Interval,ScheduleClock
from app.raid_rooms.schemas.cycle_wire import BInterval
from app.raid_rooms.schedules.availability import normalize
from app.raid_rooms.common import time_policy
from app.raids.service import KST
from tests.raid_rooms.schedules.test_recruitment_cycle_times_http import (
    consent,lifecycle,candidate,ready,sources,imported,people,worlds,client,
    scheduled,submission,plan)


def span(start='18:03',end='20:17',weekday=1,offset=0):
    return dict(weekday=weekday,start=start,end=end,end_day_offset=offset)


@pytest.mark.parametrize('row',[span(),span('23:57','00:02',7,1),span('18:03','18:03',1,1)])
def test_minute_interval_and_wire_accept_same_valid_values(row):
    assert Interval.model_validate(row).model_dump()==row
    assert BInterval.model_validate(row).model_dump()==row


@pytest.mark.parametrize('row',[span('18:03','18:03'),span('20:17','18:03'),span('18:03','18:04',1,1),
    span('24:00'),span('18:03:00'),span('18:03:00.1'),span('8:03'),span('18:03 '),span(offset=True)])
def test_rejected_boundaries(row):
    with pytest.raises(ValidationError):Interval.model_validate(row)


def test_normalization_and_coverage_do_not_round_to_grid():
    assert normalize([span('23:57','00:02',7,1)])==[
        dict(start_minute=0,end_minute=2),dict(start_minute=10077,end_minute=10080)]
    normalized=normalize([span(),span('19:01','21:07'),span('21:07','21:09'),span()])
    assert normalized==[dict(start_minute=1083,end_minute=1269)]
    start=datetime(2026,11,16,18,5,tzinfo=KST)
    window=normalize([span()])
    candidates=[]
    for minute in range(0,150,5):
        s=start+timedelta(minutes=minute)
        if time_policy.covered(s,s+timedelta(minutes=30),window):candidates.append(s.strftime('%H:%M'))
    assert candidates[0]=='18:05' and candidates[-1]=='19:45'
    assert not time_policy.covered(start-timedelta(minutes=5),start+timedelta(minutes=25),window)
    sunday=datetime(2026,11,22,23,57,tzinfo=KST)
    assert time_policy.covered(sunday,sunday+timedelta(minutes=5),normalize([span('23:57','00:02',7,1)]))
    with pytest.raises(ValidationError):TypeAdapter(ScheduleClock).validate_python('18:03')
    assert TypeAdapter(ScheduleClock).validate_python('18:05')=='18:05'


def test_actual_http_personal_roundtrip_ack_and_target_copy(consent):
    engine,a,b=consent;rid,c,n=scheduled(a)
    url='/v1/me/play-availability'
    intervals=[span(),span('23:57','00:02',7,1),span('18:03','18:03',3,1)]
    with client(a) as http:
        before=http.get(url).json();key={'Idempotency-Key':str(uuid.uuid4())}
        body=dict(expected_version=before['version'],timezone='Asia/Seoul',intervals=intervals)
        saved=http.put(url,json=body,headers=key)
        assert saved.status_code==200,saved.text
        ack=saved.json();assert ack['intervals']==intervals and ack['normalized_intervals']==normalize(intervals)
        assert http.get(url).json()==ack
        path=f'/v2/me/raid-rooms/{rid}/availability-submission'
        source=submission(a,rid,n).model_dump(mode='json')
        headers={'Idempotency-Key':str(uuid.uuid4())}
        copied=http.put(path,json=source,headers=headers)
        assert copied.status_code==200,copied.text
        assert copied.json()['data']['intervals']==intervals
        assert http.get(path,params={'target_cycle_key':n}).json()['data']['intervals']==intervals
        assert http.put(path,json=source,headers=headers).json()==copied.json()
        snapshot=plan(a,rid,c)
        update=http.put(url,json=dict(body,expected_version=ack['version'],intervals=[]),headers={'Idempotency-Key':str(uuid.uuid4())})
        assert update.status_code==200
        assert http.get(path,params={'target_cycle_key':n}).json()['data']['intervals']==intervals
        current_plan=plan(a,rid,c)
        for name in ('revision','sessions','schedule_groups','game_items'):
            assert current_plan['data'][name]==snapshot['data'][name]
        assert http.put(url,json=body,headers=key).json()==ack
        assert http.get(url).json()==update.json()
        assert http.put(url,json=body,headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==409
        bad=dict(body,expected_version=update.json()['version'],intervals=[span('18:03:00')])
        assert http.put(url,json=bad,headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==400
        assert http.get(url).json()==update.json()


def test_actual_beta_candidates_use_minute_tables_and_exact_busy_edges(consent,monkeypatch):
    from sqlalchemy import select
    from app.core.database import session,now
    from app.raid_rooms.schedules import beta_schedule
    from app.raid_rooms.models.cycle_models import RoomCycle
    from app.raid_rooms.models.integrated_models import RecruitmentRoom
    from app.raid_rooms.models.beta_models import BetaSchedule
    from app.raid_rooms.models.source_models import TimeReservation,SessionParticipation
    from app.raid_rooms.models.integrated_models import RecruitmentSession,RecruitmentSegment
    from tests.raid_rooms.schedules.test_explicit_departure_minutes import create_at,clone
    from tests.raid_rooms.admissions.test_beta_recruitment import beta_join
    from tests.raid_rooms.schedules.test_recruitment_cycle_times import save_personal
    _,a,b=consent
    with session() as db:start=time_policy.ceil_tick(now(db)+timedelta(hours=2)).astimezone(KST)+timedelta(minutes=3)
    end=start+timedelta(hours=6)
    intervals=[span(start.strftime('%H:%M'),end.strftime('%H:%M'),start.isoweekday(),int(start.date()!=end.date()))]
    for w in (a,b):save_personal(w,intervals=intervals)
    rid,key,base,*_=create_at(a,base=(end+timedelta(hours=2)).astimezone(timezone.utc),enabled=True)
    original=beta_schedule.initial
    monkeypatch.setattr(beta_schedule,'initial',lambda *args,**kwargs:None)
    beta_join(b,rid,key)
    monkeypatch.setattr(beta_schedule,'initial',original)
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));room=db.get(RecruitmentRoom,rid)
        saved=db.get(BetaSchedule,row.id);duration=saved.base_ends_at-saved.base_starts_at
        result=beta_schedule.evaluate(db,room,row,now(db))
        assert result['state']=='ready',result
        first=result['earliest_start'];assert first==time_policy.ceil_tick(start)
        assert result['latest_start']+duration<=end
        own=db.scalar(select(TimeReservation).where(TimeReservation.session_id==saved.session_id,TimeReservation.user_id==a['uid'],TimeReservation.released_at.is_(None)))
        for overlap,expected in ((1,first+timedelta(minutes=5)),(0,first)):
            with db.begin_nested() as savepoint:
                busy_end=first+timedelta(minutes=overlap);busy_start=busy_end-timedelta(minutes=30)
                external=clone(db.get(RecruitmentSession,saved.session_id),id=uuid.uuid4(),starts_at=busy_start,ends_at=busy_end);db.add(external);db.flush()
                part=clone(db.get(SessionParticipation,own.participation_id),id=uuid.uuid4(),session_id=external.id);db.add(part);db.flush()
                segment=clone(db.get(RecruitmentSegment,own.segment_id),id=uuid.uuid4(),session_id=external.id,starts_at=busy_start,ends_at=busy_end,duration_minutes=30);db.add(segment);db.flush()
                busy=clone(own,id=uuid.uuid4(),session_id=external.id,participation_id=part.id,segment_id=segment.id,starts_at=busy_start,ends_at=busy_end)
                db.add(busy);db.flush()
                assert beta_schedule.evaluate(db,room,row,now(db))['earliest_start']==expected
                savepoint.rollback()
