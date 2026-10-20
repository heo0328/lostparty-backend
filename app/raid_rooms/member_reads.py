"""Private member reads and anonymous cross-room busy intervals, read only."""
import uuid
from datetime import date,timedelta
from sqlalchemy import select
from app.game_accounts.support import fail,cursor_encode,cursor_decode
from app.game_accounts.support import GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import admission_service as base,search,scheduling as graph,management,participation_core as core
from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentMembership as Member,RecruitmentAssignment as Assignment,RecruitmentRound as Round
from app.raid_rooms.source_models import AvailabilitySubmission,TimeReservation as Reservation,ContinuationChoice as Choice,RecruitmentApplication as Application
from app.raid_rooms.models import MemberHead,DirectoryHead
from app.groups.models import GroupMembership


def badge(db,room,uid):
    return room.group_id is not None and db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==room.group_id,GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is not None


def detail(principal,rid):
    with search.snapshot(principal,public=True) as (db,uid,stamp):
        room=base.room(db,uid,rid);mine=db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==uid,Member.ended_at.is_(None))) if uid else None
        if mine is None:fail('ROOM_MEMBERSHIP_REQUIRED',403)
        values=[]
        # Public detail exposes only public room characters and scoped membership
        # IDs. Member-only plan/submissions remain separate authenticated resources.
        for m in graph.members(db,rid):
            assignments=list(db.scalars(select(Assignment).where(Assignment.membership_id==m.id).order_by(Assignment.joined_at.desc(),Assignment.id)))
            recent=assignments[0] if assignments else None
            comparison=None;reason=None;build=None
            if recent:
                captured=recent.build or {}
                try:
                    from app.auth.models import User
                    if db.get(User,m.user_id).status!='active':fail('ROOM_TARGET_UNAVAILABLE')
                    selected=base.context.selection(db,m.user_id,recent.character_id,recent.selected_role)
                    character=core.identity.selected_character(db,m.user_id,selected.model_dump(mode='json'))
                    if (selected.expected_ownership_revision,selected.expected_lifecycle_revision)!=(recent.ownership_revision,recent.lifecycle_revision):
                        fail('OWNERSHIP_REQUIRED',403)
                    config=db.get(management.RoomSettings,room.id)
                    comparison=core.power_comparison(db,m.user_id,selected,config.dealer_min if recent.selected_role=='dealer' else config.support_min)
                except GameError as error:reason=error.code
                build=dict(role=recent.selected_role,version=captured.get('success_summary_version'),summary=captured.get('success_summary'),saved_at=captured.get('success_saved_at'),
                    current_summary_version=comparison['current_summary_version'] if comparison else None,
                    stale=reason is not None or comparison is None or captured.get('success_summary_version')!=comparison['current_summary_version'])
            values.append(dict(membership_id=m.id,revision=m.revision,room_role='leader' if m.id==room.leader_membership_id else 'member',group_member=badge(db,room,m.user_id),joined_at=m.joined_at,
                character=dict(character_id=recent.character_id,display=recent.display,selected_role=recent.selected_role) if recent else None,
                assignments=[dict(assignment_id=a.id,item_id=a.item_id,round_id=a.round_id,state=a.state,party_no=a.party_no,slot_no=a.slot_no) for a in assignments if db.get(Round,a.round_id).cycle_key==date.fromisoformat(graph.raids.cycle(stamp).cycle_key)],
                comparison=comparison,build=build,is_me=m.user_id==uid,status='needs_review' if reason else 'valid',status_reason=reason))
        card=search.card(db,room,uid,stamp)
        return dict(room=card,settings=management.settings_view(db,room,mine) if mine else None,members_revision=room.members_revision,members=values,
            my_membership=dict(membership_id=mine.id,revision=mine.revision,room_role='leader' if mine.id==room.leader_membership_id else 'member',group_member=badge(db,room,uid)) if mine else None,
            plan_revision=room.plan_revision,permissions=card['permissions'],access=dict(state='allowed',policy_snapshot=base.context.policy(db,room),evaluated_at=stamp,issues=[]))


def summary(principal,rid):
    with search.snapshot(principal,public=True) as (db,uid,stamp):
        return search.card(db,base.room(db,uid,rid),uid,stamp)


