"""R2-C integrated unscheduled commands. Main activation remains at R5."""
import uuid
from datetime import timedelta
from contextlib import contextmanager
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from app.core.database import session, now
from app.game_accounts.support import authorize,fail,reserve,release,commit_result,GameError
from app.groups.admission_core import display
from app.groups.models import GroupMembership
from app.raid_rooms import admission_context as context, participation_core as core
from app.raid_rooms import admission_schemas as s
from app.raid_rooms.participation_commands import Selection, Target
from app.raid_rooms.integrated_models import (RecruitmentRoom as Room,RecruitmentItem as Item,
    RecruitmentRound as Round,RecruitmentMembership as Member,RecruitmentAssignment as Assignment,RecruitmentSession as Session)
from app.raid_rooms.source_models import RoomSettings, ItemSettings, RecruitmentApplication as Application, OpeningEvent, ScheduleGroup
from app.raids import service as raids

DURATION_POLICY='difficulty-duration-v1'
DEFAULT_DURATION={'normal':10,'hard':20,'nightmare':30,'stage1':10,'stage2':20,'stage3':30}


@contextmanager
def snapshot(principal):
    with session() as db,db.begin():
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        db.execute(text('SET TRANSACTION READ ONLY'))
        yield db,authorize(db,principal),now(db)


def room(db,uid,rid):
    row=db.get(Room,rid)
    if row is None:fail('ROOM_NOT_FOUND',404)
    if row.scope=='group' and db.scalar(select(Member.id).where(Member.room_id==rid,Member.user_id==uid,Member.ended_at.is_(None))) is None:
        if db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==row.group_id,
                GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is None:fail('ROOM_NOT_FOUND',404)
    return row


def member(db,uid,row,leader=False):
    value=db.scalar(select(Member).where(Member.room_id==row.id,Member.user_id==uid,Member.ended_at.is_(None)))
    if value is None:fail('ROOM_MEMBERSHIP_REQUIRED',403)
    if leader and value.id!=row.leader_membership_id:fail('ROOM_LEADER_REQUIRED',403)
    return value


def unscheduled(db,row):
    if row.ended_at is not None:fail('ROOM_NOT_ACTIVE')
    if row.migration_state!='ready':fail('ROOM_REVIEW_REQUIRED')


def cas(row,data):
    if (row.revision!=data.expected_room_revision or row.members_revision!=data.expected_members_revision or row.plan_revision!=data.expected_plan_revision):
        fail('REVISION_CONFLICT')


def revision(resource,row,version=None):
    return dict(resource=resource,id=row.id,revision=version if version is not None else row.revision)


def ack(key,row,membership,assignments,stamp,*,application=None):
    revisions=[revision('room',row),revision('members',row,row.members_revision),revision('plan',row,row.plan_revision)]
    revisions += [revision('membership',membership)]+[revision('assignment',r) for r in assignments]
    if application is not None:revisions.append(revision('application',application))
    return dict(command_id=key,outcome='applied',revisions=revisions,executed_at=stamp)


def execute(principal,operation,key,payload,run):
    ticket,replay=reserve(principal,'recruitment-'+operation,key,payload)
    if replay:return replay  # reserve reauthenticates; original actor/key/body owns this minimal ACK.
    try:
        with session() as db,db.begin():
            uid=authorize(db,principal,write=True)
            from app.raid_rooms.v1_compat import reject_write
            reject_write(db)
            stamp=now(db);cycle=raids.cycle(stamp)
            outcome=run(db,uid,stamp)
            status,result=outcome[:2]
            if result.get('outcome')!='noop':core.legacy.directory(db)
            value=commit_result(db,ticket,status,result)
            db.flush()
            final=now(db)
            if raids.cycle(final).cycle_key!=cycle.cycle_key:fail('CYCLE_CHANGED')
            if len(outcome)==3:outcome[2](final)
            return value
    except Exception:
        release(ticket)
        raise


def creation_context(principal,cid,role,items,gid):
    with snapshot(principal) as (db,uid,stamp):return context.creation(db,uid,cid,role,items,gid,stamp)


