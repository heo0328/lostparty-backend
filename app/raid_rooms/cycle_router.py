"""Candidate write router. Intentionally absent from main until W4 cutover.

Only isolated tests mount this router against the shadow schema. Publishing
these paths in the runtime OpenAPI would falsely claim mixed-worker readiness.
"""
from app.raid_rooms import beta_profile,beta_schemas
import json
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Query, Request, Header
from pydantic import UUID4
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
from app.raid_rooms import character_candidates
from app.raid_rooms.candidate_schemas import CandidatePage
from app.raid_rooms import session_display_schemas as display_schemas
from app.raid_rooms import resume_review, resume_review_schemas
from app.raid_rooms import completion_correction, completion_correction_schemas as correction_schemas
from app.raid_rooms import admission_candidates
from app.raid_rooms.admission_candidate_schemas import AdmissionCandidatePage
from app.raid_rooms import application_display_schemas, group_link_display as group_link,group_connection


from app.raid_rooms import atomic_members, atomic_member_schemas as atomic_schemas
from app.raid_rooms import membership_actions, membership_readers, membership_action_schemas as membership_schemas


class CycleRoute(AvailabilityRoute):
    def capture_body(self,request,value):
        beta_profile.capture_body(value)

    def repeated_query(self,request):
        return {'experience_levels'} if request.method=='GET' and request.url.path.endswith('/raid-rooms') else set()

    def get_route_handler(self):
        parent=super().get_route_handler()
        async def bounded(request:Request):
            try:
                profile=request.query_params.get('contract_profile')
                if profile is not None and profile!=beta_profile.PROFILE:fail('INVALID_REQUEST',400)
                with beta_profile.request_scope(dict(request.query_params) if profile else None):
                    return await parent(request)
            except (AuthError,RequestValidationError,SQLAlchemyError) as error:
                code=('SERVICE_UNAVAILABLE' if isinstance(error,SQLAlchemyError) else
                      getattr(error,'code','INVALID_REQUEST'))
                status=getattr(error,'status',400 if isinstance(error,RequestValidationError) else 503)
                value=response(request,code,status,getattr(error,'retry_after',None),getattr(error,'retry_at',None))
                body=json.loads(value.body)
                body['error']['details']=getattr(error,'cycle_details',None)
                return JSONResponse(status_code=status,headers={k:v for k,v in value.headers.items() if k!='content-length'},content=body)
        return bounded

    def allowed_query(self,request):
        fields=self.legacy_allowed_query(request)|{'contract_profile'}
        if beta_profile.enabled():
            if request.method=='GET' and request.url.path.endswith(('/raid-room-creation-context','/opening-context')):
                fields|={'base_starts_at','early_coordination_enabled','early_additional_members'}
                if request.url.path.endswith('/raid-room-creation-context'):
                    fields|={'next_base_starts_at','next_early_coordination_enabled','next_early_additional_members'}
            if request.method=='GET' and request.url.path.endswith(('/detail','/plan')):
                fields|={'include_coordination_wait'}
            if request.method=='GET' and request.url.path.endswith('/raid-rooms'):
                fields|={'departure_windows','schedule_states'}
        return fields

    def legacy_allowed_query(self, request):
        if request.method=='POST' and request.url.path.endswith('/weekly-resume-proposals'):return {'preview_only'}
        if request.method=='POST' and request.url.path.endswith('/raid-rooms/search'):return {'include_group_state'}
        if request.method!='GET':return set()
        if request.url.path.endswith('/raid-room-character-candidates'):return {'filter_context_token','limit','cursor'}
        if request.url.path.endswith('/personal-completion-departure-context'):return {'target_cycle_key','round_id'}
        if request.url.path.endswith('/member-removal-context'):return {'target_cycle_key','target_cycle_member_id'}
        if request.url.path.endswith('/completion-correction-context'):return {'target_cycle_key'}
        if request.url.path.endswith('/common-context'):return {'command','target_group_id'}
        if request.url.path.endswith('/command-context'):return {'target_cycle_key','command','round_id'}
        if request.url.path.endswith('/candidates'):return {'target_cycle_key'}
        if request.url.path.endswith('/schedule-context'):return {'target_cycle_key','target_session_id'}
        if request.url.path.endswith('/raid-schedule-overlaps'):return {'target_cycle_key','limit','cursor'}
        if request.url.path.endswith('/continuation-context'):return {'target_cycle_key','action','character_id','selected_role','include_session_display'}
        if request.url.path.endswith('/opening-context'):return {'target_cycle_key','intent','character_id','selected_role','include_session_display'}
        if request.url.path.endswith(('/participation-cancellation-context','/leadership-transfer-context')):return {'target_cycle_key'}
        if request.url.path.endswith('/raid-room-member-projections'):return {'room_ids','target_cycle_key','group_ids','filter_context_token'}
        if request.url.path.endswith('/raid-room-filter-context'):return {'group_ids'}
        if request.url.path.endswith('/raid-rooms'):return {'scope','group_id','raid_id','difficulty_id','limit','cursor','target_cycle_key','experience_levels','include_group_state'}
        if request.url.path.endswith('/raid-room-memberships'):return {'target_cycle_key','state','limit','cursor','reader_profile','include_group_state'}
        if request.url.path.endswith('/applications') or request.url.path.endswith('/raid-room-applications'):
            return {'target_cycle_key','state','limit','cursor','reader_profile'} if request.url.path.endswith('/applications') else {'target_cycle_key','state','limit','cursor','include_group_state'}
        if request.url.path.endswith('/raid-room-creation-context'):
            return {'target_cycle_key','character_id','selected_role','items','group_id',
                'continuation_enabled','next_character_id','next_selected_role'}
        if request.url.path.endswith('/admission-character-candidates'):return {'target_cycle_key','intent','limit','cursor'}
        if request.url.path.endswith('/admission-context'):
            return {'target_cycle_key','character_id','selected_role','intent','include_session_display'}
        if request.url.path.endswith('/plan'):return {'target_cycle_key','include_resume_display','reader_profile','membership_id','cycle_member_id','include_group_state'}
        if request.url.path.endswith('/detail'):
            return {'target_cycle_key','reader_profile','membership_id','cycle_member_id','include_group_state'}
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
def create(data:inputs.Create|beta_schemas.BetaCreateRequest,principal:Principal,key:Key):
    data=beta_profile.request_model(data,inputs.Create,beta_schemas.BetaCreateRequest)
    return creation.create(principal,key,data)[1]


