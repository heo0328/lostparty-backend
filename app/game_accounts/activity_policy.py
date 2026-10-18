"""Manual activity eligibility; initial selection and raid levels are separate policies."""
from app.game_accounts import lifecycle


def eligible(db, character):
    return lifecycle.usable(db, character)


def require_eligible(db, character):
    lifecycle.require_usable(db, character)
