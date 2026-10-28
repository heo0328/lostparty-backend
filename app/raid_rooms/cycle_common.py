"""Global commands bind every actual effect; no invented target or G1 fallback."""
from app.raid_rooms import beta_profile
from datetime import timedelta,datetime
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.auth.models import User
from app.groups.models import Group,GroupMembership
from app.game_accounts.support import fail,GameError
from app.game_accounts.lifecycle import digest
from app.raid_rooms import (cycles,cycle_commands as commands,cycle_lifecycle as life,cycle_planning as plan,
    cycle_management as management,cycle_leadership as leadership,cycle_schedule as graph,
    cycle_outcomes as outcomes,command_context as opaque,cycle_wire as wire)
from app.raid_rooms.cycle_models import RoomCycle,CycleMember,CycleGeneration
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.source_models import TimeReservation as Reservation
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentRound as Round,RecruitmentItem as Item
from app.raid_rooms.cycle_creation import permission


def snapshot(obj):return plan.snapshot(obj) if obj is not None else None


def scope(stamp):return dict(server_now=stamp,current_cycle_key=commands.raids.cycle(stamp).cycle_key,policy_version=cycles.POLICY)


def authority(db,uid,room,stamp):
    row=cycles.common_authority_cycle(db,room.id,stamp)
    if row is None:fail('COMMON_AUTHORITY_UNAVAILABLE',403)
    if row.state=='review_required' or row.generation is None:fail('ROOM_REVIEW_REQUIRED')
    cm=life.actual_member(db,row,uid)
    if cm is None or commands.leadership(db,row)['leader_cycle_member_id']!=cm.id:fail('COMMON_LEADER_REQUIRED',403)
    life.qualify(db,room,row,cm)
    return row


def linked_group(db,uid,room):
    if room.group_id is None:return
    group=db.get(Group,room.group_id)
    if group is None or group.ended_at is not None:fail('GROUP_NOT_ACTIVE')
    if db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==group.id,GroupMembership.user_id==uid,
            GroupMembership.ended_at.is_(None))) is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)


def common_permission(db,uid,room,stamp):
    try:authority(db,uid,room,stamp);return permission(None)
    except GameError as error:return permission(error.code)