def admission_context(principal,rid,cid,role,intent):
    with snapshot(principal) as (db,uid,stamp):
        row=room(db,uid,rid);unscheduled(db,row)
        return context.admission(db,uid,row,cid,role,intent,stamp)


def create(principal,key,data):
    def run(db,uid,stamp):
        current=context.creation(db,uid,data.selection.character_id,data.selection.selected_role,
            [s.ItemChoice(raid_id=i.raid_id,difficulty_id=i.difficulty_id) for i in data.items],data.group_id,stamp)
        context.verify(data.selection_context.context_token,current['context_token'])
        if data.selection!=current['selection']:fail('REVISION_CONFLICT')
        if data.expected_cycle_key!=current['expected_cycle_key']:fail('CYCLE_CHANGED')
        if data.expected_catalog_version!=current['catalog_version']:fail('CATALOG_VERSION_CONFLICT')
        if data.expected_group_revision!=current['group_revision']:fail('REVISION_CONFLICT')
        if [i.expected_weekly_revision for i in data.items]!=[i['expected_weekly_revision'] for i in current['targets']]:fail('REVISION_CONFLICT')
        rid,mid=uuid.uuid4(),uuid.uuid4()
        party_size=next(r.party_size for r in raids.catalog().raids if r.raid_id==data.items[0].raid_id) if len(data.items)==1 else 4
        row=Room(id=rid,leader_membership_id=mid,title=data.title,scope=data.scope,group_id=data.group_id,
            app_capacity=party_size,revision=1,members_revision=1,plan_revision=1,migration_state='ready',created_at=stamp)
        db.add(row);db.flush()
        db.add(Member(id=mid,room_id=rid,user_id=uid,revision=1,joined_at=stamp));db.flush()
        combat=data.combat_requirement
        db.add(RoomSettings(room_id=rid,revision=1,continuation_revision=1,admission_mode=data.admission_mode,
            experience_level=data.experience_level,combat_input_mode=combat.input_mode,dealer_min=combat.dealer_min,
            support_min=combat.support_min,continuation_enabled=data.continuation.enabled,
            auto_open_enabled=data.continuation.auto_open_enabled,
            auto_open_effective_cycle=core.weekly.parse_cycle(current['expected_cycle_key'])+timedelta(days=7) if data.continuation.auto_open_enabled else None))
        targets=[];items=[];rounds=[]
        for choice in data.items:
            if choice.duration_minutes is None and choice.difficulty_id not in DEFAULT_DURATION:fail('DURATION_POLICY_UNAVAILABLE')
            item=Item(id=uuid.uuid4(),room_id=rid,raid_id=choice.raid_id,revision=1,created_at=stamp)
            db.add(item);db.flush()
            rd=Round(id=uuid.uuid4(),room_id=rid,item_id=item.id,cycle_key=core.weekly.parse_cycle(current['expected_cycle_key']),
                difficulty_id=choice.difficulty_id,catalog_version=current['catalog_version'],
                game_party_size=next(r.party_size for r in raids.catalog().raids if r.raid_id==choice.raid_id),revision=1,state='active',created_at=stamp)
            db.add(rd);db.flush()
            db.add(ItemSettings(item_id=item.id,room_id=rid,revision=1,difficulty_id=choice.difficulty_id,
                catalog_version=current['catalog_version'],duration_minutes=choice.duration_minutes,duration_policy_version=DURATION_POLICY))
            db.add(OpeningEvent(id=uuid.uuid4(),room_id=rid,item_id=item.id,target_cycle=rd.cycle_key,mode='manual',
                settings_revision=1,authorized_effective_at=stamp,search_floor_at=stamp+timedelta(minutes=30),processed_at=stamp,state='applied'))
            targets.append(Target(item_id=item.id,round_id=rd.id,party_no=choice.party_no,
                expected_round_revision=1,expected_weekly_revision=choice.expected_weekly_revision))
            items.append(item);rounds.append(rd)
        db.flush()
        membership,assignments,_=core.admit_bundle(db,uid,row,data.selection,targets,current['expected_cycle_key'])
        from app.raid_rooms import scheduling
        scheduling.install(db,row,data.schedule_groups,stamp,creating=True)
        scheduling.evaluate_initial(db,row,stamp)
        row.revision=row.members_revision=row.plan_revision=1
        result=ack(key,row,membership,assignments,stamp)
        result['revisions'] += [revision('item',i) for i in items]+[revision('round',r) for r in rounds]
        return 201,result
    return execute(principal,'create',key,jsonable_encoder(data),run)