def projections(principal,gid,rids,token=None,group_ids=None):
    if not rids or len(set(rids))!=len(rids):fail('INVALID_REQUEST',400)
    with base.snapshot(principal) as (db,uid,stamp):
        gids=group_ids if group_ids is not None else [gid]
        if gid not in gids:fail('INVALID_REQUEST',400)
        ctx,mapping=search.filter_context(db,uid,gids,stamp)
        if token is not None and token!=ctx['filter_context_token']:fail('FILTER_CONTEXT_STALE')
        refs={u:ref for ref,u in mapping.items()};values=[]
        for rid in rids:
            room=base.room(db,uid,rid)
            if room.group_id!=gid:fail('ROOM_NOT_FOUND',404)
            members=[]
            for m in graph.members(db,rid):
                a=db.scalar(select(Assignment).where(Assignment.membership_id==m.id).order_by(Assignment.joined_at.desc()).limit(1))
                gm=db.scalar(select(GroupMembership).where(GroupMembership.group_id==gid,GroupMembership.user_id==m.user_id,GroupMembership.ended_at.is_(None)))
                if a:members.append(dict(raid_membership_id=m.id,group_membership_id=gm.id if gm else None,member_ref=refs.get(m.user_id) if token and gm else None,character_id=a.character_id,display=a.display,group_member=gm is not None))
            values.append(dict(room_id=rid,members=members))
        return dict(group_id=gid,members_revision=next(g['members_revision'] for g in ctx['groups'] if g['group_id']==gid),evaluated_at=stamp,rooms=values)


def paginate(rows,limit,cursor,scope,revision):
    offset=cursor_decode(cursor,scope,revision) if cursor else 0
    if offset>len(rows):fail('INVALID_REQUEST',400)
    return rows[offset:offset+limit],cursor_encode(dict(scope=scope,revision=revision,offset=offset+limit)) if offset+limit<len(rows) else None


def memberships(principal,state,limit,cursor):
    with base.snapshot(principal) as (db,uid,stamp):
        cycle=date.fromisoformat(graph.raids.cycle(stamp).cycle_key);values=[]
        for m in db.scalars(select(Member).where(Member.user_id==uid).order_by(Member.joined_at.desc(),Member.id.desc())):
            current=m.ended_at is None
            if state!='all' and (state=='current')!=current:continue
            room=db.get(Room,m.room_id)
            assignments=list(db.scalars(select(Assignment).join(Round,Round.id==Assignment.round_id).where(Assignment.membership_id==m.id,Round.cycle_key==cycle).order_by(Assignment.joined_at.desc())))
            active=any(a.state=='active' for a in assignments);completed=any(a.state=='completed' for a in assignments)
            choices=list(db.scalars(select(Choice).where(Choice.membership_id==m.id,Choice.target_cycle==cycle+timedelta(days=7),Choice.ended_at.is_(None))))
            future='blocked' if any(c.state=='blocked' for c in choices) else 'selected' if choices else 'not_selected'
            can_view_current=current or room.scope=='public' or badge(db,room,uid)
            values.append(dict(membership_id=m.id,revision=m.revision,room_id=m.room_id,state='current' if current else 'ended',room_role='leader' if m.id==room.leader_membership_id else 'member',joined_at=m.joined_at,ended_at=m.ended_at,
                current_week_state='participating' if active else 'completed' if completed else 'stopped' if assignments else 'next_week_only',next_week_choice_state=future,
                assignments=[dict(assignment_id=a.id,revision=a.revision,item_id=a.item_id,round_id=a.round_id,character_id=a.character_id,selected_role=a.selected_role,state=a.state) for a in assignments],
                room=search.card(db,room,uid,stamp) if can_view_current else None,recovery_only=False,history_only=not current,permissions=dict(view_plan=dict(allowed=current,reason=None if current else 'ROOM_MEMBERSHIP_REQUIRED'))))
        head=db.get(MemberHead,uid);rev=head.membership_revision if head else 1
        values,token=paginate(values,limit,cursor,['memberships',str(uid),state,limit],digest([rev,values]))
        return dict(items=values,membership_head=rev,next_cursor=token,evaluated_at=stamp)


def applications(principal,rid,state,limit,cursor):
    with base.snapshot(principal) as (db,uid,stamp):
        if rid:
            room=base.room(db,uid,rid);base.member(db,uid,room,leader=True)
            query=select(Application).where(Application.room_id==rid)
        else:query=select(Application).where(Application.user_id==uid)
        values=[]
        for app in db.scalars(query.order_by(Application.created_at.desc(),Application.id.desc())):
            if state!='all' and app.state!=state:continue
            values.append(dict(application_id=app.id,room_id=app.room_id,revision=app.revision,state=app.state,created_at=app.created_at,expires_at=app.expires_at,ended_at=app.ended_at,
                character_id=app.character_id,selected_role=app.selected_role,display=app.display,admission_origin=dict(scope=app.origin_scope,group_id=app.origin_group_id)))
        head=db.get(DirectoryHead,1);rev=head.revision
        values,token=paginate(values,limit,cursor,['applications',str(uid),str(rid),state,limit],digest([rev,values]))
        return dict(items=values,applications_revision=rev,next_cursor=token,evaluated_at=stamp)


