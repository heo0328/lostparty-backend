"""Private target detail and plan. Historical/global assignments are not aliases."""
from datetime import timedelta
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.auth.models import User
from app.game_accounts.support import fail, GameError
from app.game_accounts.lifecycle import digest
from app.groups.models import GroupMembership
from app.raid_rooms import (admission_service as base, admission_context as context, cycle_admission as admission,
    cycle_queries as directory, cycle_commands as commands, cycle_schedule as schedule, cycle_wire as wire)
from app.raid_rooms.cycle_creation import scope, permission
from app.raid_rooms.cycle_models import CycleMember, CycleAssignment, CycleSubmission, CycleRound
from app.raid_rooms.integrated_models import RecruitmentMembership as Member, RecruitmentAssignment as Assignment
from app.raid_rooms.source_models import (ScheduleGroup,ScheduleAlternative,SessionBinding,
    SessionParticipation as Participation,TimeReservation as Reservation)
from app.raid_rooms.schedule_views import segment_view
from app.raid_rooms import completed_room_lifecycle as archive


def read_target(db,uid,rid,key,stamp):
    from app.raid_rooms import cycles
    room=commands.base.room(db,uid,rid)
    _,row=cycles.resolve(db,rid,key,stamp)
    if row is None:fail('TARGET_NOT_OPEN')
    admission.capacity(row)
    return room,row


