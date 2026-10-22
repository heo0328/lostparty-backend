"""Current-C v1 projections. Unsafe old commands recover ACKs then require v2."""
from functools import wraps
from inspect import signature
from typing import get_args,get_origin
from types import UnionType
from pydantic import BaseModel,TypeAdapter,ValidationError
from sqlalchemy import text
from app.core.database import session,now
from app.game_accounts.support import fail


def enabled(db=None):
    if db is not None:return list(db.scalars(text('SELECT version_num FROM public.alembic_version')))==['0029_cycle_outcomes']
    with session() as connection:return enabled(connection)


def reject_write(db):
    if enabled(db):fail('CLIENT_UPGRADE_REQUIRED')


def shape(annotation,value):
    """Discard v2-only fields, then validate against the unchanged v1 DTO."""
    if value is None:return None
    origin=get_origin(annotation);args=get_args(annotation)
    if origin is list:return [shape(args[0],v) for v in value]
    if origin is dict:return {k:shape(args[1],v) for k,v in value.items()}
    if origin is UnionType or str(origin)=='typing.Union':
        for choice in args:
            try:return TypeAdapter(choice).validate_python(shape(choice,value))
            except (ValidationError,TypeError,ValueError):continue
        raise ValueError('Unsupported legacy projection')
    if isinstance(annotation,type) and issubclass(annotation,BaseModel):
        return {k:shape(field.annotation,value[k]) for k,field in annotation.model_fields.items() if k in value}
    return value


def project(model,value):return model.model_validate(shape(model,value)).model_dump(mode='json')


def disabled():return dict(allowed=False,reason='CLIENT_UPGRADE_REQUIRED')


def card(value):
    from app.raid_rooms.search_router import Card
    value=dict(value);value['cycle_key']=value['target_cycle_key']
    return project(Card,value)


def settings(value):
    from app.raid_rooms.management_router import Settings
    value=dict(value);value['continuation']=dict(enabled=value['continuation']['enabled'],auto_open_enabled=False,
        revision=value['continuation']['revision'],auto_open_effective_cycle=None)
    value['permissions']={k:disabled() for k in ('edit_settings','edit_continuation','change_visibility')}
    return project(Settings,value)


def membership(value):
    value=dict(value);value['room_role']='leader' if value.pop('target_role','none')=='leader' else 'member'
    return value


def read_permissions(value):
    if isinstance(value,dict):
        if 'permissions' in value:
            value['permissions']={name:(permission if name.startswith('view_') or name=='read' else disabled())
                for name,permission in value['permissions'].items()}
        for child in value.values():read_permissions(child)
    elif isinstance(value,list):
        for child in value:read_permissions(child)
    return value


def read(kind):
    def decorate(fn):
        sig=signature(fn)
        @wraps(fn)
        def invoke(*args,**kwargs):
            if not enabled():return fn(*args,**kwargs)
            bound=sig.bind(*args,**kwargs);bound.apply_defaults();values=bound.arguments
            if kind=='availability' and values['rid'] is None:return fn(*args,**kwargs)
            return read_permissions(dispatch(kind,values))
        return invoke
    return decorate


def dispatch(kind,v):
    from app.raid_rooms import (cycle_queries as directory,cycle_member_reads as members,cycle_lists as lists,
        cycle_commands as commands,cycle_times as times,cycle_legacy as legacy,cycle_management as management,
        cycle_schedule_service as schedules,cycle_schemas as inputs,admission_schemas as old,member_schemas as own)
    with session() as db:key=commands.raids.cycle(now(db)).cycle_key
    principal=v['principal'];rid=v.get('rid')
    if kind=='search':
        data=inputs.Search.model_validate(v['data'].model_dump(mode='json')|{'target_cycle_key':key})
        result=directory.search(principal,data)['data'];result['items']=[card(c) for c in result['items']]
        from app.raid_rooms.search_router import Page
        return project(Page,result)
    if kind=='card':return card(directory.get_card(principal,rid,key)['data'])
    if kind=='settings':return settings(management.get(principal,rid,key)['data'])
    if kind=='plan':
        result=members.plan(principal,rid,key)['data'];result['cycle_key']=key
        result['my_membership']=membership(result['my_membership'])
        for a in result['my_assignments']:a['cycle_key']=key
        return project(old.Plan,result)
    if kind=='detail':
        result=members.detail(principal,rid,key)['data'];result['room']=card(result['room'])
        result['settings']=settings(result['settings']) if result['settings'] else None
        result['members']=[membership(m) for m in result['members']]
        if result['my_membership']:result['my_membership']=membership(result['my_membership'])
        return project(own.Detail,result)
    if kind=='memberships':
        result=lists.memberships(principal,key,v['state'],v['limit'],v['cursor'])['data']
        for item in result['items']:
            item['room_role']='leader' if item['target_role']=='leader' else 'member'
            item['current_week_state']={'participating':'participating','completed':'completed','stopped':'stopped'}.get(item['target_participation_state'],'next_week_only')
            item['next_week_choice_state']='not_selected'
            if item['room']:item['room']=card(item['room'])
        return project(own.MembershipPage,result)
    if kind=='applications':
        result=lists.applications(principal,key,rid=rid,state='accepted' if v['state']=='approved' else v['state'],limit=v['limit'],cursor=v['cursor'])['data']
        return project(own.ApplicationPage,result)
    if kind=='application':
        result=commands.application(principal,v['aid']);data=result['data']
        if result['scope']['target_cycle_key']!=key:fail('CLIENT_UPGRADE_REQUIRED')
        if 'application' in data:
            data['permissions']={k:disabled() for k in data['permissions']};return project(old.Review,data)
        return project(old.ApplicationView,data)
    if kind=='choices':
        target=v.get('target') or key
        if target!=key:fail('CLIENT_UPGRADE_REQUIRED')
        data=legacy.get(principal,rid,key)['data'];data['target_cycle']=key
        from app.raid_rooms.continuation_router import Choices
        return project(Choices,data)
    if kind=='availability':
        from app.raid_rooms.availability_schemas import SubmissionOut
        return project(SubmissionOut,times.get_submission(principal,rid,key)['data'])
    if kind=='time':
        data=times.time_context(principal,rid,key,v['target_session_id'])['data'];data['cycle_key']=key
        return project(own.TimeContext,data)
    if kind=='overlaps':
        data=times.overlaps(principal,key,v['limit'],v['cursor'])['data'];data['cycle_key']=key
        return project(own.OverlapPage,data)
    if kind=='candidates':
        from app.raid_rooms.schedule_router import Candidate
        return project(Candidate,schedules.candidates(principal,v['gid'],key)['data'])
    if kind=='projections':
        return project(own.ProjectionPage,lists.projections(principal,v['gid'],v['rids'],key,v['token'],v['group_ids'])['data'])
    fail('CLIENT_UPGRADE_REQUIRED')