def time_context(principal,rid,target_session_id=None):
    with base.snapshot(principal) as (db,uid,stamp):
        room=base.room(db,uid,rid);base.member(db,uid,room)
        cycle=graph.raids.cycle(stamp);values=[]
        if target_session_id is not None and target_session_id not in {v.id for v in graph.sessions(db,rid,stamp)}:fail('SESSION_NOT_FOUND',404)
        for m in graph.members(db,rid):
            table=db.get(AvailabilitySubmission,m.id)
            reservations=list(db.scalars(select(Reservation).where(Reservation.user_id==m.user_id,Reservation.session_id!=target_session_id if target_session_id is not None else True,Reservation.starts_at<cycle.ends_at,Reservation.ends_at>cycle.starts_at).order_by(Reservation.starts_at,Reservation.ends_at)))
            revision=1+sum(r.schedule_revision+1+int(r.released_at is not None) for r in reservations)
            intervals=[]
            for r in reservations:
                if r.released_at is not None:continue
                start=max(r.starts_at,cycle.starts_at);end=min(r.ends_at,cycle.ends_at)
                if intervals and start<=intervals[-1]['ends_at']:intervals[-1]['ends_at']=max(end,intervals[-1]['ends_at'])
                else:intervals.append(dict(starts_at=start,ends_at=end))
            from app.raid_rooms.availability import submission_output
            a=db.scalar(select(Assignment).where(Assignment.membership_id==m.id).order_by(Assignment.joined_at.desc()).limit(1))
            values.append(dict(membership_id=m.id,display=a.display if a else None,submission=submission_output(m,table),
                anonymous_busy=dict(state='ready',revision=revision,intervals=intervals)))
        return dict(room_id=rid,cycle_key=cycle.cycle_key,members_revision=room.members_revision,plan_revision=room.plan_revision,evaluated_at=stamp,members=values,
            target_session_id=target_session_id,permissions=dict(view_schedule_context=dict(allowed=True,reason=None)))


def overlaps(principal,limit,cursor):
    with base.snapshot(principal) as (db,uid,stamp):
        allowed=set(db.scalars(select(Member.room_id).join(Room,Room.id==Member.room_id).where(Member.user_id==uid,Member.ended_at.is_(None),Room.ended_at.is_(None))))
        reservations=list(db.scalars(select(Reservation).where(Reservation.user_id==uid,Reservation.room_id.in_(allowed),Reservation.released_at.is_(None),Reservation.ends_at>stamp).order_by(Reservation.starts_at,Reservation.id)))
        pairs=[]
        def endpoint(r):
            a=db.get(Assignment,r.assignment_id);rd=db.get(Round,r.round_id);item=db.get(graph.Item,r.item_id);room=db.get(Room,r.room_id)
            raid=next((v for v in graph.raids.catalog().raids if v.raid_id==item.raid_id),None)
            return dict(reservation_id=r.id,room_id=r.room_id,item_ids=[r.item_id],session_id=r.session_id,character_id=a.character_id,character_display=a.display,
                raid_display=dict(raid_id=item.raid_id,difficulty_id=rd.difficulty_id,display_name=raid.display_name if raid else item.raid_id),room_title=room.title,starts_at=r.starts_at,ends_at=r.ends_at)
        for i,a in enumerate(reservations):
            for b in reservations[i+1:]:
                if b.starts_at>=a.ends_at:break
                if a.session_id==b.session_id:continue
                pairs.append(dict(pair_id=digest(sorted([[str(a.id),a.schedule_revision],[str(b.id),b.schedule_revision]])),left=endpoint(a),right=endpoint(b),starts_at=max(a.starts_at,b.starts_at),ends_at=min(a.ends_at,b.ends_at)))
        pairs.sort(key=lambda p:(p['starts_at'],p['pair_id']));count=len(pairs)
        affected={p[side]['reservation_id'] for p in pairs for side in ('left','right')}
        room_count=len({r.room_id for r in reservations if r.id in affected})
        revision=digest([[str(r.id),r.schedule_revision] for r in reservations]);page,token=paginate(pairs,limit,cursor,['overlaps',str(uid),limit],revision)
        return dict(items=page,cycle_key=graph.raids.cycle(stamp).cycle_key,pair_count=count,affected_room_count=room_count,reservation_count=len(affected),revision=revision,next_cursor=token,evaluated_at=stamp)
