"""Agreed F6-C contract against synthetic restricted PostgreSQL at 0029."""
import json
import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func, text
from app.core.database import session, now
from app.game_accounts.support import GameError
from app.raid_rooms import resume_review as review, resume_review_schemas as schema
from app.raid_rooms import cycle_schemas as inputs, cycle_member_reads as reads
from app.raid_rooms import cycle_resume as resume, cycle_schedule_service as schedules
from app.raid_rooms import cycle_proposals as votes, command_context as opaque, cycle_lifecycle as life
from app.raid_rooms.cycle_outcome_models import CycleResume, CycleOutcome
from app.raid_rooms.source_models import ScheduleProposal, TimeReservation
from app.raid_rooms.cycle_consent_models import CycleConsent
from app.raid_rooms.integrated_models import RecruitmentRound as Round
from tests.test_recruitment_cycle_outcomes import (
    outcomes, planning, consent, lifecycle, candidate, ready, sources, imported, people, worlds,
    scheduled, plan, actor, complete, resume_body, resume_response, propose_resume, vote,
    add_member, fingerprints, commands, cycles, denied, graph,
)
from tests.test_recruitment_cycle_times_http import client
from concurrent.futures import ThreadPoolExecutor


def stopped(a, b=None):
    rid, c, n = scheduled(a)
    if b: add_member(b, rid, c)
    complete(a, rid, c, 'close_weekly')
    return rid, c, n


def request(a, rid, key, groups=None):
    return resume_body(a, rid, key, groups).model_dump(mode='json', exclude_unset=True)


def preview(a, rid, body):
    result = review.preview(actor(a['uid']), rid, inputs.Resume.model_validate(body))
    schema.ResumePreviewContext.model_validate(result)
    assert result['data']['kind'] == 'weekly_resume_preview'
    value = result['data']['resume_review']
    assert value['display']['status'] == 'ready'
    assert value['display']['permission']['allowed'] and value['confirmation']
    assert len(value['confirmation']['context_token'].encode()) <= 4096
    return value


def create(a, rid, key, groups=None):
    body = request(a, rid, key, groups)
    value = preview(a, rid, body)
    data = inputs.Resume.model_validate(body | dict(resume_context_token=value['confirmation']['context_token']))
    command = uuid.uuid4()
    ack = resume.create(actor(a['uid']), rid, command, data)
    pid = uuid.UUID(next(v['id'] for v in ack[1]['data']['revisions'] if v['resource'] == 'proposal'))
    return pid, ack, command, data, value


def proposal(a, rid, key, pid):
    result = reads.plan(actor(a['uid']), rid, key, True)
    schema.ResumePlanContext.model_validate(result)
    return next(v for v in result['data']['proposals'] if v['proposal_id'] == str(pid))


def response(a, rid, key, pid, answer='accept'):
    p = proposal(a, rid, key, pid)
    body = resume_response(a, rid, key, pid, answer).model_dump(mode='json', exclude_unset=True)
    return inputs.Respond.model_validate(body | dict(resume_context_token=p['resume_review']['confirmation']['context_token']))


def test_preview_is_readonly_protected_single_member_apply_and_original_ack(outcomes):
    engine, a, b = outcomes
    rid, c, n = stopped(a)
    body = request(a, rid, c)
    before = fingerprints(engine)
    value = preview(a, rid, body)
    assert fingerprints(engine) == before
    shown = value['display']
    assert shown['proposal_id'] is shown['proposal_revision'] is shown['proposal_plan_revision'] is None
    assert shown['target_cycle_key'] == c and shown['target_generation'] == 1
    assert shown['effect']['creator_accept_on_submit'] is False
    assert shown['groups'][0]['alternatives'][0]['session_id'] is None
    assert preview(a, rid, body)['display']['display_revision'] == shown['display_revision']
    pid, ack, command, data, _ = create(a, rid, c)
    assert ack[1]['data']['outcome'] == 'recorded'
    p = proposal(a, rid, c, pid)
    assert p['accepted_count'] == 0
    assert p['resume_review']['display']['basis_revision'] == shown['basis_revision']
    result = schedules.respond(actor(a['uid']), pid, uuid.uuid4(), response(a, rid, c, pid))
    assert result[1]['data']['outcome'] == 'applied'
    after = proposal(a, rid, c, pid)['resume_review']
    assert after['display']['status'] == 'ready' and after['confirmation'] is None
    assert after['display']['effect']['new_assignment_count'] == 2
    before = fingerprints(engine)
    assert resume.create(actor(a['uid']), rid, command, data) == ack
    assert fingerprints(engine) == before


