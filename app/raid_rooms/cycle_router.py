"""Candidate write router. Intentionally absent from main until W4 cutover.

Only isolated tests mount this router against the shadow schema. Publishing
these paths in the runtime OpenAPI would falsely claim mixed-worker readiness.
"""
import json
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import TypeAdapter, ValidationError
from app.game_accounts.router import Principal, Key
from app.game_accounts.support import fail
from app.core.errors import AuthError, response
from app.raid_rooms.availability_router import AvailabilityRoute, unique_pairs
from app.raid_rooms.search_router import FilterContext
from app.raid_rooms import (cycle_creation as creation, cycle_commands as commands, cycle_wire as s,
    cycle_schemas as inputs, cycle_queries as queries, cycle_member_reads as members,cycle_lists as lists)
from app.raid_rooms.router import OptionalPrincipal
from app.raid_rooms import cycle_opening,cycle_continuation,cycle_leadership,cycle_character
from app.raid_rooms import cycle_outcomes,cycle_resume,cycle_management,cycle_common
from app.raid_rooms import cycle_times
from app.raid_rooms import cycle_schedule_service


class CycleRoute(AvailabilityRoute):
    def repeated_query(self,request):
        return {'experience_levels'} if request.method=='GET' and request.url.path.endswith('/raid-rooms') else set()

    def get_route_handler(self):
        parent=super().get_route_handler()
        async def bounded(request:Request):
            try:return await parent(request)
            except (AuthError,RequestValidationError,SQLAlchemyError) as error:
                code=getattr(error,'code','INVALID_REQUEST' if isinstance(error,RequestValidationError) else 'SERVICE_UNAVAILABLE')
                status=getattr(error,'status',400 if isinstance(error,RequestValidationError) else 503)
                value=response(request,code,status,getattr(error,'retry_after',None),getattr(error,'retry_at',None))
                body=json.loads(value.body)
                body['error']['details']=getattr(error,'cycle_details',None)
                return JSONResponse(status_code=status,headers={k:v for k,v in value.headers.items() if k!='content-length'},content=body)
        return bounded

    def allowed_query(self, request):
        if request.method!='GET':return set()
        if request.url.path.endswith('/common-context'):return {'command'}
        if request.url.path.endswith('/command-context'):return {'target_cycle_key','command','round_id'}
        if request.url.path.endswith('/candidates'):return {'target_cycle_key'}
        if request.url.path.endswith('/schedule-context'):return {'target_cycle_key','target_session_id'}
        if request.url.path.endswith('/raid-schedule-overlaps'):return {'target_cycle_key','limit','cursor'}
        if request.url.path.endswith('/continuation-context'):return {'target_cycle_key','action','character_id','selected_role'}
        if request.url.path.endswith('/opening-context'):return {'target_cycle_key','intent','character_id','selected_role'}
        if request.url.path.endswith(('/participation-cancellation-context','/leadership-transfer-context')):return {'target_cycle_key'}
        if request.url.path.endswith('/raid-room-member-projections'):return {'room_ids','target_cycle_key','group_ids','filter_context_token'}
        if request.url.path.endswith('/raid-room-filter-context'):return {'group_ids'}
        if request.url.path.endswith('/raid-rooms'):return {'scope','group_id','raid_id','difficulty_id','limit','cursor','target_cycle_key','experience_levels'}
        if request.url.path.endswith('/raid-room-memberships') or request.url.path.endswith('/applications') or request.url.path.endswith('/raid-room-applications'):
            return {'target_cycle_key','state','limit','cursor'}
        if request.url.path.endswith('/raid-room-creation-context'):
            return {'target_cycle_key','character_id','selected_role','items','group_id',
                'continuation_enabled','next_character_id','next_selected_role'}
        if request.url.path.endswith('/admission-context'):
            return {'target_cycle_key','character_id','selected_role','intent'}
        if request.url.path.endswith('/detail') or request.url.path.endswith('/plan'):
            return {'target_cycle_key'}
        if '/raid-rooms/' in request.url.path:return {'target_cycle_key'}
        return set()