def admit(principal,rid,key,data,*,applying=False):
    def run(db,uid,stamp):
        row=room(db,uid,rid);unscheduled(db,row);cas(row,data)
        from app.raid_rooms import scheduling,proposals
        scheduling.deadlines(db,row,data.target_session_ids,stamp)
        existing_deadlines=[s.starts_at-timedelta(minutes=30) for s in scheduling.sessions(db,rid)
            if s.state=='confirmed' and (db.get(scheduling.SessionBinding,s.id).required or s.id in data.target_session_ids)]
        current=context.admission(db,uid,row,data.selection.character_id,data.selection.selected_role,'apply' if applying else 'join',stamp)
        context.verify(data.selection_context.context_token,current['context_token'])
        if data.selection!=current['selection']:fail('REVISION_CONFLICT')
        if data.expected_policy_snapshot!=current['policy_snapshot']:fail('POLICY_CONTEXT_CHANGED')
        if data.expected_cycle_key!=current['expected_cycle_key']:fail('CYCLE_CHANGED')
        if data.expected_catalog_version!=current['catalog_version']:fail('CATALOG_VERSION_CONFLICT')
        permission=current['permissions']['apply' if applying else 'join']
        if not permission['allowed']:fail(permission['reason'])
        mine=db.scalar(select(Member).where(Member.room_id==rid,Member.user_id==uid,Member.ended_at.is_(None)))
        if mine is not None and db.scalar(select(Assignment.id).join(Round,Round.id==Assignment.round_id).where(
                Assignment.membership_id==mine.id,Assignment.state=='active',Round.cycle_key==core.weekly.parse_cycle(data.expected_cycle_key))) is not None:fail('ROOM_MEMBER_EXISTS')
        session_ids={s.id for s in scheduling.sessions(db,rid)}
        if len(set(data.target_session_ids))!=len(data.target_session_ids) or set(data.target_session_ids)-session_ids:fail('INVALID_REQUEST',400)
        membership,assignments,power=core.admit_bundle(db,uid,row,data.selection,data.target_items,data.expected_cycle_key,validate_only=applying,pending=applying)
        if applying:
            pending=db.scalar(select(Application).where(Application.room_id==rid,Application.user_id==uid,Application.state=='pending'))
            if pending is not None:
                if pending.expires_at>stamp:fail('ROOM_APPLICATION_EXISTS')
                pending.state='expired';pending.ended_at=stamp;pending.revision+=1;db.flush()
            app_id=uuid.uuid4()
            build=jsonable_encoder(power)
            source=db.get(core.RolePowerSuccess,(uid,data.selection.character_id,data.selection.expected_ownership_revision,data.selection.selected_role))
            if source is not None:build['success_summary']=source.source_summary
            build['admission_origin']=dict(application_id=str(app_id),room_id=str(rid),actor_id=str(uid),
                scope=row.scope,group_id=str(row.group_id) if row.group_id else None,scope_revision=row.revision,created_at=stamp.isoformat())
            build['target_session_ids']=[str(i) for i in data.target_session_ids]
            value=Application(id=app_id,room_id=rid,user_id=uid,revision=1,
                selection=jsonable_encoder(data.selection),targets=jsonable_encoder(data.target_items),
                display=display(core.identity.selected_character(db,uid,jsonable_encoder(data.selection))),build=build,
                origin_state='known',origin_scope=row.scope,origin_group_id=row.group_id,state='pending',
                created_at=stamp,expires_at=raids.cycle(stamp).ends_at)
            db.add(value);core.legacy.touch_user(db,uid,application=True)
            result=(201,dict(command_id=key,room_id=rid,application_id=value.id,revision=1,state='pending',executed_at=stamp))
        else:
            scheduling.enrol(db,row,membership,data.target_session_ids,stamp)
            scheduling.evaluate_initial(db,row,stamp);proposals.reevaluate(db,row,stamp)
            result=(200,ack(key,row,membership,assignments,stamp))
        def final(current):
            if any(current>=deadline for deadline in existing_deadlines):fail('RECRUITMENT_CLOSED')
        return *result,final
    return execute(principal,'apply' if applying else 'join',key,dict(room_id=str(rid),body=jsonable_encoder(data)),run)


