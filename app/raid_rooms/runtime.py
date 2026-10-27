"""Admission controls for candidate HTTP; production routes remain unregistered."""
import os
from app.game_accounts.support import fail

SETTING = 'RAID_ROOM_ADMISSIONS_ENABLED'


def admissions_enabled():
    value = os.getenv(SETTING, 'false').lower()
    if value not in ('true', 'false', '1', '0'):
        raise ValueError('Invalid recruitment admission configuration')
    return value in ('true', '1')


def admission_reason():
    try:
        return None if admissions_enabled() else 'SERVICE_UNAVAILABLE'
    except ValueError:
        return 'SERVICE_UNAVAILABLE'


def admission_policy(policy):
    """Wrap an explicit reviewed policy at the post-replay execution boundary.

    Recovery and read functions must not use this policy. Replay is handled before
    the service invokes it. The wrapped policy remains mandatory even when enabled.
    """
    if not callable(policy):
        raise TypeError('An explicit reviewed admission policy is required')

    def checked(db, uid, room, round, selection, character):
        reason = admission_reason()
        if reason:
            fail(reason, 503)
        policy(db, uid, room, round, selection, character)
    return checked
