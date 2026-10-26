"""Actor/target-scoped membership and application pages, without GET writes."""
from app.raid_rooms import beta_profile, beta_schedule, beta_output
from sqlalchemy import select,func,and_,or_
from app.game_accounts.support import fail,cursor_encode,cursor_decode
from app.game_accounts.lifecycle import digest
from app.raid_rooms import admission_service as base, cycles, cycle_queries as directory, cycle_commands as commands
from app.raid_rooms import cycle_member_reads as members, cycle_wire as wire
from app.raid_rooms.cycle_creation import scope,permission
from app.raid_rooms.cycle_models import RoomCycle,CycleMember
from app.raid_rooms.cycle_application_models import CycleApplication as Application
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentRoom as Room
from app.raid_rooms.models import MemberHead
from app.groups.models import GroupMembership
from app.raid_rooms import completed_room_lifecycle as archive


def applications(principal,key,*,rid=None,state='pending',limit=20,cursor=None,reader_profile=None):
    from app.raid_rooms import application_display as display, application_display_schemas as display_schemas
    if reader_profile is not None and (reader_profile != display.PROFILE or rid is None):fail('INVALID_REQUEST',400)
    if state not in ('pending','accepted','rejected','withdrawn','expired','cancelled','all') or type(limit) is not int or not 1<=limit<=50:fail('INVALID_REQUEST',400)
    with base.snapshot(principal) as (db,uid,stamp):
        target=cycles.target(stamp,key)
        row=None
        query=select(Application).join(RoomCycle,RoomCycle.id==Application.cycle_id).where(RoomCycle.cycle_key==target.key)
        if rid is not None:
            room,row=commands.resolve(db,uid,rid,key,stamp)
            commands.require_leader(db,uid,row)
            query=query.where(Application.cycle_id==row.id,Application.generation==row.generation)
        else:query=query.where(Application.user_id==uid)
        all_rows=query.subquery()
        head=1+db.scalar(select(func.coalesce(func.sum(all_rows.c.revision),0)))
        if head>2147483647:fail('SERVICE_UNAVAILABLE',503)
        pending=(Application.state=='pending') & (Application.expires_at>stamp)
        if state=='pending':query=query.where(pending)
        elif state=='expired':query=query.where((Application.state=='expired')|((Application.state=='pending')&(Application.expires_at<=stamp)))
        elif state!='all':query=query.where(Application.state==state)
        expired_ids=list(db.scalars(select(all_rows.c.id).where(all_rows.c.state=='pending',all_rows.c.expires_at<=stamp).order_by(all_rows.c.id)))
        revision=digest([head,expired_ids and list(map(str,expired_ids)),target.current.isoformat(),limit,state])
        binding=['cycle-applications',str(uid),str(principal[1].id),str(rid),key]
        if reader_profile is not None:
            binding.append(reader_profile)
            revision=digest([revision,str(row.id),row.generation])
        offset=cursor_decode(cursor,binding,revision) if cursor else 0
        rows=list(db.scalars(query.order_by(Application.created_at.desc(),Application.id.desc()).offset(offset).limit(limit+1)))
        token=cursor_encode(dict(scope=binding,revision=revision,offset=offset+limit)) if len(rows)>limit else None
        items=[]
        projected=display.projections(db,rows[:limit],row) if reader_profile is not None else {}
        for app in rows[:limit]:
            actual=db.get(RoomCycle,app.cycle_id)
            items.append(dict(application_id=app.id,room_id=app.room_id,revision=app.revision,
                state='expired' if app.state=='pending' and app.expires_at<=stamp else app.state,
                created_at=app.created_at,expires_at=app.expires_at,ended_at=app.ended_at,character_id=app.selection['character_id'],
                selected_role=app.selection['selected_role'],display=app.display,
                admission_origin=dict(scope=app.origin_scope,group_id=app.origin_group_id),target_cycle_key=actual.cycle_key,
                target_generation=app.generation))
            if reader_profile is not None:items[-1].update(projected[app.id])
        model=display_schemas.ApplicationDisplayPageResponse if reader_profile is not None else wire.OutputContract3GetV2RaidRoomsRoomIdApplications
        result=beta_output.render(db,uid,stamp,model,dict(scope=scope(stamp,key,row),
            data=dict(items=items,applications_revision=head,next_cursor=token,evaluated_at=stamp)))
        return display.bounded(result) if reader_profile is not None else result


