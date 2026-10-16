"""Activity selection rules; neither grants ownership nor changes stored choices."""
from decimal import Decimal
from app.core.game_policy import DEFAULT_MIN_ITEM_LEVEL
from app.game_accounts.observations import number
from app.game_accounts.provider import ProviderUnavailable
from app.game_accounts import lifecycle
from app.game_accounts.support import fail


def meets_level(character):
    try:
        value = number(character.summary.get('item_level'))
    except ProviderUnavailable:
        return False
    return value is not None and Decimal(value) >= DEFAULT_MIN_ITEM_LEVEL


def eligible(db, character):
    return lifecycle.usable(db, character) and meets_level(character)


def require_eligible(db, character):
    lifecycle.require_usable(db, character)
    if not meets_level(character):
        fail('CHARACTER_UNUSABLE')
