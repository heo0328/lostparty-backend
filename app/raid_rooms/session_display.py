"""Bounded, read-only prejoin display snapshots. No session/consent creation."""
import json
from datetime import timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.lifecycle import digest
from app.game_accounts.support import fail
from app.raid_rooms import cycle_schedule as schedule
from app.raid_rooms.integrated_models import RecruitmentSession as Session
from app.raid_rooms.cycle_application_models import CycleSession
from app.raid_rooms.source_models import SessionBinding
from app.raid_rooms.schedule_heads import ScheduleHead

MAX_RESPONSE_BYTES = 1024 * 1024


def enabled(token):
    if 'session_display_version' not in token:
        return False
    if type(token['session_display_version']) is not int or token['session_display_version'] != 1:
        fail('CONTEXT_INVALID', 400)
    return True


def marker(include):
    return {'session_display_version': 1} if include else {}


def finish(uid, flow, value, evidence=()):
    value['display_revision'] = digest(jsonable_encoder([uid, flow, value, evidence]))
    return jsonable_encoder(value)


def existing(db, uid, row, stamp, flow, choices=None):
    rows = list(db.execute(select(Session, SessionBinding.required)
        .join(CycleSession, CycleSession.session_id == Session.id)
        .join(SessionBinding, SessionBinding.session_id == Session.id)
        .join(ScheduleHead, ScheduleHead.group_id == SessionBinding.group_id)
        .where(CycleSession.cycle_id == row.id, CycleSession.generation == row.generation,
               ScheduleHead.active.is_(True), Session.state.in_(('unconfirmed', 'confirmed'))).order_by(Session.id)))
    supplied = {str(v['session_id']): v for v in choices} if choices is not None else None
    if supplied is not None and set(supplied) != {str(s.id) for s, _ in rows}:
        fail('SERVICE_UNAVAILABLE', 503)
    values = []
    for sess, required in rows:
        deadline = sess.starts_at - timedelta(minutes=30) if sess.state == 'confirmed' else None
        closed = deadline is not None and stamp >= deadline
        choice = dict(required=required, join_deadline=deadline, permission=dict(allowed=not closed,
            reason='RECRUITMENT_CLOSED' if closed else None, next_change_at=deadline if not closed else None))
        if supplied is not None:
            choice = {k: supplied[str(sess.id)][k] for k in ('required', 'join_deadline', 'permission')}
        values.append(dict(session_id=sess.id, revision=sess.revision, schedule_revision=sess.schedule_revision,
            state=sess.state, starts_at=sess.starts_at, ends_at=sess.ends_at, **choice))
    return finish(uid, flow, dict(kind='existing', selection_mode='select_session_ids', target_cycle_key=row.cycle_key,
        room_cycle_id=row.id, target_generation=row.generation, plan_revision=row.plan_revision,
        sessions=values, previews=[]))


def none(uid, row, flow):
    return finish(uid, flow, dict(kind='none', selection_mode='no_session_selection', target_cycle_key=row.cycle_key,
        room_cycle_id=row.id, target_generation=row.generation, plan_revision=row.plan_revision, sessions=[], previews=[]))


def preview(db, uid, source, key, cycle_id, generation, settings, inputs):
    groups = schedule.groups(db, source)
    heads = {h.client_key: h.group_id for h in db.scalars(select(ScheduleHead).where(
        ScheduleHead.group_id.in_([g.id for g in groups])))} if groups else {}
    by_id = {g.id: g for g in groups}
    settings_by_item = {v['item_id']: v for v in settings['items']}
    minutes = {item.raid_id: settings_by_item[str(item.id)]['duration_minutes']
               for item, _ in schedule.admission.rounds(db, source)}
    output = []
    for item in inputs:
        group = by_id[heads[item.client_group_key]]
        group_ref = digest([str(cycle_id), generation, str(group.id)])
        alternatives = []
        for alt in item.alternatives:
            start = schedule.local_start(key, alt.weekday, alt.starts_local) if item.planning_mode == 'manual' else None
            durations = [minutes[r] for r in alt.item_order]
            total = sum(durations) if durations and all(type(v) is int and v > 0 for v in durations) else None
            end = start + timedelta(minutes=total) if start is not None and total is not None else None
            materialization = ('on_open' if item.occurrence_mode == 'each' or len(item.alternatives) == 1 else 'after_group_selection') if item.planning_mode == 'manual' else 'after_coordination' if item.planning_mode == 'coordinated' else 'not_scheduled'
            alternatives.append(dict(preview_ref=digest([group_ref, alt.client_alternative_key]), session_id=None,
                state='preview', weekday=alt.weekday, starts_at=start, ends_at=end,
                time_state='bounded' if end is not None else 'start_only' if start is not None else 'undetermined',
                materialization=materialization))
        output.append(dict(preview_group_ref=group_ref, source_group_revision=group.revision,
            planning_mode=item.planning_mode, occurrence_mode=item.occurrence_mode, day_scope=item.day_scope,
            required=item.required, alternatives=sorted(alternatives, key=lambda a: a['preview_ref'])))
    return finish(uid, 'opening', dict(kind='opening_preview', selection_mode='opening_implicit_enrolment',
        target_cycle_key=key, room_cycle_id=cycle_id, target_generation=generation, plan_revision=None,
        sessions=[], previews=sorted(output, key=lambda g: g['preview_group_ref'])),
        [source.id, source.generation, source.revision, source.plan_revision, source.settings_revision,
         settings, jsonable_encoder(inputs)])


def output(model, value, include, *, snapshot=None):
    from app.raid_rooms import beta_output
    result = beta_output.render(*snapshot,model,value,exclude_unset=True) if snapshot is not None else model.model_validate(value).model_dump(mode='json', exclude_unset=True)
    if include and len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_RESPONSE_BYTES:
        fail('RESPONSE_TOO_LARGE', 413)
    return result
