from app.raid_rooms.models.roster_participation import Capability

"""One current selection, immutable historical assignments and generation capability.

The caller owns its snapshot or serialized command transaction. Request capability
is never an authorization bypass; it is signed into new character contexts.
"""

from contextlib import contextmanager

from contextvars import ContextVar

from fastapi.encoders import jsonable_encoder

from sqlalchemy import select

from app.auth.models import stamp

from app.game_accounts.rosters.lifecycle import digest

from app.game_accounts.common.support import fail

from app.game_accounts.rosters import roster_presence

PROFILE = 'remaining-active-1'

_state = ContextVar('roster_participation_request', default=None)

def enabled():
    return bool(_state.get() and _state.get()['profile'])

def query():
    return (_state.get() or {}).get('query', {})

@contextmanager
def using(parameters=None):
    parameters = dict(parameters or {})
    profile = parameters.get('participation_profile')
    if profile is not None and profile != PROFILE:
        fail('INVALID_REQUEST', 400)
    for key in ('include_character_issues',):
        if parameters.get(key, 'false') not in ('true', 'false'):
            fail('INVALID_REQUEST', 400)
    value = dict(profile=profile, query=parameters, metadata={})
    token = _state.set(value)
    try:
        yield value
    finally:
        _state.reset(token)

def marker():
    return {'participation_profile': PROFILE} if enabled() else {}

def check_marker(token):
    if (token.get('participation_profile') == PROFILE) != enabled():
        fail('CONTEXT_INVALID', 400)

def split(db, row, cm):
    from app.raid_rooms.participation.cycle_lifecycle import assignments
    values = assignments(db, row, cm)
    from app.raid_rooms.models.cycle_models import CycleAssignment
    seen=set()
    for a in values:
        link=db.get(CycleAssignment,a.id)
        if a.id in seen or link is None or (link.room_id,link.cycle_id,link.generation,link.cycle_member_id,
                link.membership_id,link.user_id,link.item_id,link.round_id)!=(row.room_id,row.id,row.generation,cm.id,
                cm.membership_id,cm.user_id,a.item_id,a.round_id) or (a.room_id,a.membership_id,a.user_id)!=(row.room_id,cm.membership_id,cm.user_id):
            fail('SOURCE_PARTICIPATION_REQUIRED',403)
        seen.add(a.id)
    active=[a for a in values if a.state=='active']
    if len({a.item_id for a in active})!=len(active) or len({(a.character_id,a.selected_role) for a in active})>1:
        fail('ROOM_REVIEW_REQUIRED')
    values.sort(key=lambda a: (str(a.item_id), str(a.round_id), str(a.id)))
    return [a for a in values if a.state == 'active'], [a for a in values if a.state != 'active']

def replacement(db, row, cm):
    active, preserved = split(db, row, cm)
    if not active or (preserved and not enabled()):
        fail('ROUND_NOT_ACTIVE')
    return active

def required(db, row):
    return bool(row and row.generation and roster_presence.enabled(db) and db.scalar(select(Capability.id).where(
        Capability.cycle_id == row.id, Capability.generation == row.generation)))

def require_client(db, row):
    if required(db, row) and not enabled():
        fail('CLIENT_UPGRADE_REQUIRED')

def activate(db, row, stamp):
    if not required(db, row):
        db.add(Capability(cycle_id=row.id, generation=row.generation, created_at=stamp))
        db.flush()

def member(db, row, cm):
    active, preserved = split(db, row, cm)
    def assignment(a):
        return dict(assignment_id=a.id, revision=a.revision, item_id=a.item_id, round_id=a.round_id,
            character_id=a.character_id, selected_role=a.selected_role, party_no=a.party_no, slot_no=a.slot_no)
    current = None
    if active:
        if len({(a.character_id, a.selected_role) for a in active}) != 1:
            fail('ROOM_REVIEW_REQUIRED')
        first = active[0]
        current = dict(character_id=first.character_id, selected_role=first.selected_role,
            display={k: first.display.get(k) for k in ('server_name', 'character_name', 'class_name')})
    value = dict(room_id=row.room_id, target_cycle_key=row.cycle_key.isoformat(), room_cycle_id=row.id,
        target_generation=row.generation, membership_id=cm.membership_id, cycle_member_id=cm.id,
        cycle_member_revision=cm.revision, active_assignments=[assignment(a) for a in active],
        preserved_assignments=[dict(assignment(a), state=a.state) for a in preserved], current_character=current)
    # Actor binding is independent of the destination candidate. The outer
    # character context also signs policies, deadlines and candidate revisions.
    from app.raid_rooms.models.integrated_models import RecruitmentMembership as Member
    persistent=db.get(Member,cm.membership_id)
    from app.raid_rooms.group_links import cycle_group_policy
    from app.raid_rooms.schedules import cycle_schedule
    policy=cycle_group_policy.get(db,row) if cycle_group_policy.enabled(db) else None
    policy_stamp=[policy.revision,policy.scope,policy.group_id] if policy else None
    sessions=[[s.id,s.revision,s.schedule_revision,s.state,s.starts_at,s.ends_at] for s in cycle_schedule.sessions(db,row)]
    value['binding_revision'] = digest(jsonable_encoder([PROFILE, cm.user_id, value,
        persistent.revision,persistent.ended_at,row.revision,row.settings_snapshot,row.plan_revision,policy_stamp,sessions,
        [[a.id, a.revision, a.display, a.build, a.ownership_revision, a.lifecycle_revision] for a in active+preserved]]))
    return value
