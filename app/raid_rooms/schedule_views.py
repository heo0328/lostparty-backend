from datetime import date
"""Read-only schedule projections. No reservation, response or evaluation writes."""
from sqlalchemy import select
from app.raid_rooms import scheduling as graph,proposals
from app.raid_rooms.source_models import SessionParticipation as Participation,TimeReservation as Reservation,ScheduleGroup,ScheduleAlternative,SessionBinding,ProposalTarget,ProposalResponse,AvailabilitySubmission


def permission(allowed,reason):return dict(allowed=bool(allowed),reason=None if allowed else reason)


def segment_view(db,segment):
    round=db.get(graph.Round,segment.round_id)
    evidence=db.get(graph.SegmentDurationEvidence,segment.id)
    return dict(segment_id=segment.id,item_id=segment.item_id,round_id=segment.round_id,starts_at=segment.starts_at,ends_at=segment.ends_at,
        duration_minutes=segment.duration_minutes,duration_source=segment.duration_source,policy_version=evidence.duration_policy_version if evidence else 'legacy_review_required',
        state='planned' if round.state=='active' else 'released',released_reason=None if round.state=='active' else round.state)


def fields(db,room,mine,stamp):
    leader=mine.id==room.leader_membership_id
    live=graph.sessions(db,room.id,stamp);groups=[];sessions=[];participations=[];segment_sets=[];proposal_views=[]
    cycle=graph.raids.cycle(stamp)
    current_groups=graph.groups(db,room.id,cycle.cycle_key)
    pending_current=False
    for group in current_groups:
        alts=[]
        for alt in db.scalars(select(ScheduleAlternative).where(ScheduleAlternative.group_id==group.id).order_by(ScheduleAlternative.id)):
            clock=lambda v:f'{v//60:02}:{v%60:02}' if v is not None else None
            alts.append(dict(alternative_id=alt.id,session_id=alt.session_id,weekday=alt.weekday,starts_local=clock(alt.start_minute),
                leader_latest_start_local=clock(alt.latest_start_minute),item_ids=alt.item_order))
        state='not_evaluated'
        if group.planning_mode=='coordinated' and group.selected_session_id is None:state=graph.candidate(db,room,group,stamp)['state']
        groups.append(dict(group_id=group.id,revision=group.revision,client_group_key=db.get(graph.ScheduleHead,group.id).client_key,occurrence_mode=group.occurrence_mode,
            planning_mode=group.planning_mode,day_scope=group.day_scope,required=group.required,auto_confirm_additional_members=group.auto_additional_members,
            alternatives=alts,selected_session_id=group.selected_session_id,resolution='selected' if group.selected_session_id else 'all' if group.occurrence_mode=='each' else 'unresolved',
            candidate_state=state,permissions=dict(select=permission(leader and group.selected_session_id is None,'SCHEDULE_PROPOSAL_REQUIRED'))))
    for session in live:
        binding=db.get(SessionBinding,session.id);group=db.get(ScheduleGroup,binding.group_id);segments=graph.segments(db,session.id)
        segment_sets.append(dict(session_id=session.id,segments=[segment_view(db,s) for s in segments]))
        sessions.append(dict(session_id=session.id,revision=session.revision,round_ids=[s.round_id for s in segments],required=binding.required,
            mode=group.planning_mode,state=session.state,schedule_revision=session.schedule_revision,starts_at=session.starts_at,ends_at=session.ends_at,
            duration_minutes=int((session.ends_at-session.starts_at).total_seconds()//60) if session.starts_at else sum(s.duration_minutes for s in segments),duration_source='item_sum',duration_policy_version='difficulty-duration-v1',
            earliest_start=session.starts_at,latest_start=session.starts_at,join_deadline=session.starts_at-graph.timedelta(minutes=30) if session.state=='confirmed' else None,
            candidate_state='ready' if session.starts_at else 'not_evaluated',permissions=dict(propose_schedule=permission(leader and session.state=='confirmed','SCHEDULE_NOT_CONFIRMED'))))
        own=db.scalar(select(Participation).where(Participation.session_id==session.id,Participation.membership_id==mine.id))
        if own:
            reservations=list(db.scalars(select(Reservation).where(Reservation.participation_id==own.id)))
            active=[r for r in reservations if r.released_at is None]
            warnings=[]
            if active and any(graph.busy(db,mine.user_id,r.starts_at,r.ends_at,excluding=session.id) for r in active):warnings.append('TIME_OVERLAP')
            table=db.get(AvailabilitySubmission,mine.id)
            if session.starts_at and (table is None or not graph.time.covered(session.starts_at,session.ends_at,table.normalized_intervals)):warnings.append('OUTSIDE_AVAILABILITY')
            enabled=own.state=='active' and session.state=='confirmed' and stamp<session.ends_at and bool(graph.assignments(db,mine,session))
            participations.append(dict(participation_id=own.id,revision=own.revision,session_id=session.id,
                assignment_ids=[a.id for a in graph.assignments(db,mine,session)],state=own.state,required=binding.required,participating=own.state=='active',
                confirmation_state=own.confirmation_state,confirmed_at=own.confirmed_at,confirmed_schedule_revision=own.confirmed_schedule_revision,
                reservation_state='active' if len(active)==len(segments) and active else 'partial' if active else 'released' if reservations else 'none',
                overlap_warning='TIME_OVERLAP' in warnings,warnings=warnings,permissions=dict(confirm_participation=permission(enabled,'PARTICIPATION_ENDED'))))
    for prop in db.scalars(select(graph.Proposal).where(graph.Proposal.room_id==room.id).order_by(graph.Proposal.created_at,graph.Proposal.id)):
        targets=list(db.scalars(select(ProposalTarget).where(ProposalTarget.proposal_id==prop.id).order_by(ProposalTarget.session_id)))
        response=db.get(ProposalResponse,(prop.id,mine.id,1,prop.proposal_plan_revision))
        current=prop.created_at>=cycle.starts_at
        pending_current|=prop.state=='pending' and current
        eligible=any(p.membership_id==mine.id for t in targets for p in proposals.eligible(db,db.get(graph.Session,t.session_id)))
        proposal_views.append(dict(proposal_id=prop.id,revision=prop.revision,proposal_plan_revision=prop.proposal_plan_revision,created_from_plan_revision=prop.created_from_plan_revision,
            state=prop.state,target_session_ids=[t.session_id for t in targets],base_schedules=[dict(session_id=t.session_id,schedule_revision=t.base_schedule_revision) for t in targets],
            proposed_sessions=[dict(session_id=t.session_id,segments=[{k:v for k,v in s.items() if k!='item_settings_revision'}|dict(state='planned',released_reason=None) for s in t.proposed_segments]) for t in targets],
            votes=proposals.votes(db,prop),my_response=dict(proposal_id=prop.id,proposal_plan_revision=prop.proposal_plan_revision,membership_id=mine.id,membership_generation=1,
                response=response.response if response else 'pending',response_revision=response.revision if response else 1,responded_at=response.responded_at if response else None,
                response_set='existing' if mine.joined_at<=prop.created_at else 'newcomer'),permissions=dict(respond_proposal=permission(prop.state=='pending' and current and eligible,'CYCLE_CHANGED' if not current else 'PROPOSAL_TARGET_REQUIRED' if not eligible else 'PROPOSAL_NOT_PENDING'))))
    from app.raid_rooms.resume_models import ResumeProposal
    from app.raid_rooms.resume import target_members
    for prop in db.scalars(select(ResumeProposal).where(ResumeProposal.room_id==room.id).order_by(ResumeProposal.created_at,ResumeProposal.id)):
        targets=target_members(db,prop);accepted=sum(prop.responses.get(str(m.id))=='accept' for m in targets)
        current=prop.content['cycle']==cycle.cycle_key
        pending_current|=prop.state=='pending' and current
        proposal_views.append(dict(proposal_id=prop.id,kind='weekly_resume',revision=prop.revision,proposal_plan_revision=1,
            created_from_plan_revision=prop.created_from_plan_revision,state=prop.state,target_round_ids=[v['id'] for v in prop.content['rounds']],
            eligible_count=len(targets),accepted_count=accepted,required_votes=graph.time.quorum(len(targets)) if targets else 1,
            my_response=prop.responses.get(str(mine.id),'pending'),permissions=dict(respond_proposal=permission(
                prop.state=='pending' and current and mine.id in {m.id for m in targets},'CYCLE_CHANGED' if not current else 'PROPOSAL_TARGET_REQUIRED'))))
    return dict(schedule_state='change_pending' if pending_current else 'confirmed' if live and all(s.state=='confirmed' for s in live) else 'unconfirmed' if live else 'unscheduled',
        schedule_groups=groups,sessions=sessions,session_segments=segment_sets,my_participations=participations,proposals=proposal_views)
