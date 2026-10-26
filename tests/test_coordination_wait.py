"""Opt-in read status and immutable old responses; isolated data only."""
import uuid
from datetime import timedelta
from app.raids.service import KST
from app.raid_rooms.integrated_models import RecruitmentRoom
import pytest
from sqlalchemy import select,inspect
from app.core.database import session,now
from app.raid_rooms import beta_profile,beta_schedule,availability,cycle_member_reads
from app.raid_rooms.beta_models import BetaSchedule,BetaAvailabilityCopy
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleSubmission
from tests.test_beta_recruitment import (beta,current,candidate,ready,sources,imported,people,worlds,create_beta,beta_join,actor)
from tests.test_recruitment_cycle_times_http import client
from tests.test_raid_room_migrations import table_digests


def wait(w,rid,key,enabled=True):
    with beta_profile.using({'include_coordination_wait':'true'} if enabled else {}):
        return cycle_member_reads.detail(actor(w['uid']),rid,key)['data']['beta_schedule']


def test_wait_statuses_are_read_only_and_missing_copy_is_not_empty_candidate(beta,monkeypatch):
    engine,a,b=beta;rid,key,base,_,_=create_beta(a,enabled=True)
    value=wait(a,rid,key);assert value['coordination_wait']==dict(status='waiting_members',missing_members=1)
    original=beta_schedule.initial
    monkeypatch.setattr(beta_schedule,'initial',lambda *args,**kw:None)
    beta_join(b,rid,key);monkeypatch.setattr(beta_schedule,'initial',original)
    before=table_digests(engine,set(inspect(engine).get_table_names()))
    assert wait(a,rid,key)['coordination_wait']==dict(status='pending',missing_members=None)
    assert table_digests(engine,set(before))==before
    with session() as db,db.begin():
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));saved=db.get(BetaSchedule,row.id)
        members=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id)))
        missing=db.get(BetaAvailabilityCopy,members[-1].id);db.delete(missing)
    assert wait(a,rid,key)['coordination_wait']['status']=='unavailable'
    with session() as db,db.begin():
        db.add(BetaAvailabilityCopy(cycle_member_id=members[-1].id,state='unset',source_personal_version=1,copied_at=now(db)))
        day=(base.astimezone(KST).isoweekday()+1)%7+1
        intervals=[dict(weekday=day,start='00:00',end='01:00',end_day_offset=0)]
        for member in members:
            table=db.get(CycleSubmission,member.id);table.intervals=intervals;table.normalized_intervals=availability.normalize(intervals)
            db.get(BetaAvailabilityCopy,member.id).state='configured'
    assert wait(a,rid,key)['coordination_wait']['status']=='no_earlier_candidate'
    with session() as db,db.begin():
        saved=db.get(BetaSchedule,row.id);saved.early_enabled=False;saved.early_additional_members=None
    assert wait(a,rid,key)['coordination_wait']['status']=='not_applicable'


def test_wait_http_omitted_false_reader_combinations_and_one_evaluation(beta,monkeypatch):
    _,a,b=beta;rid,key,_,_,_=create_beta(a,enabled=True);calls=[]
    original=beta_schedule._evaluate
    def counted(*args,**kw):calls.append(1);return original(*args,**kw)
    monkeypatch.setattr(beta_schedule,'_evaluate',counted)
    with client(a) as http:
        for path,reader in [(f'/v2/raid-rooms/{rid}/detail',None),(f'/v2/raid-rooms/{rid}/detail','application-display-1'),
                (f'/v2/raid-rooms/{rid}/detail','membership-actions-1'),(f'/v2/me/raid-rooms/{rid}/plan',None),
                (f'/v2/me/raid-rooms/{rid}/plan','membership-actions-1')]:
            query=dict(contract_profile='beta-recruitment-1',target_cycle_key=key)
            if reader:query['reader_profile']=reader
            for flag in [None,'false','true']:
                calls.clear();params=query|({'include_coordination_wait':flag} if flag else {})
                r=http.get(path,params=params);assert r.status_code==200,r.json()
                assert r.headers['cache-control']=='no-store'
                schedule=r.json()['data']['beta_schedule']
                assert ('coordination_wait' in schedule)==(flag=='true')
                if flag=='true':
                    assert schedule['coordination_wait']==dict(status='waiting_members',missing_members=1)
                    assert len(calls)==1
        path=f'/v2/raid-rooms/{rid}/detail'
        for params in [dict(target_cycle_key=key,include_coordination_wait='true'),
                dict(contract_profile='beta-recruitment-1',target_cycle_key=key,include_coordination_wait='yes')]:
            assert http.get(path,params=params).status_code==400
        assert http.get(f'/v2/raid-rooms/{rid}',params=dict(contract_profile='beta-recruitment-1',target_cycle_key=key,include_coordination_wait='true')).status_code==400
    with client(b) as http:
        result=http.get(f'/v2/me/raid-rooms/{rid}/plan',params=dict(contract_profile='beta-recruitment-1',target_cycle_key=key,include_coordination_wait='true'))
        assert result.status_code==403