def test_two_member_proposal_requires_token_and_acceptors_only_consent(outcomes):
    engine, a, b = outcomes
    rid, c, n = stopped(a, b)
    pid, ack, _, _, shown = create(a, rid, c)
    assert shown['display']['effect']['creator_accept_on_submit'] is True
    assert proposal(b, rid, c, pid)['accepted_count'] == 1
    before = fingerprints(engine)
    denied('CONTEXT_INVALID', schedules.respond, actor(b['uid']), pid, uuid.uuid4(), resume_response(b, rid, c, pid))
    assert fingerprints(engine) == before
    command = uuid.uuid4(); data = response(b, rid, c, pid)
    result = schedules.respond(actor(b['uid']), pid, command, data)
    assert result[1]['data']['outcome'] == 'applied'
    before = fingerprints(engine)
    assert schedules.respond(actor(b['uid']), pid, command, data) == result
    assert fingerprints(engine) == before
    assert proposal(a, rid, c, pid)['resume_review']['display']['effect']['accepted_count'] == 2
    with session() as db, db.begin():
        assert db.get(CycleResume, pid).content['review_version'] == 1
        assert db.scalar(select(func.count()).select_from(CycleConsent).where(
            CycleConsent.evidence['authorization']['kind'].astext == 'weekly_resume')) == 2


