"""Read-only service archive predicate, shared before pagination and every new write."""
import uuid
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import aliased
from app.game_accounts.support import fail
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleRound, CycleMember
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentRound as Round, RecruitmentAssignment as Assignment, RecruitmentItem as Item


def archived(room_id):
    """All item evidence completed, no later live/unknown/stopped actual cycle.

    Completed assignment evidence is historical fact; a personal correction does
    not rewrite it. No weekly source/participant count substitutes for that fact.
    """
    row=aliased(RoomCycle);gen=aliased(CycleGeneration);later=aliased(RoomCycle);later_gen=aliased(CycleGeneration)
    link=aliased(CycleRound);rd=aliased(Round);a=aliased(Assignment);item=aliased(Item)
    completed=select(a.id).where(a.round_id==rd.id,a.state=='completed').correlate(rd).exists()
    unfinished=select(a.id).where(a.round_id==rd.id,a.state.in_(('active','stopped_incomplete'))).correlate(rd).exists()
    links=select(link.round_id).where(link.cycle_id==row.id,link.generation==row.generation,link.is_current.is_(True)).correlate(row)
    bad=select(link.round_id).join(rd,rd.id==link.round_id).where(link.cycle_id==row.id,link.generation==row.generation,
        link.is_current.is_(True),~or_(rd.state=='completed',and_(rd.state=='active',completed,~unfinished))).correlate(row).exists()
    missing=select(item.id).where(item.room_id==row.room_id,~select(link.round_id).where(link.cycle_id==row.id,
        link.generation==row.generation,link.item_id==item.id,link.is_current.is_(True)).correlate(row,item).exists()).correlate(row).exists()
    blocked=select(later.id).outerjoin(later_gen,and_(later_gen.cycle_id==later.id,later_gen.generation==later.generation)).where(
        later.room_id==row.room_id,later.cycle_key>row.cycle_key,
        or_(later.state.in_(('open','review_required')),later_gen.state=='stopped')).correlate(row).exists()
    return select(row.id).join(gen,and_(gen.cycle_id==row.id,gen.generation==row.generation)).where(
        row.room_id==room_id,row.provenance=='explicit',row.state=='closed',gen.state=='completed',
        links.exists(),~bad,~missing,~blocked).correlate_except(row,gen).exists()


def is_archived(db,rid):return bool(db.scalar(select(archived(rid))))


def require_active(db,rid):
    room=db.get(Room,rid)
    if room is not None and (room.ended_at is not None or is_archived(db,rid)):fail('ROOM_NOT_ACTIVE')


def mutation_room(db,payload):
    """Resolve all existing command envelope identifiers, never parse token data."""
    from app.raid_rooms.source_models import ScheduleGroup, ScheduleProposal
    from app.raid_rooms.integrated_models import RecruitmentSession
    from app.raid_rooms.cycle_application_models import CycleApplication
    raw=payload.get('room_id')
    if raw:return uuid.UUID(str(raw))
    for field,model in [('round_id',Round),('session_id',RecruitmentSession),('proposal_id',ScheduleProposal),('group_id',ScheduleGroup),('application_id',CycleApplication)]:
        if payload.get(field):
            obj=db.get(model,uuid.UUID(str(payload[field])))
            if obj is not None:return obj.room_id
    return None


def permissions(value):
    """Override only executable permissions; record access stays explicit."""
    for name in value:
        if name not in ('view_detail','view_plan'):
            value[name]=dict(allowed=False,reason='ROOM_NOT_ACTIVE',next_change_at=None)