errors={code:{'model':s.Error} for code in (400,401,403,404,409,413,429,503)}
router=APIRouter(prefix='/v2',tags=['recruitment-cycle-candidate'],route_class=CycleRoute)
Role=Literal['dealer','support']


@router.get('/me/raid-room-creation-context',response_model=s.OutputContract3GetV2MeRaidRoomCreationContext,responses=errors)
def creation_context(principal:Principal,target_cycle_key:str,character_id:UUID,selected_role:Role,
    items:Annotated[str,Query(max_length=32768)],group_id:UUID|None=None,continuation_enabled:bool=False,
    next_character_id:UUID|None=None,next_selected_role:Role|None=None):
    try:
        raw=json.loads(items,object_pairs_hook=unique_pairs)
        if not isinstance(raw,list) or any(not isinstance(v,dict) or set(v)!={'raid_id','difficulty_id'} for v in raw):
            raise ValueError()
        choices=TypeAdapter(list[s.BCreateTarget]).validate_python([dict(v,expected_weekly_revision=1) for v in raw])
    except (ValueError,TypeError,ValidationError,RecursionError):fail('INVALID_REQUEST',400)
    return creation.get(principal,character_id,selected_role,choices,group_id,target_cycle_key,
        continuation_enabled,next_character_id,next_selected_role)


@router.post('/raid-rooms',response_model=s.CreateAck,status_code=201,responses=errors)
def create(data:inputs.Create,principal:Principal,key:Key):
    return creation.create(principal,key,data)[1]


@router.get('/raid-rooms/{room_id}/admission-context',response_model=s.OutputContract3GetV2RaidRoomsRoomIdAdmissionContext,response_model_exclude_unset=True,responses=errors)
def admission_context(room_id:UUID,principal:Principal,target_cycle_key:str,character_id:UUID,
    selected_role:Role,intent:Literal['apply','join','change_character']):
    return commands.get_context(principal,room_id,target_cycle_key,character_id,selected_role,intent)


