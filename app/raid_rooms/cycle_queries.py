"""Read-only target directory. All predicates run in SQL before pagination."""
from datetime import timedelta
from sqlalchemy import select, func, or_
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail, cursor_encode, cursor_decode
from app.game_accounts.lifecycle import digest
from app.groups.models import Group, GroupMembership
from app.raid_rooms.queries import snapshot
from app.raid_rooms import cycles, cycle_admission as admission, cycle_schedule as schedule, search as filters
from app.raid_rooms import cycle_commands as commands, cycle_wire as wire
from app.raid_rooms.cycle_creation import scope, permission
from app.raid_rooms.cycle_models import RoomCycle, CycleMember, CycleRound, CycleAssignment
from app.raid_rooms.integrated_models import RecruitmentRoom as Room, RecruitmentMembership as Member, RecruitmentAssignment as Assignment
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_rooms.source_models import ScheduleGroup
from app.raid_rooms import completed_room_lifecycle as archive


def role(db,uid,row):
    own=db.scalar(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.user_id==uid,
        CycleMember.state.in_(('participating','completed','stopped','review_required')),Member.ended_at.is_(None))) if uid else None
    if own is None:return 'none'
    return 'leader' if own.id==commands.leadership(db,row)['leader_cycle_member_id'] else 'member'


def card(db,room,row,uid,stamp,loaded=None):
    ended=room.ended_at is not None or (loaded['archived'] if loaded is not None else archive.is_archived(db,room.id))
    settings=row.settings_snapshot
    leader=loaded['leadership'] if loaded is not None else commands.leadership(db,row)
    leader_assignment=db.scalar(select(Assignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).where(
        CycleAssignment.cycle_member_id==leader['leader_cycle_member_id']).order_by(Assignment.id).limit(1)) if loaded is None else None
    groups=loaded['groups'] if loaded is not None else schedule.groups(db,row)
    starts=loaded['starts'] if loaded is not None else [s.starts_at for s in schedule.sessions(db,row) if s.state=='confirmed']
    items=loaded['items'] if loaded is not None else [dict(item_id=i.id,raid_id=i.raid_id,difficulty_id=r.difficulty_id,game_party_size=r.game_party_size,round_id=r.id)
        for i,r in admission.rounds(db,row)]
    return dict(room_id=room.id,revision=room.revision,title=room.title,scope=room.scope,group_id=room.group_id,
        admission_mode=settings['admission_mode'],experience_level=settings['experience_level'],app_capacity=settings['app_capacity'],
        app_member_count=loaded['count'] if loaded is not None else admission.member_count(db,row),state='ended' if ended else 'active',items=items,game_items=items,
        leader_display=loaded['leader_display'] if loaded is not None else leader_assignment.display if leader_assignment else None,created_at=room.created_at,
        phase='ended' if ended else cycles.target(stamp,row.cycle_key.isoformat()).phase,restricted=row.state=='review_required',
        schedule_summary=dict(mode=groups[0].planning_mode if len(groups)==1 else 'multiple' if groups else 'unscheduled',
            occurrence_mode=groups[0].occurrence_mode if len(groups)==1 else None,confirmed_starts_at=sorted(starts),
            earliest_start=min(starts) if starts else None,latest_start=max(starts) if starts else None),
        combat_requirement=settings['combat_requirement'],continuation_enabled=settings['continuation_enabled'],
        permissions=dict(view_detail=permission(None if uid else 'AUTH_REQUIRED'),
            view_plan=permission(None if (loaded['role'] if loaded is not None else role(db,uid,row))!='none' else 'WEEKLY_PARTICIPANT_REQUIRED')),
        leadership=leader,my_target_role=loaded['role'] if loaded is not None else role(db,uid,row),target_cycle_key=row.cycle_key.isoformat(),
        target_state=loaded['state'] if loaded is not None else commands.target_state(db,row),target_revision=row.revision,
        room_cycle_id=row.id,target_generation=row.generation)


def get_card(principal,rid,key):
    with snapshot(principal,public=True) as (db,uid,stamp):
        query=select(Room).where(Room.id==rid,filters.visible(uid))
        room=db.scalar(query)
        if room is None:fail('ROOM_NOT_FOUND',404)
        if archive.is_archived(db,rid):fail('ROOM_NOT_FOUND',404)
        _,row=cycles.resolve(db,rid,key,stamp)
        if row is None:fail('TARGET_NOT_OPEN')
        admission.capacity(row)
        return wire.OutputContract3GetV2RaidRoomsRoomId.model_validate(dict(scope=scope(stamp,key,row),
            data=card(db,room,row,uid,stamp))).model_dump(mode='json')


