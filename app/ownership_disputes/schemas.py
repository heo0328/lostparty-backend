from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator, ConfigDict
from app.game_accounts.schemas import DTO, Name, Version, PreviewOut


class Target(DTO):
    server_name: Name
    character_name: Name


class OwnershipContext(DTO):
    relation: Literal['self','other','unverified','unresolved']
    notice_code: Literal['OTHER_OWNER_VERIFIED'] | None
    observed_at: datetime
    can_start_claim: bool
    blocked_reason: Literal['ALREADY_VERIFIED','IDENTITY_UNRESOLVED','DISPUTE_ALREADY_ACTIVE','DISPUTE_CAPACITY_REACHED'] | None


class PreviewV2(DTO):
    preview: PreviewOut
    ownership_context: OwnershipContext
    server_now: datetime


class ClaimStartIn(DTO):
    model_config = ConfigDict(extra='forbid', json_schema_extra={'oneOf': [
        {'properties': {'source': {'const': 'direct_input'}}, 'required': ['source','character_name'],
         'not': {'anyOf': [{'required': [k]} for k in ('registration_id','expected_registration_version','target_character')]}},
        {'properties': {'source': {'const': 'registration'}}, 'required': ['source','registration_id','expected_registration_version','target_character'],
         'not': {'required': ['character_name']}}
    ]})
    source: Literal['direct_input','registration']
    character_name: Name = Field(default=None, json_schema_extra=lambda x: x.pop('default', None))
    registration_id: UUID = Field(default=None, json_schema_extra=lambda x: x.pop('default', None))
    expected_registration_version: Version = Field(default=None, json_schema_extra=lambda x: x.pop('default', None))
    target_character: Target = Field(default=None, json_schema_extra=lambda x: x.pop('default', None))

    @model_validator(mode='after')
    def choice(self):
        required = {'source','character_name'} if self.source == 'direct_input' else {'source','registration_id','expected_registration_version','target_character'}
        if self.model_fields_set != required:
            raise ValueError('Exactly one strict source required')
        return self


class VersionIn(DTO):
    expected_version: Version


class CharacterSelection(DTO):
    registration_id: UUID
    character_id: UUID
    expected_registration_version: Version
    expected_ownership_revision: Version
    expected_roster_revision: Version
    expected_lifecycle_revision: Version


class DefenseStartIn(DTO):
    expected_dispute_version: Version
    selection: CharacterSelection


ProofResult = Literal['REQUIRED_EQUIPMENT_PRESENT','NON_REQUIRED_EQUIPMENT_CHANGED',
    'PROVIDER_EVIDENCE_PENDING','ROSTER_EVIDENCE_PENDING','VERIFIED','DISPUTE_OPENED',
    'OWNER_DEFENDED','DISPUTE_CAPACITY_REACHED','DISPUTE_ALREADY_ACTIVE','REVISION_CONFLICT',
    'IDENTITY_CONFLICT','LOSTARK_KEY_CHANGED','PARENT_DISPUTE_ENDED','DEFENSE_WINDOW_CLOSED',
    'VERIFICATION_EXPIRED','VERIFICATION_CANCELLED']


class VerificationV2(DTO):
    verification_id: UUID
    version: Version
    purpose: Literal['claim','defense']
    source: Literal['direct_input','registration','dispute_defense']
    source_registration_id: UUID | None
    equipment_status: Literal['pending','passed','expired','cancelled','invalidated']
    ownership_outcome: Literal['none','verified','dispute_opened','defended','blocked']
    ownership_context: OwnershipContext
    target: Target
    required_slots: Annotated[list[Literal['무기','투구','어깨','상의','하의','장갑']], Field(min_length=1,max_length=3)]
    created_at: datetime
    equipment_expires_at: datetime
    server_now: datetime
    ended_at: datetime | None
    result_code: ProofResult | None
    dispute_id: UUID | None
    registration_id: UUID | None
    allowed_actions: list[Literal['confirm','cancel','view_dispute','open_registration']]


DisputeReason = Literal['OWNER_DEFENDED','OWNERSHIP_TRANSFERRED','CHALLENGER_CANCELLED',
    'OWNER_CHANGED','TARGET_CHANGED','PARTY_IMPACT_REVIEW_REQUIRED','REGISTRATION_REMOVED',
    'REGISTRATION_CONFLICT','REGISTRATION_LIMIT','UPSTREAM_UNAVAILABLE','LOSTARK_KEY_NOT_CONFIGURED',
    'LOSTARK_KEY_REJECTED','WAITING_FOR_EARLIER_DISPUTE','MEMBER_UNAVAILABLE']


class DisputeOut(DTO):
    dispute_id: UUID
    version: Version
    viewer_role: Literal['challenger','owner']
    state: Literal['defending','defended','transferred','cancelled','invalidated','review_required']
    phase: Literal['awaiting_defense','settlement_due','retrying_settlement','finished','review_required']
    target: Target
    started_at: datetime
    defense_deadline: datetime
    server_now: datetime
    defense_available_until: datetime | None
    resolved_at: datetime | None
    reason_code: DisputeReason | None
    next_retry_at: datetime | None
    my_registration_id: UUID | None
    my_active_verification_ids: list[UUID]
    allowed_actions: list[Literal['cancel_dispute','start_defense','view_my_verifications','request_settlement','open_registration']]


class VerificationPage(DTO):
    items: list[VerificationV2]
    next_cursor: str | None
    feed_revision: Version
    server_now: datetime


class DisputePage(DTO):
    items: list[DisputeOut]
    next_cursor: str | None
    feed_revision: Version
    server_now: datetime
