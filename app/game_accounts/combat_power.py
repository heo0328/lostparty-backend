"""Combat-power parsing/selection primitives; no REST or DB writes."""
from decimal import Decimal

from app.core.game_policy import DEFAULT_MIN_ITEM_LEVEL
from app.game_accounts.observations import number
from app.game_accounts.provider import ProviderUnavailable


def default_collection_target(item_level):
    """Use the shared item-level default without creating activity rights."""
    value = number(item_level)
    return value is not None and Decimal(value) >= DEFAULT_MIN_ITEM_LEVEL


def parse_profile_power(profile, server_name, character_name):
    """None means not supplied; invalid/mismatched data is a failed fetch."""
    if not isinstance(profile, dict) or (
        profile.get('ServerName') != server_name
        or profile.get('CharacterName') != character_name
    ):
        raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
    return number(profile.get('CombatPower'))
