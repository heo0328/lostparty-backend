"""Whole-minute search ranges, using disposable PostgreSQL and synthetic HTTP."""
import json
import uuid
from datetime import date,datetime,time,timedelta,timezone
import pytest
from sqlalchemy import select,inspect
from app.core.database import session
from app.game_accounts.support import GameError
from app.raid_rooms import beta_schemas,beta_schedule,beta_profile,time_policy,cycle_member_reads,cycle_schedule_service,cycle_schemas
from app.raid_rooms.beta_models import BetaSchedule
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.integrated_models import RecruitmentSession
from app.raid_rooms.router import optional_principal
from app.raids.service import KST
from tests.test_beta_recruitment import beta,current,candidate,ready,sources,imported,people,worlds,create_beta,PROFILE,actor,client
from tests.test_raid_room_migrations import table_digests


def window(start,end):return dict(starts_at=start.isoformat(),ends_at=end.isoformat())


def search(http,key,windows,*,method='get',limit=20,cursor=None):
    if method=='get':
        params={**PROFILE,'target_cycle_key':key,'departure_windows':json.dumps(windows),'limit':limit}
        if cursor:params['cursor']=cursor
        return http.get('/v2/raid-rooms',params=params)
    body=dict(category='all',admission_scope='public',group_ids=[],filter_context_token=None,member_conditions=[],
        raid_ids=[],difficulty_ids=[],limit=limit,cursor=cursor,target_cycle_key=key,departure_windows=windows)
    return http.post('/v2/raid-rooms/search',params=PROFILE,json=body)


def ids(response):
    assert response.status_code==200,response.json()
    return [v['room_id'] for v in response.json()['data']['items']]


def move(rid,key,start,*,confirmed=False,effective=None):
    with session() as db,db.begin():
        target=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        saved=db.get(BetaSchedule,target.id);sess=db.get(RecruitmentSession,saved.session_id)
        duration=saved.base_ends_at-saved.base_starts_at
        saved.base_starts_at=start;saved.base_ends_at=start+duration
        sess.starts_at=effective or start;sess.ends_at=sess.starts_at+duration
        if confirmed:saved.confirmation_kind='early_confirmed';sess.state='confirmed'


def test_minute_search_get_post_exact_boundaries_and_read_only(beta):
    engine,a,b=beta;rid,key,base,_,_=create_beta(a)
    tables=set(inspect(engine).get_table_names())-{'alembic_version'};before=table_digests(engine,tables)
    with client(b) as http:
        for method in ['get','post']:
            for start,end,expected in [(base-timedelta(minutes=2),base+timedelta(minutes=2),[str(rid)]),
                    (base,base+timedelta(minutes=1),[str(rid)]),
                    (base-timedelta(minutes=1),base,[]),
                    (base+timedelta(minutes=1),base+timedelta(minutes=4),[]),
                    (base,base+timedelta(minutes=5),[str(rid)])]:
                assert ids(search(http,key,[window(start,end)],method=method))==expected
    assert table_digests(engine,tables)==before


def test_minute_search_midnight_cycle_edges_and_effective_departure(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a,combined=True)
    first=datetime.combine(date.fromisoformat(key),time(6),KST).astimezone(timezone.utc)
    last=first+timedelta(days=7);midnight=first+timedelta(days=1,hours=18)
    with client(b) as http:
        for method in ['get','post']:
            move(rid,key,midnight)
            assert ids(search(http,key,[window(midnight-timedelta(minutes=2),midnight+timedelta(minutes=3))],method=method))==[str(rid)]
            move(rid,key,first)
            assert ids(search(http,key,[window(first,first+timedelta(minutes=1))],method=method))==[str(rid)]
            move(rid,key,last-timedelta(minutes=5))
            assert ids(search(http,key,[window(last-timedelta(minutes=7),last)],method=method))==[str(rid)]
            # A confirmed session is searched at its actual departure, not its base.
            move(rid,key,base,confirmed=True,effective=base-timedelta(minutes=10))
            assert ids(search(http,key,[window(base-timedelta(minutes=12),base-timedelta(minutes=8))],method=method))==[str(rid)]
            assert ids(search(http,key,[window(base-timedelta(minutes=2),base+timedelta(minutes=2))],method=method))==[]
        next_key=(date.fromisoformat(key)+timedelta(days=7)).isoformat()
        next_start=last+timedelta(hours=4)
        move(rid,next_key,next_start)
        assert ids(search(http,next_key,[window(next_start-timedelta(minutes=2),next_start+timedelta(minutes=2))]))==[str(rid)]


def test_minute_search_invalid_bounds_and_write_grid_preserved(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a)
    first=datetime.combine(date.fromisoformat(key),time(6),KST).astimezone(timezone.utc);last=first+timedelta(days=7)
    pairs=[(base+timedelta(seconds=1),base+timedelta(minutes=2)),
        (base,base+timedelta(minutes=2,microseconds=1)),
        (base.astimezone(KST),base+timedelta(minutes=2)),
        (base.replace(tzinfo=None),base+timedelta(minutes=2)),(base,base),(base+timedelta(minutes=1),base),
        (first,first+timedelta(days=1,minutes=1)),(first-timedelta(minutes=1),first+timedelta(minutes=1)),
        (last-timedelta(minutes=1),last+timedelta(minutes=1))]
    with client(b) as http:
        for method in ['get','post']:
            for start,end in pairs:
                result=search(http,key,[window(start,end)],method=method)
                assert result.status_code==400,result.json()
                assert result.json()['error']['code']=='INVALID_REQUEST'
            assert ids(search(http,key,[window(first,first+timedelta(days=1))],method=method))==([str(rid)] if first<=base<first+timedelta(days=1) else [])
    assert time_policy.TICK==timedelta(minutes=5)
    assert not time_policy.aligned(base+timedelta(minutes=1))
    with pytest.raises(GameError,match='INVALID_REQUEST'):
        time_policy.interval(base+timedelta(minutes=1),base+timedelta(minutes=31),key)


def test_minute_search_union_before_pagination_and_cursor_binding(beta):
    _,a,b=beta;rid,key,base,_,_=create_beta(a);second,_,_,_,_=create_beta(b)
    move(second,key,base+timedelta(minutes=10))
    with client(a) as http:
        http.app.dependency_overrides[optional_principal]=lambda:None
        narrow=[window(base-timedelta(minutes=2),base+timedelta(minutes=2))]
        assert ids(search(http,key,narrow,limit=1))==[str(rid)]  # Newer nonmatching room cannot occupy page 1.
        windows=[window(base-timedelta(minutes=2),base+timedelta(minutes=2)),
            window(base+timedelta(minutes=1),base+timedelta(minutes=12))]
        for method in ['get','post']:
            page=search(http,key,windows,method=method,limit=1);first_ids=ids(page)
            cursor=page.json()['data']['next_cursor'];assert cursor
            other=search(http,key,list(reversed(windows)),method=method,limit=1,cursor=cursor)
            assert set(first_ids+ids(other))=={str(rid),str(second)}
            assert other.json()['data']['next_cursor'] is None
            changed=[window(base-timedelta(minutes=3),base+timedelta(minutes=12))]
            rejected=search(http,key,changed,method=method,limit=1,cursor=cursor)
            assert rejected.status_code==409 and rejected.json()['error']['code']=='CURSOR_STALE'
