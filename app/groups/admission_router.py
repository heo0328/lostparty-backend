from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from app.game_accounts.router import Principal, Key
from app.game_accounts.schemas import GameErrorOut, Name
from app.game_accounts.support import fail
from app.groups import admission_schemas as s, admissions, join_codes
from app.groups.router import Limit, Cursor
from app.groups.schemas import GroupDetail


async def strict_input(request: Request):
    path = request.url.path
    allowed = set()
    if request.method == 'GET':
        if path.endswith('/invite-candidates'):
            allowed = {'character_name'}
        elif path == '/v1/me/group-relations':
            allowed = {'view', 'state', 'limit', 'cursor'}
        elif path.endswith('/join-relations'):
            allowed = {'state', 'limit', 'cursor'}
        elif path.endswith('/blocked-subjects'):
            allowed = {'limit', 'cursor'}
    if (set(request.query_params)-allowed or
            any(len(request.query_params.getlist(key)) != 1 for key in request.query_params) or
            (request.method == 'GET' and await request.body())):
        fail('INVALID_REQUEST', 400)


router = APIRouter(prefix='/v1', tags=['groups'], dependencies=[Depends(strict_input)])
errors = {code: {'model': GameErrorOut} for code in (400,401,403,404,409,429,503)}
State = Literal['pending', 'all']
View = Literal['received_invitations', 'sent_applications', 'sent_invitations']


@router.get('/groups/{group_id}/invite-candidates', response_model=s.InviteCandidates, responses=errors)
def candidates(group_id: UUID, character_name: Name, principal: Principal):
    return admissions.candidates(principal, group_id, character_name)


@router.post('/groups/{group_id}/invitations', status_code=201, response_model=s.GroupRelation, responses=errors)
def invite(group_id: UUID, data: s.InviteIn, principal: Principal, key: Key):
    return admissions.new_request(principal, group_id, key, data, 'invitation')[1]


@router.post('/groups/{group_id}/applications', status_code=201, response_model=s.GroupRelation, responses=errors)
def apply(group_id: UUID, data: s.ApplyIn, principal: Principal, key: Key):
    return admissions.new_request(principal, group_id, key, data, 'application')[1]


@router.get('/me/group-relations', response_model=s.RelationPage, responses=errors)
def my_relations(principal: Principal, view: View = 'received_invitations', state: State = 'pending',
                 limit: Limit = 20, cursor: Cursor = None):
    return admissions.relation_list(principal, view, state, limit, cursor)


@router.get('/groups/{group_id}/join-relations', response_model=s.RelationPage, responses=errors)
def managed_relations(group_id: UUID, principal: Principal, state: State = 'pending', limit: Limit = 20, cursor: Cursor = None):
    return admissions.relation_list(principal, None, state, limit, cursor, group_id)


@router.get('/group-relations/{relation_id}', response_model=s.GroupRelation, responses=errors)
def relation(relation_id: UUID, principal: Principal):
    return admissions.get_relation(principal, relation_id)


@router.post('/group-relations/{relation_id}/accept', response_model=GroupDetail, responses=errors)
def accept(relation_id: UUID, data: s.AcceptIn, principal: Principal, key: Key):
    return admissions.action(principal, relation_id, 'accept', key, data)[1]


@router.post('/group-relations/{relation_id}/approve', response_model=s.GroupRelation, responses=errors)
def approve(relation_id: UUID, data: s.RelationAction, principal: Principal, key: Key):
    return admissions.action(principal, relation_id, 'approve', key, data)[1]


@router.post('/group-relations/{relation_id}/reject', response_model=s.GroupRelation, responses=errors)
def reject(relation_id: UUID, data: s.RejectIn, principal: Principal, key: Key):
    return admissions.action(principal, relation_id, 'reject', key, data)[1]


@router.post('/group-relations/{relation_id}/cancel', response_model=s.GroupRelation, responses=errors)
def cancel(relation_id: UUID, data: s.RelationAction, principal: Principal, key: Key):
    return admissions.action(principal, relation_id, 'cancel', key, data)[1]


@router.get('/groups/{group_id}/blocked-subjects', response_model=s.BlockPage, responses=errors)
def blocked(group_id: UUID, principal: Principal, limit: Limit = 20, cursor: Cursor = None):
    return admissions.blocked_list(principal, group_id, limit, cursor)


@router.post('/groups/{group_id}/join-subjects/{subject_id}/block', response_model=s.JoinSubject, responses=errors)
def block(group_id: UUID, subject_id: UUID, data: s.BlockIn, principal: Principal, key: Key):
    return admissions.block(principal, group_id, subject_id, True, key, data)[1]


@router.post('/groups/{group_id}/join-subjects/{subject_id}/unblock', response_model=s.JoinSubject, responses=errors)
def unblock(group_id: UUID, subject_id: UUID, data: s.BlockIn, principal: Principal, key: Key):
    return admissions.block(principal, group_id, subject_id, False, key, data)[1]


@router.get('/groups/{group_id}/join-code', response_model=s.JoinCode, responses=errors)
def code(group_id: UUID, principal: Principal):
    return join_codes.get(principal, group_id)


@router.post('/groups/{group_id}/join-code', status_code=201, response_model=s.JoinCode, responses=errors)
def create_code(group_id: UUID, data: s.CreateCodeIn, principal: Principal, key: Key):
    return join_codes.mutate(principal, group_id, 'create', key, data)[1]


@router.post('/groups/{group_id}/join-code/regenerate', response_model=s.JoinCode, responses=errors)
def regenerate_code(group_id: UUID, data: s.CodeCommand, principal: Principal, key: Key):
    return join_codes.mutate(principal, group_id, 'regenerate', key, data)[1]


@router.post('/groups/{group_id}/join-code/revoke', response_model=s.JoinCode, responses=errors)
def revoke_code(group_id: UUID, data: s.CodeCommand, principal: Principal, key: Key):
    return join_codes.mutate(principal, group_id, 'revoke', key, data)[1]


@router.put('/groups/{group_id}/join-code/visibility', response_model=s.JoinCode, responses=errors)
def code_visibility(group_id: UUID, data: s.CodeVisibilityIn, principal: Principal, key: Key):
    return join_codes.mutate(principal, group_id, 'visibility', key, data)[1]


@router.post('/group-join-codes/preview', response_model=s.CodePreview, responses=errors)
def preview(data: s.CodeInput, principal: Principal, request: Request):
    return join_codes.preview(principal, data.code, request.client.host)


@router.post('/group-join-codes/join', response_model=GroupDetail, responses=errors)
def join(data: s.CodeJoinIn, principal: Principal, key: Key, request: Request):
    return join_codes.join(principal, key, data, request.client.host)[1]