@router.get('/raid-rooms/{room_id}/admission-character-candidates',response_model=AdmissionCandidatePage,responses=errors,
    description='Read-only own candidates for apply/join/change_character under admission-eligibility-2. All roles and counts use the same eligibility as commands; no occupancy, provider calls or writes. Cursors bind actor/session, room, actual target and intent; changed snapshot is CURSOR_STALE.')
def admission_character_candidates(room_id:UUID,principal:Principal,target_cycle_key:str,
    intent:Literal['apply','join','change_character'],limit:Annotated[int,Query(ge=1,le=100)]=50,
    cursor:Annotated[str,Query(min_length=1,max_length=2048)]|None=None):
    return admission_candidates.get(principal,room_id,target_cycle_key,intent,limit,cursor)


@router.get('/raid-rooms/{room_id}/admission-context',response_model=display_schemas.AdmissionDisplayContext,response_model_exclude_unset=True,responses=errors,
    description='Apply/change_character use admission-eligibility-2: product-supported roles, bundle level, role-specific retained power, actual-target completion/occupancy and per-party composition. Change targets bind the exact own assignments and original-party-first valid placement. Pending never reserves a slot; current command tokens and consent must still match.')
def admission_context(room_id:UUID,principal:Principal,target_cycle_key:str,character_id:UUID,
    selected_role:Role,intent:Literal['apply','join','change_character'],include_session_display:Literal['true','false']='false'):
    return commands.get_context(principal,room_id,target_cycle_key,character_id,selected_role,intent,include_session_display=="true")