def test_http_preview_key_modes_flags_legacy_shapes_and_strict_new_field(outcomes):
    engine, a, b = outcomes
    rid, c, n = stopped(a)
    body = request(a, rid, c)
    path = f'/v2/raid-rooms/{rid}/weekly-resume-proposals'
    before = fingerprints(engine)
    with client(a) as http:
        result = http.post(path, params={'preview_only': 'true'}, json=body)
        assert result.status_code == 200, result.json().get('error')
        assert result.headers['cache-control'] == 'no-store'
        schema.ResumePreviewContext.model_validate(result.json())
        assert fingerprints(engine) == before
        assert http.post(path, json=body).status_code == 400
        for bad in ('', 'null', 'TRUE', '1', 'yes'):
            assert http.post(path, params={'preview_only': bad}, json=body).status_code == 400
        assert http.post(path, params=[('preview_only','true'),('preview_only','false')], json=body).status_code == 400
        assert http.post(path, params={'preview_only':'true'}, json=body | dict(resume_context_token=None)).status_code == 400
        assert http.post(path, params={'preview_only':'true'}, json=body | dict(resume_context_token='invalid')).status_code == 400
        token = result.json()['data']['resume_review']['confirmation']['context_token']
        headers = {'Idempotency-Key': str(uuid.uuid4())}
        result = http.post(path, json=body | dict(resume_context_token=token), headers=headers)
        assert result.status_code == 200, result.json().get('error')
        assert result.json()['data']['outcome'] == 'recorded'
        url = f'/v2/me/raid-rooms/{rid}/plan'
        for query in ({'target_cycle_key':c}, {'target_cycle_key':c,'include_resume_display':'false'}):
            result = http.get(url, params=query)
            assert result.status_code == 200
            assert all('resume_review' not in p for p in result.json()['data']['proposals'])
        result = http.get(url, params={'target_cycle_key':c,'include_resume_display':'true'})
        assert result.status_code == 200, result.json().get('error')
        assert result.json()['data']['proposals'][0]['resume_review']
        for bad in ('', 'null', '1', 'TRUE'):
            assert http.get(url, params={'target_cycle_key':c,'include_resume_display':bad}).status_code == 400
        assert http.get(url, params=[('target_cycle_key',c),('include_resume_display','true'),('include_resume_display','false')]).status_code == 400
        pid = uuid.UUID(result.json()['data']['proposals'][0]['proposal_id'])
        reply = response(a, rid, c, pid).model_dump(mode='json', exclude_unset=True)
        result = http.post(f'/v2/raid-schedule-proposals/{pid}/responses', json=reply | dict(resume_context_token=None),
            headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code == 400
        result = http.post(f'/v2/raid-schedule-proposals/{pid}/responses', json=reply,
            headers={'Idempotency-Key':str(uuid.uuid4())})
        assert result.status_code == 200, result.json().get('error')
        assert result.json()['data']['outcome'] == 'applied'


@pytest.mark.parametrize('groups', [None, []])
def test_retained_and_explicit_empty_are_distinct_and_bound(outcomes, groups):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    body = request(a, rid, c, groups)
    value = preview(a, rid, body)
    assert value['display']['origin'] == ('retained' if groups is None else 'explicit')
    assert bool(value['display']['groups']) == (groups is None)
    changed = body | dict(schedule_groups=[] if groups is None else None,
        resume_context_token=value['confirmation']['context_token'])
    before = fingerprints(engine)
    denied('TARGET_CONTEXT_STALE', resume.create, actor(a['uid']), rid, uuid.uuid4(), inputs.Resume.model_validate(changed))
    assert fingerprints(engine) == before
    pid, _, _, _, _ = create(a, rid, c, groups)
    schedules.respond(actor(a['uid']), pid, uuid.uuid4(), response(a, rid, c, pid))
    assert len(plan(a, rid, c)['data']['sessions']) == (1 if groups is None else 0)


def explicit_groups(a, rid, key, mode, occurrence, count, scope):
    items = [v['item_id'] for v in plan(a, rid, key)['data']['game_items'] if v['round_state'] == 'stopped_incomplete']
    with session() as db, db.begin():
        start = graph.graph.time.ceil_tick(now(db) + timedelta(hours=2)).astimezone(commands.raids.KST)
    return [dict(client_group_key='resume-explicit', existing_group_id=None, expected_group_revision=None,
        planning_mode=mode, occurrence_mode=occurrence, day_scope=scope, required=True,
        auto_confirm_additional_members=1 if mode == 'coordinated' else None,
        alternatives=[dict(client_alternative_key=f'alt-{i}', existing_session_id=None, expected_session_revision=None,
            weekday=start.isoweekday(), starts_local=start.strftime('%H:%M') if mode == 'manual' else None,
            leader_latest_start_local='23:55' if mode == 'coordinated' else None, item_ids=items) for i in range(count)])]


@pytest.mark.parametrize('mode,occurrence,count,scope,materialization', [
    ('manual','each',2,'selected_weekdays','on_apply'),
    ('manual','one_of',2,'selected_weekdays','after_group_selection'),
    ('coordinated','one_of',1,'selected_weekdays','after_coordination'),
    ('coordinated','one_of',0,'any_current_cycle','after_coordination'),
    ('unscheduled','one_of',1,'selected_weekdays','not_scheduled'),
])
def test_explicit_modes_projection_and_apply(outcomes, mode, occurrence, count, scope, materialization):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    groups = explicit_groups(a, rid, c, mode, occurrence, count, scope)
    before = fingerprints(engine)
    value = preview(a, rid, request(a, rid, c, groups))
    for alt in value['display']['groups'][0]['alternatives']:
        assert alt['materialization'] == materialization and alt['session_id'] is None
        assert alt['item_ids'] == groups[0]['alternatives'][0]['item_ids']
        assert alt['time_state'] == ('bounded' if mode == 'manual' else 'undetermined')
    assert fingerprints(engine) == before
    pid, _, _, _, _ = create(a, rid, c, groups)
    assert schedules.respond(actor(a['uid']), pid, uuid.uuid4(), response(a, rid, c, pid))[1]['data']['outcome'] == 'applied'
    assert len(plan(a, rid, c)['data']['sessions']) == (count if materialization == 'on_apply' else 0)


def test_legacy_unverifiable_no_fabricated_duration_and_old_commands_work(outcomes):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    pid = propose_resume(a, rid, c, None)
    value = proposal(a, rid, c, pid)['resume_review']
    assert value['display']['status'] == 'legacy_unverifiable' and value['confirmation'] is None
    assert value['display']['basis_revision'] is value['display']['settings_revision'] is None
    assert all(i['duration_minutes'] is None for i in value['display']['items'])
    assert all(v['time_state'] == 'start_only' and v['ends_at'] is None for g in value['display']['groups'] for v in g['alternatives'])
    original = resume_response(a, rid, c, pid)
    assert 'resume_context_token' not in review.command_body(original)
    before = fingerprints(engine)
    bad = inputs.Respond.model_validate(original.model_dump(mode='json', exclude_unset=True) | dict(resume_context_token='invalid'))
    denied('CONTEXT_INVALID', schedules.respond, actor(a['uid']), pid, uuid.uuid4(), bad)
    assert fingerprints(engine) == before
    assert schedules.respond(actor(a['uid']), pid, uuid.uuid4(), original)[1]['data']['outcome'] == 'applied'


@pytest.mark.parametrize('change', ['settings', 'round', 'assignment', 'group'])
def test_fixed_basis_change_stales_proposal_and_never_writes(outcomes, change):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    pid, _, _, _, _ = create(a, rid, c)
    data = response(a, rid, c, pid)
    with session() as db, db.begin():
        binding = db.get(CycleResume, pid); row = db.get(commands.RoomCycle, binding.cycle_id)
        if change == 'settings':
            row.settings_revision += 1
        elif change == 'round': db.get(Round, uuid.UUID(binding.content['rounds'][0]['id'])).revision += 1
        elif change == 'assignment': db.get(life.Assignment, uuid.UUID(binding.content['assignments'][0]['id'])).revision += 1
        else: graph.groups(db, row)[0].revision += 1
    before = fingerprints(engine)
    value = proposal(a, rid, c, pid)['resume_review']
    assert value['display']['status'] == 'stale' and value['confirmation'] is None
    denied('PROPOSAL_CONTEXT_CHANGED', schedules.respond, actor(a['uid']), pid, uuid.uuid4(), data)
    assert fingerprints(engine) == before


def test_actor_flow_tamper_and_body_order_are_bound(outcomes):
    engine, a, b = outcomes; rid, c, n = stopped(a, b)
    body = request(a, rid, c); value = preview(a, rid, body)
    token = value['confirmation']['context_token']
    data = inputs.Resume.model_validate(body | dict(resume_context_token=token))
    before = fingerprints(engine)
    denied('CONTEXT_INVALID', resume.create, actor(b['uid']), rid, uuid.uuid4(), data)
    denied('CONTEXT_INVALID', resume.create, actor(a['uid']), rid, uuid.uuid4(), data.model_copy(update={'resume_context_token':token+'x'}))
    assert fingerprints(engine) == before
    groups = explicit_groups(a, rid, c, 'manual', 'each', 1, 'selected_weekdays')
    body = request(a, rid, c, groups); token = preview(a, rid, body)['confirmation']['context_token']
    changed = json.loads(json.dumps(body)); changed['schedule_groups'][0]['alternatives'][0]['item_ids'].reverse()
    denied('TARGET_CONTEXT_STALE', resume.create, actor(a['uid']), rid, uuid.uuid4(), inputs.Resume.model_validate(changed | dict(resume_context_token=token)))
    pid, _, _, _, _ = create(a, rid, c)
    bad = response(b, rid, c, pid).model_copy(update={'resume_context_token':token})
    denied('CONTEXT_INVALID', schedules.respond, actor(b['uid']), pid, uuid.uuid4(), bad)


@pytest.mark.parametrize('stage', ['create', 'respond', 'final'])
def test_expiry_and_final_expiry_roll_back(outcomes, monkeypatch, stage):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    body = request(a, rid, c); token = preview(a, rid, body)['confirmation']['context_token']
    if stage == 'respond':
        pid, _, _, _, _ = create(a, rid, c); data = response(a, rid, c, pid)
    else: data = inputs.Resume.model_validate(body | dict(resume_context_token=token))
    real = cycles.now; calls = []
    def clock(db):
        calls.append(1)
        return real(db) + (timedelta(seconds=121) if stage != 'final' or len(calls) > 1 else timedelta())
    monkeypatch.setattr(cycles, 'now', clock)
    before = fingerprints(engine)
    if stage == 'respond': denied('COMMAND_CONTEXT_EXPIRED', schedules.respond, actor(a['uid']), pid, uuid.uuid4(), data)
    else: denied('COMMAND_CONTEXT_EXPIRED', resume.create, actor(a['uid']), rid, uuid.uuid4(), data)
    assert fingerprints(engine) == before


def test_rejector_reconnects_without_new_time_consent_and_other_cycle_kept(outcomes, people):
    engine, a, b = outcomes; rid, c, n = scheduled(a)
    third = people('resume-review-third')
    add_member(b, rid, c); add_member(third, rid, c)
    n_before = plan(a, rid, n)
    complete(a, rid, c, 'close_weekly')
    pid, _, _, _, _ = create(a, rid, c)
    assert schedules.respond(actor(third['uid']), pid, uuid.uuid4(), response(third, rid, c, pid, 'reject'))[1]['data']['outcome'] == 'recorded'
    assert schedules.respond(actor(b['uid']), pid, uuid.uuid4(), response(b, rid, c, pid))[1]['data']['outcome'] == 'applied'
    assert plan(third, rid, c)['data']['my_participations'][0]['confirmation_state'] == 'confirmation_pending'
    after = plan(a, rid, n)
    assert after['scope']['target_revision'] == n_before['scope']['target_revision']
    with session() as db, db.begin():
        assert not db.scalar(select(TimeReservation.id).where(TimeReservation.user_id == third['uid'], TimeReservation.released_at.is_(None)))


def test_concurrent_protected_submit_has_one_original_receipt(outcomes):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    body = request(a, rid, c); token = preview(a, rid, body)['confirmation']['context_token']
    data = inputs.Resume.model_validate(body | dict(resume_context_token=token)); key = uuid.uuid4()
    def run(_):
        try: return resume.create(actor(a['uid']), rid, key, data)
        except GameError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, range(2)))
    ack = next(r for r in results if isinstance(r, tuple))
    assert all(r == ack or r == 'REQUEST_IN_PROGRESS' for r in results)
    assert resume.create(actor(a['uid']), rid, key, data) == ack
    with session() as db, db.begin(): assert db.scalar(select(func.count()).select_from(CycleResume)) == 1


