from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, StrictBool, StrictInt
from app.game_accounts.schemas import DTO, Version

Nonnegative = Annotated[StrictInt, Field(ge=0)]


class LimitValues(DTO):
    group_capacity: Nonnegative
    joined_groups: Nonnegative
    raid_rooms: Nonnegative


class UsageMetric(DTO):
    used: Nonnegative | None
    remaining: Nonnegative | None
    state: Literal['within', 'at_limit', 'exceeded', 'unavailable']
    can_increase: StrictBool | None


class Usage(DTO):
    joined_groups: UsageMetric
    raid_rooms: UsageMetric


class AccountLimitIssue(DTO):
    code: Literal['MEMBER_GROUP_LIMIT_EXCEEDED', 'MEMBER_RAID_LIMIT_EXCEEDED']
    dimension: Literal['joined_groups', 'raid_rooms']
    used: Nonnegative
    limit: Nonnegative


class UsageLimits(DTO):
    policy_version: Literal['member-room-limits-v1']
    evaluated_at: datetime
    limits_revision: Version
    usage_revision: Version
    limit_source: Literal['default', 'account']
    updated_at: datetime | None
    limits: LimitValues
    usage: Usage
    issues: list[AccountLimitIssue]
