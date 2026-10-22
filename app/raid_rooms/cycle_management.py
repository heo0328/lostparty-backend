"""Actual target settings, seats and removal; persistent and other targets survive."""
from copy import deepcopy
from decimal import Decimal
from sqlalchemy import select
from app.game_accounts.support import fail,GameError
from app.raid_rooms import (cycle_commands as commands,cycle_lifecycle as life,cycle_planning as plan,
    cycle_schedule as graph,cycle_schedule_service as schedules,cycle_leadership as leadership,
    cycle_outcomes as outcomes,cycles,cycle_wire as wire)
from app.raid_rooms.cycle_models import CycleMember,CycleSubmission
from app.raid_rooms.cycle_creation import scope,permission


def target(db,uid,rid,key,stamp,body=None):
    outcomes.ready(db)
    return schedules.target(db,uid,rid,key,stamp,body,leader=True)


def edit_permission(db,uid,room,row,stamp):
    try:target(db,uid,room.id,row.cycle_key.isoformat(),stamp);return permission(None)
    except GameError as error:return permission(error.code)


def get(principal,rid,key):
    from app.raid_rooms import cycle_member_reads as reads
    with commands.base.snapshot(principal) as (db,uid,stamp):
        outcomes.ready(db);room,row=reads.read_target(db,uid,rid,key,stamp)
        commands.base.member(db,uid,room)
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdSettings.model_validate(dict(scope=scope(stamp,key,row),
            data=reads.settings(db,room,row,uid,stamp))).model_dump(mode='json')


def remove_member(db,room,row,cm,command,stamp):
    owned=life.assignments(db,row,cm)
    evidence=dict(assignments=[life.assignment_snapshot(a) for a in owned],
        participations=leadership.release_parts(db,row,cm,stamp))
    submission=db.get(CycleSubmission,cm.id)
    if submission is not None:
        evidence['submission']=plan.snapshot(submission);db.delete(submission)
    for a in owned:
        if a.state=='active':life.admission.core.release_assignment(db,a,stamp)
    cm.state='removed';cm.ended_at=stamp;cm.revision+=1
    life.event(db,row,cm,command,'removed',stamp,evidence)
    db.flush()


def command(principal,rid,key,data,operation):
    body=data.model_dump(mode='json')
    def run(db,uid,stamp):
        room,row,actor=target(db,uid,rid,body['target_cycle_key'],stamp,body)
        guard=graph.final_deadlines(db,row,[],stamp,join=False)
        if operation=='settings':
            if row.settings_revision!=data.expected_settings_revision:fail('REVISION_CONFLICT')
            combat=body['combat_requirement']
            if combat['input_mode']=='shared' and combat['dealer_min']!=combat['support_min']:fail('INVALID_REQUEST',400)
            if any(v is not None and not Decimal(v).is_finite() for v in (combat['dealer_min'],combat['support_min'])):fail('INVALID_REQUEST',400)
            updated={**deepcopy(row.settings_snapshot),**{n:body[n] for n in ('experience_level','combat_requirement','admission_mode')}}
            changed=updated!=row.settings_snapshot
            if changed:row.settings_snapshot=updated;row.settings_revision+=1;plan.bump(db,row)
        elif operation=='formation':
            pairs=life.admission.rounds(db,row)
            values=outcomes.assignments(db,row);active=[a for a in values if a.state=='active']
            links={m.membership_id:m for m in db.scalars(select(CycleMember).where(CycleMember.cycle_id==row.id,
                CycleMember.generation==row.generation,CycleMember.state=='participating'))}
            by={(links[a.membership_id].id,a.item_id):a for a in active if a.membership_id in links}
            choices={(p.cycle_member_id,p.item_id):p for p in data.placements}
            if len(by)!=len(active) or len(choices)!=len(data.placements) or set(choices)!=set(by):fail('ROOM_ITEMS_CHANGED')
            final={};checked=set()
            for ident,p in choices.items():
                a=by[ident];cm=links[a.membership_id]
                if cm.revision!=p.expected_cycle_member_revision:fail('REVISION_CONFLICT')
                if cm.id not in checked:life.qualify(db,room,row,cm);checked.add(cm.id)
                rd=next(r for _,r in pairs if r.id==a.round_id)
                if p.party_no>min(life.admission.capacity(row),rd.game_party_size)//4:fail('ROOM_COMPOSITION_CONFLICT')
                bucket=final.setdefault((rd.id,p.party_no),[])
                if any(old.slot_no==p.slot_no for old,_ in bucket):fail('ROOM_COMPOSITION_CONFLICT')
                bucket.append((p,a))
            for bucket in final.values():
                dealers=[a for _,a in bucket if a.selected_role=='dealer'];supports=[a for _,a in bucket if a.selected_role=='support']
                if len(dealers)>3 or len(supports)>1 or len({a.display['class_name'] for a in dealers})!=len(dealers):fail('ROOM_COMPOSITION_CONFLICT')
            changed=any((a.party_no,a.slot_no)!=(choices[ident].party_no,choices[ident].slot_no) for ident,a in by.items())
            if changed:
                # Release the immediate seat index only, within this transaction.
                for a in active:a.state='left';a.ended_at=stamp
                db.flush()
                for ident,a in by.items():
                    p=choices[ident];a.party_no=p.party_no;a.slot_no=p.slot_no;a.state='active';a.ended_at=None;a.revision+=1
                row.members_revision+=1;plan.bump(db,row)
        else:
            cm=db.get(CycleMember,data.target_cycle_member_id)
            if cm is None or (cm.cycle_id,cm.generation)!=(row.id,row.generation):fail('TARGET_SCOPE_MISMATCH',400)
            if cm.id==actor.id or cm.state not in life.VALID_STATES:fail('ROOM_REMOVAL_TARGET_INVALID')
            if actor.revision!=data.expected_cycle_member_revision or cm.revision!=data.expected_removed_cycle_member_revision:fail('REVISION_CONFLICT')
            remove_member(db,room,row,cm,key,stamp);row.members_revision+=1;plan.bump(db,row);changed=True
            plan.refresh(db,room,row,uid,key,stamp)
        db.flush()
        revisions=[dict(resource='target',id=row.id,revision=row.revision),dict(resource='settings',id=row.id,revision=row.settings_revision)]
        return 200,life.ack(db,row,key,stamp,outcome='applied' if changed else 'noop',revisions=revisions),guard
    return cycles.execute(principal,{'settings':'target-settings','formation':'formation','remove':'remove'}[operation],key,
        dict(room_id=str(rid),body=body),run)