def context(db,uid,rid,kind,stamp):
    outcomes.ready(db)
    if kind not in ('edit_common_settings','leave','end'):fail('INVALID_REQUEST',400)
    room=commands.base.room(db,uid,rid);actor=commands.base.member(db,uid,room)
    from app.raid_rooms.completed_room_lifecycle import require_active
    require_active(db,rid)
    current=cycles.target(stamp,commands.raids.cycle(stamp).cycle_key).current
    rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id==rid,
        RoomCycle.cycle_key.in_((current,current+timedelta(days=7)))).order_by(RoomCycle.cycle_key)))
    members=list(db.scalars(select(Member).where(Member.room_id==rid,Member.ended_at.is_(None)).order_by(Member.id)))
    public=[];hidden=[];effects=[];reason=None;auth=cycles.common_authority_cycle(db,rid,stamp)
    if kind!='leave':
        try:authority(db,uid,room,stamp)
        except GameError as error:reason=error.code
    if kind=='end' and len(members)!=1:reason=reason or 'ROOM_LAST_MEMBER_REQUIRED'
    for row in rows:
        actual=list(db.scalars(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
            CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
            CycleMember.state.in_((*life.VALID_STATES,'review_required')),Member.ended_at.is_(None)).order_by(CycleMember.id)))
        mine=next((m for m in actual if m.membership_id==actor.id),None)
        all_assignments=outcomes.assignments(db,row) if row.generation is not None else []
        active=[a for a in all_assignments if a.state=='active' and (kind!='leave' or a.membership_id==actor.id)]
        parts=[p for cm in actual for p in leadership.own_parts(db,row,cm)]
        reservations=list(db.scalars(select(Reservation).where(Reservation.assignment_id.in_([a.id for a in all_assignments])).order_by(Reservation.id)))
        ledgers=[]
        for a in all_assignments:
            rd=db.get(Round,a.round_id);item=db.get(Item,a.item_id)
            identity=(a.user_id,a.character_id,item.raid_id,rd.cycle_key)
            ledgers.append([snapshot(db.get(life.WeeklyState,identity)),snapshot(db.get(life.WeeklyOccupancy,identity))])
        apps=list(db.scalars(select(CycleApplication).where(CycleApplication.cycle_id==row.id,CycleApplication.state=='pending').order_by(CycleApplication.id)))
        hidden.append([snapshot(row),[snapshot(m) for m in actual],[[str(m.user_id),db.get(User,m.user_id).status] for m in actual],
            [snapshot(a) for a in all_assignments],[snapshot(p) for p in parts],
            [snapshot(r) for r in reservations],ledgers,[snapshot(a) for a in apps]])
        effect=(kind=='edit_common_settings' and row.generation is not None) or (row.state in ('open','review_required') and (kind=='end' or mine is not None)) or bool(active)
        if kind=='end' and (any(m.membership_id!=actor.id for m in actual) or any(a.user_id!=uid and a.state=='active' for a in all_assignments)):reason=reason or 'ROOM_LAST_MEMBER_REQUIRED'
        if not effect:continue
        if any(m.state=='review_required' and (kind=='end' or m.membership_id==actor.id) for m in actual):reason=reason or 'ROOM_REVIEW_REQUIRED'
        if row.generation is None or row.state=='review_required':reason=reason or 'ROOM_REVIEW_REQUIRED';continue
        lead=commands.leadership(db,row)
        if kind=='leave' and row.state=='open' and mine and lead['leader_cycle_member_id']==mine.id:
            reason=reason or 'LEADERSHIP_RESOLUTION_REQUIRED'
        public.append(dict(target_cycle_key=row.cycle_key,room_cycle_id=row.id,generation=row.generation,target_revision=row.revision,
            leadership=lead,member_count=len(actual) if kind!='leave' else int(mine is not None),assignment_count=len(active),
            reservation_count=sum(r.released_at is None and (kind!='leave' or r.membership_id==actor.id) for r in reservations),
            members_revision=row.members_revision,plan_revision=row.plan_revision,actor_cycle_member_id=mine.id if mine else None,
            actor_cycle_member_revision=mine.revision if mine else None))
        effects.append((row,actual,mine))
    group=db.get(Group,room.group_id) if room.group_id else None
    memberships=list(db.scalars(select(GroupMembership).where(GroupMembership.group_id==room.group_id,
        GroupMembership.user_id==uid).order_by(GroupMembership.id))) if group else []
    data=dict(room_id=rid,command=kind,room_revision=room.revision,persistent_membership_revision=actor.revision,
        impact_cycles=public,permission=permission(reason),expected_cycle_key=current,authorization_cycle_key=auth.cycle_key if auth else None,
        current_settings=dict(title=room.title,scope=room.scope,group_id=room.group_id,group_revision=group.revision if group else None))
    auth_proof=None
    if kind!='leave' and reason is None:
        auth_cm=life.actual_member(db,auth,uid);_,auth_proof=life.qualify(db,room,auth,auth_cm)
    binding=digest(jsonable_encoder([auth_proof,uid,kind,scope(stamp)['current_cycle_key'],data,snapshot(room),snapshot(actor),
        [snapshot(m) for m in members],hidden,snapshot(group),[snapshot(m) for m in memberships]]))
    expires=min(stamp+timedelta(seconds=120),commands.raids.cycle(stamp).ends_at)
    data.update(context_token=opaque.seal(dict(actor=str(uid),room=str(rid),command=kind,digest=binding,expires=expires.isoformat())),issued_at=stamp,expires_at=expires)
    return dict(scope=scope(stamp),data=data),binding,room,actor,effects


def get(principal,rid,kind):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        result,*_=context(db,uid,rid,kind,stamp)
        return wire.CommonContext.model_validate(result).model_dump(mode='json')