@router.post('/raid-rooms/{room_id}/join',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def join(room_id:UUID,data:inputs.Admission,principal:Principal,key:Key):
    return commands.admit(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/applications',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,status_code=201,responses=errors,
    description='Revalidate admission-eligibility-2 and exact displayed target parties before creating pending. Unsupported roles are ROLE_NOT_SUPPORTED. Capture item_level/item_level_source=application_snapshot/item_level_fetched_at in application display from the selected character and original confirmation time. No confirmed assignment, weekly occupancy or reservation is created; original ACK replay is preserved.')
def apply(room_id:UUID,data:inputs.Admission|beta_schemas.BetaApplyRequest,principal:Principal,key:Key):
    data=beta_profile.request_model(data,inputs.Admission,beta_schemas.BetaApplyRequest)
    return commands.admit(principal,room_id,key,data,applying=True)[1]


@router.get('/raid-room-applications/{application_id}',response_model=s.OutputContract3GetV2RaidRoomApplicationsApplicationId,responses=errors)
def application(application_id:UUID,principal:Principal):return commands.application(principal,application_id)


@router.post('/raid-room-applications/{application_id}/approve',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors,
    description='Revalidate admission-eligibility-2 at the stored application parties under the mutation lock. Qualification failure preserves pending and all business occupancy/reservations; no automatic rejection, withdrawal or party relocation. Original ACK replay is preserved.')
def approve(application_id:UUID,data:inputs.Approve,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data)[1]


@router.post('/raid-room-applications/{application_id}/reject',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,responses=errors)
def reject(application_id:UUID,data:inputs.Approve,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data,action='reject')[1]


@router.post('/raid-room-applications/{application_id}/withdraw',response_model=s.OutputContract3PostV2RaidRoomsRoomIdApplications,responses=errors)
def withdraw(application_id:UUID,data:inputs.Withdraw,principal:Principal,key:Key):
    return commands.process(principal,application_id,key,data,action='withdraw')[1]


@router.post('/raid-rooms/search',response_model=group_link.GroupSearchPage|s.OutputContract3PostV2RaidRoomsSearch,responses=errors,
    description='Authenticated search excludes own active persistent membership with participating/review_required CM in the selected actual T/current generation, in SQL before sorting and pagination. Opposite-only, pending and historical relations are preserved. Cursor semantics: own-target-participation-excluded-v1; old semantics/head changes return CURSOR_STALE (409), foreign/tampered scope INVALID_REQUEST (400).')
def search(data:inputs.Search|beta_schemas.BetaSearchRequest,principal:OptionalPrincipal=None,include_group_state:Literal['true','false']='false'):
    data=beta_profile.request_model(data,inputs.Search,beta_schemas.BetaSearchRequest)
    return queries.search(principal,data,include_group_state=='true')


@router.get('/raid-rooms',response_model=group_link.GroupSearchPage|s.OutputContract3PostV2RaidRoomsSearch,responses=errors,description='GET adapter uses the same SQL exclusion, cursor scope and own-target-participation-excluded-v1 semantics as POST /v2/raid-rooms/search.')
def room_list(target_cycle_key:str,principal:OptionalPrincipal=None,scope:Literal['public','group']='public',
    group_id:UUID|None=None,raid_id:str|None=None,difficulty_id:str|None=None,
    limit:Annotated[int,Query(ge=1,le=50)]=20,cursor:Annotated[str|None,Query(max_length=2048)]=None,
    experience_levels:Annotated[list[s.ExperienceFilterValue],Query()]=[],include_group_state:Literal['true','false']='false'):
    if difficulty_id and not raid_id:fail('INVALID_REQUEST',400)
    try:
        data=(beta_schemas.BetaSearchRequest if beta_profile.enabled() else inputs.Search).model_validate(dict(category='all',admission_scope=scope,group_ids=[group_id] if group_id else [],
            filter_context_token=None,member_conditions=[],raid_ids=[raid_id] if raid_id else [],
            difficulty_ids=[difficulty_id] if difficulty_id else [],limit=limit,cursor=cursor,
            target_cycle_key=target_cycle_key,experience_levels=experience_levels,**({k:json.loads(beta_profile.query()[k],object_pairs_hook=unique_pairs) for k in ('departure_windows','schedule_states') if k in beta_profile.query()} if beta_profile.enabled() else {})))
    except (ValidationError,ValueError,TypeError):fail('INVALID_REQUEST',400)
    return queries.search(principal,data,include_group_state=='true')


@router.get('/me/raid-room-filter-context',response_model=FilterContext,responses=errors)
def filter_context(principal:Principal,group_ids:Annotated[str,Query(max_length=32768)]):
    try:ids=TypeAdapter(list[UUID]).validate_python(json.loads(group_ids,object_pairs_hook=unique_pairs))
    except (ValueError,TypeError,ValidationError,RecursionError):fail('INVALID_REQUEST',400)
    return queries.filters.get_context(principal,ids)


@router.get('/groups/{group_id}/raid-room-character-candidates',response_model=CandidatePage,responses=errors)
def group_character_candidates(group_id:UUID,principal:Principal,
    filter_context_token:Annotated[str,Query(min_length=64,max_length=64,pattern=r'^[0-9a-f]{64}$')],
    limit:Annotated[int,Query(ge=1,le=100)]=50,
    cursor:Annotated[str|None,Query(min_length=1,max_length=2048)]=None):
    return character_candidates.get(principal,group_id,filter_context_token,limit,cursor)


@router.get('/raid-rooms/{room_id}',response_model=s.OutputContract3GetV2RaidRoomsRoomId,responses=errors)
def card(room_id:UUID,target_cycle_key:str,principal:OptionalPrincipal=None):return queries.get_card(principal,room_id,target_cycle_key)


@router.get('/raid-rooms/{room_id}/detail',response_model=group_link.GroupLinkedDetail|group_link.GroupLinkedMembershipDetail|group_link.GroupLinkedApplicationDetail|s.OutputContract3GetV2RaidRoomsRoomIdDetail|membership_schemas.DetailProfile|application_display_schemas.ApplicationDisplayDetailResponse,response_model_exclude_unset=True,responses=errors)
def detail(room_id:UUID,target_cycle_key:str,principal:Principal,include_coordination_wait:Literal['true','false']='false',reader_profile:Literal['membership-actions-1','application-display-1']|None=None,
    membership_id:UUID|None=None,cycle_member_id:UUID|None=None,include_group_state:Literal['true','false']='false'):
    if include_group_state=='true':
        if reader_profile!='membership-actions-1' and (membership_id is not None or cycle_member_id is not None):fail('INVALID_REQUEST',400)
        return group_link.get(principal,room_id,target_cycle_key,'detail',reader_profile=reader_profile,membership_id=membership_id,cycle_member_id=cycle_member_id)
    if reader_profile == 'membership-actions-1':
        return membership_readers.get(principal,room_id,target_cycle_key,'detail',membership_id=membership_id,cycle_member_id=cycle_member_id)
    if membership_id is not None or cycle_member_id is not None:fail('INVALID_REQUEST',400)
    return members.detail(principal,room_id,target_cycle_key,reader_profile=reader_profile)


@router.get('/me/raid-rooms/{room_id}/plan',response_model=group_link.GroupLinkedPlan|group_link.GroupLinkedMembershipPlan|resume_review_schemas.ResumePlanContext|membership_schemas.PlanProfile,response_model_exclude_unset=True,responses=errors)
def plan(room_id:UUID,target_cycle_key:str,principal:Principal,include_coordination_wait:Literal['true','false']='false',include_resume_display:Literal['true','false']='false',
    reader_profile:Literal['membership-actions-1']|None=None,membership_id:UUID|None=None,cycle_member_id:UUID|None=None,include_group_state:Literal['true','false']='false'):
    if include_group_state=='true':
        if reader_profile is None and (membership_id is not None or cycle_member_id is not None):fail('INVALID_REQUEST',400)
        return group_link.get(principal,room_id,target_cycle_key,'plan',reader_profile=reader_profile,membership_id=membership_id,cycle_member_id=cycle_member_id,include_resume_display=include_resume_display=='true')
    if reader_profile is not None:
        return membership_readers.get(principal,room_id,target_cycle_key,'plan',membership_id=membership_id,cycle_member_id=cycle_member_id,include_resume_display=include_resume_display=='true')
    if membership_id is not None or cycle_member_id is not None:fail('INVALID_REQUEST',400)
    return members.plan(principal,room_id,target_cycle_key,include_resume_display=='true')


AppState=Literal['pending','accepted','rejected','withdrawn','expired','cancelled','all']
Limit=Annotated[int,Query(ge=1,le=50)]
Cursor=Annotated[str|None,Query(max_length=2048)]


@router.get('/me/raid-room-applications',response_model=group_link.GroupApplicationPage|s.OutputContract3GetV2RaidRoomsRoomIdApplications,responses=errors)
def my_applications(principal:Principal,target_cycle_key:str,state:AppState='pending',limit:Limit=20,cursor:Cursor=None,include_group_state:Literal['true','false']='false'):
    return lists.applications(principal,target_cycle_key,state=state,limit=limit,cursor=cursor,include_group_state=include_group_state=='true')


@router.get('/raid-rooms/{room_id}/applications',response_model=s.OutputContract3GetV2RaidRoomsRoomIdApplications|application_display_schemas.ApplicationDisplayPageResponse,responses=errors,
    description='application-display-1 always includes display.item_level, item_level_source and item_level_fetched_at. Preserve a real application_snapshot; legacy missing values use current_saved only for the same applicant/character/ownership revision and confirmed active source, otherwise unavailable. Original fetched time may be null; no backfill, provider calls, extra queries or approval decision. Other display fields stay application snapshots.')
def applications(room_id:UUID,principal:Principal,target_cycle_key:str,state:AppState='pending',limit:Limit=20,cursor:Cursor=None,
    reader_profile:Literal['application-display-1']|None=None):
    return lists.applications(principal,target_cycle_key,rid=room_id,state=state,limit=limit,cursor=cursor,reader_profile=reader_profile)


@router.get('/me/raid-room-memberships',response_model=group_link.GroupMembershipPage|group_link.GroupActionMembershipPage|s.OutputContract3GetV2MeRaidRoomMemberships|membership_schemas.MembershipPage,responses=errors)
def memberships(principal:Principal,target_cycle_key:str,state:Literal['current','ended','all']='current',limit:Limit=20,cursor:Cursor=None,reader_profile:Literal['membership-actions-1']|None=None,include_group_state:Literal['true','false']='false'):
    if reader_profile is not None:return membership_readers.memberships(principal,target_cycle_key,state,limit,cursor,include_group_state=='true')
    return lists.memberships(principal,target_cycle_key,state,limit,cursor,include_group_state=='true')


@router.get('/groups/{group_id}/raid-room-member-projections',response_model=s.OutputContract3GetV2GroupsGroupIdRaidRoomMemberProjections,responses=errors)
def projections(group_id:UUID,principal:Principal,target_cycle_key:str,room_ids:Annotated[str,Query(max_length=32768)],
    filter_context_token:str|None=None,group_ids:Annotated[str|None,Query(max_length=32768)]=None):
    try:
        rids=[UUID(v) for v in room_ids.split(',')]
        gids=[UUID(v) for v in group_ids.split(',')] if group_ids is not None else None
    except ValueError:fail('INVALID_REQUEST',400)
    return lists.projections(principal,group_id,rids,target_cycle_key,filter_context_token,gids)


@router.get('/me/raid-rooms/{room_id}/continuation-context',response_model=display_schemas.ContinuationDisplayContext,response_model_exclude_unset=True,responses=errors)
def continuation_context(room_id:UUID,principal:Principal,target_cycle_key:str,action:Literal['join','decline']='join',
    character_id:UUID|None=None,selected_role:Role|None=None,include_session_display:Literal["true","false"]="false"):
    return cycle_continuation.get(principal,room_id,target_cycle_key,action,character_id,selected_role,include_session_display=="true")


@router.post('/raid-rooms/{room_id}/continuation-participations',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def continue_participation(room_id:UUID,principal:Principal,key:Key,data:inputs.Continue):
    return cycle_continuation.execute(principal,room_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/continuation-declines',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def decline_continuation(room_id:UUID,principal:Principal,key:Key,data:inputs.Decline):
    return cycle_continuation.execute(principal,room_id,key,data,decline=True)[1]


@router.get('/me/raid-rooms/{room_id}/opening-context',response_model=display_schemas.OpeningDisplayContext,response_model_exclude_unset=True,responses=errors)
def opening_context(room_id:UUID,principal:Principal,target_cycle_key:str,intent:Literal['open','reopen'],
    character_id:UUID|None=None,selected_role:Role|None=None,include_session_display:Literal["true","false"]="false"):
    return cycle_opening.get(principal,room_id,target_cycle_key,intent,character_id,selected_role,include_session_display=="true")


@router.post('/raid-rooms/{room_id}/recruitment-openings',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors)
def open_recruitment(room_id:UUID,principal:Principal,key:Key,data:inputs.Open|beta_schemas.BetaOpenRequest):
    data=beta_profile.request_model(data,inputs.Open,beta_schemas.BetaOpenRequest)
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


@router.post('/raid-rooms/{room_id}/character-changes',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin,responses=errors,
    description='Atomically replace only the exact own current target assignments under admission-eligibility-2. Original party is preferred, then an eligible opposite party in eight-person rooms. Current token, actor revisions, target parties and consent must match; failure preserves old character, reservations and opposite target. Original ACK replay is preserved.')
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
def edit_schedule(room_id:UUID,principal:Principal,key:Key,data:inputs.EditGroups|beta_schemas.BetaScheduleEditRequest):
    data=beta_profile.request_model(data,inputs.EditGroups,beta_schemas.BetaScheduleEditRequest)
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


@router.post('/raid-rooms/{room_id}/weekly-resume-proposals',response_model=s.OutputContract3PostV2RaidRoomsRoomIdJoin|resume_review_schemas.ResumePreviewContext,response_model_exclude_unset=True,responses=errors)
def resume_current_cycle(room_id:UUID,principal:Principal,data:inputs.Resume,
    key:Annotated[UUID4|None,Header(alias='Idempotency-Key')]=None,preview_only:Literal['true','false']='false'):
    if preview_only=='true':return resume_review.preview(principal,room_id,data)
    if key is None:fail('INVALID_REQUEST',400)
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


@router.get('/me/raid-rooms/{room_id}/common-context',response_model=group_connection.GroupConnectionContext|s.CommonContext,responses=errors)
def common_context(room_id:UUID,principal:Principal,command:Literal['edit_common_settings','leave','end'],target_group_id:UUID|None=None):
    return cycle_common.get(principal,room_id,command,target_group_id)


@router.put('/raid-rooms/{room_id}/common-settings',response_model=s.CommonSettingsAck,responses=errors)
def edit_common_settings(room_id:UUID,principal:Principal,key:Key,data:inputs.CommonSettings):
    return cycle_common.execute(principal,room_id,key,data,'edit_common_settings')[1]


@router.post('/raid-rooms/{room_id}/leave',response_model=s.GlobalMembershipAck,responses=errors)
def leave_global(room_id:UUID,principal:Principal,key:Key,data:inputs.GlobalMembership):
    return cycle_common.execute(principal,room_id,key,data,'leave')[1]


@router.post('/raid-rooms/{room_id}/end',response_model=s.GlobalMembershipAck,responses=errors)
def end_global(room_id:UUID,principal:Principal,key:Key,data:inputs.GlobalMembership):
    return cycle_common.execute(principal,room_id,key,data,'end')[1]


@router.get('/me/raid-rooms/{room_id}/continuation-choices',response_model=s.OutputContract3GetV2MeRaidRoomsRoomIdContinuationChoices,responses=errors)
def legacy_choices(room_id:UUID,principal:Principal,target_cycle_key:str):
    from app.raid_rooms import cycle_legacy
    return cycle_legacy.get(principal,room_id,target_cycle_key)


# Preserve the operation IDs already consumed from the fixed contract.
for _route in router.routes:
    _method=next(iter(_route.methods)).lower()
    _name=_method+'__'+_route.path.strip('/').replace('/','_').replace('{','').replace('}','')
    _route.operation_id=_name if _route.path.rsplit('/',1)[-1] in (
        'continuation-context','continuation-participations','continuation-declines',
        'participation-cancellation-context','participation-cancellations','opening-context',
        'recruitment-openings','leadership-transfer-context','leadership-transfers') else 'contract3_'+_name
    if _route.path.endswith('/manual-completion'):_route.operation_id='contract3_manual_completion'


@router.get('/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context', response_model=correction_schemas.CorrectionContext, responses=errors)
def completion_correction_context(character_id:UUID,raid_id:str,principal:Principal,target_cycle_key:str):
    return completion_correction.context(principal,character_id,raid_id,target_cycle_key)


@router.post('/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections', response_model=correction_schemas.CorrectionResult, responses=errors)
def correct_completion(character_id:UUID,raid_id:str,principal:Principal,key:Key,data:correction_schemas.CorrectionCommand):
    return completion_correction.execute(principal,character_id,raid_id,key,data)[1]


@router.get('/raid-rooms/{room_id}/personal-completion-departure-context',response_model=atomic_schemas.DepartureContext,responses=errors)
def departure_context(room_id:UUID,target_cycle_key:atomic_schemas.CycleKey,round_id:UUID,principal:Principal):
    return atomic_members.get(principal,room_id,target_cycle_key,round_id=round_id)


@router.post('/raid-rooms/{room_id}/personal-completion-departures',response_model=atomic_schemas.ActionResult,responses=errors)
def personal_departure(room_id:UUID,data:atomic_schemas.DepartureCommand,principal:Principal,key:Key):
    return atomic_members.execute(principal,room_id,key,data,departure=True)[1]


@router.get('/raid-rooms/{room_id}/member-removal-context',response_model=atomic_schemas.RemovalContext,responses=errors)
def member_removal_context(room_id:UUID,target_cycle_key:atomic_schemas.CycleKey,target_cycle_member_id:UUID,principal:Principal):
    return atomic_members.get(principal,room_id,target_cycle_key,cmid=target_cycle_member_id)


@router.post('/raid-rooms/{room_id}/member-removals',response_model=atomic_schemas.ActionResult,responses=errors)
def atomic_removal(room_id:UUID,data:atomic_schemas.RemovalCommand,principal:Principal,key:Key):
    return atomic_members.execute(principal,room_id,key,data)[1]


@router.get('/raid-rooms/{room_id}/membership-action-context',response_model=membership_schemas.Context,responses=errors,description='Active persistent membership is the menu entrance; selected-T membership/leadership and recovery guards apply per option. GET never assigns leadership. Requires schema0031.')
def membership_action_context(room_id:UUID,target_cycle_key:atomic_schemas.CycleKey,principal:Principal):
    return membership_actions.get(principal,room_id,target_cycle_key)


@router.post('/raid-rooms/{room_id}/membership-actions',response_model=membership_schemas.Result,responses=errors,description='Exact six-field actor/view-T/action/opaque-token command. One transaction validates the complete selected option, cleans up, succeeds departure despite no qualified successor, records explicit recovery and C-to-N effects. Original ACK replay lasts24h; unchanged legacy operations use separate namespaces. Requires schema0031.')
def membership_action(room_id:UUID,data:membership_schemas.Command,principal:Principal,key:Key):
    return membership_actions.execute(principal,room_id,key,data)[1]


# include_router rebuilds each APIRoute with these opt-in response unions.
# Each legacy model remains untouched; beta models have their own required keys.
for _route in router.routes:
    _beta=beta_schemas.annotation(_route.response_model)
    if _beta != _route.response_model:
        _route.response_model=_route.response_model|_beta
    _parameters=[dict(name='contract_profile',**{'in':'query'},required=False,
        schema=dict(type='string',enum=[beta_profile.PROFILE]))]
    if _route.path.endswith(('/raid-room-creation-context','/opening-context')):
        for _prefix in ('','next_') if _route.path.endswith('/raid-room-creation-context') else ('',):
            for _key,_schema in [('base_starts_at',dict(type='string',format='date-time')),
                    ('early_coordination_enabled',dict(type='boolean')),
                    ('early_additional_members',dict(type='integer',minimum=1,maximum=7))]:
                _parameters.append(dict(name=_prefix+_key,**{'in':'query'},required=False,schema=_schema,
                    description='Required as specified by beta-recruitment-wire-2 only when contract_profile opts in.'))
    if _route.path=='/v2/raid-rooms' and 'GET' in _route.methods:
        for _key in ('departure_windows','schedule_states'):
            _parameters.append(dict(name=_key,**{'in':'query'},required=False,
                content={'application/json':{'schema':json.loads(json.dumps(beta_schemas.BetaSearchRequest.model_json_schema()['properties'][_key]).replace('#/$defs/','#/components/schemas/'))}}))
    _route.openapi_extra={'parameters':_parameters,'x-beta-contract-profile':beta_profile.PROFILE}
