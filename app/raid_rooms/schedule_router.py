from uuid import UUID
from fastapi import APIRouter
from app.game_accounts.router import Principal,Key
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms.admission_schemas import Ack,DTO,Version
from app.raid_rooms import schedule_schemas as s,schedule_service as service
from datetime import datetime
from typing import Literal


class Candidate(DTO):
    group_id: UUID
    revision: Version
    plan_revision: Version
    evaluated_at: datetime
    state: Literal['ready','no_candidate','search_limited']
    earliest_start: datetime|None
    latest_start: datetime|None


router=APIRouter(prefix='/v1',tags=['recruitment-scheduling'],route_class=AdmissionRoute)


@router.put('/raid-rooms/{room_id}/schedule-groups',response_model=Ack,responses=errors)
def edit(room_id:UUID,data:s.EditGroups,principal:Principal,key:Key):return service.edit(principal,room_id,key,data)[1]


@router.get('/raid-schedule-groups/{group_id}/candidates',response_model=Candidate,responses=errors)
def candidates(group_id:UUID,principal:Principal):return service.candidates(principal,group_id)


@router.post('/raid-schedule-groups/{group_id}/selections',response_model=Ack,responses=errors)
def select(group_id:UUID,data:s.SelectGroup,principal:Principal,key:Key):return service.select_group(principal,group_id,key,data)[1]


@router.post('/raid-rooms/{room_id}/schedule-proposals',response_model=Ack,responses=errors)
def propose(room_id:UUID,data:s.Propose,principal:Principal,key:Key):return service.propose(principal,room_id,key,data)[1]


@router.post('/raid-schedule-proposals/{proposal_id}/responses',response_model=Ack,responses=errors)
def respond(proposal_id:UUID,data:s.Respond,principal:Principal,key:Key):return service.respond(principal,proposal_id,key,data)[1]


@router.post('/raid-sessions/{session_id}/participation-confirmations',response_model=Ack,responses=errors)
def confirm(session_id:UUID,data:s.Confirm,principal:Principal,key:Key):return service.confirm(principal,session_id,key,data)[1]
