"""Enrich only typed opt-in DTO positions inside the caller's read snapshot."""
from copy import deepcopy
from typing import get_args, get_origin, Union, Annotated
import types
import uuid
from pydantic import BaseModel
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.raid_rooms import beta_profile,beta_schemas,beta_schedule
from app.raid_rooms.beta_models import BetaApplicationMemo,BetaAvailabilityCopy
from app.raid_rooms.cycle_models import RoomCycle,CycleMember
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.integrated_models import RecruitmentMembership as Member,RecruitmentRoom as Room


def identity(db,uid,row):
    saved=beta_schedule.get(db,row)
    if saved is None or saved.generation!=row.generation or row.state!='open':return None
    room=db.get(Room,row.room_id)
    if room is None or room.ended_at is not None:return None
    cm=db.scalar(select(CycleMember).join(Member,Member.id==CycleMember.membership_id).where(
        CycleMember.cycle_id==row.id,CycleMember.generation==row.generation,CycleMember.user_id==uid,
        CycleMember.state=='participating',Member.ended_at.is_(None)))
    return dict(number=saved.number,password=saved.password) if cm else None


def enrich(db,uid,stamp,model,payload):
    value=deepcopy(jsonable_encoder(payload))
    def walk(node,annotation,row=None):
        origin=get_origin(annotation)
        if origin is Annotated:return walk(node,get_args(annotation)[0],row)
        if origin in (Union,types.UnionType):
            if node is None:return None
            options=get_args(annotation)
            objects=[v for v in options if isinstance(v,type) and issubclass(v,BaseModel)]
            if objects and isinstance(node,dict):
                # Distinct closed envelope shapes choose their declared branch;
                # final validation still rejects missing/foreign keys.
                chosen=max(objects,key=lambda v:sum(k in node for k in v.model_fields))
                return walk(node,chosen,row)
            return node
        if origin is list:return [walk(v,get_args(annotation)[0],row) for v in node]
        if not isinstance(annotation,type) or not issubclass(annotation,BaseModel) or not isinstance(node,dict):return node
        scope=node.get('scope',{})
        if not isinstance(scope,dict):scope={}
        if scope.get('room_cycle_id'):row=db.get(RoomCycle,uuid.UUID(scope['room_cycle_id']))
        locator=node.get('target',node)
        if not isinstance(locator,dict):locator={}
        rid=locator.get('room_id');key=locator.get('target_cycle_key')
        if rid and key:
            from datetime import date
            row=db.scalar(select(RoomCycle).where(RoomCycle.room_id==uuid.UUID(rid),RoomCycle.cycle_key==date.fromisoformat(key)))
        app=None
        if node.get('application_id'):
            app=db.get(CycleApplication,uuid.UUID(node['application_id']))
            if app:
                row=db.get(RoomCycle,app.cycle_id)
                if row.generation!=app.generation:row=None
        for key,info in annotation.model_fields.items():
            if key in node:node[key]=walk(node[key],info.annotation,row)
        additions=beta_schemas.ADDITIONS.get(annotation.__name__,{})
        historical='MembershipAction' in annotation.__name__ and node.get('content',False) is None
        if 'beta_schedule' in additions:node['beta_schedule']=None if historical else beta_schedule.view(db,row,stamp)
        if 'recruitment_identity' in additions:node['recruitment_identity']=None if historical else identity(db,uid,row)
        if 'application_memo' in additions:
            aid=node.get('application_id')
            memo=db.get(BetaApplicationMemo,uuid.UUID(aid)) if aid else None
            node['application_memo']=memo.memo if memo else None
        if 'availability_copy' in additions:
            copied=db.get(BetaAvailabilityCopy,uuid.UUID(node['cycle_member_id']))
            node['availability_copy']=dict(state=copied.state,source_personal_version=copied.source_personal_version,copied_at=copied.copied_at) if copied else None
        return node
    return walk(value,model)


def render(db,uid,stamp,model,payload,*,exclude_unset=False):
    from app.raid_rooms import cycle_group_policy
    if "group_policy_version" in model.model_fields:payload=cycle_group_policy.enrich(db,payload)
    if not beta_profile.enabled():
        return model.model_validate(jsonable_encoder(payload)).model_dump(mode='json',exclude_unset=exclude_unset)
    if not beta_schedule.available(db):
        from app.game_accounts.support import fail
        fail('RECRUITMENT_COMMAND_NOT_READY',503)
    value=enrich(db,uid,stamp,model,payload)
    return beta_schemas.output_model(model).model_validate(value).model_dump(mode='json',exclude_unset=exclude_unset)
