from typing import Annotated
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut
from app.game_accounts.support import fail
from app.groups import schemas, http_service, management, display
from app.groups import display_schemas as ds
from app.groups import extended_management, raid_state, management_schemas as ms
from app.member_limits import schemas as limit_schemas, service as limits


async def strict_input(request: Request):
    path = request.url.path
    allowed = set()
    if request.method == 'GET':
        if path in ('/v1/groups', '/v1/me/groups') or path.endswith(('/members', '/activity-characters', '/raid-rooms')):
            allowed = {'limit', 'cursor'}
        if path == '/v1/me/groups' or path.startswith('/v1/me/groups/') or path.endswith('/members'):
            allowed.add('reader_profile')
        if path.endswith('/management'):
            allowed.add('management_profile')
        if path == '/v1/groups':
            allowed.add('q')
    if (set(request.query_params)-allowed or
            any(len(request.query_params.getlist(key)) != 1 for key in request.query_params) or
            (request.method == 'GET' and await request.body())):
        fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1', tags=['groups'], dependencies=[Depends(strict_input)])
errors = {code: {'model': GameErrorOut} for code in (400, 401, 403, 404, 409, 503)}
Limit = Annotated[int, Query(ge=1, le=50)]
Cursor = Annotated[str | None, Query(min_length=1, max_length=2048)]


@router.get('/me/usage-limits', response_model=limit_schemas.UsageLimits, responses=errors)
def usage_limits(principal: Principal):
    return limits.get(principal)


@router.post('/groups', status_code=201, response_model=schemas.GroupDetail, responses=errors)
def create(data: schemas.GroupCreateIn, principal: Principal, key: Key):
    return http_service.create(principal, key, data)[1]


@router.get('/groups', response_model=schemas.GroupSummaryPage, responses=errors)
def public_list(q: Annotated[str, Query(max_length=64)] = '', limit: Limit = 20, cursor: Cursor = None):
    return http_service.public_list(q, limit, cursor)


@router.get('/groups/{group_id}', response_model=schemas.GroupSummary, responses=errors)
def public_detail(group_id: UUID):
    return http_service.get_public(group_id)


@router.get('/me/groups', response_model=ds.DisplayMyGroupPage | schemas.MyGroupPage, responses=errors)
def my_list(principal: Principal, limit: Limit = 20, cursor: Cursor = None, reader_profile: Literal['group-display-1'] | None = None):
    if reader_profile: return display.my_groups(principal, limit, cursor)
    return http_service.my_list(principal, limit, cursor)


@router.get('/me/groups/{group_id}', response_model=ds.DisplayDetail | schemas.GroupDetail, responses=errors)
def private_detail(group_id: UUID, principal: Principal, reader_profile: Literal['group-display-1'] | None = None):
    if reader_profile: return display.my_groups(principal, gid=group_id)
    return http_service.get_private(principal, group_id)


@router.get('/groups/{group_id}/members', response_model=ds.DisplayMemberPage | schemas.GroupMemberPage, responses=errors)
def members(group_id: UUID, principal: Principal, limit: Limit = 20, cursor: Cursor = None, reader_profile: Literal['group-display-1'] | None = None):
    if reader_profile: return display.members(principal, group_id, limit, cursor)
    return http_service.members(principal, group_id, limit, cursor)


@router.patch('/groups/{group_id}', response_model=schemas.GroupDetail, responses=errors)
def rename(group_id: UUID, data: schemas.GroupRenameIn, principal: Principal, key: Key):
    return http_service.rename(principal, group_id, key, data)[1]


@router.get('/groups/{group_id}/management', response_model=ms.ExtendedGroupManagement | schemas.GroupManagement, responses=errors)
def group_management(group_id: UUID, principal: Principal, management_profile: Literal['group-management-1'] | None = None):
    if management_profile: return extended_management.get(principal, group_id)
    return management.get(principal, group_id)


@router.post('/groups/{group_id}/leadership-transfer', response_model=schemas.LeadershipTransferAck, responses=errors)
def transfer_leadership(group_id: UUID, data: schemas.TransferLeadershipIn, principal: Principal, key: Key):
    return management.transfer(principal, group_id, key, data)[1]


@router.post('/groups/{group_id}/leave', response_model=schemas.GroupLeaveAck, responses=errors)
def leave_group(group_id: UUID, data: schemas.LeaveGroupIn, principal: Principal, key: Key):
    return management.leave(principal, group_id, key, data)[1]


@router.get('/groups/{group_id}/members/{membership_id}/activity-characters', response_model=ds.ActivityCharacterPage, responses=errors)
def activity_characters(group_id: UUID, membership_id: UUID, principal: Principal, limit: Limit = 20, cursor: Cursor = None):
    return display.activity(principal, group_id, membership_id, limit, cursor)


@router.get('/me/group-request-counts', response_model=ds.GroupRequestCounts, responses=errors)
def request_counts(principal: Principal):
    return display.counts(principal)


@router.get('/groups/{group_id}/join-request-counts', response_model=ds.GroupJoinRequestCounts, responses=errors)
def join_request_counts(group_id: UUID, principal: Principal):
    return display.counts(principal, group_id)


@router.post('/groups/{group_id}/disband', response_model=ms.GroupDisbandAck, responses=errors)
def disband(group_id: UUID, data: ms.DisbandGroupIn, principal: Principal, key: Key):
    return extended_management.command(principal, group_id, key, data, 'disband')[1]


@router.post('/groups/{group_id}/members/{membership_id}/remove', response_model=ms.GroupRemoveAck, responses=errors)
def remove_member(group_id: UUID, membership_id: UUID, data: ms.RemoveGroupMemberIn, principal: Principal, key: Key):
    return extended_management.command(principal, group_id, key, data, 'remove', membership_id)[1]


@router.put('/groups/{group_id}/representative', response_model=ms.GroupRepresentativeAck, responses=errors)
def change_representative(group_id: UUID, data: ms.ChangeGroupRepresentativeIn, principal: Principal, key: Key):
    return extended_management.command(principal, group_id, key, data, 'representative')[1]


@router.get('/groups/{group_id}/raid-rooms', response_model=ms.GroupRaidRoomPage, responses=errors)
def group_raid_rooms(group_id: UUID, principal: Principal, limit: Limit = 20, cursor: Cursor = None):
    return raid_state.listing(principal, group_id, limit, cursor)