def badge(db,room,uid):
    return room.group_id is not None and db.scalar(select(GroupMembership.id).where(
        GroupMembership.group_id==room.group_id,GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is not None


def own_cycle_member(db,row,member):
    return db.scalar(select(CycleMember).where(CycleMember.cycle_id==row.id,
        CycleMember.generation==row.generation,CycleMember.membership_id==member.id,
        CycleMember.state.in_(('participating','completed','stopped','review_required'))))


def own_view(db,room,row,member):
    actual=own_cycle_member(db,row,member)
    return dict(membership_id=member.id,revision=member.revision,group_member=badge(db,room,member.user_id),
        target_role=directory.role(db,member.user_id,row),cycle_member_id=actual.id if actual else None,
        cycle_member_revision=actual.revision if actual else None,
        joined_order=str(actual.joined_order) if actual and actual.joined_order is not None else None)


def assignments(db,row,member_id=None):
    query=select(Assignment,CycleAssignment).join(CycleAssignment,CycleAssignment.assignment_id==Assignment.id).join(
        CycleRound,CycleRound.round_id==Assignment.round_id).where((CycleRound.is_current.is_(True)) | (Assignment.state=='completed'),
        CycleAssignment.cycle_id==row.id,CycleAssignment.generation==row.generation)
    if member_id is not None:query=query.where(Assignment.membership_id==member_id)
    return list(db.execute(query.order_by(Assignment.joined_at,Assignment.id)))


def formation(db,row):
    leader=commands.leadership(db,row)['leader_cycle_member_id']
    values=assignments(db,row)
    current=[];history=[]
    for item,rd in admission.rounds(db,row):
        active={(a.party_no,a.slot_no):(a,link) for a,link in values if a.round_id==rd.id and a.state=='active'}
        for party in range(1,min(admission.capacity(row),rd.game_party_size)//4+1):
            for slot in range(1,5):
                value=active.get((party,slot));a,link=value if value else (None,None)
                current.append(dict(target_cycle_key=row.cycle_key,round_id=rd.id,party_no=party,slot_no=slot,
                    assignment_id=a.id if a else None,status='participating' if a else 'empty',
                    is_leader=link is not None and link.cycle_member_id==leader))
        for a,link in values:
            if a.item_id==item.id and a.state=='completed':
                history.append(dict(target_cycle_key=row.cycle_key,round_id=a.round_id,party_no=a.party_no,slot_no=a.slot_no,
                    assignment_id=a.id,status='completed',is_leader=link.cycle_member_id==leader))
    return dict(formation_slots=current,formation_history=history,unplaced_assignments=[])


def settings(db,room,row,uid,stamp):
    source=row.settings_snapshot
    result=dict(room_id=room.id,revision=row.settings_revision,room_revision=room.revision,
        experience_level=source['experience_level'],combat_requirement=source['combat_requirement'],
        continuation=dict(enabled=source['continuation_enabled'],opening_mode='explicit',revision=row.settings_revision),
        scope=room.scope,group_id=room.group_id,admission_mode=source['admission_mode'],
        permissions={name:permission('RECRUITMENT_COMMAND_NOT_READY') for name in
            ('edit_settings','edit_common_settings','open_next_cycle','reopen_next_cycle')},
        leadership=commands.leadership(db,row),my_target_role=directory.role(db,uid,row))
    from app.raid_rooms.cycle_leadership import action_permissions
    actions=action_permissions(db,uid,room,row,stamp)
    for name in ('open_next_cycle','reopen_next_cycle'):result['permissions'][name]=actions[name]
    from app.raid_rooms import cycle_outcomes,cycle_management,cycle_common
    if cycle_outcomes.enabled(db):
        result['permissions']['edit_settings']=cycle_management.edit_permission(db,uid,room,row,stamp)
        result['permissions']['edit_common_settings']=cycle_common.common_permission(db,uid,room,stamp)
    if archive.is_archived(db,room.id):archive.permissions(result['permissions'])
    return result


def detail(principal,rid,key):
    with base.snapshot(principal) as (db,uid,stamp):
        room,row=read_target(db,uid,rid,key,stamp)
        if archive.is_archived(db,rid):base.member(db,uid,room)
        mine=db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==uid,Member.ended_at.is_(None)))
        values=[]
        for actual in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,
                CycleMember.generation==row.generation,CycleMember.state.in_(('participating','completed','stopped','review_required')))
                .order_by(CycleMember.joined_order,CycleMember.id)):
            member=db.get(Member,actual.membership_id)
            owned=assignments(db,row,member.id)
            recent=owned[-1][0] if owned else None
            comparison=None;reason=None;build=None
            if recent and mine is not None:
                try:
                    if db.get(User,actual.user_id).status!='active':fail('ROOM_TARGET_UNAVAILABLE')
                    selected=context.selection(db,actual.user_id,recent.character_id,recent.selected_role)
                    if (selected.expected_ownership_revision,selected.expected_lifecycle_revision)!=(recent.ownership_revision,recent.lifecycle_revision):
                        fail('OWNERSHIP_REQUIRED',403)
                    minimum=row.settings_snapshot['combat_requirement']['dealer_min' if recent.selected_role=='dealer' else 'support_min']
                    comparison=admission.core.power_comparison(db,actual.user_id,selected,minimum)
                except GameError as error:reason=error.code
                captured=recent.build or {}
                build=dict(role=recent.selected_role,version=captured.get('success_summary_version'),summary=captured.get('success_summary'),
                    saved_at=captured.get('success_saved_at'),current_summary_version=comparison['current_summary_version'] if comparison else None,
                    stale=reason is not None or comparison is None or captured.get('success_summary_version')!=comparison['current_summary_version'])
            values.append(own_view(db,room,row,member)|dict(joined_at=actual.joined_at or member.joined_at,
                character=dict(character_id=recent.character_id,display=recent.display,selected_role=recent.selected_role) if recent else None,
                assignments=[dict(assignment_id=a.id,item_id=a.item_id,round_id=a.round_id,state=a.state,
                    party_no=a.party_no,slot_no=a.slot_no) for a,link in owned],comparison=comparison,build=build,is_me=actual.user_id==uid,
                status='needs_review' if reason else 'valid',status_reason=reason,target_state=actual.state))
        result=dict(scope=scope(stamp,key,row),data=dict(room=directory.card(db,room,row,uid,stamp),
            settings=settings(db,room,row,uid,stamp),members_revision=row.members_revision,members=values,
            my_membership=own_view(db,room,row,mine) if mine else None,plan_revision=row.plan_revision,
            permissions=dict(view_detail=permission(),view_plan=permission(None if mine and own_cycle_member(db,row,mine) else 'WEEKLY_PARTICIPANT_REQUIRED')),
            access=dict(state='allowed',policy_snapshot=digest([str(row.id),row.generation,row.revision]),evaluated_at=stamp,issues=[]),
            leadership=commands.leadership(db,row),my_target_role=directory.role(db,uid,row),**formation(db,row)))
        return wire.OutputContract3GetV2RaidRoomsRoomIdDetail.model_validate(result).model_dump(mode='json')


