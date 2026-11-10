"""Issue47 v3: one locked command, exact live effects, immutable history proof."""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.game_accounts.common.support import GameError, fail
from app.game_accounts.rosters.lifecycle import digest
from app.raid_rooms.admissions import cycle_commands as commands
from app.raid_rooms.admissions.cycle_creation import scope, permission
from app.raid_rooms.common import beta_profile, command_context, cycles
from app.raid_rooms.group_links import cycle_group_policy as policy
from app.raid_rooms.participation import cycle_lifecycle as life
from app.raid_rooms.participation import cycle_leadership as leaders
from app.raid_rooms.participation.atomic_members import cycle_proof
from app.raid_rooms.schedules import cycle_schedule as graph
from app.raid_rooms.schedules import cycle_planning as plan
from app.raid_rooms.schemas import batch_completion_schemas as wire
from app.raid_rooms.models.cycle_models import CycleAssignment, CycleGeneration, CycleMember, CycleRound, CycleSubmission
from app.raid_rooms.models.cycle_application_models import CycleApplication
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.integrated_models import RecruitmentRound as Round
from app.raid_rooms.models.source_models import TimeReservation
from app.raid_rooms.outcomes import batch_snapshot as snapshots
from app.raid_rooms.outcomes import cycle_outcomes as outcomes
from app.raid_weekly.models import WeeklyState


def ordered(values):
    return sorted(values, key=str)


