"""Server-proven current generation identity, never a client eligibility flag."""
from app.auth.models import User
from app.game_accounts.common.support import fail
from app.game_accounts.rosters import roster_presence
from app.game_accounts.models.models import Account
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import NameClaim
from app.game_accounts.models.models import Registration
from app.groups.admission_core import owned_selection_character
from app.raid_rooms.admissions import admission_context
from app.raid_rooms.models.cycle_models import RoomCycle
from app.raid_rooms.models.cycle_models import CycleMember
from app.raid_rooms.models.cycle_models import CycleAssignment
from app.raid_rooms.models.cycle_models import CycleGeneration
from app.raid_rooms.models.integrated_models import RecruitmentMembership as Member


def selection(db, room, row, cm):
    """Prove this generation's seat; return its active choice, or None for history."""
    from app.raid_rooms.participation.cycle_lifecycle import assignments
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
    active = [a for a in owned if a.state == 'active']
    if not owned or (active and len({(a.character_id,a.selected_role) for a in active}) != 1):
        fail('ROOM_REVIEW_REQUIRED')
    for a in owned:
        link = db.get(CycleAssignment, a.id)
        if (link is None or (link.room_id,link.cycle_id,link.generation,link.cycle_member_id,
                link.membership_id,link.user_id,link.item_id,link.round_id) !=
                (room.id,current.id,current.generation,actual.id,member.id,actual.user_id,a.item_id,a.round_id)
                or (a.room_id,a.membership_id,a.user_id) != (room.id,member.id,actual.user_id)
                or a.state not in ('active','completed','stopped_incomplete')):
            fail('SOURCE_PARTICIPATION_REQUIRED', 403)
    # History proves this membership, never a current character selection.
    if not active:
        return None
    chosen_rows = active
    chosen = admission_context._selection_snapshot(db,actual.user_id,chosen_rows[0].character_id,chosen_rows[0].selected_role)
    character(db, actual.user_id, chosen, chosen_rows)
    return chosen


def character(db, uid, chosen, owned):
    """Current identity, or an exact observation-only revision chain for this seat."""
    value = db.get(Character, chosen.character_id)
    account = db.get(Account, value.account_id) if value else None
    claim = db.get(NameClaim, (value.server_name, value.character_name)) if value else None
    registration = db.get(Registration, chosen.registration_id)
    retained = bool(value and account and registration
        and registration.user_id == uid and registration.account_id == account.id
        and registration.deleted_at is None and account.owner_id == uid
        and account.verified_at is not None and claim and claim.character_id == value.id
        and registration.version == chosen.expected_registration_version
        and account.ownership_revision == chosen.expected_ownership_revision
        and account.roster_revision == chosen.expected_roster_revision
        and value.lifecycle_revision == chosen.expected_lifecycle_revision
        and all(a.character_id == value.id and a.user_id == uid
                and a.ownership_revision == account.ownership_revision
                and roster_presence.retained_revision(db, account, value, a.lifecycle_revision) for a in owned))
    if retained:
        return value
    value = owned_selection_character(db, uid, chosen.model_dump(mode='json'))
    if any((a.ownership_revision, a.lifecycle_revision) !=
            (chosen.expected_ownership_revision, chosen.expected_lifecycle_revision) for a in owned):
        fail('OWNERSHIP_REQUIRED', 403)
    return value