def schedule_fields(db,room,row,mine,stamp,include_resume_display=False):
    graph=schedule.graph
    groups=[];sessions=[];parts=[];segments=[]
    enabled=schedule.planning_enabled(db)
    leader=False
    if enabled:
        from app.raid_rooms import cycle_schedule_service as service,cycle_planning,cycle_proposals
        try:service.target(db,mine.user_id,room.id,row.cycle_key.isoformat(),stamp,leader=True);leader=True
        except GameError:pass
    for group in sorted(schedule.groups(db,row),key=lambda g:str(g.id)):
        alternatives=[]
        for alt in schedule.alternatives(db,group):
            clock=lambda v:f'{v//60:02}:{v%60:02}' if v is not None else None
            alternatives.append(dict(alternative_id=alt.id,session_id=alt.session_id,weekday=alt.weekday,
                starts_local=clock(alt.start_minute),leader_latest_start_local=clock(alt.latest_start_minute),item_ids=alt.item_order))
        value=cycle_planning.candidate(db,room,row,group,stamp) if enabled and group.planning_mode=='coordinated' else None
        groups.append(dict(group_id=group.id,revision=group.revision,client_group_key=db.get(graph.ScheduleHead,group.id).client_key,
            occurrence_mode=group.occurrence_mode,planning_mode=group.planning_mode,day_scope=group.day_scope,required=group.required,
            auto_confirm_additional_members=group.auto_additional_members,alternatives=alternatives,selected_session_id=group.selected_session_id,
            resolution='selected' if group.selected_session_id else 'all' if group.occurrence_mode=='each' else 'unresolved',
            candidate_state=value['state'] if value else 'not_evaluated',permissions=dict(select=permission(None if leader and group.selected_session_id is None and group.planning_mode!='unscheduled' else 'SCHEDULE_PROPOSAL_REQUIRED' if enabled else 'RECRUITMENT_COMMAND_NOT_READY'))))
    actual=own_cycle_member(db,row,mine)
    for session in schedule.sessions(db,row,history=row.state!='open'):
        binding=db.get(SessionBinding,session.id);group=db.get(ScheduleGroup,binding.group_id)
        values=graph.segments(db,session.id)
        segments.append(dict(session_id=session.id,segments=[segment_view(db,s) for s in values]))
        sessions.append(dict(session_id=session.id,revision=session.revision,round_ids=[s.round_id for s in values],
            required=binding.required,mode=group.planning_mode,state=session.state,schedule_revision=session.schedule_revision,
            starts_at=session.starts_at,ends_at=session.ends_at,duration_minutes=sum(s.duration_minutes for s in values),
            duration_source='item_sum',duration_policy_version='difficulty-duration-v1',earliest_start=session.starts_at,
            latest_start=session.starts_at,join_deadline=session.starts_at-timedelta(minutes=30) if session.state=='confirmed' else None,
            candidate_state='ready' if session.starts_at else 'not_evaluated',permissions=dict(propose_schedule=permission(None if leader and session.state=='confirmed' and stamp<session.ends_at else 'SCHEDULE_NOT_CONFIRMED' if enabled else 'RECRUITMENT_COMMAND_NOT_READY'))))
        own=db.scalar(select(Participation).where(Participation.session_id==session.id,Participation.membership_id==mine.id))
        if own is not None:
            from app.raid_rooms.cycle_times import confirm_permission
            reservations=list(db.scalars(select(Reservation).where(Reservation.participation_id==own.id)))
            active=[r for r in reservations if r.released_at is None]
            owned_rounds={a.round_id for a,link in assignments(db,row,mine.id) if a.state=='active'}
            expected_segments=[s for s in graph.active_segments(db,session.id) if s.round_id in owned_rounds]
            warnings=[]
            if any(graph.busy(db,mine.user_id,r.starts_at,r.ends_at,excluding=session.id) for r in active):warnings.append('TIME_OVERLAP')
            submission=db.get(CycleSubmission,actual.id) if actual else None
            if session.starts_at and (submission is None or not graph.time.covered(session.starts_at,session.ends_at,submission.normalized_intervals)):
                warnings.append('OUTSIDE_AVAILABILITY')
            parts.append(dict(participation_id=own.id,revision=own.revision,session_id=session.id,
                assignment_ids=[a.id for a,link in assignments(db,row,mine.id) if a.round_id in {s.round_id for s in values}],state=own.state,required=binding.required,
                participating=own.state=='active',confirmation_state=own.confirmation_state,confirmed_at=own.confirmed_at,
                confirmed_schedule_revision=own.confirmed_schedule_revision,
                reservation_state='active' if active and len(active)==len(expected_segments) else 'partial' if active else 'released' if reservations else 'none',
                overlap_warning='TIME_OVERLAP' in warnings,warnings=warnings,
                permissions=dict(confirm_participation=confirm_permission(db,mine.user_id,row,session.id,stamp))))
    views=cycle_proposals.views(db,row,mine,stamp) if enabled else []
    from app.raid_rooms import cycle_outcomes
    if cycle_outcomes.enabled(db):
        from app.raid_rooms import cycle_resume
        views+=cycle_resume.views(db,row,mine,stamp,include_resume_display)
    return dict(schedule_state='change_pending' if any(v['state']=='pending' for v in views) else 'confirmed' if sessions and all(s['state']=='confirmed' for s in sessions) else 'unconfirmed' if sessions else 'unscheduled',
        schedule_groups=groups,sessions=sessions,session_segments=segments,my_participations=parts,proposals=views)


