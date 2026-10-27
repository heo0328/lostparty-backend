"""Current C/N participation, shared by lists and transaction-owned quota checks."""
from datetime import date, timedelta
import uuid
from sqlalchemy import select, func, and_, or_, text
from app.core.database import now
from app.raid_rooms.cycle_models import RoomCycle, CycleMember
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member
from app.raid_rooms.completed_room_lifecycle import archived
from app.member_limits.models import MemberUsageHead, MemberUsageLimits
from app.game_accounts.support import fail

POLICY='active-target-rooms-1'


def enabled(db):
    if 'active_usage_ready' not in db.info:
        # Pre-cutover isolated fixtures keep their original non-cycle policy.
        db.info['active_usage_ready']=db.scalar(text("SELECT to_regclass('public.recruitment_room_cycles')")) is not None
    return db.info['active_usage_ready']


def stamp(db):
    return db.info['active_usage_stamp'] if 'active_usage_stamp' in db.info else now(db)


def predicate(member=Member, room=Room, target=RoomCycle, actual=CycleMember):
    return and_(member.ended_at.is_(None),room.ended_at.is_(None),~archived(room.id),
        actual.state.in_(('participating','review_required')),target.state.in_(('open','review_required')),
        or_(actual.generation==target.generation,and_(actual.generation.is_(None),target.generation.is_(None))))


def query(uids, at):
    from app.raids.service import cycle
    current=date.fromisoformat(cycle(at).cycle_key)
    return select(Member.user_id,Member.room_id).join(Room,Room.id==Member.room_id).join(RoomCycle,RoomCycle.room_id==Room.id).join(
        CycleMember,and_(CycleMember.cycle_id==RoomCycle.id,CycleMember.membership_id==Member.id)).where(
        Member.user_id.in_(list(uids)),RoomCycle.cycle_key.in_((current,current+timedelta(days=7))),predicate()).distinct()


def count(db,uid):
    return db.scalar(select(func.count()).select_from(query([uid],stamp(db)).subquery()))


def contains(db,uid,rid):
    return bool(db.scalar(query([uid],stamp(db)).where(Member.room_id==rid).exists().select()))


def capture(db,uid,rid,payload):
    uids={uid}
    if rid is not None:
        uids.update(db.scalars(select(Member.user_id).where(Member.room_id==rid,Member.ended_at.is_(None))))
    if payload.get('application_id'):
        from app.raid_rooms.cycle_application_models import CycleApplication
        app=db.get(CycleApplication,uuid.UUID(str(payload['application_id'])))
        if app is not None:uids.add(app.user_id)
    rooms={u:set() for u in uids}
    for u,r in db.execute(query(uids,stamp(db))):rooms[u].add(r)
    revisions=dict(db.execute(select(MemberUsageHead.user_id,MemberUsageHead.revision).where(MemberUsageHead.user_id.in_(uids))).all())
    return rooms,{u:revisions.get(u,1) for u in uids}


def finish(db,before):
    from app.member_limits.service import values
    rooms,revisions=before;after={u:set() for u in rooms}
    for u,r in db.execute(query(rooms,stamp(db))):after[u].add(r)
    for uid,old in rooms.items():
        current=after[uid]
        if current==old:continue
        if current-old and len(current)>values(db.get(MemberUsageLimits,uid)).raid_rooms:
            fail('MEMBER_RAID_LIMIT_REACHED')
        head=db.get(MemberUsageHead,uid)
        if (head.revision if head else 1)==revisions[uid]:
            if head is None:db.add(MemberUsageHead(user_id=uid,revision=2))
            else:head.revision+=1