def memberships(principal,key,state='current',limit=20,cursor=None):
    if state not in ('current','ended','all') or type(limit) is not int or not 1<=limit<=50:fail('INVALID_REQUEST',400)
    with base.snapshot(principal) as (db,uid,stamp):
        target=cycles.target(stamp,key)
        query=select(Member,Room).join(Room,Room.id==Member.room_id).where(Member.user_id==uid)
        actual_query=select(CycleMember.id).join(RoomCycle,RoomCycle.id==CycleMember.cycle_id).where(
            RoomCycle.room_id==Member.room_id,RoomCycle.cycle_key==target.key,CycleMember.membership_id==Member.id,
            or_(CycleMember.generation==RoomCycle.generation,and_(CycleMember.generation.is_(None),RoomCycle.generation.is_(None))))
        from app.raid_rooms.active_usage import predicate
        active=actual_query.where(predicate()).correlate(Member,Room).exists()
        history=actual_query.where(CycleMember.state.in_(('completed','stopped','cancelled','removed'))).correlate(Member).exists()
        if state=='current':query=query.where(active)
        elif state=='ended':query=query.where(or_(Member.ended_at.is_not(None),Room.ended_at.is_not(None),archive.archived(Room.id),history))
        head=db.get(MemberHead,uid)
        revision=head.membership_revision if head else 1
        binding=['cycle-memberships',str(uid),str(principal[1].id),key,state,limit]
        epoch=digest([revision,cycles.directory_revision(db,target.key),target.current.isoformat()])
        offset=cursor_decode(cursor,binding,epoch) if cursor else 0
        rows=list(db.execute(query.order_by(Member.joined_at.desc(),Member.id.desc()).offset(offset).limit(limit+1)))
        token=cursor_encode(dict(scope=binding,revision=epoch,offset=offset+limit)) if len(rows)>limit else None
        items=[]
        for member,room in rows[:limit]:
            _,row=cycles.resolve(db,room.id,key,stamp)
            actual=db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.membership_id==member.id).order_by(CycleMember.joined_order.desc().nullslast(),CycleMember.id.desc())) if row else None
            ready=row is not None and row.provenance=='explicit' and row.generation is not None and bool(row.settings_snapshot)
            detail=members.own_view(db,room,row,member) if ready else dict(target_role='none',cycle_member_id=None,
                cycle_member_revision=actual.revision if actual else None,joined_order=str(actual.joined_order) if actual and actual.joined_order else None)
            if actual:
                detail.update(cycle_member_id=actual.id,cycle_member_revision=actual.revision,joined_order=str(actual.joined_order) if actual.joined_order else None)
            owned=members.assignments(db,row,member.id) if ready else []
            items.append(dict(membership_id=member.id,revision=member.revision,room_id=room.id,
                state='current' if member.ended_at is None else 'ended',joined_at=member.joined_at,ended_at=member.ended_at,
                assignments=[dict(assignment_id=a.id,revision=a.revision,item_id=a.item_id,round_id=a.round_id,
                    character_id=a.character_id,selected_role=a.selected_role,state=a.state,target_cycle_key=key,
                    cycle_member_id=link.cycle_member_id) for a,link in owned],
                room=directory.card(db,room,row,uid,stamp) if ready else None,
                recovery_only=not ready,history_only=member.ended_at is not None,
                permissions=dict(view_plan=permission(None if ready and actual and member.ended_at is None else 'ROOM_REVIEW_REQUIRED' if actual and not ready else 'WEEKLY_PARTICIPANT_REQUIRED')),
                target_role=detail['target_role'],cycle_member_id=detail['cycle_member_id'],
                cycle_member_revision=detail['cycle_member_revision'],joined_order=detail['joined_order'],
                target_participation_state=('cancelled' if actual.state=='removed' else actual.state) if actual else 'review_required' if row and not ready else 'not_selected',
                target_cycle_key=key,room_cycle_id=row.id if row else None,target_generation=row.generation if row else None,
                target_revision=row.revision if row else None))
        return beta_output.render(db,uid,stamp,wire.OutputContract3GetV2MeRaidRoomMemberships,dict(scope=scope(stamp,key),
            data=dict(items=items,membership_head=revision,next_cursor=token,evaluated_at=stamp)))


def projections(principal,gid,rids,key,token=None,gids=None):
    if not rids or len(set(rids))!=len(rids):fail('INVALID_REQUEST',400)
    gids=gids if gids is not None else [gid]
    if gid not in gids:fail('INVALID_REQUEST',400)
    with base.snapshot(principal) as (db,uid,stamp):
        source,mapping=directory.filters.filter_context(db,uid,gids,stamp)
        if token is not None and token!=source['filter_context_token']:fail('FILTER_CONTEXT_STALE')
        refs={uid:ref for ref,uid in mapping.items()}
        values=[]
        for rid in rids:
            room,row=commands.resolve(db,uid,rid,key,stamp)
            if room.group_id!=gid:fail('ROOM_NOT_FOUND',404)
            actuals=list(db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,
                CycleMember.generation==row.generation,CycleMember.state.in_(('participating','completed','stopped')))
                .order_by(CycleMember.joined_order)))
            result=[]
            for actual in actuals:
                assignments=members.assignments(db,row,actual.membership_id)
                if not assignments:continue
                assignment=assignments[-1][0]
                group_member=db.scalar(select(GroupMembership).where(GroupMembership.group_id==gid,
                    GroupMembership.user_id==actual.user_id,GroupMembership.ended_at.is_(None)))
                result.append(dict(raid_membership_id=actual.membership_id,
                    group_membership_id=group_member.id if group_member else None,
                    member_ref=refs.get(actual.user_id) if token and group_member else None,
                    character_id=assignment.character_id,display=assignment.display,group_member=group_member is not None,
                    target_cycle_key=key,cycle_member_id=actual.id))
            values.append(dict(room_id=rid,members=result,target_cycle_key=key,room_cycle_id=row.id,
                target_generation=row.generation,target_revision=row.revision))
        return beta_output.render(db,uid,stamp,wire.OutputContract3GetV2GroupsGroupIdRaidRoomMemberProjections,dict(scope=scope(stamp,key),
            data=dict(group_id=gid,members_revision=next(g['members_revision'] for g in source['groups'] if g['group_id']==gid),
                evaluated_at=stamp,rooms=values)))