def plan(principal,rid,key,include_resume_display=False):
    with base.snapshot(principal) as (db,uid,stamp):
        room,row=read_target(db,uid,rid,key,stamp);mine=base.member(db,uid,room)
        if own_cycle_member(db,row,mine) is None:fail('WEEKLY_PARTICIPANT_REQUIRED',403)
        items=[dict(item_id=i.id,revision=i.revision,raid_id=i.raid_id,difficulty_id=r.difficulty_id,
            catalog_version=r.catalog_version,game_party_size=r.game_party_size,round_id=r.id,round_revision=r.revision,round_state=r.state)
            for i,r in admission.rounds(db,row)]
        own=[dict(assignment_id=a.id,revision=a.revision,membership_id=mine.id,item_id=a.item_id,round_id=a.round_id,
            character_id=a.character_id,selected_role=a.selected_role,state=a.state,ended_at=a.ended_at,raid_participation_state=a.state,
            completion_source=(a.build or {}).get('completion_source'),completed_at=(a.build or {}).get('completed_at'),target_cycle_key=key)
            for a,link in assignments(db,row,mine.id)]
        result=dict(scope=scope(stamp,key,row),data=dict(room_id=room.id,revision=row.plan_revision,
            members_revision=row.members_revision,server_time=stamp,app_capacity=admission.capacity(row),game_items=items,
            my_membership=own_view(db,room,row,mine),my_assignments=own,
            permissions={name:permission('RECRUITMENT_COMMAND_NOT_READY') for name in
                ('edit_schedule_groups','cancel_target_participation','transfer_leadership','open_next_cycle','reopen_next_cycle',
                 'view_common_context','leave_global','end_global')},leadership=commands.leadership(db,row),
            my_target_role=directory.role(db,uid,row),target_cycle_key=key,target_state=commands.target_state(db,row),
            **formation(db,row),**schedule_fields(db,room,row,mine,stamp,include_resume_display)))
        from app.raid_rooms.cycle_leadership import action_permissions
        result['data']['permissions'].update(action_permissions(db,uid,room,row,stamp))
        if schedule.planning_enabled(db):
            from app.raid_rooms.cycle_schedule_service import target
            reason=None
            try:target(db,uid,room.id,key,stamp,leader=True)
            except GameError as error:reason=error.code
            if reason is None and any(s.state=='confirmed' for s in schedule.sessions(db,row)):reason='SCHEDULE_PROPOSAL_REQUIRED'
            result['data']['permissions']['edit_schedule_groups']=permission(reason)
        from app.raid_rooms import cycle_outcomes,cycle_common
        if cycle_outcomes.enabled(db):
            for name,kind in (('leave_global','leave'),('end_global','end')):
                try:result['data']['permissions'][name]=cycle_common.context(db,uid,room.id,kind,stamp)[0]['data']['permission']
                except GameError as error:result['data']['permissions'][name]=permission(error.code)
            result['data']['permissions']['view_common_context']=permission(None)
        if archive.is_archived(db,rid):archive.permissions(result['data']['permissions'])
        if include_resume_display:
            from app.raid_rooms import resume_review, resume_review_schemas
            return resume_review.output(resume_review_schemas.ResumePlanContext,result)
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdPlan.model_validate(jsonable_encoder(result)).model_dump(mode='json')
