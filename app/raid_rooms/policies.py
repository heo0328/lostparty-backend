"""Explicit initial public/finite policy. No default injection into F1 services."""
from app.game_accounts.support import fail
from app.raids import service as raids
from app.raid_rooms import core


def public_finite(db, uid, room, round, selection, character):
    core.supported(room)
    if round.starts_at is None or round.ends_at is None:
        fail('SCHEDULE_REVIEW_REQUIRED')
    cycle = raids.cycle(round.starts_at)
    if (round.starts_at >= round.ends_at or
            cycle.cycle_key != round.cycle_key.isoformat() or round.ends_at > cycle.ends_at):
        fail('SCHEDULE_REVIEW_REQUIRED')
    # P1 remains display data. Minimum combat-power requirements are not enabled.
