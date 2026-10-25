"""Read-only resume review snapshots and versioned command confirmation."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import uuid
from types import SimpleNamespace
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.lifecycle import digest
from app.game_accounts.support import fail, GameError
from app.raid_rooms import cycle_schedule as graph, cycle_planning as planning
from app.raid_rooms import cycle_lifecycle as life, cycle_commands as commands
from app.raid_rooms import command_context as opaque, cycle_outcomes as outcomes
from app.raid_rooms import cycle_wire as wire, resume_review_schemas as schemas
from app.raid_rooms.cycle_outcome_models import CycleOutcome

MAX_RESPONSE_BYTES = 1024 * 1024


def command_body(data):
    """Keep every old field/default, omitting only an absent new extension."""
    value = data.model_dump(mode='json')
    if 'resume_context_token' not in data.model_fields_set:
        value.pop('resume_context_token', None)
    return value


def output(model, value, bounded=True, *, snapshot=None):
    from app.raid_rooms import beta_output
    result = beta_output.render(*snapshot,model,value,exclude_unset=True) if snapshot is not None else model.model_validate(jsonable_encoder(value)).model_dump(mode='json', exclude_unset=True)
    if bounded and len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_RESPONSE_BYTES:
        fail('RESPONSE_TOO_LARGE', 413)
    return result


def group_proof(db, row):
    return jsonable_encoder([[planning.snapshot(g), planning.snapshot(db.get(graph.ScheduleHead, g.id)),
             [planning.snapshot(a) for a in graph.alternatives(db, g)]]
            for g in sorted(graph.groups(db, row), key=lambda g: str(g.id))])


def items(db, row, content, settings=None):
    by_id = {str(i.id): i for i, _ in graph.admission.rounds(db, row)}
    settings = {v['item_id']: v for v in settings['items']} if settings else {}
    return sorted([dict(item_id=r['item_id'], source_round_id=r['id'],
        raid_id=by_id[r['item_id']].raid_id, difficulty_id=r['difficulty_id'], catalog_version=r['catalog_version'],
        duration_minutes=settings.get(r['item_id'], {}).get('duration_minutes'),
        duration_source=settings.get(r['item_id'], {}).get('duration_source')) for r in content['rounds']],
        key=lambda v: v['item_id'])


def capture(db, room, row, cm, content, body, pending):
    basis = dict(origin='retained' if body['schedule_groups'] is None else 'explicit',
        settings_revision=row.settings_revision, settings_snapshot=deepcopy(row.settings_snapshot),
        items=items(db, row, content, row.settings_snapshot), groups=deepcopy(content['schedule_groups']),
        source_groups=group_proof(db, row), leadership=jsonable_encoder(commands.leadership(db, row)),
        superseded_proposals=[[str(p.id), p.revision, p.proposal_plan_revision] for p in pending],
        creator_accept_on_submit=len(content['members']) >= 2 and str(cm.id) in {m['id'] for m in content['members']})
    basis['basis_revision'] = digest([jsonable_encoder(basis), content])
    return jsonable_encoder(basis)


def project_groups(row, basis, *, validate_at=None):
    durations = {str(v['item_id']): v['duration_minutes'] for v in basis['items']}
    groups = []
    for g in basis['groups']:
        ref = digest([str(row.id), row.generation, g['client_group_key']])
        alternatives = []
        for a in g['alternatives']:
            start = graph.local_start(row.cycle_key.isoformat(), a['weekday'], a['starts_local']) if g['planning_mode'] == 'manual' and a['starts_local'] is not None else None
            minutes = [durations.get(str(i)) for i in a['item_ids']]
            total = sum(minutes) if minutes and all(type(v) is int and v > 0 for v in minutes) else None
            end = start + timedelta(minutes=total) if start is not None and total is not None else None
            if validate_at is not None and start is not None:
                if end is None: fail('DURATION_POLICY_UNAVAILABLE')
                graph.graph.time.interval(start, end, row.cycle_key.isoformat(),
                    floor=validate_at + timedelta(minutes=30), current=validate_at)
            mode = ('on_apply' if g['occurrence_mode'] == 'each' or len(g['alternatives']) == 1 else 'after_group_selection') if g['planning_mode'] == 'manual' else 'after_coordination' if g['planning_mode'] == 'coordinated' else 'not_scheduled'
            alternatives.append(dict(alternative_ref=digest([ref, a['client_alternative_key']]),
                weekday=a['weekday'], starts_local=a['starts_local'], leader_latest_start_local=a['leader_latest_start_local'],
                item_ids=a['item_ids'], session_id=None, starts_at=start, ends_at=end,
                time_state='bounded' if end else 'start_only' if start else 'undetermined', materialization=mode))
        groups.append(dict(group_ref=ref, planning_mode=g['planning_mode'], occurrence_mode=g['occurrence_mode'],
            day_scope=g['day_scope'], required=g['required'], auto_confirm_additional_members=g['auto_confirm_additional_members'],
            alternatives=sorted(alternatives, key=lambda a: a['alternative_ref'])))
    return sorted(groups, key=lambda g: g['group_ref'])


def valid_basis(db, row, content, basis, members):
    if (row.settings_revision != basis['settings_revision'] or row.settings_snapshot != basis['settings_snapshot'] or
            jsonable_encoder(commands.leadership(db, row)) != basis['leadership'] or group_proof(db, row) != basis['source_groups']):
        fail('PROPOSAL_CONTEXT_CHANGED')
    actual = {str(r.id): r for _, r in graph.admission.rounds(db, row) if r.state == 'stopped_incomplete'}
    if set(actual) != {r['id'] for r in content['rounds']} or any(actual[r['id']].revision != r['revision'] for r in content['rounds']):
        fail('PROPOSAL_CONTEXT_CHANGED')
    for cm in members:
        saved = {v['id']: v for v in content['assignments'] if v['membership_id'] == str(cm.membership_id)}
        current = [a for a in life.assignments(db, row, cm) if str(a.round_id) in actual and a.state == 'stopped_incomplete']
        if not current or {str(a.id) for a in current} != set(saved) or any(a.revision != saved[str(a.id)]['revision'] for a in current):
            fail('PROPOSAL_CONTEXT_CHANGED')


def effect(db, row, cm, content, basis, members, accepted, required):
    ids = {str(m.membership_id) for m in members}
    own_items = {a['item_id'] for a in content['assignments'] if cm and a['membership_id'] == str(cm.membership_id)}
    immediate = sum(a['materialization'] == 'on_apply' and bool(own_items & set(a['item_ids']))
        for g in project_groups(row, basis) for a in g['alternatives']
        if cm and (g['required'] or str(cm.id) == basis['leadership']['leader_cycle_member_id']))
    return dict(eligible_count=len(members), accepted_count=accepted, required_votes=required,
        new_round_count=len(content['rounds']), new_assignment_count=sum(a['membership_id'] in ids for a in content['assignments']),
        completed_preserved_count=sum(a.state == 'completed' for a in outcomes.assignments(db, row)),
        superseded_proposal_count=len(basis['superseded_proposals']),
        creator_accept_on_submit=basis['creator_accept_on_submit'], my_immediate_session_count_on_accept=immediate)


def display(uid, row, content, basis, groups, impact, reason, *, proposal=None, status='ready'):
    value = dict(version=1, status=status, room_id=row.room_id, room_cycle_id=row.id,
        target_cycle_key=row.cycle_key.isoformat(), target_generation=row.generation,
        proposal_id=proposal.id if proposal else None, proposal_revision=proposal.revision if proposal else None,
        proposal_plan_revision=proposal.proposal_plan_revision if proposal else None, origin=basis['origin'],
        settings_revision=basis.get('settings_revision'), basis_revision=basis.get('basis_revision'),
        items=basis['items'], groups=groups, effect=impact, permission=commands.permission(reason))
    value['display_revision'] = digest(jsonable_encoder([uid, 'respond' if proposal else 'create', value]))
    return jsonable_encoder(value)


def proof(db, room, row, members):
    return jsonable_encoder([room.revision, room.scope, life.selection_context.group_stamp(db, room.group_id),
        row.revision, row.members_revision, row.plan_revision, commands.leadership(db, row),
        [[m.id, m.revision, life.qualify(db, room, row, m)[1]] for m in members]])


def confirmation(uid, room, row, shown, hidden, stamp, *, proposal=None, request=None):
    expires = min(stamp + timedelta(seconds=120), commands.raids.cycle(stamp).ends_at)
    flow = 'respond' if proposal else 'create'
    binding = digest([shown, hidden, request])
    token = opaque.seal(dict(actor=str(uid), room=str(room.id), cycle=str(row.id), generation=row.generation,
        target=row.cycle_key.isoformat(), flow='resume-' + flow, proposal=str(proposal.id) if proposal else None,
        expires=expires.isoformat(), digest=binding, review_version=1))
    if len(token.encode()) > 4096: fail('RESPONSE_TOO_LARGE', 413)
    return dict(context_token=token, issued_at=stamp, expires_at=expires), binding


def verify(value, uid, row, flow, stamp, *, proposal=None):
    token = opaque.unseal(value)
    if (token.get('actor') != str(uid) or token.get('room') != str(row.room_id) or token.get('cycle') != str(row.id) or
            token.get('generation') != row.generation or token.get('target') != row.cycle_key.isoformat() or
            token.get('flow') != 'resume-' + flow or token.get('proposal') != (str(proposal.id) if proposal else None) or
            type(token.get('review_version')) is not int or token['review_version'] != 1):
        fail('CONTEXT_INVALID', 400)
    if stamp >= datetime.fromisoformat(token['expires']): fail('COMMAND_CONTEXT_EXPIRED')
    return token


def prepare(db, uid, rid, body, stamp):
    from app.raid_rooms import cycle_resume as resume
    if 'resume_context_token' in body: fail('INVALID_REQUEST', 400)
    room, row, cm, content, pending = resume.prepare_create(db, uid, rid, body, stamp)
    groups = [wire.BEditGroup.model_validate(g) for g in content['schedule_groups']]
    planning.validate_edit_groups(db, room, row, groups, item_ids=[uuid.UUID(r['item_id']) for r in content['rounds']])
    basis = capture(db, room, row, cm, content, body, pending)
    projected = project_groups(row, basis, validate_at=stamp)
    members = [db.get(life.CycleMember, uuid.UUID(v['id'])) for v in content['members']]
    impact = effect(db, row, cm, content, basis, members, 0, graph.graph.time.quorum(len(members)))
    shown = display(uid, row, content, basis, projected, impact, None)
    context, binding = confirmation(uid, room, row, shown, proof(db, room, row, members), stamp, request=body)
    return dict(display=shown, confirmation=context), binding, basis, (room, row, cm, content, pending)


def preview(principal, rid, data):
    from app.raid_rooms.cycle_creation import scope
    with commands.base.snapshot(principal) as (db, uid, stamp):
        review, _, _, (_, row, *_) = prepare(db, uid, rid, command_body(data), stamp)
        return output(schemas.ResumePreviewContext, dict(scope=scope(stamp, row.cycle_key.isoformat(), row),
            data=dict(kind='weekly_resume_preview', resume_review=review)))


def for_proposal(db, room, row, cm, proposal, content, stamp, *, uid=None):
    from app.raid_rooms import cycle_resume as resume
    uid = cm.user_id if cm is not None else uid
    protected = content.get('review_version') == 1
    basis = content.get('review_basis') if protected else dict(origin='legacy_unknown', items=items(db, row, content),
        groups=content['schedule_groups'])
    binding = SimpleNamespace(content=content)
    members, accepted, required = resume.counts(db, row, proposal, binding)
    reason = 'PROPOSAL_CONTEXT_CHANGED' if not protected else None
    status = 'ready' if protected else 'legacy_unverifiable'
    hidden = None
    if protected:
        if proposal.state != 'pending': reason = 'PROPOSAL_NOT_PENDING'
        elif cm is None or cm.id not in {m.id for m in members}: reason = 'PROPOSAL_TARGET_REQUIRED'
        else:
            try:
                outcomes.playable(stamp, row.cycle_key.isoformat())
                valid_basis(db, row, content, basis, members)
                project_groups(row, basis, validate_at=stamp)
                hidden = proof(db, room, row, members)
            except GameError as error:
                reason = error.code
                if reason == 'PROPOSAL_CONTEXT_CHANGED': status = 'stale'
        impact = effect(db, row, cm, content, basis, members, accepted, required)
    else:
        impact = dict(eligible_count=len(members), accepted_count=accepted, required_votes=required,
            new_round_count=None, new_assignment_count=None, completed_preserved_count=None,
            superseded_proposal_count=None, creator_accept_on_submit=None, my_immediate_session_count_on_accept=None)
    if proposal.state == 'applied':
        receipt = db.scalar(select(CycleOutcome).where(CycleOutcome.cycle_id == row.id, CycleOutcome.kind == 'resume_applied',
            CycleOutcome.evidence['proposal_id'].astext == str(proposal.id)))
        if receipt:
            recorded = receipt.evidence['vote_set']
            impact.update(eligible_count=len(recorded), accepted_count=sum(v['response'] == 'accept' for v in recorded),
                required_votes=graph.graph.time.quorum(len(recorded)))
            if protected:
                saved = receipt.evidence['review_effect']
                impact.update({k: v for k, v in saved.items() if k != 'my_immediate_session_count_on_accept'})
                # Membership IDs remain stable across resume, while their revisions change.
                impact['my_immediate_session_count_on_accept'] = effect(db, row, cm, content, basis,
                    [], 0, 1)['my_immediate_session_count_on_accept']
    shown = display(uid, row, content, basis, project_groups(row, basis), impact, reason,
        proposal=proposal, status=status)
    context = None
    binding_hash = None
    if reason is None:
        context, binding_hash = confirmation(uid, room, row, shown, hidden, stamp, proposal=proposal)
    return dict(display=shown, confirmation=context), binding_hash
