"""Bounded minimal card projection within the search transaction."""
from sqlalchemy import select, tuple_
from app.game_accounts.common.support import fail
from app.raid_rooms.common import beta_profile
from app.raid_rooms.group_links import cycle_group_policy
from app.raid_rooms.models.beta_models import BetaSchedule
from app.raid_rooms.models.cycle_group_models import CycleGroupPolicy
from app.raid_rooms.models.integrated_models import RecruitmentSession
from app.raid_rooms.schedules import beta_schedule
from app.raid_rooms.schemas import discovery as dto


def schedule(saved, session, row, stamp, count, room_ended=False):
    value = beta_schedule.display_state(saved, session, row, stamp, room_ended)
    status, missing = 'not_applicable', None
    if value['coordination_state'] == 'coordinating':
        if not saved.early_enabled or type(saved.early_additional_members) is not int or not 1 <= saved.early_additional_members <= 7:
            fail('SERVICE_UNAVAILABLE', 503)
        needed = max(0, saved.early_additional_members + 1 - count)
        status, missing = ('waiting_members', needed) if needed else ('coordinating', None)
    return dict(value, coordination_progress=dict(status=status, missing_members=missing))


def cards(db, rows, uid, stamp, loaded):
    ids = [row.id for _, row in rows]
    policies = {(v.cycle_id,v.generation): v for v in db.scalars(select(CycleGroupPolicy).where(
        tuple_(CycleGroupPolicy.cycle_id,CycleGroupPolicy.generation).in_([(row.id,row.generation) for _,row in rows])))} if ids and cycle_group_policy.enabled(db) else {}
    schedules = {}
    if ids and beta_profile.enabled():
        schedules = {s.cycle_id: (s, session) for s, session in db.execute(select(BetaSchedule, RecruitmentSession)
            .join(RecruitmentSession, RecruitmentSession.id == BetaSchedule.session_id)
            .where(BetaSchedule.cycle_id.in_(ids)))}
    result = []
    for room, row in rows:
        values = loaded[row.id]
        policy = policies.get((row.id,row.generation))
        if cycle_group_policy.enabled(db) and (policy is None or policy.generation != row.generation):
            fail('SERVICE_UNAVAILABLE', 503)
        settings = row.settings_snapshot
        groups, starts = values['groups'], values['starts']
        scheduled = schedules.get(row.id)
        display = schedule(*scheduled, row, stamp, values['count'], room.ended_at is not None) if (
            scheduled and scheduled[0].generation == row.generation) else None
        result.append(dict(room_id=room.id, revision=room.revision, title=room.title,
            scope=policy.scope if policy else room.scope, group_id=policy.group_id if policy else room.group_id,
            admission_mode=settings['admission_mode'], experience_level=settings['experience_level'],
            app_capacity=settings['app_capacity'], app_member_count=values['count'], items=values['items'],
            combat_requirement=settings['combat_requirement'], continuation_enabled=settings['continuation_enabled'],
            room_cycle_id=row.id, target_cycle_key=row.cycle_key.isoformat(), target_generation=row.generation,
            target_revision=row.revision, target_state=values['state'], restricted=row.state=='review_required',
            leader_display=values['leader_display'], schedule=display,
            view_detail_permission=dict(allowed=uid is not None, reason=None if uid else 'AUTH_REQUIRED', next_change_at=None),
            schedule_summary=dict(mode=groups[0].planning_mode if len(groups)==1 else 'multiple' if groups else 'unscheduled',
                occurrence_mode=groups[0].occurrence_mode if len(groups)==1 else None, confirmed_starts_at=sorted(starts),
                earliest_start=min(starts) if starts else None, latest_start=max(starts) if starts else None)))
    return result


def render(db, payload, room_ids, include_groups):
    from fastapi.encoders import jsonable_encoder
    from app.raid_rooms.group_links import group_list_display
    if include_groups and not cycle_group_policy.enabled(db):
        fail('GROUP_FEATURE_NOT_READY', 503)
    payload.update(cycle_group_policy.marker(db))
    payload = group_list_display.attach(db, payload, room_ids, include_groups)
    model = dto.DiscoveryGroupPage if include_groups else dto.DiscoveryPage
    return model.model_validate(jsonable_encoder(payload)).model_dump(mode='json', exclude_unset=True)
