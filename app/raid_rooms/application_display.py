"""Read-only display projections, never an approval/eligibility decision."""
import json
from sqlalchemy import select, tuple_
from pydantic import ValidationError

from app.game_accounts.models import Account, Character, CharacterRoleSummary
from app.game_accounts.power_success import RolePowerSuccess
from app.game_accounts.profile_schemas import RoleSummary
from app.game_accounts.support import fail
from app.raid_rooms.participation_commands import Selection
from app.raid_rooms.participation_core import power_value
from app.raid_rooms.cycle_application_models import CycleApplication
from app.raid_rooms.application_display_schemas import ApplicationDisplayAnalysis, ApplicationDisplayOwnApplication
from app.raid_rooms.cycle_wire import BPowerComparison

PROFILE = 'application-display-1'
MAX_RESPONSE_BYTES = 1024 * 1024


def bounded(value):
    if len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()) > MAX_RESPONSE_BYTES:
        fail('RESPONSE_TOO_LARGE', 413)
    return value


def projections(db, applications, target):
    """Constant query count for a bounded page; all keys retain applicant ownership."""
    if not applications:
        return {}
    try:
        choices = {app.id: Selection.model_validate(app.selection) for app in applications}
        characters = {c.id: c for c in db.scalars(select(Character).where(
            Character.id.in_({s.character_id for s in choices.values()})))}
        accounts = {a.id: a for a in db.scalars(select(Account).where(
            Account.id.in_({c.account_id for c in characters.values()})))}
        keys = {(a.user_id, choices[a.id].character_id, choices[a.id].expected_ownership_revision,
                 choices[a.id].selected_role) for a in applications}
        def load(model):
            columns = (model.user_id, model.character_id, model.ownership_revision, model.role)
            return {(v.user_id, v.character_id, v.ownership_revision, v.role): v
                    for v in db.scalars(select(model).where(tuple_(*columns).in_(keys)))}
        heads, successes = load(CharacterRoleSummary), load(RolePowerSuccess)
        result = {}
        for app in applications:
            choice = choices[app.id]
            character = characters.get(choice.character_id)
            account = accounts.get(character.account_id) if character is not None else None
            reason = ('CHARACTER_DATA_UNAVAILABLE' if character is None or account is None else
                      'APPLICATION_CONTEXT_CHANGED' if (account.owner_id, account.ownership_revision) !=
                      (app.user_id, choice.expected_ownership_revision) else None)
            if reason:
                result[app.id] = dict(comparison=None, analysis=None, display_reason=reason)
                continue
            key = (app.user_id, choice.character_id, choice.expected_ownership_revision, choice.selected_role)
            head, success = heads.get(key), successes.get(key)
            if success is not None:
                if head is None:
                    fail('SERVICE_UNAVAILABLE', 503)
                RoleSummary.model_validate(success.source_summary)
            summary = RoleSummary.model_validate(head.summary) if head is not None else None
            minimum = target.settings_snapshot['combat_requirement'][
                'dealer_min' if choice.selected_role == 'dealer' else 'support_min']
            projection = dict(comparison=power_value(choice.selected_role, minimum, head, success),
                analysis=dict(version=head.version, saved_at=head.saved_at, analyzed_at=summary.analyzed_at,
                              integrity_status=summary.integrity_status,
                              issues=summary.model_dump(mode='json')['issues']) if head is not None else None,
                display_reason=None)
            # Validate stored projection material before it reaches the HTTP response.
            BPowerComparison.model_validate(projection['comparison'])
            if projection['analysis'] is not None:
                ApplicationDisplayAnalysis.model_validate(projection['analysis'])
            result[app.id] = projection
        return result
    except (ValidationError, ValueError, TypeError, KeyError, ArithmeticError):
        fail('SERVICE_UNAVAILABLE', 503)


def own_application(db, uid, room, target, stamp):
    if target.generation is None:
        fail('ROOM_REVIEW_REQUIRED')
    pending = (CycleApplication.state == 'pending') & (CycleApplication.expires_at > stamp)
    app = db.scalar(select(CycleApplication).where(CycleApplication.user_id == uid,
        CycleApplication.room_id == room.id, CycleApplication.cycle_id == target.id,
        CycleApplication.generation == target.generation)
        .order_by(pending.desc(), CycleApplication.created_at.desc(), CycleApplication.id.desc()).limit(1))
    if app is None:
        return None
    try:
        return ApplicationDisplayOwnApplication.model_validate(dict(application_id=app.id, revision=app.revision,
            state='expired' if app.state == 'pending' and app.expires_at <= stamp else app.state,
            expires_at=app.expires_at)).model_dump(mode='json')
    except (ValidationError, ValueError, TypeError):
        fail('SERVICE_UNAVAILABLE', 503)