def execute(principal,rid,key,data,kind):
    body=beta_profile.body(data)
    def run(db,uid,stamp):
        if body['expected_cycle_key']!=commands.raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        token=opaque.unseal(body['context_token'])
        if (token.get('actor'),token.get('room'),token.get('command'))!=(str(uid),str(rid),kind):fail('TARGET_SCOPE_MISMATCH',400)
        if stamp>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
        result,binding,room,actor,effects=context(db,uid,rid,kind,stamp)
        if body['expected_room_revision']!=room.revision or body.get('expected_persistent_membership_revision',actor.revision)!=actor.revision:fail('REVISION_CONFLICT')
        life.require_match(token,binding)
        allowed=result['data']['permission']
        if not allowed['allowed']:
            reason=allowed['reason'];fail(reason,403 if reason in ('COMMON_LEADER_REQUIRED','COMMON_AUTHORITY_UNAVAILABLE','GROUP_MEMBERSHIP_REQUIRED','OWNERSHIP_REQUIRED','SOURCE_PARTICIPATION_REQUIRED') else 409)
        guards=[graph.final_deadlines(db,row,[],stamp,join=False) for row,_,_ in effects] if kind!='edit_common_settings' else []
        affected=[];changed=True
        if kind=='edit_common_settings':
            if data.group_id!=room.group_id:fail('GROUP_LINK_IMMUTABLE')
            if data.scope=='group' and room.group_id is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)
            if room.group_id is not None:
                group=db.get(Group,room.group_id)
                if body['expected_group_revision']!=(group.revision if group else None):fail('REVISION_CONFLICT')
                # Only entering group scope needs new group authority. Existing
                # raid leadership survives leaving or losing the linked group.
                if data.scope=='group' and room.scope!='group':
                    linked_group(db,uid,room)
            elif data.expected_group_revision is not None:fail('INVALID_REQUEST',400)
            changed=(room.title,room.scope)!=(data.title,data.scope)
            if changed:
                room.title=data.title;room.scope=data.scope;room.revision+=1
                affected=[row.cycle_key for row,_,_ in effects]
                for cycle in affected:cycles.touch_directory(db,cycle)
            value=dict(scope=scope(stamp),data=dict(command_id=key,outcome='applied' if changed else 'noop',executed_at=stamp,
                room_id=rid,room_revision=room.revision,affected_cycle_keys=affected))
            dto=wire.CommonSettingsAck
        else:
            for row,members,mine in effects:
                for cm in members:
                    if cm.membership_id==actor.id and cm.state in life.VALID_STATES:
                        management.remove_member(db,room,row,cm,key,stamp)
                # With no remaining actual participants, close only this live target.
                db.flush()
                remaining=life.admission.member_count(db,row)
                if row.state=='open' and remaining==0:
                    retained=list(db.scalars(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
                        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
                        CycleMember.state.in_(life.VALID_STATES),Member.ended_at.is_(None))))
                    if retained and kind!='end':
                        row.state='closed';generation=db.get(CycleGeneration,(row.id,row.generation))
                        generation.state='stopped' if any(m.state=='stopped' for m in retained) else 'completed'
                        generation.closed_at=stamp
                    else:leadership.close_target(db,row,stamp)
                    outcomes.obsolete(db,row)
                row.members_revision+=1;plan.bump(db,row)
                if row.state=='open':plan.refresh(db,room,row,uid,key,stamp)
                affected.append(row.cycle_key)
            # Pending applications are not actual participation, but may not outlive
            # an explicitly ended persistent relationship/room.
            for app in db.scalars(select(CycleApplication).where(CycleApplication.room_id==rid,CycleApplication.state=='pending')):
                if kind=='end' or app.user_id==uid:app.state='cancelled';app.ended_at=stamp;app.revision+=1
            actor.ended_at=stamp;actor.revision+=1;room.revision+=1
            if kind=='end':room.ended_at=stamp
            life.admission.core.legacy.touch_user(db,uid)
            value=dict(scope=scope(stamp),data=dict(command_id=key,outcome='applied',executed_at=stamp,room_id=rid,
                membership_id=actor.id,persistent_membership_revision=actor.revision,affected_cycle_keys=affected,room_ended=kind=='end',
                revisions=[dict(resource='room',id=rid,revision=room.revision),dict(resource='membership',id=actor.id,revision=actor.revision)]))
            dto=wire.GlobalMembershipAck
        db.flush()
        def final(current):
            for guard in guards:guard(current)
            if current>=datetime.fromisoformat(token['expires']):fail('COMMAND_CONTEXT_EXPIRED')
        return 200,dto.model_validate(value).model_dump(mode='json'),final
    return cycles.execute(principal,{'edit_common_settings':'common-settings','leave':'global-leave','end':'global-end'}[kind],key,
        dict(room_id=str(rid),body=body),run)