def test_eligible_reduction_changes_confirmation_and_quorum_remains_server_owned(outcomes, people):
    engine, a, b = outcomes; rid, c, n = scheduled(a)
    third = people('resume-reduced-third')
    add_member(b, rid, c); add_member(third, rid, c); complete(a, rid, c, 'close_weekly')
    pid, _, _, _, _ = create(a, rid, c)
    old = response(b, rid, c, pid)
    with session() as db, db.begin():
        row = db.get(commands.RoomCycle, db.get(CycleResume, pid).cycle_id)
        cm = life.actual_member(db, row, third['uid']); cm.state = 'removed'; cm.revision += 1
    before = fingerprints(engine)
    denied('TARGET_CONTEXT_STALE', schedules.respond, actor(b['uid']), pid, uuid.uuid4(), old)
    assert fingerprints(engine) == before
    p = proposal(b, rid, c, pid)
    assert p['resume_review']['display']['effect']['eligible_count'] == 2
    assert p['resume_review']['display']['effect']['required_votes'] == 2
    assert schedules.respond(actor(b['uid']), pid, uuid.uuid4(), response(b, rid, c, pid))[1]['data']['outcome'] == 'applied'


def test_protected_preview_response_caps_and_full_request_limit(outcomes, monkeypatch):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    body = request(a, rid, c); path = f'/v2/raid-rooms/{rid}/weekly-resume-proposals'
    with client(a) as http:
        result = http.post(path, params={'preview_only':'true'}, json=body)
        assert result.status_code == 200
        monkeypatch.setattr(review, 'MAX_RESPONSE_BYTES', len(result.content))
        assert http.post(path, params={'preview_only':'true'}, json=body).status_code == 200
        monkeypatch.setattr(review, 'MAX_RESPONSE_BYTES', len(result.content) - 1)
        before = fingerprints(engine)
        result = http.post(path, params={'preview_only':'true'}, json=body)
        assert result.status_code == 413 and result.json()['error']['code'] == 'RESPONSE_TOO_LARGE'
        assert fingerprints(engine) == before
        assert http.post(path, params={'preview_only':'true'}, content=b' ' * 32769).status_code == 413
        assert http.post(path, json=body, headers={'Idempotency-Key':'invalid'}).status_code == 400


