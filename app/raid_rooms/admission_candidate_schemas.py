"""Closed contract2 DTOs with names isolated from existing OpenAPI components."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from app.game_accounts.schemas import DTO
from app.raid_rooms.admission_schemas import PowerComparison
from app.raid_rooms.cycle_wire import Scope

Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]
Reason = Literal['ROLE_NOT_SUPPORTED','RAID_ITEM_LEVEL_REQUIRED','COMBAT_POWER_REQUIRED',
    'WEEKLY_ALREADY_COMPLETED','WEEKLY_ALREADY_PARTICIPATING','ROOM_FULL','ROOM_COMPOSITION_CONFLICT']


class AdmissionCandidateScope(Scope):
    target_revision: Version
    room_cycle_id: UUID
    target_generation: Version


class AdmissionCandidatePower(PowerComparison):
    pass


class AdmissionCandidateRole(DTO):
    supported: StrictBool
    allowed: StrictBool
    reason: Reason | None
    comparison: AdmissionCandidatePower | None

    @model_validator(mode='after')
    def coherent(self):
        if not self.supported:
            if self.allowed or self.reason != 'ROLE_NOT_SUPPORTED' or self.comparison is not None:
                raise ValueError('Unsupported role cannot grant permission')
        elif self.comparison is None or self.reason == 'ROLE_NOT_SUPPORTED' or self.allowed != (self.reason is None):
            raise ValueError('Supported role requires comparison and coherent reason')
        elif self.allowed and self.comparison.state not in ('unrestricted','meets'):
            raise ValueError('Permission requires role power')
        return self


class AdmissionCandidateRoles(DTO):
    dealer: AdmissionCandidateRole
    support: AdmissionCandidateRole


class AdmissionCandidateCharacter(DTO):
    character_id: UUID
    registration_id: UUID
    server_name: Annotated[StrictStr, Field(min_length=1,max_length=64)]
    character_name: Annotated[StrictStr, Field(min_length=1,max_length=64)]
    class_name: Annotated[StrictStr, Field(min_length=1,max_length=64)]
    item_level: Annotated[StrictStr, Field(max_length=64,pattern=r'^[0-9]+(?:\.[0-9]+)?$')]
    roles: AdmissionCandidateRoles

    @model_validator(mode='after')
    def coherent(self):
        if not (self.roles.dealer.allowed or self.roles.support.allowed):
            raise ValueError('Only eligible candidates are returned')
        for name in ('dealer','support'):
            comparison = getattr(self.roles,name).comparison
            if comparison is not None and comparison.selected_role != name:
                raise ValueError('Role comparison mismatch')
        return self


class AdmissionCandidateAssignment(DTO):
    assignment_id: UUID
    revision: Version
    item_id: UUID
    round_id: UUID
    character_id: UUID
    selected_role: Literal['dealer','support']
    party_no: Annotated[StrictInt, Field(ge=1,le=2)]
    slot_no: Annotated[StrictInt, Field(ge=1,le=4)]


class AdmissionCandidateActor(DTO):
    membership_id: UUID
    cycle_member_id: UUID
    cycle_member_revision: Version
    assignments: Annotated[list[AdmissionCandidateAssignment], Field(min_length=1,max_length=200)]


class AdmissionCandidateExclusion(DTO):
    reason: Literal['RAID_ITEM_LEVEL_REQUIRED','COMBAT_POWER_REQUIRED','WEEKLY_ALREADY_COMPLETED',
        'WEEKLY_ALREADY_PARTICIPATING','ROOM_FULL','ROOM_COMPOSITION_CONFLICT']
    detail: Literal['missing','below'] | None
    character_count: Annotated[StrictInt, Field(ge=1)]

    @model_validator(mode='after')
    def coherent(self):
        if (self.reason == 'COMBAT_POWER_REQUIRED') != (self.detail is not None):
            raise ValueError('Power exclusion requires missing/below detail')
        return self


class AdmissionCandidateData(DTO):
    room_id: UUID
    intent: Literal['apply','change_character']
    eligibility_policy_version: Literal['admission-eligibility-2']
    actor: AdmissionCandidateActor | None
    evaluated_at: datetime
    catalog_version: Annotated[StrictStr, Field(min_length=1,max_length=64)]
    snapshot_token: Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
    raw_candidate_count: Annotated[StrictInt, Field(ge=0)]
    eligible_candidate_count: Annotated[StrictInt, Field(ge=0)]
    exclusion_summary: Annotated[list[AdmissionCandidateExclusion], Field(max_length=7)]
    items: Annotated[list[AdmissionCandidateCharacter], Field(max_length=100)]
    next_cursor: Annotated[StrictStr, Field(min_length=1,max_length=2048)] | None

    @model_validator(mode='after')
    def coherent(self):
        if (self.intent == 'change_character') != (self.actor is not None):
            raise ValueError('Actor must match explicit intent')
        if not 0 <= self.eligible_candidate_count <= self.raw_candidate_count:
            raise ValueError('Invalid counts')
        keys = [(v.reason,v.detail) for v in self.exclusion_summary]
        if len(set(keys)) != len(keys) or sum(v.character_count for v in self.exclusion_summary) != self.raw_candidate_count-self.eligible_candidate_count:
            raise ValueError('Invalid exclusions')
        ids = [v.character_id for v in self.items]
        if ids != sorted(set(ids)) or len(ids) > self.eligible_candidate_count:
            raise ValueError('Invalid candidate page')
        return self


class AdmissionCandidatePage(DTO):
    scope: AdmissionCandidateScope
    data: AdmissionCandidateData
