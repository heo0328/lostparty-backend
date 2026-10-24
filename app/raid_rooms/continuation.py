"""Future intent is never a present assignment; opening uses stored authority."""
import uuid
from datetime import date,timedelta
from typing import Annotated,Literal
from pydantic import StrictBool,Field
from sqlalchemy import select
from app.core.database import session,now
from app.game_accounts.support import fail,lock,GameError
from app.raid_rooms import admission_service as base,admission_context as context,participation_core as core,scheduling as graph
from app.raid_rooms.availability_schemas import DTO,Version
from app.raid_rooms.source_models import ContinuationChoice as Choice,RoomSettings,OpeningEvent,ItemSettings,ScheduleGroup,ScheduleAlternative
from app.raid_rooms.integrated_models import RecruitmentRound as Round,RecruitmentItem as Item,RecruitmentRoom as Room,RecruitmentMembership as Member
from app.raids import service as raids


class ChoiceInput(DTO):
    item_id: uuid.UUID
    character_id: uuid.UUID
    selected_role: Literal['dealer','support']
    expected_ownership_revision: Version


class Replace(DTO):
    choice_id: uuid.UUID
    revision: Version


class ChoicesIn(DTO):
    target_cycle: str
    expected_membership_revision: Version
    expected_choices_revision: Version
    choices: list[ChoiceInput]
    replaces: list[Replace]


class ContinuationSettingsIn(DTO):
    expected_cycle_key: str
    expected_room_revision: Version
    expected_continuation_revision: Version
    enabled: StrictBool
    auto_open_enabled: StrictBool


class OpeningIn(DTO):
    target_cycle: str
    expected_room_revision: Version
    expected_continuation_revision: Version


def view(db,room,member,target):
    values=list(db.scalars(select(Choice).where(Choice.room_id==room.id,Choice.membership_id==member.id,
        Choice.target_cycle==target,Choice.ended_at.is_(None)).order_by(Choice.item_id)))
    return dict(room_id=room.id,target_cycle=target.isoformat(),membership_revision=member.revision,revision=member.revision,
        items=[dict(choice_id=c.id,revision=c.revision,item_id=c.item_id,raid_id=c.raid_id,character_id=c.character_id,
            selected_role=c.selected_role,state=c.state,blocked_reason=c.blocked_reason) for c in values],
        permissions=dict(choose_continuation=dict(allowed=room.ended_at is None,reason=None if room.ended_at is None else 'ROOM_NOT_ACTIVE')))


def get(principal,rid,target=None):
    with base.snapshot(principal) as (db,uid,stamp):
        room=base.room(db,uid,rid);member=base.member(db,uid,room)
        current=date.fromisoformat(raids.cycle(stamp).cycle_key)
        key=core.weekly.parse_cycle(target) if target else current+timedelta(days=7)
        if key not in (current,current+timedelta(days=7)):fail('INVALID_REQUEST',400)
        return view(db,room,member,key)


def replace_choices(db,room,member,target,inputs,replaces,stamp):
    settings=db.get(RoomSettings,room.id)
    if settings is None or not settings.continuation_enabled:fail('CONTINUATION_REQUIRED')
    existing=list(db.scalars(select(Choice).where(Choice.membership_id==member.id,Choice.target_cycle==target,Choice.ended_at.is_(None))))
    if len({r.choice_id for r in replaces})!=len(replaces) or {(r.choice_id,r.revision) for r in replaces}!={(c.id,c.revision) for c in existing}:fail('REVISION_CONFLICT')
    items={i.id:i for i in db.scalars(select(Item).where(Item.room_id==room.id))}
    if inputs and (len({c.item_id for c in inputs})!=len(inputs) or {c.item_id for c in inputs}!=set(items)):fail('ROOM_ITEMS_CHANGED')
    if inputs and len({(c.character_id,c.selected_role) for c in inputs})!=1:fail('BUNDLE_CHARACTER_REQUIRED')
    for value in inputs:
        if value.selected_role not in ('dealer','support'):fail('INVALID_REQUEST',400)
        choice=context.selection(db,member.user_id,value.character_id,value.selected_role)
        if choice.expected_ownership_revision!=value.expected_ownership_revision:fail('REVISION_CONFLICT')
        other=db.scalar(select(Choice.id).where(Choice.user_id==member.user_id,Choice.character_id==value.character_id,
            Choice.raid_id==items[value.item_id].raid_id,Choice.target_cycle==target,Choice.ended_at.is_(None),Choice.membership_id!=member.id))
        if other is not None:fail('CONTINUATION_CHOICE_CONFLICT')
    for old in existing:
        old.state='replaced' if inputs else 'released';old.ended_at=stamp;old.blocked_reason=None;old.revision+=1
    db.flush()
    for value in inputs:
        db.add(Choice(id=uuid.uuid4(),room_id=room.id,item_id=value.item_id,membership_id=member.id,user_id=member.user_id,
            character_id=value.character_id,raid_id=items[value.item_id].raid_id,selected_role=value.selected_role,
            ownership_revision=value.expected_ownership_revision,target_cycle=target,revision=1,state='selected'))
    member.revision+=1;room.plan_revision+=1;room.revision+=1;db.flush()


