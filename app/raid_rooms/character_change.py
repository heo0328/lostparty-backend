"""Replace an actor's unfinished bundle selection under exact source CAS."""
import uuid
from copy import deepcopy
from datetime import date,timedelta
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.game_accounts.support import fail
from app.raid_rooms import admission_service as base,admission_context as context,participation_core as core,scheduling as graph
from app.raid_rooms.admission_schemas import Admission,DTO,Version
from app.raid_rooms.source_models import ContinuationChoice as Choice,RoomSettings
from app.raid_rooms.weekly_links import WeeklyOccupancy


class AssignmentCAS(DTO):
    assignment_id: uuid.UUID
    expected_revision: Version


class ChoiceCAS(DTO):
    choice_id: uuid.UUID
    expected_revision: Version


class Change(Admission):
    expected_membership_revision: Version
    assignments: list[AssignmentCAS]
    choices: list[ChoiceCAS]


def change(principal,rid,key,data):
    def run(db,uid,stamp):
        room=base.room(db,uid,rid);actor=base.member(db,uid,room);base.unscheduled(db,room);base.cas(room,data)
        cycle=graph.raids.cycle(stamp).cycle_key
        if data.expected_cycle_key!=cycle:fail('CYCLE_CHANGED')
        if actor.revision!=data.expected_membership_revision:fail('REVISION_CONFLICT')
        fresh=context.admission(db,uid,room,data.selection.character_id,data.selection.selected_role,'change_character',stamp)
        context.verify(data.selection_context.context_token,fresh['context_token'])
        if data.selection!=fresh['selection'] or data.expected_policy_snapshot!=fresh['policy_snapshot'] or data.expected_catalog_version!=fresh['catalog_version']:fail('POLICY_CONTEXT_CHANGED')
        values=list(db.scalars(select(graph.Assignment).join(graph.Round,graph.Round.id==graph.Assignment.round_id).where(
            graph.Assignment.membership_id==actor.id,graph.Assignment.state=='active',graph.Round.state=='active',graph.Round.cycle_key==date.fromisoformat(cycle))))
        choices=list(db.scalars(select(Choice).where(Choice.membership_id==actor.id,Choice.ended_at.is_(None),Choice.target_cycle>date.fromisoformat(cycle))))
        if not values:fail('ROUND_NOT_ACTIVE')
        if len(data.assignments)!=len(values) or {(a.assignment_id,a.expected_revision) for a in data.assignments}!={(a.id,a.revision) for a in values}:fail('REVISION_CONFLICT')
        if len(data.choices)!=len(choices) or {(c.choice_id,c.expected_revision) for c in data.choices}!={(c.id,c.revision) for c in choices}:fail('REVISION_CONFLICT')
        targets={t.item_id:t for t in data.target_items}
        if len(targets)!=len(data.target_items) or set(targets)!={a.item_id for a in values}:fail('ROOM_ITEMS_CHANGED')
        character=core.identity.selected_character(db,uid,data.selection.model_dump(mode='json'))
        core._limits(db,uid,data.selection,False)
        settings=db.get(RoomSettings,rid);minimum=settings.dealer_min if data.selection.selected_role=='dealer' else settings.support_min
        power=core.power_comparison(db,uid,data.selection,minimum)
        if power['state'] in ('missing','below'):fail('COMBAT_POWER_REQUIRED')
        if data.target_session_ids:fail('INVALID_REQUEST',400)
        plans=[]
        for a in values:
            target=targets[a.item_id];rd=db.get(graph.Round,a.round_id);item=db.get(graph.Item,a.item_id)
            if target.round_id!=rd.id or target.expected_round_revision!=rd.revision or target.party_no!=a.party_no:fail('REVISION_CONFLICT')
            state=db.get(core.WeeklyState,(uid,character.id,item.raid_id,rd.cycle_key))
            if target.expected_weekly_revision!=(state.revision if state else 1):fail('REVISION_CONFLICT')
            if character.id!=a.character_id:core.weekly.require_available_for_participation(db,uid,character.id,item.raid_id,rd.cycle_key)
            difficulty=graph.raids.difficulty(item.raid_id,rd.difficulty_id,rd.catalog_version)
            from decimal import Decimal
            if not graph.raids.meets_item_level(Decimal(str(character.summary.get('item_level'))),difficulty):fail('RAID_ITEM_LEVEL_REQUIRED')
            plans.append((a,rd,item))
        for c in choices:
            if db.scalar(select(Choice.id).where(Choice.user_id==uid,Choice.character_id==character.id,Choice.raid_id==c.raid_id,Choice.target_cycle==c.target_cycle,Choice.ended_at.is_(None),Choice.membership_id!=actor.id)):fail('CONTINUATION_CHOICE_CONFLICT')
        for a,rd,item in plans:core.release_assignment(db,a,stamp)
        db.flush()
        for a,rd,item in plans:
            core._slot(db,room,rd,data.selection,character,a.party_no)
            history=list((a.build or {}).get('selection_history',[]))+[dict(character_id=str(a.character_id),selected_role=a.selected_role,ownership_revision=a.ownership_revision,lifecycle_revision=a.lifecycle_revision,changed_at=stamp.isoformat())]
            a.character_id=character.id;a.selected_role=data.selection.selected_role;a.display=core.identity.display(character)
            a.ownership_revision=data.selection.expected_ownership_revision;a.lifecycle_revision=data.selection.expected_lifecycle_revision
            a.build=jsonable_encoder({**power,'selection_history':history});a.state='active';a.ended_at=None;a.revision+=1
            state=db.get(core.WeeklyState,(uid,character.id,item.raid_id,rd.cycle_key))
            if state is None:
                state=core.WeeklyState(user_id=uid,character_id=character.id,raid_id=item.raid_id,cycle_key=rd.cycle_key,revision=1,updated_at=stamp);db.add(state)
            state.active_party_id=rid;state.active_difficulty_id=rd.difficulty_id;state.joined_at=stamp;state.revision+=1;state.updated_at=stamp;db.flush()
            db.add(WeeklyOccupancy(user_id=uid,character_id=character.id,raid_id=item.raid_id,cycle_key=rd.cycle_key,room_id=rid,item_id=item.id,round_id=rd.id,assignment_id=a.id,joined_at=stamp));db.flush()
        for c in choices:
            c.character_id=character.id;c.selected_role=data.selection.selected_role;c.ownership_revision=data.selection.expected_ownership_revision;c.state='selected';c.blocked_reason=None;c.revision+=1
        actor.revision+=1;room.members_revision+=1;room.plan_revision+=1;room.revision+=1;core.legacy.touch_user(db,uid);core.legacy.directory(db)
        return 200,base.ack(key,room,actor,[a for a,_,_ in plans],stamp)
    return base.execute(principal,'change-character',key,dict(room_id=str(rid),body=data.model_dump(mode='json')),run)