def approve(principal,aid,key,data):
    def run(db,uid,stamp):
        app=db.get(Application,aid)
        if app is None:fail('ROOM_APPLICATION_NOT_FOUND',404)
        row=db.get(Room,app.room_id);actor=member(db,uid,row,leader=True)
        unscheduled(db,row);cas(row,data)
        if data.expected_cycle_key!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        if app.revision!=data.expected_application_revision:fail('REVISION_CONFLICT')
        if app.state!='pending' or stamp>=app.expires_at:fail('APPLICATION_NOT_PENDING')
        require_origin(app)
        from app.raid_rooms import scheduling,proposals
        selected=[uuid.UUID(i) for i in app.build.get('target_session_ids',[])]
        scheduling.deadlines(db,row,selected,stamp)
        existing_deadlines=[s.starts_at-timedelta(minutes=30) for s in scheduling.sessions(db,row.id)
            if s.state=='confirmed' and (db.get(scheduling.SessionBinding,s.id).required or s.id in selected)]
        original=Selection.model_validate(app.selection)
        choice=context.selection(db,app.user_id,original.character_id,original.selected_role)
        if (choice.expected_ownership_revision!=original.expected_ownership_revision or
                choice.expected_lifecycle_revision!=original.expected_lifecycle_revision):fail('APPLICATION_CONTEXT_CHANGED')
        targets=[]
        for saved in app.targets:
            target=Target.model_validate(saved)
            rd=db.get(Round,target.round_id);item=db.get(Item,target.item_id)
            if rd is None or item is None or rd.room_id!=row.id or rd.item_id!=item.id:fail('APPLICATION_CONTEXT_CHANGED')
            state=db.get(core.WeeklyState,(app.user_id,choice.character_id,item.raid_id,rd.cycle_key))
            targets.append(target.model_copy(update=dict(expected_round_revision=rd.revision,expected_weekly_revision=state.revision if state else 1)))
        membership,assignments,_=core.admit_bundle(db,app.user_id,row,choice,targets,data.expected_cycle_key,public_origin_application=app)
        scheduling.enrol(db,row,membership,selected,stamp);scheduling.evaluate_initial(db,row,stamp);proposals.reevaluate(db,row,stamp)
        app.state='accepted';app.ended_at=stamp;app.revision+=1
        core.legacy.touch_user(db,app.user_id,application=True)
        def final(current):
            if current>=app.expires_at:fail('APPLICATION_NOT_PENDING')
            if any(current>=deadline for deadline in existing_deadlines):fail('RECRUITMENT_CLOSED')
        return 200,ack(key,row,membership,assignments,stamp,application=app),final
    return execute(principal,'approve',key,dict(application_id=str(aid),body=jsonable_encoder(data)),run)