def test_wait_legacy_and_historical_null_do_not_invent_metadata(beta):
    from tests.test_recruitment_cycle_commands import create_room
    from tests.test_membership_actions import run
    _,a,b=beta;ack=create_room(a);rid=uuid.UUID(ack['room_id']);key=ack['created_cycles'][0]['target_cycle_key']
    assert wait(a,rid,key) is None
    # A different user's beta creation avoids reusing the old creator's occupied ledger.
    rid,key,_,_,_=create_beta(b)
    with session() as db:
        cm=db.scalar(select(CycleMember).where(CycleMember.room_id==rid,CycleMember.user_id==b['uid']))
        mid,cid=str(cm.membership_id),str(cm.id)
    with beta_profile.using():run(b,rid,key,'dissolve_led_targets')
    with client(b) as http:
        result=http.get(f'/v2/raid-rooms/{rid}/detail',params=dict(contract_profile='beta-recruitment-1',target_cycle_key=key,
            reader_profile='membership-actions-1',include_coordination_wait='true',membership_id=mid,cycle_member_id=cid))
        assert result.status_code==200,result.json()
        assert result.json()['data']['content'] is None
        assert result.json()['data']['beta_schedule'] is None


def test_wait_read_database_failure_stays_error_not_no_candidate(beta,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from tests.test_recruitment_cycle_times import fingerprints
    engine,a,b=beta;rid,key,_,_,_=create_beta(a,enabled=True);before=fingerprints(engine)
    def unavailable(*args):raise OperationalError('synthetic unavailable',{},RuntimeError())
    monkeypatch.setattr(beta_schedule,'_evaluate',unavailable)
    with client(a) as http:
        path=f'/v2/raid-rooms/{rid}/detail'
        params=dict(contract_profile='beta-recruitment-1',target_cycle_key=key)
        assert http.get(path,params=params).status_code==200
        response=http.get(path,params=params|dict(include_coordination_wait='true'))
        assert response.status_code==503 and response.json()['error']['code']=='SERVICE_UNAVAILABLE'
    assert fingerprints(engine)==before


def test_wait_deadline_pending_and_explicit_unset_share_auto_candidate(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a,enabled=True)
    with session() as db:
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid));room=RecruitmentRoom
        value=beta_schedule.evaluate(db,db.get(room,rid),row,base-timedelta(minutes=20))
        assert value['status']=='pending' and value['missing_members'] is None
    # Both unset copies are valid all-available; the existing write confirms normally.
    beta_join(b,rid,key)
    assert wait(a,rid,key)['coordination_wait']['status']=='not_applicable'
    with beta_profile.using():
        detail=cycle_member_reads.detail(actor(a['uid']),rid,key)
        assert detail['data']['beta_schedule']['coordination_state']=='early_confirmed'


def test_missing_actual_participation_evidence_never_excludes_a_member_from_coordination(beta,monkeypatch):
    from app.raid_rooms.source_models import SessionParticipation
    _,a,b=beta;rid,key,_,_,_=create_beta(a,enabled=True)
    monkeypatch.setattr(beta_schedule,'initial',lambda *args,**kw:None)
    beta_join(b,rid,key)
    with session() as db,db.begin():
        cm=db.scalar(select(CycleMember).where(CycleMember.room_id==rid,CycleMember.user_id==b['uid']))
        part=db.scalar(select(SessionParticipation).where(SessionParticipation.room_id==rid,SessionParticipation.membership_id==cm.membership_id))
        part.state='ended';part.revision+=1
    assert wait(a,rid,key)['coordination_wait']['status']=='unavailable'