def put(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);member=base.member(db,uid,room);base.unscheduled(db,room)
        target=core.weekly.parse_cycle(data.target_cycle)
        if target!=date.fromisoformat(raids.cycle(stamp).cycle_key)+timedelta(days=7):fail('CYCLE_CHANGED')
        if member.revision!=data.expected_membership_revision or member.revision!=data.expected_choices_revision:fail('REVISION_CONFLICT')
        replace_choices(db,room,member,target,data.choices,data.replaces,stamp)
        return 200,view(db,room,member,target)
    return base.execute(principal,'future-choices',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def settings(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);member=base.member(db,uid,room,leader=True);base.unscheduled(db,room)
        value=db.get(RoomSettings,rid)
        if data.expected_cycle_key!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        if room.revision!=data.expected_room_revision or value.continuation_revision!=data.expected_continuation_revision:fail('REVISION_CONFLICT')
        if data.auto_open_enabled and not data.enabled:fail('INVALID_REQUEST',400)
        changed=(value.continuation_enabled,value.auto_open_enabled)!=(data.enabled,data.auto_open_enabled)
        if changed:
            if data.auto_open_enabled and not value.auto_open_enabled:value.auto_open_effective_cycle=date.fromisoformat(raids.cycle(stamp).cycle_key)+timedelta(days=7)
            if not data.auto_open_enabled:value.auto_open_effective_cycle=None
            value.continuation_enabled=data.enabled;value.auto_open_enabled=data.auto_open_enabled
            value.continuation_revision+=1;value.revision+=1;room.revision+=1;room.plan_revision+=1
        return 200,dict(command_id=key,outcome='applied' if changed else 'noop',executed_at=stamp,
            revisions=[base.revision('room',room),dict(resource='continuation',id=room.id,revision=value.continuation_revision)])
    return base.execute(principal,'continuation',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def open_current(db,room,stamp,*,automatic=False):
    cycle=raids.cycle(stamp);target=date.fromisoformat(cycle.cycle_key);settings=db.get(RoomSettings,room.id)
    if not settings.continuation_enabled:fail('CONTINUATION_REQUIRED')
    if automatic and (not settings.auto_open_enabled or settings.auto_open_effective_cycle is None or settings.auto_open_effective_cycle>target):fail('AUTO_OPEN_NOT_EFFECTIVE')
    items=list(db.scalars(select(Item).where(Item.room_id==room.id).order_by(Item.id)))
    leader=db.get(Member,room.leader_membership_id)
    from app.auth.models import User
    if leader is None or leader.ended_at is not None or db.get(User,leader.user_id).status!='active':fail('ROOM_LEADER_UNAVAILABLE')
    if all(db.scalar(select(OpeningEvent.id).where(OpeningEvent.item_id==i.id,OpeningEvent.target_cycle==target,OpeningEvent.state=='applied')) is not None for i in items):return False
    if automatic:
        chosen=set(db.scalars(select(Choice.item_id).where(Choice.membership_id==leader.id,Choice.target_cycle==target,Choice.ended_at.is_(None))))
        if chosen!={i.id for i in items}:fail('LEADER_CONTINUATION_REQUIRED')
    newly=False
    for item in items:
        event=db.scalar(select(OpeningEvent).where(OpeningEvent.room_id==room.id,OpeningEvent.item_id==item.id,OpeningEvent.target_cycle==target,OpeningEvent.state=='applied'))
        if event:continue
        mode='scheduled_auto' if automatic else 'manual'
        event=db.scalar(select(OpeningEvent).where(OpeningEvent.room_id==room.id,OpeningEvent.item_id==item.id,OpeningEvent.target_cycle==target,OpeningEvent.mode==mode))
        effective=cycle.starts_at if automatic else stamp
        if event is None:
            event=OpeningEvent(id=uuid.uuid4(),room_id=room.id,item_id=item.id,target_cycle=target,mode=mode,settings_revision=settings.continuation_revision,
                authorized_effective_at=effective,search_floor_at=effective+timedelta(minutes=30),state='scheduled')
            db.add(event)
        item_settings=db.get(ItemSettings,item.id)
        try:raids.difficulty(item.raid_id,item_settings.difficulty_id,item_settings.catalog_version)
        except raids.CatalogSelectionError as error:fail(error.code)
        round=db.scalar(select(Round).where(Round.item_id==item.id,Round.cycle_key==target,Round.state=='active'))
        if round is None:
            prior=db.scalar(select(Round.id).where(Round.item_id==item.id,Round.cycle_key==target))
            if prior is not None:fail('WEEKLY_REOPEN_REQUIRES_REVIEW')
            round=Round(id=uuid.uuid4(),room_id=room.id,item_id=item.id,cycle_key=target,difficulty_id=item_settings.difficulty_id,
                catalog_version=item_settings.catalog_version,game_party_size=next(r.party_size for r in raids.catalog().raids if r.raid_id==item.raid_id),
                revision=1,state='active',created_at=stamp)
            db.add(round)
        event.state='applied';event.processed_at=stamp;event.blocked_reason=None;newly=True
    db.flush()
    if not newly:return False
    for member in graph.members(db,room.id):
        choices=list(db.scalars(select(Choice).where(Choice.membership_id==member.id,Choice.target_cycle==target,Choice.ended_at.is_(None))))
        if {c.item_id for c in choices}!={i.id for i in items}:continue
        try:
            with db.begin_nested():
                cid=choices[0].character_id;role=choices[0].selected_role
                selected=context.selection(db,member.user_id,cid,role)
                if any(c.ownership_revision!=selected.expected_ownership_revision or c.character_id!=cid or c.selected_role!=role for c in choices):fail('OWNERSHIP_REQUIRED',403)
                targets=[]
                for item in items:
                    rd=db.scalar(select(Round).where(Round.item_id==item.id,Round.cycle_key==target,Round.state=='active'))
                    state=db.get(core.WeeklyState,(member.user_id,cid,item.raid_id,target))
                    character=core.identity.selected_character(db,member.user_id,selected.model_dump(mode='json'))
                    party=None
                    for n in range(1,min(room.app_capacity//4,rd.game_party_size//4)+1):
                        try:core._slot(db,room,rd,selected,character,n);party=n;break
                        except GameError as error:
                            if error.code not in ('ROOM_FULL','ROOM_COMPOSITION_CONFLICT'):raise
                    if party is None:fail('ROOM_COMPOSITION_CONFLICT')
                    targets.append(base.Target(item_id=item.id,round_id=rd.id,party_no=party,expected_round_revision=rd.revision,expected_weekly_revision=state.revision if state else 1))
                core.admit_bundle(db,member.user_id,room,selected,targets,cycle.cycle_key)
                for choice in choices:
                    if choice.state=='blocked':choice.state='selected';choice.blocked_reason=None;choice.revision+=1
        except GameError as error:
            if automatic and member.id==leader.id:raise
            for choice in choices:choice.state='blocked';choice.blocked_reason=error.code;choice.revision+=1
    if not graph.groups(db,room.id,cycle.cycle_key):
        prior=db.scalar(select(ScheduleGroup.cycle_key).where(ScheduleGroup.room_id==room.id,ScheduleGroup.cycle_key<target).order_by(ScheduleGroup.cycle_key.desc()).limit(1))
        templates=[]
        if prior is not None:
            by_id={str(i.id):i.raid_id for i in items}
            for old in graph.groups(db,room.id,prior.isoformat()):
                alts=[]
                for alt in db.scalars(select(ScheduleAlternative).where(ScheduleAlternative.group_id==old.id)):
                    clock=lambda n:f'{n//60:02}:{n%60:02}' if n is not None else None
                    alts.append(dict(client_alternative_key=alt.client_key,existing_session_id=None,expected_session_revision=None,
                        weekday=alt.weekday,starts_local=clock(alt.start_minute),leader_latest_start_local=clock(alt.latest_start_minute),item_order=[by_id[i] for i in alt.item_order]))
                templates.append(base.s.ScheduleGroup(client_group_key=db.get(graph.ScheduleHead,old.id).client_key,existing_group_id=None,expected_group_revision=None,
                    occurrence_mode=old.occurrence_mode,planning_mode=old.planning_mode,day_scope=old.day_scope,required=old.required,
                    auto_confirm_additional_members=old.auto_additional_members,alternatives=alts))
            graph.install(db,room,templates,stamp,creating=True)
    graph.evaluate_initial(db,room,stamp)
    room.plan_revision+=1;room.revision+=1;db.flush()
    return True


def opening(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);member=base.member(db,uid,room,leader=True);base.unscheduled(db,room)
        settings=db.get(RoomSettings,rid)
        if data.target_cycle!=raids.cycle(stamp).cycle_key:fail('CYCLE_CHANGED')
        if room.revision!=data.expected_room_revision or settings.continuation_revision!=data.expected_continuation_revision:fail('REVISION_CONFLICT')
        changed=open_current(db,room,stamp)
        return 200,dict(command_id=key,outcome='applied' if changed else 'noop',executed_at=stamp,revisions=[base.revision('room',room),base.revision('plan',room,room.plan_revision)])
    return base.execute(principal,'open',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)


def process_due():
    with session() as db:
        from app.raid_rooms.readiness import require_legacy_worker
        require_legacy_worker(db)
        ids=list(db.scalars(select(Room.id).join(RoomSettings,RoomSettings.room_id==Room.id).where(Room.ended_at.is_(None),
            Room.migration_state=='ready').order_by(Room.id)))
    for rid in ids:
        try:process_room(rid)
        except Exception as error:
            from app.core.observability import job_item_failed
            job_item_failed('legacy_opening', error)


def process_room(rid):
    with session() as db,db.begin():
        from app.raid_rooms.readiness import require_legacy_worker
        require_legacy_worker(db)
        lock(db,'game-mutations-v1');stamp=now(db);room=db.get(Room,rid);value=db.get(RoomSettings,rid)
        target=date.fromisoformat(raids.cycle(stamp).cycle_key)
        changed=False
        from app.raid_rooms.resume_models import ResumeProposal
        for model in (graph.Proposal,ResumeProposal):
            for proposal in db.scalars(select(model).where(model.room_id==rid,model.state=='pending',model.created_at<raids.cycle(stamp).starts_at)):
                proposal.state='obsolete';proposal.revision+=1;changed=True
        for old in db.scalars(select(Round).where(Round.room_id==rid,Round.cycle_key<target,Round.state=='active')):
            for assignment in db.scalars(select(graph.Assignment).where(graph.Assignment.round_id==old.id,graph.Assignment.state=='active')):
                graph.release(db,assignment=assignment,reason='cycle_closed',stamp=stamp)
                core.release_assignment(db,assignment,stamp);assignment.state='stopped_incomplete'
            old.state='stopped_incomplete';old.ended_at=stamp;old.revision+=1;changed=True
        if changed:
            room.plan_revision+=1;room.revision+=1;core.legacy.directory(db);db.flush()
        if room.ended_at is not None or not value.auto_open_enabled or value.auto_open_effective_cycle is None or value.auto_open_effective_cycle>target:return
        try:
            with db.begin_nested():open_current(db,room,stamp,automatic=True)
        except GameError as error:
            for item in db.scalars(select(Item).where(Item.room_id==rid)):
                if db.scalar(select(OpeningEvent.id).where(OpeningEvent.item_id==item.id,OpeningEvent.target_cycle==target,OpeningEvent.state=='applied')):continue
                event=db.scalar(select(OpeningEvent).where(OpeningEvent.item_id==item.id,OpeningEvent.target_cycle==target,OpeningEvent.mode=='scheduled_auto'))
                if event is None:
                    effective=raids.cycle(stamp).starts_at
                    event=OpeningEvent(id=uuid.uuid4(),room_id=rid,item_id=item.id,target_cycle=target,mode='scheduled_auto',settings_revision=value.continuation_revision,
                        authorized_effective_at=effective,search_floor_at=effective+timedelta(minutes=30))
                    db.add(event)
                event.state='blocked';event.blocked_reason=error.code;event.processed_at=stamp


# Two-cycle storage never falls back to the legacy global room graph.
from app.raid_rooms.v1_compat import read as _current_read
get=_current_read('choices')(get)
