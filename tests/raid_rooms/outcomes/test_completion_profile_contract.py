"""Contract-driven HTTP pairs, with current permission and replay semantics intact."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import uuid

import pytest
from fastapi.routing import APIRoute
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import inspect, select
from starlette.requests import Request

from app.core.database import session
from app.main import app as legacy_app, create_two_cycle_app
from app.raid_rooms.contracts.roster_openapi import PARTICIPATION_OPERATIONS
from app.raid_rooms.participation import roster_participation as rp
from app.raid_rooms.participation import cycle_character
from app.raid_rooms.reads import cycle_member_reads
from app.raid_rooms.models.cycle_models import RoomCycle
from app.raid_rooms.models.integrated_models import RecruitmentRoom
from app.raid_rooms.models.beta_models import BetaSchedule
from app.raid_rooms.schedules import beta_schedule
from app.raid_rooms.schemas import completion_correction_schemas
from tests.raid_rooms.participation.test_roster_public_contract import (
    presence_db, policy_db, group_beta, beta, current, candidate, ready, sources,
    imported, people, worlds, bundle, Q, P, change, complete, actor,
)
from tests.raid_rooms.outcomes.test_recruitment_cycle_outcomes import outcome_body, manual_body
from tests.raid_rooms.schedules.test_recruitment_cycle_times_http import client
from tests.raid_rooms.schedules.test_recruitment_cycle_times import confirmation
from tests.raid_rooms.schedules.test_recruitment_cycle_planning import scoped, make_proposal, response
from tests.raid_rooms.common.test_raid_room_migrations import table_digests

CONTRACT = json.loads(Path('openapi/two-cycle.openapi.yaml').read_text())
CONTEXT = '/v2/raid-rooms/{room_id}/command-context'
COMPLETIONS = [('complete_item', 'completion'), ('personal_completion', 'personal-completion')]


def query(method, template, **extra):
    """Mirror a client opting in only when its pinned contract declares support."""
    names = {p['name'] for p in CONTRACT['paths'][template][method]['parameters'] if p['in'] == 'query'}
    assert set(extra) <= names
    return {k: v for k, v in (Q | P).items() if k in names} | extra


def business(engine):
    tables = {t for t in inspect(engine).get_table_names() if t.startswith(('recruitment_', 'raid_'))}
    return table_digests(engine, tables)


def command(http, method, template, path, body, *, parameters=None, key=None):
    return http.request(method, path, params=query(method, template) if parameters is None else parameters,
                        json=body, headers={'Idempotency-Key': key or str(uuid.uuid4())})


def checked(result, template, method, status):
    assert result.status_code == status, result.json().get('error')
    assert result.headers['cache-control'] == 'no-store'
    response = CONTRACT['paths'][template][method]['responses'][str(status)]
    if '$ref' in response:
        response = CONTRACT['components']['responses'][response['$ref'].rsplit('/', 1)[1]]
    schema = response['content']['application/json']['schema']
    Draft202012Validator(dict(schema, components=CONTRACT['components']),
                        format_checker=FormatChecker()).validate(result.json())
    return result.json()


def completion_context(http, w, rid, cycle, kind, *, parameters=None, round_id=None):
    if round_id is None:
        view = cycle_member_reads.plan(actor(w['uid']), rid, cycle)
        round_id = view['data']['game_items'][0]['round_id']
    options = query('get', CONTEXT, target_cycle_key=cycle, command=kind, round_id=str(round_id))
    if parameters is not None:
        options = parameters | dict(target_cycle_key=cycle, command=kind, round_id=str(round_id))
    value = checked(http.get(CONTEXT.format(room_id=rid), params=options), CONTEXT, 'get', 200)
    assert value['data']['permission']['allowed']
    return value


def test_profile_declarations_match_every_runtime_route():
    application = create_two_cycle_app()
    actual = application.openapi()
    supported = set()
    for route in application.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods & {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
            if route.path not in actual['paths'] or method.lower() not in actual['paths'][route.path]:
                continue
            request = Request({'type': 'http', 'method': method, 'scheme': 'http', 'path': route.path,
                               'query_string': b'', 'headers': [], 'server': ('test', 80)})
            runtime = hasattr(route, 'allowed_query') and 'participation_profile' in route.allowed_query(request)
            parameters = [p for p in actual['paths'][route.path][method.lower()].get('parameters', [])
                          if p.get('name') == 'participation_profile']
            assert len(parameters) == int(runtime), (method, route.path)
            if runtime:
                supported.add((method.lower(), route.path))
                assert parameters[0]['in'] == 'query' and parameters[0]['required'] is False
                assert parameters[0]['schema'] == {'type': 'string', 'enum': [rp.PROFILE]}
    assert supported == PARTICIPATION_OPERATIONS
    assert len(supported) == 69
    for method in ('get', 'put'):
        assert not any(p.get('name') == 'participation_profile' for p in
                       actual['paths']['/v2/me/application-message-presets'][method].get('parameters', []))


def test_both_complete_contract_objects_match_generated_schema():
    assert legacy_app.openapi() == json.loads(Path('openapi/openapi.yaml').read_text())
    assert create_two_cycle_app().openapi() == CONTRACT


@pytest.mark.parametrize('kind,suffix', COMPLETIONS)
def test_pinned_contract_drives_completion_query_and_original_ack(presence_db, kind, suffix):
    engine, a, _ = presence_db
    rid, cycle, next_cycle = bundle(a)
    opposite = deepcopy(cycle_member_reads.plan(actor(a['uid']), rid, next_cycle)['data']['my_assignments'])
    template = '/v2/raid-rounds/{round_id}/' + suffix
    with client(a) as http:
        value = completion_context(http, a, rid, cycle, kind)
        body = outcome_body(value).model_dump(mode='json')
        path = template.format(round_id=value['data']['target_round_id'])
        key = str(uuid.uuid4())
        result = command(http, 'post', template, path, body, key=key)
        original = checked(result, template, 'post', 200)
        after = business(engine)
        assert checked(command(http, 'post', template, path, body, key=key), template, 'post', 200) == original
        assert business(engine) == after
    assert cycle_member_reads.plan(actor(a['uid']), rid, next_cycle)['data']['my_assignments'] == opposite
    own = cycle_member_reads.plan(actor(a['uid']), rid, cycle)['data']['my_assignments']
    assert sum(a['state'] == 'completed' for a in own) == 1
    assert sum(a['state'] == 'active' for a in own) == 1


@pytest.mark.parametrize('kind,suffix', COMPLETIONS)
@pytest.mark.parametrize('get_profile,post_profile', [(False, False), (True, True), (True, False), (False, True)])
def test_explicit_profile_pairs_keep_validation(presence_db, kind, suffix, get_profile, post_profile):
    engine, a, _ = presence_db
    rid, cycle, *_ = bundle(a, continuation=False)
    template = '/v2/raid-rounds/{round_id}/' + suffix
    with client(a) as http:
        value = completion_context(http, a, rid, cycle, kind, parameters=Q | (P if get_profile else {}))
        body = outcome_body(value).model_dump(mode='json')
        before = business(engine)
        result = command(http, 'post', template, template.format(round_id=value['data']['target_round_id']), body,
                         parameters=Q | (P if post_profile else {}))
        if get_profile != post_profile:
            rejected = checked(result, template, 'post', 400)
            assert rejected['error']['code'] == 'CONTEXT_INVALID'
            assert rejected['error']['request_id']
            assert business(engine) == before
        else:
            checked(result, template, 'post', 200)


@pytest.mark.parametrize('invalid', ['', 'unknown-profile'])
def test_bad_profile_is_not_accepted(presence_db, invalid):
    engine, a, _ = presence_db
    rid, cycle, *_ = bundle(a, continuation=False)
    with client(a) as http:
        value = completion_context(http, a, rid, cycle, 'complete_item')
        template = '/v2/raid-rounds/{round_id}/completion'
        before = business(engine)
        rejected = checked(command(http, 'post', template, template.format(round_id=value['data']['target_round_id']),
                                   outcome_body(value).model_dump(mode='json'),
                                   parameters=query('post', template) | {'participation_profile': invalid}), template, 'post', 400)
        assert rejected['error']['code'] == 'INVALID_REQUEST'
        assert business(engine) == before


def test_partial_replacement_requires_profile_and_keeps_completed_history(presence_db):
    engine, a, _ = presence_db
    rid, cycle, next_cycle = bundle(a)
    complete(a, rid, cycle, index=0)
    before_plan = cycle_member_reads.plan(actor(a['uid']), rid, cycle)
    preserved = next(v for v in before_plan['data']['my_assignments'] if v['state'] == 'completed')
    opposite = cycle_member_reads.plan(actor(a['uid']), rid, next_cycle)['data']['my_assignments']
    with rp.using(P):
        cycle_character.execute(actor(a['uid']), rid, uuid.uuid4(), change(a, rid, cycle))
        active = next(v for v in cycle_member_reads.plan(actor(a['uid']), rid, cycle)['data']['my_assignments'] if v['state'] == 'active')
        assert active['character_id'] == a['ids'][1]
    with client(a) as http:
        blocked = http.get(CONTEXT.format(room_id=rid), params=Q | dict(target_cycle_key=cycle, command='personal_completion', round_id=active['round_id']))
        assert blocked.status_code == 409 and blocked.json()['error']['code'] == 'CLIENT_UPGRADE_REQUIRED'
        value = completion_context(http, a, rid, cycle, 'personal_completion', round_id=active['round_id'])
        body = outcome_body(value).model_dump(mode='json')
        template = '/v2/raid-rounds/{round_id}/personal-completion'
        path = template.format(round_id=active['round_id'])
        before = business(engine)
        # Token/profile consistency precedes capability checks on commands.
        rejected = checked(command(http, 'post', template, path, body, parameters=Q), template, 'post', 400)
        assert rejected['error']['code'] == 'CONTEXT_INVALID' and business(engine) == before
        checked(command(http, 'post', template, path, body), template, 'post', 200)
    with rp.using(P):
        plan = cycle_member_reads.plan(actor(a['uid']), rid, cycle)
        assert next(v for v in plan['data']['my_assignments'] if v['assignment_id'] == preserved['assignment_id']) == preserved
    assert cycle_member_reads.plan(actor(a['uid']), rid, next_cycle)['data']['my_assignments'] == opposite


def test_additional_five_schedule_operations_keep_policy_and_cas(presence_db):
    engine, a, _ = presence_db
    rid, cycle, *_ = bundle(a, continuation=False)
    plan = cycle_member_reads.plan(actor(a['uid']), rid, cycle)
    group = plan['data']['schedule_groups'][0]
    gid = group['group_id']
    with client(a) as http:
        template = '/v2/me/raid-schedule-overlaps'
        checked(http.get(template, params=query('get', template, target_cycle_key=cycle)), template, 'get', 200)
        template = '/v2/raid-schedule-groups/{group_id}/candidates'
        checked(http.get(template.format(group_id=gid), params=query('get', template, target_cycle_key=cycle)), template, 'get', 200)
        template = '/v2/raid-schedule-groups/{group_id}/selections'
        body = scoped(a, rid, cycle) | dict(expected_group_revision=group['revision'], alternative_id=None)
        before = business(engine)
        rejected = checked(command(http, 'post', template, template.format(group_id=gid), body), template, 'post', 409)
        assert rejected['error']['code'] == 'SCHEDULE_PROPOSAL_REQUIRED' and business(engine) == before
        # Settle the synthetic beta base deadline before confirming its session.
        with session() as db, db.begin():
            row = db.scalar(select(RoomCycle).where(RoomCycle.room_id == rid))
            base = db.get(BetaSchedule, row.id).base_starts_at
            beta_schedule.reconcile(db, db.get(RecruitmentRoom, rid), row, base - timedelta(minutes=20))
        sid, data = confirmation(a, rid, cycle)
        body = data.model_dump(mode='json')
        template = '/v2/raid-sessions/{session_id}/participation-confirmations'
        path = template.format(session_id=sid)
        before = business(engine)
        rejected = checked(command(http, 'post', template, path, body | {'expected_target_revision': body['expected_target_revision'] + 1}), template, 'post', 409)
        assert rejected['error']['code'] == 'TARGET_CONTEXT_STALE' and business(engine) == before
        key = str(uuid.uuid4())
        original = checked(command(http, 'post', template, path, body, key=key), template, 'post', 200)
        assert checked(command(http, 'post', template, path, body, key=key), template, 'post', 200) == original
        pid, _ = make_proposal(a, rid, cycle)
        body = response(a, rid, cycle, pid).model_dump(mode='json')
        template = '/v2/raid-schedule-proposals/{proposal_id}/responses'
        path = template.format(proposal_id=pid)
        key = str(uuid.uuid4())
        original = checked(command(http, 'post', template, path, body, key=key), template, 'post', 200)
        assert checked(command(http, 'post', template, path, body, key=key), template, 'post', 200) == original


def test_additional_manual_and_correction_http_pair(presence_db):
    engine, a, _ = presence_db
    from app.raids import service as raids
    from app.core.database import now
    with session() as db:
        cycle = raids.cycle(now(db)).cycle_key
    cid, raid = a['ids'][1], 'horizon_cathedral'
    root = f'/v2/me/characters/{cid}/raid-weekly-states/{raid}'
    template_root = '/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}'
    with client(a) as http:
        template = template_root + '/manual-completion'
        checked(command(http, 'put', template, root + '/manual-completion', manual_body(a, raid, cycle).model_dump(mode='json')), template, 'put', 200)
        template = template_root + '/completion-correction-context'
        value = checked(http.get(root + '/completion-correction-context', params=query('get', template, target_cycle_key=cycle)), template, 'get', 200)
        data = value['data']
        body = completion_correction_schemas.CorrectionCommand.model_validate(dict(
            target_cycle_key=cycle, expected_cycle_key=value['current_cycle_key'], expected_weekly_revision=data['weekly_revision'],
            expected_ownership_revision=data['ownership_revision'], expected_lifecycle_revision=data['lifecycle_revision'],
            correction_context_token=data['confirmation']['context_token'])).model_dump(mode='json')
        template = template_root + '/completion-corrections'
        before = business(engine)
        rejected = checked(command(http, 'post', template, root + '/completion-corrections', body, parameters=Q), template, 'post', 400)
        assert rejected['error']['code'] == 'CONTEXT_INVALID' and business(engine) == before
        key = str(uuid.uuid4())
        result = checked(command(http, 'post', template, root + '/completion-corrections', body, key=key), template, 'post', 200)
        assert result['data']['completion_sources'] == [] and result['data']['participation_restored'] is False
        after = business(engine)
        assert checked(command(http, 'post', template, root + '/completion-corrections', body, key=key), template, 'post', 200) == result
        assert business(engine) == after
