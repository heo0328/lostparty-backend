"""One authoritative blocker set shared by group disband and member room listing."""
from datetime import date, timedelta
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.lifecycle import digest
from app.groups import display, service as groups
from app.groups.models import GroupMembership
from app.raid_rooms import completed_room_lifecycle as archive, cycle_admission
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member, RecruitmentAssignment as Assignment, RecruitmentItem as Item
from app.raid_rooms.cycle_models import RoomCycle, CycleGeneration, CycleMember, CycleAssignment
from app.raids import service as raids


def evaluate(db, group, stamp):
    from app.raid_rooms import cycle_group_policy as policy
    from app.raid_rooms.cycle_group_models import CycleGroupPolicy
    selected=select(Room).where(Room.ended_at.is_(None))
    if policy.enabled(db):
        match=select(RoomCycle.id).join(CycleGroupPolicy,(CycleGroupPolicy.cycle_id==RoomCycle.id)&
            (CycleGroupPolicy.generation==RoomCycle.generation)).where(RoomCycle.room_id==Room.id,
            RoomCycle.state.in_(('open','review_required')),CycleGroupPolicy.group_id==group.id).exists()
        unknown=select(RoomCycle.id).where(RoomCycle.room_id==Room.id,RoomCycle.state.in_(('open','review_required')),
            ~select(CycleGroupPolicy.cycle_id).where(CycleGroupPolicy.cycle_id==RoomCycle.id,
                CycleGroupPolicy.generation==RoomCycle.generation).exists()).exists()
        selected=selected.where(match | ((Room.group_id==group.id)&unknown))
    else:selected=selected.where(Room.group_id==group.id,Room.scope=='group')
    rooms=list(db.scalars(selected.order_by(Room.created_at.desc(),Room.id.desc())))
    current = date.fromisoformat(raids.cycle(stamp).cycle_key)
    items, evidence, unavailable = [], [], False
    if policy.enabled(db):
        # A missing generation policy has no group attribution. Do not treat
        # that loss of evidence as proof that this group has zero blockers.
        unresolved=db.scalar(select(RoomCycle.id).join(Room,Room.id==RoomCycle.room_id).where(
            Room.ended_at.is_(None),RoomCycle.state.in_(('open','review_required')),
            RoomCycle.provenance=='explicit',RoomCycle.generation.is_not(None),
            ~select(CycleGroupPolicy.cycle_id).where(CycleGroupPolicy.cycle_id==RoomCycle.id,
                CycleGroupPolicy.generation==RoomCycle.generation).exists()).limit(1))
        if unresolved is not None:
            unavailable=True;evidence.append(['unresolved-active-group-policy'])
    for room in rooms:
        if archive.is_archived(db, room.id):
            evidence.append([room.id, room.revision, 'archived'])
            continue
        cycles = list(db.scalars(select(RoomCycle).where(RoomCycle.room_id == room.id).order_by(RoomCycle.cycle_key)))
        item_ids = set(db.scalars(select(Item.id).where(Item.room_id == room.id)))
        unknown = room.migration_state != 'ready' or not cycles or not item_ids
        targets = []
        for row in cycles:
            if policy.enabled(db):
                if row.state not in ('open','review_required'):continue
                value=policy.get(db,row,required=False)
                if value is None:
                    unknown=True
                    continue  # No group attribution: expose no target/leader data.
                if value.group_id!=group.id:continue
            gen = db.get(CycleGeneration, (row.id, row.generation)) if row.generation is not None else None
            links = cycle_admission.rounds(db, row) if gen is not None else []
            unknown = (unknown or row.provenance != 'explicit' or row.state == 'review_required' or gen is None
                or gen.state == 'review_required' or {i.id for i, _ in links} != item_ids or len(links) != len(item_ids)
                or any(rd.room_id != room.id or rd.cycle_key != row.cycle_key for _, rd in links))
            leader = db.get(CycleMember, gen.leader_cycle_member_id) if gen and gen.leader_cycle_member_id else None
            membership = db.get(Member, leader.membership_id) if leader else None
            shown = None
            if membership:
                stored = db.scalar(select(Assignment.display).join(CycleAssignment, CycleAssignment.assignment_id == Assignment.id)
                    .where(CycleAssignment.cycle_member_id == leader.id, CycleAssignment.cycle_id == row.id,
                        CycleAssignment.generation == row.generation).order_by(Assignment.item_id).limit(1))
                shown = groups.display(stored)
            targets.append(dict(room_cycle_id=row.id, target_cycle_key=row.cycle_key, generation=row.generation,
                target_revision=row.revision, state=row.state, leader_display=shown,
                detail_available=row.cycle_key in (current, current+timedelta(days=7)) and row.generation is not None))
            evidence.append([row.id, row.revision, row.generation, row.state,
                gen.state if gen else None, gen.leadership_revision if gen else None,
                leader.id if leader else None, leader.revision if leader else None, shown])
        if policy.enabled(db) and not targets and not unknown:continue
        unavailable = unavailable or unknown
        items.append(dict(room_id=room.id, title=room.title, scope='group', group_id=group.id,
            room_revision=room.revision, state='review_required' if unknown else 'active',
            reason='GROUP_RECRUITMENT_STATE_UNAVAILABLE' if unknown else None, targets=targets))
    state = 'unavailable' if unavailable else 'blocked' if items else 'clear'
    revision = digest(jsonable_encoder([group.revision, group.members_revision, current, items, evidence]))
    return dict(state=state, blocking_room_count=None if unavailable else len(items), evidence_revision=revision), items


def listing(principal, gid, limit, cursor):
    with display.snapshot(principal) as (db, uid, stamp):
        group = groups.group(db, gid); own = groups.member(db, uid, group)
        result, rows = evaluate(db, group, stamp)
        items, following, _ = display.paginate(principal, 'group-raid-rooms', rows,
            [result, own.id, own.revision], limit, cursor, group_id=str(gid))
        return display.bounded(dict(group_id=gid, group_revision=group.revision, members_revision=group.members_revision,
            evaluated_at=stamp, **result, items=items, next_cursor=following))