def test_real_authentication_preview_and_plan_remain_scoped(outcomes):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.errors import register
    from app.main import no_store
    from app.raid_rooms.cycle_router import router
    from app.auth.models import Session
    engine, a, b = outcomes; rid, c, n = stopped(a)
    app = FastAPI(); register(app); app.include_router(router); app.middleware('http')(no_store)
    path = f'/v2/raid-rooms/{rid}/weekly-resume-proposals'; body = request(a, rid, c)
    before = fingerprints(engine)
    with TestClient(app) as http:
        assert http.post(path, params={'preview_only':'true'}, json=body).status_code == 401
        assert http.post(path, params={'preview_only':'true'}, json=body, headers={'Authorization':'Bearer invalid'}).status_code == 401
        result = http.post(path, params={'preview_only':'true'}, json=body, headers=a['headers'])
        assert result.status_code == 200, result.json().get('error')
        assert result.headers['cache-control'] == 'no-store'
        assert http.post(path, params={'preview_only':'true'}, json=body, headers=b['headers']).status_code == 403
        assert http.get(f'/v2/me/raid-rooms/{rid}/plan', params=dict(target_cycle_key=c,include_resume_display='true'), headers=b['headers']).status_code == 403
        assert fingerprints(engine) == before
        with session() as db, db.begin(): db.scalar(select(Session).where(Session.user_id == a['uid'])).revoked_at = now(db)
        assert http.post(path, params={'preview_only':'true'}, json=body, headers=a['headers']).status_code == 401


