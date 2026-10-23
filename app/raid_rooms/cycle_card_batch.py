"""Request-local directory projections. Never cache a member's visibility.

The caller selects/filters/pages RoomCycle rows inside its read-only snapshot
before loading these bounded relations. Single-card reads retain their path.
"""
from collections import defaultdict
from sqlalchemy import select, func, and_
from app.game_accounts.support import fail
from app.raid_rooms.cycle_models import CycleGeneration, CycleMember, CycleAssignment, CycleRound, RoomCycle
from app.raid_rooms.cycle_application_models import CycleSession
from app.raid_rooms.cycle_lifecycle_models import CycleScheduleGroup
from app.raid_rooms.integrated_models import (RecruitmentMembership as Member,
    RecruitmentAssignment as Assignment, RecruitmentItem as Item, RecruitmentRound as Round,
    RecruitmentSession as Session)
from app.raid_rooms.source_models import ScheduleGroup, SessionBinding
from app.raid_rooms.schedule_heads import ScheduleHead
from app.raid_rooms.weekly_links import WeeklyOccupancy


def load(db, rows, uid):
    if not rows:return {}
    ids=[row.id for row in rows]
    # Every join to an actual graph is scoped to the selected generation.
    current=and_(CycleGeneration.cycle_id==RoomCycle.id,CycleGeneration.generation==RoomCycle.generation)
    generations={g.cycle_id:g for g in db.scalars(select(CycleGeneration).join(RoomCycle,current).where(RoomCycle.id.in_(ids)))}
    leader_ids=[g.leader_cycle_member_id for g in generations.values() if g.leader_cycle_member_id]
    leaders={m.id:m for m in db.scalars(select(CycleMember).where(CycleMember.id.in_(leader_ids)))} if leader_ids else {}
    displays={}
    if leader_ids:
        # A resumed member can have many historical assignments. Read only the
        # same first display as the single-card projection, not the full history.
        first_display=select(Assignment.display).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).where(
            CycleAssignment.cycle_member_id==CycleMember.id).order_by(Assignment.id).limit(1).correlate(CycleMember).scalar_subquery()
        displays=dict(db.execute(select(CycleMember.id,first_display).where(CycleMember.id.in_(leader_ids))).all())
    own={}
    if uid:
        for cm in db.scalars(select(CycleMember).join(RoomCycle,and_(RoomCycle.id==CycleMember.cycle_id,
                RoomCycle.generation==CycleMember.generation)).join(Member,Member.id==CycleMember.membership_id).where(
                RoomCycle.id.in_(ids),CycleMember.user_id==uid,Member.ended_at.is_(None),
                CycleMember.state.in_(('participating','completed','stopped','review_required')))):
            own.setdefault(cm.cycle_id,cm)
    counts=dict(db.execute(select(CycleRound.cycle_id,func.count(func.distinct(Assignment.membership_id))).join(
        RoomCycle,and_(RoomCycle.id==CycleRound.cycle_id,RoomCycle.generation==CycleRound.generation)).join(
        Assignment,Assignment.round_id==CycleRound.round_id).join(WeeklyOccupancy,WeeklyOccupancy.assignment_id==Assignment.id).where(
        RoomCycle.id.in_(ids),CycleRound.is_current.is_(True),Assignment.state=='active').group_by(CycleRound.cycle_id)).all())
    items=defaultdict(list)
    for cid,item,rd in db.execute(select(CycleRound.cycle_id,Item,Round).join(Item,and_(
            CycleRound.item_id==Item.id,CycleRound.room_id==Item.room_id)).join(Round,Round.id==CycleRound.round_id).join(
            RoomCycle,and_(RoomCycle.id==CycleRound.cycle_id,RoomCycle.generation==CycleRound.generation)).where(
            RoomCycle.id.in_(ids),CycleRound.is_current.is_(True)).order_by(Item.id)):
        items[cid].append(dict(item_id=item.id,raid_id=item.raid_id,difficulty_id=rd.difficulty_id,game_party_size=rd.game_party_size,round_id=rd.id))
    groups=defaultdict(list)
    if any(row.generation==1 for row in rows):
        query=select(RoomCycle.id,ScheduleGroup).join(ScheduleGroup,and_(ScheduleGroup.room_id==RoomCycle.room_id,
            ScheduleGroup.cycle_key==RoomCycle.cycle_key)).join(ScheduleHead,ScheduleHead.group_id==ScheduleGroup.id).where(
            RoomCycle.id.in_(ids),RoomCycle.generation==1,ScheduleHead.active.is_(True))
        for cid,group in db.execute(query):groups[cid].append(group)
    if any(row.generation>1 for row in rows):
        query=select(RoomCycle.id,ScheduleGroup).join(CycleScheduleGroup,and_(CycleScheduleGroup.cycle_id==RoomCycle.id,
            CycleScheduleGroup.generation==RoomCycle.generation)).join(ScheduleGroup,ScheduleGroup.id==CycleScheduleGroup.group_id).join(
            ScheduleHead,ScheduleHead.group_id==ScheduleGroup.id).where(RoomCycle.id.in_(ids),RoomCycle.generation>1,ScheduleHead.active.is_(True))
        for cid,group in db.execute(query):groups[cid].append(group)
    starts=defaultdict(list)
    for cid,start in db.execute(select(CycleSession.cycle_id,Session.starts_at).join(Session,Session.id==CycleSession.session_id).join(
            RoomCycle,and_(RoomCycle.id==CycleSession.cycle_id,RoomCycle.generation==CycleSession.generation)).join(
            SessionBinding,SessionBinding.session_id==Session.id).join(ScheduleHead,ScheduleHead.group_id==SessionBinding.group_id).where(
            RoomCycle.id.in_(ids),ScheduleHead.active.is_(True),Session.state=='confirmed').order_by(Session.id)):
        starts[cid].append(start)
    from app.raid_rooms import completed_room_lifecycle as archive
    archived_ids=set(db.scalars(select(RoomCycle.room_id).where(RoomCycle.id.in_(ids),archive.archived(RoomCycle.room_id))))
    result={}
    for row in rows:
        gen=generations.get(row.id);leader=leaders.get(gen.leader_cycle_member_id) if gen else None
        if gen is None or (leader is None and gen.state!='cancelled'):fail('ROOM_REVIEW_REQUIRED')
        leadership=dict(leader_cycle_member_id=leader.id if leader else None,leadership_revision=gen.leadership_revision,
            leader_membership_id=leader.membership_id if leader else None)
        mine=own.get(row.id)
        role='none' if mine is None else 'leader' if mine.id==leadership['leader_cycle_member_id'] else 'member'
        result[row.id]=dict(archived=row.room_id in archived_ids,leadership=leadership,leader_display=displays.get(gen.leader_cycle_member_id),
            groups=groups[row.id],starts=starts[row.id],items=items[row.id],count=counts.get(row.id,0),role=role,
            state={'cancelled':'cancelled','completed':'completed','stopped':'stopped_incomplete','review_required':'review_required'}.get(gen.state,'open'))
    return result
