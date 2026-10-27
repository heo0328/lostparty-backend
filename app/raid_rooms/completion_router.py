from uuid import UUID
from typing import Literal
from fastapi import APIRouter
from app.game_accounts.router import Principal,Key
from app.raid_rooms.admission_router import AdmissionRoute,errors
from app.raid_rooms.admission_schemas import Ack
from app.raid_rooms import completion as service,command_context,resume
from app.raid_rooms.command_schemas import Context


class CommandRoute(AdmissionRoute):
    def allowed_query(self,request):
        if request.method=='GET' and request.url.path.endswith('/command-context'):return {'command','round_id'}
        return super().allowed_query(request)


router=APIRouter(prefix='/v1',tags=['recruitment-completion'],route_class=CommandRoute)


@router.post('/raid-rooms/{room_id}/weekly-resume-proposals',response_model=Ack,responses=errors)
def resume_weekly(room_id:UUID,data:resume.ResumeRequest,principal:Principal,key:Key):
    return resume.create(principal,room_id,key,data)[1]


@router.get('/raid-rooms/{room_id}/command-context',response_model=Context,responses=errors)
def context(room_id:UUID,command:Literal['close_weekly','complete_item','personal_completion'],principal:Principal,round_id:UUID|None=None):
    return command_context.get(principal,room_id,command,round_id)


@router.post('/raid-rooms/{room_id}/weekly-incomplete-closures',response_model=Ack,responses=errors)
def close(room_id:UUID,data:service.ContextRequest,principal:Principal,key:Key):return service.command(principal,room_id,key,data,'close_weekly')[1]


@router.post('/raid-rounds/{round_id}/completion',response_model=Ack,responses=errors)
def complete(round_id:UUID,data:service.ContextRequest,principal:Principal,key:Key):
    return service.command(principal,None,key,data,'complete_item',round_id)[1]


@router.post('/raid-rounds/{round_id}/personal-completion',response_model=Ack,responses=errors)
def personal(round_id:UUID,data:service.Personal,principal:Principal,key:Key):
    return service.command(principal,None,key,data,'personal_completion',round_id)[1]


@router.post('/raid-rooms/{room_id}/leave',response_model=Ack,responses=errors)
def leave(room_id:UUID,data:service.MembershipCommand,principal:Principal,key:Key):return service.membership_command(principal,room_id,key,data,'leave')[1]


@router.post('/raid-rooms/{room_id}/transfer-leadership',response_model=Ack,responses=errors)
def transfer(room_id:UUID,data:service.Transfer,principal:Principal,key:Key):return service.membership_command(principal,room_id,key,data,'transfer')[1]


@router.post('/raid-rooms/{room_id}/end',response_model=Ack,responses=errors)
def end(room_id:UUID,data:service.MembershipCommand,principal:Principal,key:Key):return service.membership_command(principal,room_id,key,data,'end')[1]
