"""Metadata prepared in the service's read snapshot, attached after legacy validation.

The router validates the unchanged base envelope first. Only declared metadata
roots are attached; stored command ACKs never acquire a new response shape.
"""
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from uuid import UUID
from datetime import date
from app.raid_rooms import roster_participation as participation
from app.raid_rooms.participation import character_issues
from app.raid_rooms.cycle_models import RoomCycle, CycleMember
from app.game_accounts.support import fail
from app.game_accounts import roster_presence


def publish(db,uid,stamp,value,kind):
    state=participation._state.get()
    if state is None:return value
    q=state['query']
    warnings=q.get('include_character_issues')=='true'
    if not warnings and not participation.enabled():return value
    if not roster_presence.enabled(db):fail('RECRUITMENT_COMMAND_NOT_READY',503)
    if kind in ('candidates','preview') and q.get('intent','change_character')!='change_character':return value
    meta={}
    key=value.get('scope',{}).get('target_cycle_key')
    rows=[]
    if kind=='memberships':
        items=value['data']['items']
        room_ids={UUID(str((v.get('target') or v)['room_id'])) for v in items}
        if warnings:meta['character_issues']=character_issues.own_page(db,uid,stamp,room_ids,key)
        if participation.enabled():
            rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id.in_(room_ids),RoomCycle.cycle_key==date.fromisoformat(key))))
    else:
        data=value['data'];target=data.get('target',data.get('room',data))
        rid=UUID(str(target['room_id']))
        row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==rid,RoomCycle.cycle_key==date.fromisoformat(key)))
        if row:rows=[row]
        if warnings:meta['character_issue_context']=character_issues.room_context(db,uid,rid,key,stamp)
    historical=bool(kind in ('detail','plan') and value['data'].get('access',{}).get('read_only'))
    if historical:
        rows=[]
        if warnings:
            context=meta['character_issue_context']
            for target in context['target_summaries']:target.update(state='not_authorized',has_issues=None,affected_participant_count=None)
            context['selected_target_issues']=None
    if participation.enabled():
        members=[]
        for row in rows:
            query=select(CycleMember).where(CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,
                CycleMember.state.in_(('participating','completed','stopped','review_required')))
            if kind in ('memberships','candidates','preview'):query=query.where(CycleMember.user_id==uid)
            # Room metadata follows actual-target visibility, never persistent
            # membership or the opposite week's permission.
            if kind in ('detail','plan'):
                viewer=db.scalar(select(CycleMember.id).where(CycleMember.cycle_id==row.id,
                    CycleMember.generation==row.generation,CycleMember.user_id==uid,
                    CycleMember.state.in_(('participating','completed','review_required'))))
                if viewer is None:continue
            members.extend(participation.member(db,row,cm) for cm in db.scalars(query.order_by(CycleMember.id)))
        if kind in ('candidates','preview'):
            # Apply/join have no existing actor and therefore no new metadata.
            if members:meta['participation_context']=dict(profile=participation.PROFILE,evaluated_at=stamp,actor=members[0])
        else:meta['participation_context']=dict(profile=participation.PROFILE,evaluated_at=stamp,members=members)
    state['metadata']=jsonable_encoder(meta)
    return value


def legacy_restriction(db,row,value,*,profile):
    if not participation.required(db,row) or participation.enabled():return value
    if profile:
        value['content']=None
        value['viewer'].update(mode='recovery',role='none')
        value['recovery'].update(state='unverified',reason='CLIENT_UPGRADE_REQUIRED',revision=None,
            remaining_review_reasons=['CLIENT_UPGRADE_REQUIRED'],menu_access=False)
        permissions=[*value['permissions'].values(),value['recovery']['can_request_recovery']]
    else:
        value.update(recovery_only=True,room=None)
        permissions=list(value['permissions'].values())
    for item in permissions:item.update(allowed=False,reason='CLIENT_UPGRADE_REQUIRED',next_change_at=None)
    return value


def bind_page(db,uid,stamp,binding,epoch):
    q=participation.query()
    if not participation.enabled() and q.get('include_character_issues')!='true':return binding,epoch
    from app.game_accounts.rosters.lifecycle import digest
    issues=character_issues.own_page(db,uid,stamp)
    marker=[participation.marker(),q.get('include_character_issues','false')]
    return [binding,marker],digest([epoch,issues['issues_revision'],marker])
