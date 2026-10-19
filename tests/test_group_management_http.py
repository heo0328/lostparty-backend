"""Published G3 paths, strict wire contract and response-loss recovery over HTTP."""
import uuid
import pytest
from sqlalchemy import event
from app.core.database import engine
from tests.test_group_admissions import worlds, group, apply, action, new_code, join, post
from tests.test_group_management import setup, command
from tests.test_representative import error


def path(gid, operation='management'):
    return '/v1/groups/'+gid+'/'+operation


def test_http_transfer_leave_and_historical_ack_after_rejoin(client, worlds):
    a, b, gid = setup(client, worlds)
    code = new_code(client, a, gid).json()['code']
    key = uuid.uuid4()
    data = command(a, gid, b).model_dump(mode='json')
    result = post(client, a, path(gid, 'leadership-transfer'), data, key)
    assert result.status_code == 200, result.text
    assert result.headers['Cache-Control'] == 'no-store'
    assert post(client, a, path(gid, 'leadership-transfer'), data, key).json() == result.json()
    assert set(result.json()) == {'group_id', 'previous_leader_membership_id', 'leader_membership_id',
        'group_revision', 'members_revision', 'previous_leader_membership_revision',
        'leader_membership_revision', 'transferred_at'}
    leave_data = command(a, gid).model_dump(mode='json')
    leave_key = uuid.uuid4()
    left = post(client, a, path(gid, 'leave'), leave_data, leave_key)
    assert left.status_code == 200, left.text
    assert set(left.json()) == {'group_id', 'membership_id', 'membership_revision', 'ended_at'}
    error(client.get(path(gid), headers=a['headers']), 403, 'GROUP_MEMBERSHIP_REQUIRED')
    assert post(client, a, path(gid, 'leave'), leave_data, leave_key).json() == left.json()
    assert post(client, a, path(gid, 'leadership-transfer'), data, key).json() == result.json()
    rejoined = join(client, a, code)
    assert rejoined.status_code == 200, rejoined.text
    assert rejoined.json()['my_membership']['membership_id'] != left.json()['membership_id']
    assert post(client, a, path(gid, 'leave'), leave_data, leave_key).json() == left.json()
    assert client.get(path(gid), headers=a['headers']).json()['my_membership']['role'] == 'member'


@pytest.mark.parametrize('operation,method', [('management','get'),('leadership-transfer','post'),('leave','post')])
def test_auth_no_store_and_bearer(client, operation, method):
    out = getattr(client, method)(path(str(uuid.uuid4()), operation))
    error(out, 401, 'ACCESS_INVALID')
    assert out.headers['Cache-Control'] == 'no-store'
    assert out.headers['WWW-Authenticate'] == 'Bearer'


def test_management_permissions_and_get_performs_no_writes(client, worlds):
    a, b, gid = setup(client, worlds)
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split()[0].upper())
    event.listen(engine(), 'before_cursor_execute', record)
    try:
        leader = client.get(path(gid), headers=a['headers'])
        member = client.get(path(gid), headers=b['headers'])
    finally:
        event.remove(engine(), 'before_cursor_execute', record)
    assert leader.status_code == member.status_code == 200
    assert statements and set(statements) == {'SELECT'}
    assert leader.json()['permissions']['leave'] == dict(allowed=False, reason='GROUP_LEADER_TRANSFER_REQUIRED')
    assert leader.json()['permissions']['disband'] == dict(allowed=False, reason='GROUP_RECRUITMENT_STATE_UNAVAILABLE')
    assert member.json()['permissions']['leave'] == dict(allowed=True, reason=None)
    assert set(member.json()) == {'group_id', 'group_revision', 'members_revision', 'my_membership', 'permissions'}
    assert str(b['uid']) not in member.text


@pytest.mark.parametrize('operation', ['leave', 'leadership-transfer'])
@pytest.mark.parametrize('mutation', ['missing','null','bool','string','float','extra','membership'])
def test_strict_commands(client, worlds, operation, mutation):
    a, b, gid = setup(client, worlds)
    w = b if operation == 'leave' else a
    data = command(w, gid, b if operation == 'leadership-transfer' else None).model_dump(mode='json')
    if mutation == 'missing':
        del data['expected_group_revision']
    elif mutation == 'extra':
        data['actor_id'] = str(a['uid'])
    elif mutation == 'membership':
        data['expected_membership_id'] = 'not-a-uuid'
    else:
        data['expected_group_revision'] = {'null':None, 'bool':True, 'string':'1', 'float':1.5}[mutation]
    error(post(client, w, path(gid, operation), data), 400, 'INVALID_REQUEST')


def test_strict_get_query_body_and_command_headers(client, worlds):
    a, b, gid = setup(client, worlds)
    error(client.get(path(gid)+'?limit=1', headers=a['headers']), 400, 'INVALID_REQUEST')
    error(client.get(path(gid)+'?x=1&x=2', headers=a['headers']), 400, 'INVALID_REQUEST')
    error(client.request('GET', path(gid), headers=a['headers'], json={}), 400, 'INVALID_REQUEST')
    data = command(b, gid).model_dump(mode='json')
    error(client.post(path(gid, 'leave'), headers=b['headers'], json=data), 400, 'INVALID_REQUEST')
    error(post(client, b, path(gid, 'leave'), data, 'not-a-key'), 400, 'INVALID_REQUEST')
    error(post(client, b, path(gid, 'leave')+'?x=1', data), 400, 'INVALID_REQUEST')


def test_role_and_stale_errors_use_existing_envelope(client, worlds):
    a, b, gid = setup(client, worlds)
    error(post(client, a, path(gid, 'leave'), command(a, gid).model_dump(mode='json')),
          409, 'GROUP_LEADER_TRANSFER_REQUIRED')
    data = command(a, gid, b).model_dump(mode='json')
    data['expected_group_revision'] += 1
    error(post(client, a, path(gid, 'leadership-transfer'), data), 409, 'REVISION_CONFLICT')
    data = command(b, gid, a).model_dump(mode='json')
    error(post(client, b, path(gid, 'leadership-transfer'), data), 403, 'GROUP_LEADER_REQUIRED')


def test_g3_openapi_matches_published_contract():
    import json
    from pathlib import Path
    from app.main import app
    previous = json.loads(Path('openapi/openapi.yaml').read_text())
    actual = app.openapi()
    assert actual == previous
    for operation in ('management', 'leadership-transfer', 'leave'):
        endpoint = actual['paths']['/v1/groups/{group_id}/'+operation]
        assert set(endpoint) == ({'get'} if operation == 'management' else {'post'})
