"""Server-proven current generation identity, never a client eligibility flag."""
from app.auth.models import User
from app.game_accounts.support import fail
from app.groups.admission_core import owned_selection_character
from app.raid_rooms import admission_context
from app.raid_rooms.cycle_models import RoomCycle, CycleMember, CycleAssignment, CycleGeneration
from app.raid_rooms.integrated_models import RecruitmentMembership as Member


def selection(db, room, row, cm):
    from app.raid_rooms.cycle_lifecycle import assignments
    current = db.get(RoomCycle, row.id)
    actual = db.get(CycleMember, cm.id)
    if (current is None or current.room_id != room.id or current.provenance != 'explicit'
            or current.generation is None or current.generation != row.generation
            or actual is None or (actual.room_id, actual.cycle_id, actual.generation) !=
            (room.id, current.id, current.generation)):
        fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    # Internal review projections may alter state, never the persisted identity/revision.
    if any(getattr(actual, k) != getattr(cm, k) for k in ('membership_id','user_id','revision')):
        fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    if actual.state not in ('participating','completed','stopped','review_required'):
        fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    member = db.get(Member, actual.membership_id)
    gen = db.get(CycleGeneration, (current.id, current.generation))
    if (gen is None or member is None or member.ended_at is not None or
            (member.room_id, member.user_id) != (room.id, actual.user_id)):
        fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    user = db.get(User, actual.user_id)
    if user is None or user.status != 'active':
        fail('ROOM_TARGET_UNAVAILABLE')
    owned = assignments(db, current, actual)
    if not owned or len({(a.character_id,a.selected_role) for a in owned}) != 1:
        fail('ROOM_REVIEW_REQUIRED')
    for a in owned:
        link = db.get(CycleAssignment, a.id)
        if (link is None or (link.room_id,link.cycle_id,link.generation,link.cycle_member_id,
                link.membership_id,link.user_id,link.item_id,link.round_id) !=
                (room.id,current.id,current.generation,actual.id,member.id,actual.user_id,a.item_id,a.round_id)
                or (a.room_id,a.membership_id,a.user_id) != (room.id,member.id,actual.user_id)
                or a.state not in ('active','completed','stopped_incomplete')):
            fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    chosen = admission_context._selection_snapshot(db,actual.user_id,owned[0].character_id,owned[0].selected_role)
    owned_selection_character(db,actual.user_id,chosen.model_dump(mode='json'))
    if any((a.ownership_revision,a.lifecycle_revision) !=
            (chosen.expected_ownership_revision,chosen.expected_lifecycle_revision) for a in owned):
        fail('OWNERSHIP_REQUIRED', 403)
    return chosen