def test_whole_opt_in_plan_one_mib_limit_and_legacy_payload_stays_unchanged(outcomes):
    from sqlalchemy import insert
    from app.raid_rooms.source_models import ScheduleAlternative
    engine, a, b = outcomes; rid, c, n = stopped(a)
    with session() as db, db.begin():
        row = db.scalar(select(commands.RoomCycle).where(commands.RoomCycle.room_id == rid,
            commands.RoomCycle.cycle_key == date.fromisoformat(c)))
        g = graph.groups(db, row)[0]; alt = graph.alternatives(db, g)[0]
        db.execute(insert(ScheduleAlternative), [dict(id=uuid.uuid4(), room_id=rid, group_id=g.id,
            client_key=f'large-review-{i}', weekday=alt.weekday, start_minute=alt.start_minute,
            latest_start_minute=None, item_order=alt.item_order, session_id=None) for i in range(5000)])
    pid = propose_resume(a, rid, c, None)
    before = fingerprints(engine)
    with client(a) as http:
        path = f'/v2/me/raid-rooms/{rid}/plan'
        result = http.get(path, params=dict(target_cycle_key=c,include_resume_display='true'))
        assert result.status_code == 413 and result.json()['error']['code'] == 'RESPONSE_TOO_LARGE'
        result = http.get(path, params=dict(target_cycle_key=c))
        assert result.status_code == 200
        assert 'resume_review' not in next(p for p in result.json()['data']['proposals'] if p['proposal_id'] == str(pid))
    assert fingerprints(engine) == before