def plan(principal,rid):
    with snapshot(principal) as (db,uid,stamp):
        row=room(db,uid,rid);mine=member(db,uid,row);unscheduled(db,row)
        cycle=raids.cycle(stamp).cycle_key
        items=[];rounds={};seen_items=set()
        for item,rd in db.execute(select(Item,Round).join(Round,Round.item_id==Item.id).where(
                Item.room_id==rid,Round.cycle_key==core.weekly.parse_cycle(cycle)).order_by(Item.id,Round.created_at.desc(),Round.id.desc())):
            rounds[rd.id]=rd
            if item.id in seen_items:continue
            seen_items.add(item.id)
            items.append(dict(item_id=item.id,revision=item.revision,raid_id=item.raid_id,difficulty_id=rd.difficulty_id,
                catalog_version=rd.catalog_version,game_party_size=rd.game_party_size,round_id=rd.id,round_revision=rd.revision,round_state=rd.state))
        assignments=[]
        for value in db.scalars(select(Assignment).where(Assignment.membership_id==mine.id,Assignment.round_id.in_(rounds)).order_by(Assignment.id)):
            assignments.append(dict(assignment_id=value.id,revision=value.revision,membership_id=mine.id,item_id=value.item_id,
                round_id=value.round_id,cycle_key=cycle,character_id=value.character_id,selected_role=value.selected_role,
                state=value.state,ended_at=value.ended_at,raid_participation_state=value.state,
                completion_source=(value.build or {}).get('completion_source'),completed_at=(value.build or {}).get('completed_at')))
        group_member=row.group_id is not None and db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==row.group_id,
            GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is not None
        result=dict(room_id=rid,revision=row.plan_revision,members_revision=row.members_revision,cycle_key=cycle,server_time=stamp,
            app_capacity=row.app_capacity,game_items=items,schedule_state='unscheduled',schedule_groups=[],sessions=[],session_segments=[],
            my_membership=dict(membership_id=mine.id,revision=mine.revision,room_role='leader' if mine.id==row.leader_membership_id else 'member',group_member=group_member),
            my_assignments=assignments,my_participations=[],proposals=[],permissions={name:dict(allowed=False,reason='RECRUITMENT_COMMAND_NOT_READY')
                for name in ('edit_schedule_groups','leave','transfer_leadership','end')})
        from app.raid_rooms.schedule_views import fields
        result.update(fields(db,row,mine,stamp))
        leader=mine.id==row.leader_membership_id
        active_members=list(db.scalars(select(Member.id).where(Member.room_id==rid,Member.ended_at.is_(None))))
        for name,allowed,reason in [('edit_schedule_groups',leader and not any(s['state']=='confirmed' for s in result['sessions']),'SCHEDULE_PROPOSAL_REQUIRED' if leader else 'ROOM_LEADER_REQUIRED'),
            ('leave',not leader,'LEADERSHIP_RESOLUTION_REQUIRED'),('transfer_leadership',leader and len(active_members)>1,'ROOM_TRANSFER_TARGET_INVALID'),
            ('end',leader and len(active_members)==1,'ROOM_LAST_MEMBER_REQUIRED')]:
            result['permissions'][name]=dict(allowed=allowed,reason=None if allowed else reason)
        return result


def require_origin(app):
    origin=app.build.get('admission_origin',{}) if isinstance(app.build,dict) else {}
    if (not isinstance(origin,dict) or app.origin_state!='known' or origin.get('application_id')!=str(app.id) or
            origin.get('room_id')!=str(app.room_id) or origin.get('actor_id')!=str(app.user_id) or
            origin.get('scope')!=app.origin_scope or origin.get('group_id')!=(str(app.origin_group_id) if app.origin_group_id else None) or
            type(origin.get('scope_revision')) is not int or origin['scope_revision']<1):
        fail('APPLICATION_ORIGIN_REVIEW_REQUIRED')


