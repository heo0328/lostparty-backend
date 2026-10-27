"""Future intent does not consume present raid ledger or time resources."""
import uuid
from datetime import date,timedelta
from sqlalchemy import select,func
from app.core.database import session
from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentAssignment as Assignment
from app.raid_rooms.source_models import ContinuationChoice as Choice,OpeningEvent,RoomSettings
from app.raid_rooms.weekly_links import WeeklyOccupancy
from tests.test_recruitment_completion import http,bundle
from tests.test_recruitment_admission import ready,sources,imported,people,worlds,post
from tests.test_recruitment_scheduling import plan
from tests.test_raid_room_http import err


def choices(http,w,rid):
    out=http.get(f'/v1/me/raid-rooms/{rid}/continuation-choices',headers=w['headers'])
    assert out.status_code==200,out.text
    return out.json()


def test_choices_are_future_only_exact_replacement_and_no_present_side_effects(ready,http):
    target,a,b,_=ready;rid=bundle(http,a);p=plan(http,a,rid);c=choices(http,a,rid)
    with session() as db:
        before=db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))
        own=db.scalar(select(Assignment).where(Assignment.room_id==uuid.UUID(rid)))
        ownership=own.ownership_revision
    body=dict(target_cycle=c['target_cycle'],expected_membership_revision=c['membership_revision'],expected_choices_revision=c['revision'],
        choices=[dict(item_id=i['item_id'],character_id=a['ids'][0],selected_role='dealer',expected_ownership_revision=ownership) for i in p['game_items']],replaces=[])
    out=http.put(f'/v1/me/raid-rooms/{rid}/continuation-choices',json=body,headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())})
    assert out.status_code==200,out.text
    with session() as db:
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==before
        assert db.scalar(select(func.count()).select_from(Choice).where(Choice.room_id==uuid.UUID(rid),Choice.ended_at.is_(None)))==2
    c=choices(http,a,rid);body.update(expected_membership_revision=c['membership_revision'],expected_choices_revision=c['revision'],choices=[])
    err(http.put(f'/v1/me/raid-rooms/{rid}/continuation-choices',json=body,headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())}),409,'REVISION_CONFLICT')
    body['replaces']=[dict(choice_id=i['choice_id'],revision=i['revision']) for i in c['items']]
    out=http.put(f'/v1/me/raid-rooms/{rid}/continuation-choices',json=body,headers={**a['headers'],'Idempotency-Key':str(uuid.uuid4())})
    assert out.status_code==200,out.text
    assert choices(http,a,rid)['items']==[]


def test_opening_same_cycle_noop_preserves_authority_floor(ready,http):
    target,a,b,_=ready;rid=bundle(http,a);p=plan(http,a,rid)
    with session() as db:
        r=db.get(Room,uuid.UUID(rid));s=db.get(RoomSettings,r.id)
        body=dict(target_cycle=p['cycle_key'],expected_room_revision=r.revision,expected_continuation_revision=s.continuation_revision)
        before=[(e.id,e.authorized_effective_at,e.search_floor_at,e.processed_at) for e in db.scalars(select(OpeningEvent).where(OpeningEvent.room_id==r.id))]
    out=post(http,a,f'raid-rooms/{rid}/recruitment-openings',body)
    assert out.status_code==200,out.text
    assert out.json()['outcome']=='noop'
    with session() as db:
        assert [(e.id,e.authorized_effective_at,e.search_floor_at,e.processed_at) for e in db.scalars(select(OpeningEvent).where(OpeningEvent.room_id==uuid.UUID(rid)))]==before


def test_late_automatic_opening_uses_boundary_authority_not_worker_clock(ready,http,monkeypatch):
    from app.raid_rooms import continuation,scheduling,participation_core
    from app.raids import service as raids
    from app.raid_rooms.integrated_models import RecruitmentRound as Round
    from datetime import datetime,timezone
    target,a,b,_=ready;rid=bundle(http,a);p=plan(http,a,rid);c=choices(http,a,rid)
    with session() as db,db.begin():
        room=db.get(Room,uuid.UUID(rid));settings=db.get(RoomSettings,room.id);settings.auto_open_enabled=True
        settings.auto_open_effective_cycle=date.fromisoformat(c['target_cycle'])
        own=db.scalar(select(Assignment).where(Assignment.room_id==room.id))
        for item in p['game_items']:
            db.add(Choice(id=uuid.uuid4(),room_id=room.id,item_id=uuid.UUID(item['item_id']),membership_id=own.membership_id,user_id=a['uid'],character_id=own.character_id,raid_id=item['raid_id'],selected_role='dealer',ownership_revision=own.ownership_revision,target_cycle=settings.auto_open_effective_cycle,revision=1,state='selected'))
    boundary=datetime.combine(date.fromisoformat(c['target_cycle']),datetime.min.time(),raids.KST).replace(hour=6).astimezone(timezone.utc)
    delayed=boundary+timedelta(hours=6)
    for module in (continuation,scheduling,participation_core):monkeypatch.setattr(module,'now',lambda db:delayed)
    continuation.process_due()
    with session() as db:
        events=list(db.scalars(select(OpeningEvent).where(OpeningEvent.room_id==uuid.UUID(rid),OpeningEvent.target_cycle==date.fromisoformat(c['target_cycle']))))
        assert len(events)==2 and all(e.state=='applied' for e in events)
        assert all(e.authorized_effective_at==boundary and e.search_floor_at==boundary+timedelta(minutes=30) and e.processed_at==delayed for e in events)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==2
        assert {r.state for r in db.scalars(select(Round).where(Round.room_id==uuid.UUID(rid),Round.cycle_key==date.fromisoformat(p['cycle_key'])))}=={'stopped_incomplete'}
    continuation.process_due()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(OpeningEvent).where(OpeningEvent.room_id==uuid.UUID(rid),OpeningEvent.target_cycle==date.fromisoformat(c['target_cycle'])))==2


def test_blocked_auto_open_retry_keeps_original_boundary_floor(ready,http,monkeypatch):
    from app.raid_rooms import continuation,scheduling,participation_core
    from app.raids import service as raids
    from datetime import datetime,timezone
    target,a,b,_=ready;rid=bundle(http,a);p=plan(http,a,rid);next_cycle=date.fromisoformat(p['cycle_key'])+timedelta(days=7)
    with session() as db,db.begin():
        value=db.get(RoomSettings,uuid.UUID(rid));value.auto_open_enabled=True;value.auto_open_effective_cycle=next_cycle
    boundary=datetime.combine(next_cycle,datetime.min.time(),raids.KST).replace(hour=6).astimezone(timezone.utc)
    clock=[boundary+timedelta(hours=6)]
    for module in (continuation,scheduling,participation_core):monkeypatch.setattr(module,'now',lambda db:clock[0])
    continuation.process_due();clock[0]+=timedelta(hours=1);continuation.process_due()
    with session() as db:
        events=list(db.scalars(select(OpeningEvent).where(OpeningEvent.room_id==uuid.UUID(rid),OpeningEvent.target_cycle==next_cycle)))
        assert len(events)==2 and all(e.state=='blocked' and e.blocked_reason=='LEADER_CONTINUATION_REQUIRED' for e in events)
        assert all(e.authorized_effective_at==boundary and e.search_floor_at==boundary+timedelta(minutes=30) and e.processed_at==clock[0] for e in events)
        assert db.scalar(select(func.count()).select_from(WeeklyOccupancy).where(WeeklyOccupancy.room_id==uuid.UUID(rid)))==0