def test_completed_creator_is_not_falsely_shown_as_implicit_acceptor(outcomes, people):
    engine, a, b = outcomes; rid, c, n = scheduled(a)
    third = people('resume-creator-completed')
    add_member(b, rid, c); add_member(third, rid, c)
    complete(a, rid, c, 'personal_completion', 0)
    complete(a, rid, c, 'personal_completion', 1)
    complete(b, rid, c, 'close_weekly')
    pid, _, _, _, value = create(a, rid, c)
    assert value['display']['effect']['eligible_count'] == 2
    assert value['display']['effect']['creator_accept_on_submit'] is False
    assert proposal(b, rid, c, pid)['accepted_count'] == 0


@pytest.mark.parametrize('boundary', ['next', 'before_play'])
def test_preview_current_cycle_and_wednesday_ten_boundary(outcomes, monkeypatch, boundary):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    body = request(a, rid, n if boundary == 'next' else c)
    if boundary == 'before_play':
        stamp = datetime.combine(date.fromisoformat(c), datetime.min.time().replace(hour=9, minute=55),
            commands.raids.KST).astimezone(timezone.utc)
        monkeypatch.setattr(commands.base, 'now', lambda db: stamp)
    before = fingerprints(engine)
    denied('TARGET_CYCLE_NOT_CURRENT' if boundary == 'next' else 'PLAY_NOT_STARTED',
        review.preview, actor(a['uid']), rid, inputs.Resume.model_validate(body))
    assert fingerprints(engine) == before


def test_wednesday_early_preview_uses_end_of_actual_cycle(outcomes):
    _, a, b = outcomes; rid, c, n = stopped(a)
    groups = explicit_groups(a, rid, c, 'manual', 'one_of', 1, 'selected_weekdays')
    groups[0]['alternatives'][0].update(weekday=3, starts_local='00:05')
    shown = preview(a, rid, request(a, rid, c, groups))['display']
    alt = shown['groups'][0]['alternatives'][0]
    start = datetime.fromisoformat(alt['starts_at'].replace('Z','+00:00')).astimezone(commands.raids.KST)
    assert start.date() == date.fromisoformat(c) + timedelta(days=7)
    assert start.hour == 0 and start.minute == 5 and shown['target_cycle_key'] == c


def test_legacy_manual_without_clock_is_readable_but_unconfirmable(outcomes):
    engine, a, b = outcomes; rid, c, n = stopped(a)
    groups = explicit_groups(a, rid, c, 'manual', 'one_of', 1, 'selected_weekdays')
    groups[0]['alternatives'][0]['starts_local'] = None
    # The historical create DTO allowed this combination before apply checked it.
    pid = propose_resume(a, rid, c, groups)
    before = fingerprints(engine)
    value = proposal(a, rid, c, pid)['resume_review']
    assert value['display']['status'] == 'legacy_unverifiable' and value['confirmation'] is None
    alt = value['display']['groups'][0]['alternatives'][0]
    assert alt['starts_at'] is alt['ends_at'] is None and alt['time_state'] == 'undetermined'
    assert fingerprints(engine) == before