def application(principal,aid):
    with snapshot(principal) as (db,uid,stamp):
        app=db.get(Application,aid)
        if app is None:fail('ROOM_APPLICATION_NOT_FOUND',404)
        row=db.get(Room,app.room_id)
        mine=db.scalar(select(Member).where(Member.room_id==row.id,Member.user_id==uid,Member.ended_at.is_(None)))
        leader=mine is not None and mine.id==row.leader_membership_id
        if uid!=app.user_id and not leader:fail('ROOM_APPLICATION_NOT_FOUND',404)
        state='expired' if app.state=='pending' and stamp>=app.expires_at else app.state
        view=dict(application_id=aid,room_id=row.id,revision=app.revision,state=state,
            created_at=app.created_at,expires_at=app.expires_at,ended_at=app.expires_at if state=='expired' else app.ended_at,
            display=app.display,character_id=app.selection['character_id'],selected_role=app.selection['selected_role'],
            admission_origin=dict(scope=app.origin_scope,group_id=str(app.origin_group_id) if app.origin_group_id else None))
        if not leader:return view
        if row.scope=='group' and db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==row.group_id,
                GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None))) is None:fail('GROUP_MEMBERSHIP_REQUIRED',403)
        unscheduled(db,row)
        require_origin(app)
        reason=None;comparison=None
        try:
            if state!='pending':fail('APPLICATION_NOT_PENDING')
            original=Selection.model_validate(app.selection)
            choice=context.selection(db,app.user_id,original.character_id,original.selected_role)
            if (choice.expected_ownership_revision!=original.expected_ownership_revision or
                    choice.expected_lifecycle_revision!=original.expected_lifecycle_revision):fail('APPLICATION_CONTEXT_CHANGED')
            targets=[]
            for saved in app.targets:
                target=Target.model_validate(saved);rd=db.get(Round,target.round_id);item=db.get(Item,target.item_id)
                if rd is None or item is None:fail('APPLICATION_CONTEXT_CHANGED')
                weekly=db.get(core.WeeklyState,(app.user_id,choice.character_id,item.raid_id,rd.cycle_key))
                targets.append(target.model_copy(update=dict(expected_round_revision=rd.revision,expected_weekly_revision=weekly.revision if weekly else 1)))
            settings=db.get(RoomSettings,row.id)
            comparison=core.power_comparison(db,app.user_id,choice,settings.dealer_min if choice.selected_role=='dealer' else settings.support_min)
            core.admit_bundle(db,app.user_id,row,choice,targets,raids.cycle(stamp).cycle_key,validate_only=True,public_origin_application=app)
        except GameError as error:reason=error.code
        return dict(application=view,
            room_revision=row.revision,members_revision=row.members_revision,plan_revision=row.plan_revision,server_time=stamp,
            eligibility=dict(evaluated_at=stamp,state='blocked' if reason else 'eligible',reasons=[reason] if reason else [],comparison=comparison),
            permissions=dict(approve=dict(allowed=leader and reason is None,reason=reason if leader else 'ROOM_LEADER_REQUIRED'),
                reject=dict(allowed=leader and state=='pending',reason=None if leader and state=='pending' else 'APPLICATION_NOT_PENDING')))


def finish_application(principal,aid,key,data,*,withdrawing=False):
    def run(db,uid,stamp):
        app=db.get(Application,aid)
        if app is None or (withdrawing and app.user_id!=uid):fail('ROOM_APPLICATION_NOT_FOUND',404)
        row=db.get(Room,app.room_id)
        if not withdrawing:
            member(db,uid,row,leader=True);cas(row,data)
            if data.expected_cycle_key!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        if app.revision!=data.expected_application_revision:fail('REVISION_CONFLICT')
        if app.state!='pending' or stamp>=app.expires_at:fail('APPLICATION_NOT_PENDING')
        app.state='withdrawn' if withdrawing else 'rejected';app.ended_at=stamp;app.revision+=1
        core.legacy.touch_user(db,app.user_id,application=True)
        def final(current):
            if current>=app.expires_at:fail('APPLICATION_NOT_PENDING')
        return 200,dict(command_id=key,room_id=row.id,application_id=aid,revision=app.revision,state=app.state,executed_at=stamp),final
    return execute(principal,'withdraw' if withdrawing else 'reject',key,dict(application_id=str(aid),body=jsonable_encoder(data)),run)


# Two-cycle storage never falls back to the legacy global room graph.
from app.raid_rooms.v1_compat import read as _current_read
creation_context=_current_read('upgrade')(creation_context)
admission_context=_current_read('upgrade')(admission_context)
plan=_current_read('plan')(plan)
application=_current_read('application')(application)
