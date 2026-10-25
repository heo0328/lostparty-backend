"""Closed opt-in DTOs built from existing typed fields; no legacy model mutation."""
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import types
from typing import Annotated, Literal, Union, get_args, get_origin
from uuid import UUID
from pydantic import (AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt,
                      StrictStr, create_model, field_validator, model_validator)
from app.raid_rooms import cycle_schemas as legacy, beta_text
from app.game_accounts.support import fail

Version=Annotated[StrictInt,Field(ge=1,le=2147483647)]
Threshold=Annotated[StrictInt,Field(ge=1,le=7)]


class Closed(BaseModel):
    model_config=ConfigDict(extra='forbid')


class BetaScheduleConfig(Closed):
    base_starts_at: AwareDatetime
    early_coordination_enabled: StrictBool
    early_additional_members: Threshold | None

    @model_validator(mode='after')
    def valid_setting(self):
        if self.early_coordination_enabled != (self.early_additional_members is not None):
            raise ValueError('Coordination threshold must match enabled flag')
        return self


class BetaScheduleTarget(BetaScheduleConfig):
    target_cycle_key: StrictStr


class BetaScheduleView(Closed):
    policy_version: Literal['beta-schedule-1']
    revision: Version
    session_id: UUID
    base_starts_at: AwareDatetime
    base_ends_at: AwareDatetime
    base_deadline_at: AwareDatetime
    early_coordination_enabled: StrictBool
    early_additional_members: Threshold | None
    coordination_state: Literal['base_committed','coordinating','early_confirmed','base_confirmed','proposal_confirmed','deadline_pending','needs_review','ended']
    coordination_active: StrictBool
    confirmed_starts_at: AwareDatetime | None
    confirmed_ends_at: AwareDatetime | None
    effective_starts_at: AwareDatetime
    effective_ends_at: AwareDatetime
    admission_deadline: AwareDatetime
    deadline_status: Literal['not_due','due_unprocessed','processed','obsolete']
    pending_transition: Literal['base_confirmation_due','departure_review_due'] | None
    review_reason: Literal['departure_passed_unconfirmed'] | None
    evaluated_at: AwareDatetime


class AvailabilityCopyView(Closed):
    state: Literal['unset','configured']
    source_personal_version: Version
    copied_at: AwareDatetime


class RecruitmentIdentity(Closed):
    number: Annotated[StrictInt,Field(ge=1,le=9007199254740991)]
    password: Annotated[StrictStr,Field(pattern=r'^[0-9]{5}$')]


def request(name,base,remove=(),fields=None):
    original={key:(info.annotation,deepcopy(info)) for key,info in base.model_fields.items() if key not in remove}
    original.update(fields or {})
    return create_model(name,__base__=(legacy.CanonicalCycles,Closed),**original)


BetaCreateRequest=request('BetaCreateRequest',legacy.Create,['schedule_groups'],
    {'beta_schedule_targets':(Annotated[list[BetaScheduleTarget],Field(min_length=1,max_length=2)],...)})
BetaOpenRequest=request('BetaOpenRequest',legacy.Open,fields={'beta_schedule':(BetaScheduleConfig,...)})
BetaScheduleEditRequest=request('BetaScheduleEditRequest',legacy.EditGroups,['groups'],{
    'early_coordination_enabled':(StrictBool,...),'early_additional_members':(Threshold|None,...),
    'accept_immediate_confirmation':(StrictBool,...)})


class BetaApplyRequest(legacy.Admission):
    application_memo: StrictStr | None = None

    @field_validator('application_memo')
    @classmethod
    def valid_memo(cls,value):
        beta_text.normalize(value)
        return value


class DepartureWindow(Closed):
    starts_at: AwareDatetime
    ends_at: AwareDatetime


ScheduleState=Literal['base_committed','coordinating','early_confirmed','base_confirmed','proposal_confirmed','deadline_pending','needs_review','ended','legacy']


class BetaSearchRequest(legacy.Search):
    departure_windows: Annotated[list[DepartureWindow],Field(min_length=1,max_length=16)] = Field(default=None,exclude_if=lambda v:v is None)
    schedule_states: Annotated[list[ScheduleState],Field(min_length=1,max_length=9)] = Field(default=None,exclude_if=lambda v:v is None)

    @field_validator('departure_windows','schedule_states',mode='before')
    @classmethod
    def no_explicit_null(cls,value):
        if value is None:raise ValueError('Omit an unused filter')
        return value


ADDITIONS={}
for _name in ['BCard','BDetail','ApplicationDisplayDetail','ResumePlanData','BPlan','BTimeContext','AdmissionDisplayData',
              'ContinuationDisplayData','BApplication','ApplicationDisplayItem','BApplicationView','BReview','BMembership',
              'MembershipActionMembershipEntry','MembershipActionDetailProfileData','MembershipActionPlanProfileData']:
    ADDITIONS[_name]={'beta_schedule':(BetaScheduleView|None,...)}
for _name in ['BDetail','ApplicationDisplayDetail','ResumePlanData','BPlan','MembershipActionDetailProfileData','MembershipActionPlanProfileData']:
    ADDITIONS[_name]['recruitment_identity']=(RecruitmentIdentity|None,...)
for _name in ['BApplication','ApplicationDisplayItem','BApplicationView','ApplicationDisplayOwnApplication']:
    ADDITIONS.setdefault(_name,{})['application_memo']=(StrictStr|None,...)
ADDITIONS['BSubmissionOut']={'availability_copy':(AvailabilityCopyView|None,...)}
ADDITIONS['BCreationContext']={'beta_schedule_targets':(Annotated[list[BetaScheduleTarget],Field(min_length=1,max_length=2)],...)}
ADDITIONS['OpeningDisplayData']={'beta_schedule_config':(BetaScheduleConfig,...)}


def annotation(value):
    if isinstance(value,type) and issubclass(value,BaseModel):
        return output_model(value)
    origin=get_origin(value)
    if origin is None:return value
    args=get_args(value)
    if origin is Annotated:
        return Annotated[annotation(args[0]),*args[1:]]
    mapped=tuple(annotation(arg) for arg in args)
    if mapped==args:return value
    if origin in (Union,types.UnionType):return Union[mapped]
    if origin is Literal:return value
    return origin[mapped[0]] if len(mapped)==1 else origin[mapped]


@lru_cache(maxsize=None)
def output_model(model):
    fields={};changed=False
    for key,info in model.model_fields.items():
        replacement=annotation(info.annotation)
        if replacement!=info.annotation:changed=True
        fields[key]=(replacement,deepcopy(info))
    extra=ADDITIONS.get(model.__name__,{})
    if not changed and not extra:return model
    fields.update(extra)
    return create_model('Beta_'+model.__name__,__base__=model,**fields)
