"""Internal commands, not a published HTTP contract."""
import unicodedata
from uuid import UUID
from pydantic import Field, StrictStr, field_validator
from app.game_accounts.schemas import DTO, Version


def normalize_name(value):
    if (not isinstance(value, str) or any(unicodedata.category(c) == 'Cc' or c in '\u2028\u2029' for c in value)):
        raise ValueError('Invalid group name')
    value = value.strip()
    if not 1 <= len(value) <= 20:
        raise ValueError('Group name must contain 1-20 characters')
    return value


class CreateGroup(DTO):
    registration_id: UUID
    character_id: UUID
    expected_registration_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_lifecycle_revision: Version
    # Omission is the default-name command; explicit null is not allowed.
    name: StrictStr = Field(default=None, description='Omitted selects the automatic name; explicit null is rejected.',
                            json_schema_extra=lambda schema: schema.pop('default', None))

    @field_validator('name', mode='before')
    @classmethod
    def group_name(cls, value):
        return normalize_name(value)


class RenameGroup(DTO):
    name: StrictStr
    expected_revision: Version
    expected_membership_revision: Version

    @field_validator('name', mode='before')
    @classmethod
    def group_name(cls, value):
        return normalize_name(value)