def selection(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 5:
        fail('INVALID_REQUEST', 400)
    try:
        ids = [UUID(v) if isinstance(v, str) else v for v in values]
        if any(not isinstance(v, UUID) for v in ids) or len(set(ids)) != len(ids):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        fail('INVALID_REQUEST', 400)
    return ordered(ids)


def parse_rounds(value):
    if len(value.encode()) > 512:
        fail('INVALID_REQUEST', 400)
    try:
        values = json.loads(value)
    except (ValueError, TypeError, RecursionError):
        fail('INVALID_REQUEST', 400)
    return selection(values)


def state(row, generation, actor):
    return dict(target_state=row.state, generation_state=generation.state,
                actor_cycle_member_state=actor.state)


def bounded(model, value):
    result = model.model_validate(jsonable_encoder(value)).model_dump(mode='json')
    if len(json.dumps(result, ensure_ascii=False).encode()) > 1048576:
        fail('RESPONSE_TOO_LARGE', 413)
    return result


@dataclass
class Snapshot:
    value: dict
    binding: str
    room: object
    row: object
    generation: object
    actor: object
    active: list
    completed: list
    cancelled: list
    members: dict
    rounds: list
    reservations: list
    policy_effect: dict | None


def revisions(row, generation, members, rounds, changed):
    result = [dict(resource=k, id=row.id, revision=v) for k, v in (
        ('target', row.revision), ('members', row.members_revision),
        ('plan', row.plan_revision), ('leadership', generation.leadership_revision))]
    for resource, values in (('cycle_membership', members.values()), ('round', rounds), ('assignment', changed)):
        result.extend(dict(resource=resource, id=v.id, revision=v.revision) for v in values)
    if len(result) > 64 or any(not 1 <= v['revision'] <= 2147483647 for v in result):
        fail('REVISION_CONFLICT')
    return sorted(result, key=lambda v: (v['resource'], str(v['id'])))


def _successor(db, room, row, actor, members, active):
    eligible = [m for m in members if m.state == 'participating' and any(a.membership_id == m.membership_id for a in active)]
    proof = [plan.snapshot(m) for m in members]
    def qualify(view, cm):
        try:
            _, basis = life.qualify(db, view, row, cm,
                active_rows=[a for a in active if a.membership_id == cm.membership_id])
            return None, basis
        except GameError as error:
            return error.code, None
    after = None
    if policy.enabled(db):
        chosen, basis, _, after, _ = policy.candidates(db, room, row, eligible, qualify)
        proof.append(basis)
    else:
        chosen = None
        for candidate in sorted(eligible, key=lambda m: (m.joined_order or 2**63, str(m.id))):
            reason, basis = qualify(room, candidate)
            proof.append([candidate.id, reason, basis])
            if reason is None and candidate.joined_order is not None:
                chosen = candidate
                break
    if chosen is None:
        return None, None, proof, None
    chosen_a = next(a for a in active if a.membership_id == chosen.membership_id)
    successor = dict(cycle_member_id=chosen.id, revision=chosen.revision, joined_order=str(chosen.joined_order),
                     character_id=chosen_a.character_id, character_name=chosen_a.display.get('character_name'))
    return successor, chosen, proof, policy.effect(db, row, after) if after is not None else None


def _display(db, active, completed, cancelled):
    selected, cancel = {a.id for a in completed}, {a.id for a in cancelled}
    pairs, assignments = {}, []
    for a in active:
        rd = db.get(Round, a.round_id)
        item = db.get(graph.graph.Item, a.item_id)
        if rd.id not in pairs:
            try:
                difficulty = life.raids.difficulty(item.raid_id, rd.difficulty_id, rd.catalog_version)
            except life.raids.CatalogSelectionError as error:
                fail(error.code)
            pairs[rd.id] = dict(round_id=rd.id, item_id=item.id, raid_id=item.raid_id,
                raid_name=snapshots._raid_name(item.raid_id), difficulty_id=rd.difficulty_id,
                difficulty_name=difficulty.name, catalog_version=rd.catalog_version)
        link = db.get(CycleAssignment, a.id)
        assignments.append(dict(assignment_id=a.id, round_id=a.round_id, membership_id=a.membership_id,
            cycle_member_id=link.cycle_member_id, character_id=a.character_id,
            character_name=a.display.get('character_name'),
            effect='complete' if a.id in selected else 'cancel' if a.id in cancel else 'preserve_active'))
    value = jsonable_encoder(dict(rounds=[pairs[k] for k in ordered(pairs)], assignments=assignments))
    return {**value, 'display_revision': hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()}


def prepare(db, uid, rid, key, round_ids, stamp, *, personal=False):
    selected = selection(round_ids)
    outcomes.ready(db)
    room, row, _ = life.target_row(db, uid, rid, key, stamp)
    if row is None:
        fail('TARGET_NOT_OPEN')
    if row.state != 'open':
        fail('TARGET_CYCLE_CLOSED' if row.state == 'closed' else 'ROOM_REVIEW_REQUIRED')
    generation = db.get(CycleGeneration, (row.id, row.generation))
    if generation is None or generation.state != 'open':
        fail('ROOM_REVIEW_REQUIRED')
    actor = life.actual_member(db, row, uid, states=('participating',) if personal else ('participating', 'completed'))
    if actor is None:
        fail('WEEKLY_PARTICIPANT_REQUIRED', 403)
    all_active = snapshots.active_assignments(db, row)
    current_rounds = [rd for _, rd in life.admission.rounds(db, row)]
    for r in selected:
        link = db.get(CycleRound, r)
        if link is None or (link.room_id, link.cycle_id, link.generation) != (rid, row.id, row.generation):
            fail('TARGET_SCOPE_MISMATCH', 400)
        cycles.require_current_round(db, row, r)
        if db.get(Round, r).state != 'active':
            fail('ROUND_NOT_ACTIVE')
    active = [a for a in all_active if a.membership_id == actor.membership_id] if personal else all_active
    completed = [a for a in active if a.round_id in selected]
    if {a.round_id for a in completed} != set(selected):
        fail('ROUND_NOT_ACTIVE')
    cancelled = [a for a in active if a.round_id not in selected] if personal else []
    live_members = list(db.scalars(select(CycleMember).where(CycleMember.cycle_id == row.id,
        CycleMember.generation == row.generation, CycleMember.state.in_(('participating', 'review_required'))).order_by(CycleMember.joined_order, CycleMember.id)))
    by_membership = {m.membership_id: m for m in live_members}
    for a in all_active:
        cm = by_membership.get(a.membership_id)
        link = db.get(CycleAssignment, a.id)
        member = db.get(life.Member, a.membership_id)
        if (cm is None or link.cycle_member_id != cm.id or cm.user_id != a.user_id
                or member is None or member.ended_at is not None):
            fail('ROOM_REVIEW_REQUIRED')
    leadership = commands.leadership(db, row)
    reason = None
    qualification = None
    try:
        outcomes.playable(stamp, key)
        if not personal and leadership['leader_cycle_member_id'] != actor.id:
            fail('TARGET_LEADER_REQUIRED', 403)
        _, qualification = life.qualify(db, room, row, actor,
            active_rows=[a for a in all_active if a.membership_id == actor.membership_id])
    except GameError as error:
        reason = error.code
    changed = completed + cancelled
    lease_proof = []
    for a in changed:
        item = db.get(graph.graph.Item, a.item_id)
        rd = db.get(Round, a.round_id)
        ledger_key = (a.user_id, a.character_id, item.raid_id, row.cycle_key)
        weekly, lease = db.get(WeeklyState, ledger_key), db.get(life.WeeklyOccupancy, ledger_key)
        if (weekly is None or lease is None or lease.assignment_id != a.id
                or weekly.active_party_id != rid or weekly.active_difficulty_id != rd.difficulty_id
                or weekly.joined_at != lease.joined_at):
            fail('WEEKLY_OCCUPANCY_CHANGED')
        lease_proof.append([plan.snapshot(weekly), plan.snapshot(lease)])
    parts = leaders.own_parts(db, row, actor) if personal else []
    reservations = list(db.scalars(select(TimeReservation).where(TimeReservation.released_at.is_(None),
        TimeReservation.assignment_id.in_([a.id for a in changed]) |
        TimeReservation.participation_id.in_([p.id for p in parts])).order_by(TimeReservation.id)))
    history = snapshots.preserved_completed(db, row, user_id=uid if personal else None)
    departure, candidate, candidate_proof, policy_effect = None, None, None, None
    after = state(row, generation, actor).copy()
    after_leader = {k: leadership[k] for k in ('leader_cycle_member_id', 'leader_membership_id')}
    if personal:
        others = [m for m in live_members if m.id != actor.id]
        mode = 'leave'
        successor = None
        if not others:
            complete_all = True
            for rd in current_rounds:
                prior = db.scalar(select(Assignment.id).join(CycleAssignment,
                    CycleAssignment.assignment_id == Assignment.id).where(CycleAssignment.cycle_id == row.id,
                    CycleAssignment.generation == row.generation, Assignment.round_id == rd.id,
                    Assignment.state == 'completed').limit(1))
                stopped = db.scalar(select(Assignment.id).join(CycleAssignment,
                    CycleAssignment.assignment_id == Assignment.id).where(CycleAssignment.cycle_id == row.id,
                    CycleAssignment.generation == row.generation, Assignment.round_id == rd.id,
                    Assignment.state == 'stopped_incomplete').limit(1))
                proven = rd.state == 'completed' or (rd.state == 'active' and (rd.id in selected or prior is not None) and stopped is None)
                complete_all = complete_all and proven
            mode = 'close_completed' if complete_all else 'close_incomplete'
            after.update(target_state='closed', generation_state='completed' if complete_all else 'cancelled')
            after_leader = dict(leader_cycle_member_id=None, leader_membership_id=None)
        elif leadership['leader_cycle_member_id'] == actor.id:
            mode = 'automatic_successor'
            successor, candidate, candidate_proof, policy_effect = _successor(db, room, row, actor, others, all_active)
            if successor is None:
                reason = reason or 'SUCCESSOR_UNAVAILABLE'
            else:
                after_leader = dict(leader_cycle_member_id=candidate.id, leader_membership_id=candidate.membership_id)
        departure = dict(effect=mode, successor=successor)
        after['actor_cycle_member_state'] = 'cancelled'
    else:
        if not any(a.membership_id == actor.membership_id and a.round_id not in selected for a in all_active):
            after['actor_cycle_member_state'] = 'completed'
        if not any(a.round_id not in selected for a in all_active):
            after.update(target_state='closed', generation_state='completed')
    members = {actor.id: actor}
    if not personal:
        members.update((by_membership[a.membership_id].id, by_membership[a.membership_id]) for a in completed)
    rounds = [rd for rd in current_rounds if rd.id in selected] if not personal else (
        [rd for rd in current_rounds if rd.state == 'active'] if departure['effect'].startswith('close_') else [])
    impact = dict(completed_assignment_ids=ordered(a.id for a in completed),
        cancelled_assignment_ids=ordered(a.id for a in cancelled),
        preserved_active_assignment_ids=ordered(a.id for a in active if a not in changed),
        released_reservation_count=len(reservations), preserves_other_cycles=True,
        preserves_global_membership=True, preserved_completed=history)
    action = 'batch_personal_completion_departure' if personal else 'batch_completion'
    expected = dict(expected_cycle_key=life.raids.cycle(stamp).cycle_key, target_cycle_key=key,
        room_cycle_id=str(row.id), target_generation=row.generation, expected_target_revision=row.revision,
        actor_cycle_member_id=str(actor.id), expected_cycle_member_revision=actor.revision,
        round_ids=list(map(str, selected)))
    data = dict(action=action, room_id=rid, actor_cycle_member_id=actor.id,
        actor_cycle_member_revision=actor.revision, round_ids=selected,
        display=_display(db, active, completed, cancelled), impact=impact, departure=departure,
        state=state(row, generation, actor), leadership=leadership,
        expected_after=dict(state=after, **after_leader) if reason is None else None,
        revisions=revisions(row, generation, members, rounds, changed),
        permission=permission(reason), confirmation=None)
    envelope = policy.enrich(db, dict(scope=scope(stamp, key, row), data=data))
    if policy_effect is not None:
        envelope['group_policy_effect'] = policy_effect
    hidden = [plan.snapshot(room), plan.snapshot(row), plan.snapshot(generation), qualification,
        [plan.snapshot(m) for m in live_members], [plan.snapshot(a) for a in all_active], lease_proof,
        [plan.snapshot(r) for r in reservations], [plan.snapshot(p) for p in parts],
        plan.snapshot(db.get(CycleSubmission, actor.id)) if db.get(CycleSubmission, actor.id) is not None else None,
        cycle_proof(db, row), candidate_proof,
        beta_profile.marker(), policy.marker(db)]
    stable_scope = {k: v for k, v in envelope['scope'].items() if k != 'server_now'}
    binding = digest(jsonable_encoder([uid, rid, action, stable_scope, data, hidden, policy_effect]))
    if reason is None:
        expires = min(stamp + timedelta(seconds=120), life.raids.cycle(stamp).ends_at)
        token = command_context.seal(dict(actor=str(uid), room=str(rid), target=key, command=action,
            body=expected, digest=binding, expires=expires.isoformat(), **policy.marker(db), **beta_profile.marker()))
        data['confirmation'] = dict(context_token=token, issued_at=stamp, expires_at=expires)
    model = wire.BatchPersonalContext if personal else wire.BatchPartyContext
    value = bounded(model, envelope)
    return Snapshot(value, binding, room, row, generation, actor, all_active, completed,
                    cancelled, members, rounds, reservations, policy_effect)


def get(principal, rid, key, round_ids, *, personal=False):
    with commands.base.snapshot(principal) as (db, uid, stamp):
        return prepare(db, uid, rid, key, round_ids, stamp, personal=personal).value


def _apply_assignment(db, row, assignment, stamp, *, completed, personal):
    graph.graph.release(db, assignment=assignment, reason='raid_completed' if completed else 'future_cancel', stamp=stamp)
    life.admission.core.release_assignment(db, assignment, stamp)
    if completed:
        rd = db.get(Round, assignment.round_id)
        item = db.get(graph.graph.Item, assignment.item_id)
        weekly = db.get(WeeklyState, (assignment.user_id, assignment.character_id, item.raid_id, row.cycle_key))
        if personal:
            if weekly.manual_completed_at is None:
                weekly.manual_completed_at, weekly.manual_difficulty_id = stamp, rd.difficulty_id
        elif weekly.party_completed_at is None:
            weekly.party_completed_at, weekly.completed_party_id, weekly.party_difficulty_id = stamp, row.room_id, rd.difficulty_id
        assignment.state = 'completed'
        assignment.build = {**(assignment.build or {}), 'completion_source': 'manual' if personal else 'party', 'completed_at': stamp.isoformat()}


def apply(db, snapshot, command, stamp, *, personal):
    row, actor, generation = snapshot.row, snapshot.actor, snapshot.generation
    data = snapshot.value['data']
    evidence = dict(action=data['action'], round_ids=data['round_ids'], impact=data['impact'],
                    assignments=[life.assignment_snapshot(a) for a in snapshot.completed + snapshot.cancelled])
    if personal:
        parts = leaders.own_parts(db, row, actor)
        evidence['record_schedule_segments'] = [dict(segment_id=s.id, round_id=s.round_id,
            session_id=s.session_id, starts_at=s.starts_at, ends_at=s.ends_at, state='released')
            for s in db.scalars(select(graph.Segment).where(
                graph.Segment.session_id.in_([p.session_id for p in parts]),
                graph.Segment.round_id.in_([a.round_id for a in snapshot.completed + snapshot.cancelled]))
                .order_by(graph.Segment.id))]
        evidence['participations'] = leaders.release_parts(db, row, actor, stamp)
        submission = db.get(CycleSubmission, actor.id)
        if submission is not None:
            evidence['submission'] = plan.snapshot(submission)
            db.delete(submission)
    for a in snapshot.completed:
        _apply_assignment(db, row, a, stamp, completed=True, personal=personal)
    for a in snapshot.cancelled:
        _apply_assignment(db, row, a, stamp, completed=False, personal=personal)
    if personal:
        actor.state, actor.ended_at = 'cancelled', stamp
        actor.revision += 1
        life.event(db, row, actor, command, 'cancelled', stamp, evidence)
        life.decision(db, row, actor.user_id, command, 'declined', stamp,
            dict(cancelled_cycle_member_id=actor.id, reason='personal_completion_departure'))
        mode = data['departure']['effect']
        if mode == 'automatic_successor':
            if snapshot.policy_effect is not None:
                policy.apply(db, row, snapshot.policy_effect['after'])
            generation.leader_cycle_member_id = UUID(data['departure']['successor']['cycle_member_id'])
            generation.leadership_revision += 1
            life.decision(db, row, actor.user_id, command, 'automatic_successor', stamp, data['departure'])
        elif mode.startswith('close_'):
            leaders.close_target(db, row, stamp)
            if mode == 'close_completed':
                generation.state = 'completed'
                for rd in snapshot.rounds:
                    if rd.state == 'stopped_incomplete':
                        rd.state = 'completed'
            generation.leadership_revision += 1
    else:
        for rd in snapshot.rounds:
            rd.state, rd.ended_at = 'completed', stamp
            rd.revision += 1
        affected = {a.membership_id for a in snapshot.completed}
        remaining = [a for a in snapshot.active if a not in snapshot.completed]
        for cm in snapshot.members.values():
            if cm.membership_id not in affected:
                continue
            if not any(a.membership_id == cm.membership_id for a in remaining):
                cm.state, cm.ended_at = 'completed', stamp
            cm.revision += 1
            life.event(db, row, cm, command, 'completed', stamp, evidence)
        if not remaining:
            row.state, generation.state, generation.closed_at = 'closed', 'completed', stamp
            for application in db.scalars(select(CycleApplication).where(CycleApplication.cycle_id == row.id,
                CycleApplication.generation == row.generation, CycleApplication.state == 'pending')):
                application.state, application.ended_at = 'cancelled', stamp
                application.revision += 1
        outcomes.obsolete(db, row)
    db.flush()
    outcomes.settle_participations(db, row, stamp, stopping=personal and data['departure']['effect'] == 'close_incomplete')
    row.members_revision += 1
    plan.bump(db, row)
    if row.state == 'open':
        plan.refresh(db, snapshot.room, row, actor.user_id, command, stamp)
    outcomes.event(db, row, actor.user_id, command, 'personal_completion' if personal else 'complete_item', stamp, evidence)
    db.flush()


def execute(principal, rid, command, data, *, personal=False):
    body = data.model_dump(mode='json')
    action = 'batch_personal_completion_departure' if personal else 'batch_completion'
    def run(db, uid, stamp):
        token = life.verify_token(uid, rid, body, action, stamp)
        expected_body = {**body, 'round_ids': list(map(str, selection(body['round_ids'])))}
        expected_body.pop('context_token')
        if token.get('body') != expected_body:
            fail('CONTEXT_INVALID', 400)
        snap = prepare(db, uid, rid, body['target_cycle_key'], body['round_ids'], stamp, personal=personal)
        if (str(snap.row.id), snap.row.generation, str(snap.actor.id)) != (body['room_cycle_id'], body['target_generation'], body['actor_cycle_member_id']):
            fail('TARGET_SCOPE_MISMATCH', 400)
        if (snap.row.revision, snap.actor.revision) != (body['expected_target_revision'], body['expected_cycle_member_revision']):
            fail('REVISION_CONFLICT')
        current = snap.value['data']
        if not current['permission']['allowed']:
            reason = current['permission']['reason']
            fail(reason, 403 if reason in ('TARGET_LEADER_REQUIRED', 'SOURCE_PARTICIPATION_REQUIRED', 'OWNERSHIP_REQUIRED') else 409)
        life.require_match(token, snap.binding)
        guard = graph.final_deadlines(db, snap.row, [], stamp, join=False)
        apply(db, snap, command, stamp, personal=personal)
        proof = snapshots.preserved_completed(db, snap.row, user_id=uid if personal else None,
            exclude_assignment_ids=[a.id for a in snap.completed])
        if proof != current['impact']['preserved_completed']:
            fail('TARGET_CONTEXT_STALE')
        leadership = commands.leadership(db, snap.row)
        result_state = state(snap.row, snap.generation, snap.actor)
        expected = current['expected_after']
        if jsonable_encoder(result_state) != expected['state']:
            fail('TARGET_CONTEXT_STALE')
        if any((str(leadership[k]) if leadership[k] is not None else None) != expected[k]
               for k in ('leader_cycle_member_id', 'leader_membership_id')):
            fail('TARGET_CONTEXT_STALE')
        value = dict(scope=scope(stamp, body['target_cycle_key'], snap.row), data=dict(
            action=action, command_id=command, outcome='applied', executed_at=stamp, room_id=rid,
            actor_cycle_member_id=snap.actor.id, round_ids=current['round_ids'], impact=current['impact'],
            departure=current['departure'], state=result_state, leadership=leadership,
            revisions=revisions(snap.row, snap.generation, snap.members, snap.rounds, snap.completed + snap.cancelled)))
        value = policy.enrich(db, value)
        if snap.policy_effect is not None:
            value['group_policy_effect'] = snap.policy_effect
        result = bounded(wire.BatchPersonalAck if personal else wire.BatchPartyAck, value)
        def final(current_stamp):
            outcomes.playable(current_stamp, body['target_cycle_key'])
            guard(current_stamp)
            if current_stamp >= datetime.fromisoformat(token['expires']):
                fail('COMMAND_CONTEXT_EXPIRED')
        return 200, result, final
    return cycles.execute(principal, 'batch-depart' if personal else 'batch-complete', command,
                          dict(room_id=str(rid), body=body), run)