@router.post('/raid-rooms/{room_id}/join',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def join(room_id:UUID,data:inputs.Admission,principal:Principal,key:Key):
    return commands.admit(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/applications',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,status_code=201,responses=errors)
def apply(room_id:UUID,data:inputs.Admission,principal:Principal,key:Key):
    return commands.admit(principal,room_id,key,data,applying=True)[1]


@router.get('/raid-room-applications/{application_id}',response_model=s.OutputContract3GetV2RaidRoomApplicationsApplicationId,responses=errors)
def application(application_id:UUID,principal:Principal):return commands.application(principal,application_id)


@router.post('/raid-room-applications/{application_id}/approve',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def approve(application_id:UUID,data:inputs.Approve,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data)[1]


@router.post('/raid-room-applications/{application_id}/reject',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,responses=errors)
def reject(application_id:UUID,data:inputs.Approve,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data,action='reject')[1]


@router.post('/raid-room-applications/{application_id}/withdraw',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,responses=errors)
def withdraw(application_id:UUID,data:inputs.Withdraw,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data,action='withdraw')[1]


@router.post('/raid-rooms/search',response_model=s.OutputContract3PostV2RaidRoomsSearch,responses=errors)
def search(data:inputs.Search,principal:OptionalPrincipal=None):return queries.search(principal,data)


@router.get('/raid-rooms',response_model=s.OutputContract3PostV2RaidRoomsSearch,responses=errors)
def room_list(target_cycle_key:str,principal:OptionalPrincipal=None,scope:Literal['public','group']='public',
    group_id:UUID|None=None,raid_id:str|None=None,difficulty_id:str|None=None,
    limit:Annotated[int,Query(ge=1,le=50)]=20,cursor:Annotated[str|None,Query(max_length=2048)]=None,
    experience_levels:Annotated[list[s.ExperienceFilterValue],Query()]=[]):
    if difficulty_id and not raid_id:fail('INVALID_REQUEST',400)
    try:
        data=inputs.Search.model_validate(dict(category='all',admission_scope=scope,group_ids=[group_id] if group_id else [],
            filter_context_token=None,member_conditions=[],raid_ids=[raid_id] if raid_id else [],
            difficulty_ids=[difficulty_id] if difficulty_id else [],limit=limit,cursor=cursor,
            target_cycle_key=target_cycle_key,experience_levels=experience_levels))
    except ValidationError:fail('INVALID_REQUEST',400)
    return queries.search(principal,data)


@router.get('/me/raid-room-filter-context',response_model=FilterContext,responses=errors)
def filter_context(principal:Principal,group_ids:Annotated[str,Query(max_length=32768)]):
    try:ids=TypeAdapter(list[UUID]).validate_python(json.loads(group_ids,object_pairs_hook=unique_pairs))
    except (ValueError,TypeError,ValidationError,RecursionError):fail('INVALID_REQUEST',400)
    return queries.filters.get_context(principal,ids)


@router.get('/raid-rooms/{room_id}',response_model=s.OutputContract3GetV2RaidRoomsRoomId,responses=errors)
def card(room_id:UUID,target_cycle_key:str,principal:OptionalPrincipal=None):return queries.get_card(principal,room_id,target_cycle_key)


@router.get('/raid-rooms/{room_id}/detail',response_model=s.OutputContract3GetV2RaidRoomsRoomIdDetail,responses=errors)
def detail(room_id:UUID,target_cycle_key:str,principal:Principal):return members.detail(principal,room_id,target_cycle_key)


@router.get('/me/raid-rooms/{room_id}/plan',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdPlan,responses=errors)
def plan(room_id:UUID,target_cycle_key:str,principal:Principal):return members.plan(principal,room_id,target_cycle_key)


AppState=Literal['pending','accepted','rejected','withdrawn','expired','cancelled','all']
Limit=Annotated[int,Query(ge=1,le=50)]
Cursor=Annotated[str|None,Query(max_length=2048)]


@router.get('/me/raid-room-applications',response_model=s.OutputContract3GetV2RaidRoomsRoomIdApplications,responses=errors)
def my_applications(principal:Principal,target_cycle_key:str,state:AppState='pending',limit:Limit=20,cursor:Cursor=None):
    return lists.applications(principal,target_cycle_key,state=state,limit=limit,cursor=cursor)


@router.get('/raid-rooms/{room_id}/applications',response_model=s.OutputContract3GetV2RaidRoomsRoomIdApplications,responses=errors)
def applications(room_id:UUID,principal:Principal,target_cycle_key:str,state:AppState='pending',limit:Limit=20,cursor:Cursor=None):
    return lists.applications(principal,target_cycle_key,rid=room_id,state=state,limit=limit,cursor=cursor)


@router.get('/me/raid-room-memberships',response_model=s.OutputContract3GetV2MeRaidRoomMemberships,responses=errors)
def memberships(principal:Principal,target_cycle_key:str,state:Literal['current','ended','all']='current',limit:Limit=20,cursor:Cursor=None):
    return lists.memberships(principal,target_cycle_key,state,limit,cursor)


@router.get('/groups/{group_id}/raid-room-member-projections',response_model=s.OutputContract3GetV2GroupsGroupIdRaidRoomMemberProjections,responses=errors)
def projections(group_id:UUID,principal:Principal,target_cycle_key:str,room_ids:Annotated[str,Query(max_length=32768)],
    filter_context_token:str|None=None,group_ids:Annotated[str|None,Query(max_length=32768)]=None):
    try:
        rids=[UUID(v) for v in room_ids.split(',')]
        gids=[UUID(v) for v in group_ids.split(',')] if group_ids is not None else None
    except ValueError:fail('INVALID_REQUEST',400)
    return lists.projections(principal,group_id,rids,target_cycle_key,filter_context_token,gids)


@router.get('/me/raid-rooms/{room_id}/continuation-context',response_model=s.ContinuationContext,responses=errors)
def continuation_context(room_id:UUID,principal:Principal,target_cycle_key:str,action:Literal['join','decline']='join',
    character_id:UUID|None=None,selected_role:Role|None=None):
    return cycle_continuation.get(principal,room_id,target_cycle_key,action,character_id,selected_role)


@router.post('/raid-rooms/{room_id}/continuation-participations',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def continue_participation(room_id:UUID,principal:Principal,key:Key,data:inputs.Continue):
    return cycle_continuation.execute(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/continuation-declines',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def decline_continuation(room_id:UUID,principal:Principal,key:Key,data:inputs.Decline):
    return cycle_continuation.execute(principal,room_id,key,data,decline=True)[1]


@router.get('/me/raid-rooms/{room_id}/opening-context',response_model=s.OpeningContext,responses=errors)
def opening_context(room_id:UUID,principal:Principal,target_cycle_key:str,intent:Literal['open','reopen'],
    character_id:UUID|None=None,selected_role:Role|None=None):
    return cycle_opening.get(principal,room_id,target_cycle_key,intent,character_id,selected_role)


@router.post('/raid-rooms/{room_id}/recruitment-openings',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def open_recruitment(room_id:UUID,principal:Principal,key:Key,data:inputs.Open):
    return cycle_opening.execute(principal,room_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/participation-cancellation-context',response_model=s.CancellationContext,responses=errors)
def cancellation_context(room_id:UUID,principal:Principal,target_cycle_key:str):
    return cycle_leadership.get_cancel(principal,room_id,target_cycle_key)


@router.post('/raid-rooms/{room_id}/participation-cancellations',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def cancel_participation(room_id:UUID,principal:Principal,key:Key,data:inputs.Cancel):
    return cycle_leadership.cancel(principal,room_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/leadership-transfer-context',response_model=s.TransferContext,responses=errors)
def transfer_context(room_id:UUID,principal:Principal,target_cycle_key:str):
    return cycle_leadership.get_transfer(principal,room_id,target_cycle_key)


@router.post('/raid-rooms/{room_id}/leadership-transfers',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def transfer_leadership(room_id:UUID,principal:Principal,key:Key,data:inputs.Transfer):
    return cycle_leadership.transfer(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/character-changes',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def change_character(room_id:UUID,principal:Principal,key:Key,data:inputs.Character):
    return cycle_character.execute(principal,room_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/availability-submission',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdAvailabilitySubmission,responses=errors)
def get_submission(room_id:UUID,principal:Principal,target_cycle_key:str):
    return cycle_times.get_submission(principal,room_id,target_cycle_key)


@router.put('/me/raid-rooms/{room_id}/availability-submission',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdAvailabilitySubmission,responses=errors)
def put_submission(room_id:UUID,principal:Principal,key:Key,data:inputs.Submission):
    return cycle_times.put_submission(principal,room_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/schedule-context',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdScheduleContext,responses=errors)
def schedule_context(room_id:UUID,principal:Principal,target_cycle_key:str,target_session_id:UUID|None=None):
    return cycle_times.time_context(principal,room_id,target_cycle_key,target_session_id)


@router.get('/me/raid-schedule-overlaps',response_model=s.OutputContract3GetV2MeRaidScheduleOverlaps,responses=errors)
def schedule_overlaps(principal:Principal,target_cycle_key:str,limit:Limit=20,cursor:Cursor=None):
    return cycle_times.overlaps(principal,target_cycle_key,limit,cursor)


@router.post('/raid-sessions/{session_id}/participation-confirmations',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def confirm_participation(session_id:UUID,principal:Principal,key:Key,data:inputs.Confirm):
    return cycle_times.confirm(principal,session_id,key,data)[1]


@router.put('/raid-rooms/{room_id}/schedule-groups',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def edit_schedule(room_id:UUID,principal:Principal,key:Key,data:inputs.EditGroups):
    return cycle_schedule_service.edit(principal,room_id,key,data)[1]


@router.get('/raid-schedule-groups/{group_id}/candidates',response_model=s.OutputContract3GetV2RaidScheduleGroupsGroupIdCandidates,responses=errors)
def schedule_candidates(group_id:UUID,principal:Principal,target_cycle_key:str):
    return cycle_schedule_service.candidates(principal,group_id,target_cycle_key)


@router.post('/raid-schedule-groups/{group_id}/selections',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def select_schedule(group_id:UUID,principal:Principal,key:Key,data:inputs.SelectGroup):
    return cycle_schedule_service.select_group(principal,group_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/schedule-proposals',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def propose_schedule(room_id:UUID,principal:Principal,key:Key,data:inputs.Propose):
    return cycle_schedule_service.propose(principal,room_id,key,data)[1]


@router.post('/raid-schedule-proposals/{proposal_id}/responses',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def respond_schedule(proposal_id:UUID,principal:Principal,key:Key,data:inputs.Respond):
    return cycle_schedule_service.respond(principal,proposal_id,key,data)[1]


@router.get('/raid-rooms/{room_id}/command-context',response_model=s.OutputContract3GetV2RaidRoomsRoomIdCommandContext,responses=errors)
def outcome_context(room_id:UUID,principal:Principal,target_cycle_key:str,command:Literal['close_weekly','complete_item','personal_completion'],round_id:UUID|None=None):
    return cycle_outcomes.get(principal,room_id,target_cycle_key,command,round_id)


@router.post('/raid-rooms/{room_id}/weekly-incomplete-closures',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def close_current_cycle(room_id:UUID,principal:Principal,key:Key,data:inputs.Closure):
    return cycle_outcomes.execute(principal,room_id,None,key,data,'close_weekly')[1]


@router.post('/raid-rounds/{round_id}/completion',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def complete_round(round_id:UUID,principal:Principal,key:Key,data:inputs.Outcome):
    return cycle_outcomes.execute(principal,None,round_id,key,data,'complete_item')[1]


@router.post('/raid-rounds/{round_id}/personal-completion',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def complete_personal_round(round_id:UUID,principal:Principal,key:Key,data:inputs.PersonalOutcome):
    return cycle_outcomes.execute(principal,None,round_id,key,data,'personal_completion')[1]


@router.post('/raid-rooms/{room_id}/weekly-resume-proposals',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def resume_current_cycle(room_id:UUID,principal:Principal,key:Key,data:inputs.Resume):
    return cycle_resume.create(principal,room_id,key,data)[1]


@router.put('/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion',response_model=s.ManualCompletionResult,responses=errors)
def manual_current_cycle(character_id:UUID,raid_id:str,principal:Principal,key:Key,data:inputs.Manual):
    return cycle_outcomes.manual(principal,character_id,raid_id,key,data)[1]


@router.get('/me/raid-rooms/{room_id}/settings',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdSettings,responses=errors)
def target_settings(room_id:UUID,principal:Principal,target_cycle_key:str):
    return cycle_management.get(principal,room_id,target_cycle_key)


@router.put('/raid-rooms/{room_id}/settings',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def edit_target_settings(room_id:UUID,principal:Principal,key:Key,data:inputs.TargetSettings):
    return cycle_management.command(principal,room_id,key,data,'settings')[1]


@router.put('/raid-rooms/{room_id}/formation',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def edit_target_formation(room_id:UUID,principal:Principal,key:Key,data:inputs.Formation):
    return cycle_management.command(principal,room_id,key,data,'formation')[1]


@router.post('/raid-rooms/{room_id}/removals',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def remove_target_member(room_id:UUID,principal:Principal,key:Key,data:inputs.Removal):
    return cycle_management.command(principal,room_id,key,data,'remove')[1]


@router.get('/me/raid-rooms/{room_id}/common-context',response_model=s.CommonContext,responses=errors)
def common_context(room_id:UUID,principal:Principal,command:Literal['edit_common_settings','leave','end']):
    return cycle_common.get(principal,room_id,command)


@router.put('/raid-rooms/{room_id}/common-settings',response_model=s.CommonSettingsAck,responses=errors)
def edit_common_settings(room_id:UUID,principal:Principal,key:Key,data:inputs.CommonSettings):
    return cycle_common.execute(principal,room_id,key,data,'edit_common_settings')[1]


@router.post('/raid-rooms/{room_id}/leave',response_model=s.GlobalMembershipAck,responses=errors)
def leave_global(room_id:UUID,principal:Principal,key:Key,data:inputs.GlobalMembership):
    return cycle_common.execute(principal,room_id,key,data,'leave')[1]


@router.post('/raid-rooms/{room_id}/end',response_model=s.GlobalMembershipAck,responses=errors)
def end_global(room_id:UUID,principal:Principal,key:Key,data:inputs.GlobalMembership):
    return cycle_common.execute(principal,room_id,key,data,'end')[1]
