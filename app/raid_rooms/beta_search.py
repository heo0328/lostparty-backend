"""Beta effective departure/state predicates applied before ordering/pagination."""
from datetime import datetime,timedelta
from sqlalchemy import select,case,and_,or_,literal
from sqlalchemy.orm import aliased
from app.game_accounts.support import fail
from app.raid_rooms import beta_profile,beta_schedule
from app.raid_rooms.beta_models import BetaSchedule
from app.raid_rooms.cycle_models import RoomCycle
from app.raid_rooms.cycle_application_models import CycleSession
from app.raid_rooms.integrated_models import RecruitmentSession
from app.raid_rooms.source_models import SessionBinding
from app.raid_rooms.schedule_heads import ScheduleHead
from app.raids.service import KST


def minute_boundary(stamp):
    # Search bounds describe a range, independently of the departure grid.
    return stamp.tzinfo is not None and stamp.utcoffset()==timedelta(0) and stamp.second==0 and stamp.microsecond==0


def apply(db,query,data,body,target,stamp):
    if not beta_schedule.available(db):fail('RECRUITMENT_COMMAND_NOT_READY',503)
    windows=getattr(data,'departure_windows',None)
    states=getattr(data,'schedule_states',None)
    if states and len(set(states))!=len(states):fail('INVALID_REQUEST',400)
    first=datetime.combine(target.key,datetime.min.time(),KST)+timedelta(hours=6)
    last=first+timedelta(days=7)
    normalized=[]
    for window in windows or []:
        start,end=window.starts_at,window.ends_at
        if not minute_boundary(start) or not minute_boundary(end) or not timedelta(0)<end-start<=timedelta(days=1):fail('INVALID_REQUEST',400)
        if start<first or end>last:fail('INVALID_REQUEST',400)
        normalized.append((start,end))
    merged=[]
    for start,end in sorted(normalized):
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    if windows is not None:body['departure_windows']=[dict(starts_at=a.isoformat(),ends_at=b.isoformat()) for a,b in merged]
    if states is not None:body['schedule_states']=sorted(states)
    current=aliased(RecruitmentSession)
    query=query.outerjoin(BetaSchedule,and_(BetaSchedule.cycle_id==RoomCycle.id,BetaSchedule.generation==RoomCycle.generation)).outerjoin(current,current.id==BetaSchedule.session_id)
    state=case((BetaSchedule.cycle_id.is_(None),'legacy'),
        (current.state.in_(('finished','cancelled')),'ended'),
        (BetaSchedule.confirmation_kind.is_not(None),BetaSchedule.confirmation_kind),
        (BetaSchedule.needs_review,'needs_review'),
        (BetaSchedule.base_starts_at<=stamp+timedelta(minutes=30),'deadline_pending'),
        (BetaSchedule.early_enabled,'coordinating'),else_='base_committed')
    effective=case((BetaSchedule.confirmation_kind.is_not(None),current.starts_at),else_=BetaSchedule.base_starts_at)
    if states:query=query.where(state.in_(states))
    if merged:
        legacy=select(RecruitmentSession.id).join(CycleSession,CycleSession.session_id==RecruitmentSession.id).join(
            SessionBinding,SessionBinding.session_id==RecruitmentSession.id).join(ScheduleHead,ScheduleHead.group_id==SessionBinding.group_id).where(
                CycleSession.cycle_id==RoomCycle.id,CycleSession.generation==RoomCycle.generation,
                ScheduleHead.active.is_(True),RecruitmentSession.state=='confirmed',
                or_(*(and_(RecruitmentSession.starts_at>=a,RecruitmentSession.starts_at<b) for a,b in merged))).correlate(RoomCycle).exists()
        query=query.where(or_(and_(BetaSchedule.cycle_id.is_not(None),or_(*(and_(effective>=a,effective<b) for a,b in merged))),and_(BetaSchedule.cycle_id.is_(None),legacy)))
    # Clock-driven read projection can change before the worker bumps the head.
    # Bind cursors to that deterministic due set as well as the normal directory.
    due=list(db.scalars(select(BetaSchedule.cycle_id).join(RoomCycle,RoomCycle.id==BetaSchedule.cycle_id).where(
        RoomCycle.cycle_key==target.key,BetaSchedule.confirmation_kind.is_(None),
        BetaSchedule.needs_review.is_(False),BetaSchedule.base_starts_at<=stamp+timedelta(minutes=30)).order_by(BetaSchedule.cycle_id)))
    return query,[beta_profile.PROFILE,list(map(str,due))]