def search(principal,data):
    body=data.model_dump(mode='json')
    candidate_token=body.pop('group_character_candidates_token',None)
    if candidate_token is not None:
        body['group_character_candidates_token']=candidate_token
    with snapshot(principal,public=True) as (db,uid,stamp):
        target=cycles.target(stamp,body['target_cycle_key'])
        for name in ('group_ids','raid_ids','difficulty_ids','remaining_slot_counts','experience_levels'):
            values=body.get(name)
            if values is None and name in data.model_fields_set:fail('INVALID_REQUEST',400)
            if values and len(set(values))!=len(values):fail('INVALID_REQUEST',400)
            body[name]=sorted(values or [])
        if len({c.member_ref for c in data.member_conditions})!=len(data.member_conditions):fail('INVALID_REQUEST',400)
        context_digest=None;mapping={}
        if data.group_ids:
            if uid is None:fail('AUTH_REQUIRED',401)
            ctx,mapping=filters.filter_context(db,uid,data.group_ids,stamp)
            context_digest=ctx['scope_digest']
            if data.filter_context_token is not None and ctx['filter_context_token']!=data.filter_context_token:
                fail('FILTER_CONTEXT_STALE')
        elif data.filter_context_token is not None:fail('INVALID_REQUEST',400)
        if data.member_conditions and (not data.group_ids or data.filter_context_token is None):fail('INVALID_REQUEST',400)
        if candidate_token is not None:
            if uid is None:fail('AUTH_REQUIRED',401)
            if len(data.group_ids)!=1 or data.filter_context_token is None:fail('INVALID_REQUEST',400)
            from app.raid_rooms.character_candidates import validate_search
            validate_search(db,uid,principal[1].id,data.group_ids,(ctx,mapping),candidate_token,data.member_conditions,stamp)
        count=select(func.count(func.distinct(Assignment.membership_id))).join(CycleRound,
            CycleRound.round_id==Assignment.round_id).join(WeeklyOccupancy,WeeklyOccupancy.assignment_id==Assignment.id).where(
            CycleRound.cycle_id==RoomCycle.id,CycleRound.generation==RoomCycle.generation,
            CycleRound.is_current.is_(True),Assignment.state=='active').correlate(RoomCycle).scalar_subquery()
        query=select(Room,RoomCycle).join(RoomCycle,RoomCycle.room_id==Room.id).where(
            Room.ended_at.is_(None),RoomCycle.cycle_key==target.key,RoomCycle.state=='open',
            RoomCycle.generation.is_not(None),~archive.archived(Room.id),filters.visible(uid))
        if data.category=='general':query=query.where(Room.group_id.is_(None))
        elif data.category=='group_linked':query=query.where(Room.group_id.is_not(None))
        if data.admission_scope is not None:query=query.where(Room.scope==data.admission_scope)
        if data.group_ids:query=query.where(Room.group_id.in_(data.group_ids))
        for condition in data.member_conditions:
            subject=mapping.get(condition.member_ref)
            if subject is None or len(set(condition.character_ids))!=len(condition.character_ids):fail('INVALID_REQUEST',400)
            actual=select(CycleMember.id).where(CycleMember.cycle_id==RoomCycle.id,
                CycleMember.generation==RoomCycle.generation,CycleMember.user_id==subject,
                CycleMember.state.in_(('participating','completed','stopped')))
            if condition.character_ids:
                character=select(CycleAssignment.assignment_id).join(Assignment,
                    Assignment.id==CycleAssignment.assignment_id).where(CycleAssignment.cycle_member_id==CycleMember.id,
                        Assignment.character_id.in_(condition.character_ids)).exists()
                actual=actual.where(character)
            query=query.where(actual.exists())
        if data.raid_ids or data.difficulty_ids:
            from app.raid_rooms.integrated_models import RecruitmentRound as Round,RecruitmentItem as Item
            rd=select(CycleRound.round_id).join(Round,Round.id==CycleRound.round_id).join(Item,Item.id==CycleRound.item_id).where(
                CycleRound.cycle_id==RoomCycle.id,CycleRound.generation==RoomCycle.generation,CycleRound.is_current.is_(True))
            if data.raid_ids:rd=rd.where(Item.raid_id.in_(data.raid_ids))
            if data.difficulty_ids:rd=rd.where(Round.difficulty_id.in_(data.difficulty_ids))
            query=query.where(rd.exists())
        if body['experience_levels']:
            value=RoomCycle.settings_snapshot['experience_level'].astext
            query=query.where(or_(value.in_([v for v in body['experience_levels'] if v!='unrestricted']),
                value.is_(None) if 'unrestricted' in body['experience_levels'] else False))
        if body['remaining_slot_counts']:
            size=RoomCycle.settings_snapshot['app_capacity'].as_integer()
            query=query.where((size-count).in_(body['remaining_slot_counts']))
        body['member_conditions']=sorted([dict(member_ref=c.member_ref,character_ids=sorted(map(str,c.character_ids)))
            for c in data.member_conditions],key=lambda c:c['member_ref'])
        sort=body['sort'] or dict(criterion='member_count',direction='descending')
        body['sort']=sort
        body.pop('cursor',None)
        head=cycles.directory_revision(db,target.key)
        permissions=list(db.execute(select(Group.id,Group.revision,Group.members_revision).join(GroupMembership,
            GroupMembership.group_id==Group.id).where(GroupMembership.user_id==uid,
            GroupMembership.ended_at.is_(None),Group.ended_at.is_(None)).order_by(Group.id))) if uid else []
        revision=digest(jsonable_encoder([head,target.current,body,context_digest,[list(r) for r in permissions]]))
        binding=['cycle-directory',str(uid),str(principal[1].id) if principal else None,target.key.isoformat()]
        offset=cursor_decode(data.cursor,binding,revision) if data.cursor else 0
        primary=count.asc() if sort['direction']=='ascending' else count.desc()
        rows=list(db.execute(query.order_by(primary,Room.created_at.desc(),Room.id.desc()).offset(offset).limit(data.limit+1)))
        token=cursor_encode(dict(scope=binding,revision=revision,offset=offset+data.limit)) if len(rows)>data.limit else None
        from app.raid_rooms.cycle_card_batch import load
        loaded=load(db,[t for _,t in rows[:data.limit]],uid)
        result=dict(scope=scope(stamp,target.key.isoformat()),data=dict(items=[card(db,r,t,uid,stamp,loaded[t.id]) for r,t in rows[:data.limit]],
            directory_revision=head,filter_scope_digest=context_digest,next_cursor=token,evaluated_at=stamp))
        return wire.OutputContract3PostV2RaidRoomsSearch.model_validate(result).model_dump(mode='json')
