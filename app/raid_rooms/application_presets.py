"""Small account-owned collection with durable replay, CAS and no GET writes."""
from copy import deepcopy
from typing import Annotated
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, StrictInt, UUID4, field_validator
from app.core.database import session, now
from app.game_accounts.router import Principal, Key
from app.game_accounts.support import authorize, reserve, commit_result, release, lock, fail
from app.raid_rooms.availability_router import AvailabilityRoute
from app.raid_rooms import beta_text, beta_profile, cycle_wire
from app.raid_rooms.beta_models import ApplicationMessagePresets
from app.raid_rooms.beta_schemas import Memo, MemoStored


class PresetItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID4
    text: Memo

    @field_validator('text')
    @classmethod
    def check_text(cls, value):
        beta_text.normalize(value, preset=True)
        return value  # Never normalize the idempotency payload.


class PresetPut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    items: Annotated[list[PresetItem], Field(max_length=5)]

    @field_validator('items', mode='before')
    @classmethod
    def check_limit(cls, value):
        if isinstance(value, list) and len(value)>5:
            fail('APPLICATION_PRESET_LIMIT_EXCEEDED', 400)
        return value

    @field_validator('items')
    @classmethod
    def check_ids(cls, value):
        if len({v.id for v in value})!=len(value):
            fail('INVALID_REQUEST', 400)
        return value


class StoredPresetItem(PresetItem):
    text: MemoStored


class PresetDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Annotated[StrictInt, Field(ge=1, le=2147483647)]
    items: Annotated[list[StoredPresetItem], Field(max_length=5)]
    saved_at: datetime | None


def document(row):
    return dict(version=row.version if row else 1, items=deepcopy(row.items) if row else [],
                saved_at=row.saved_at if row else None)


def get(principal):
    with session() as db:
        uid=authorize(db, principal)
        return document(db.get(ApplicationMessagePresets,uid))


def put(principal,key,data):
    # exclude_unset retains absent/null distinctions in other commands; this
    # closed resource has exactly two required fields and no hidden actor input.
    payload=data.model_dump(mode='json')
    digest_payload=dict(body=payload,raw_body=beta_profile.raw_body(payload))
    ticket,replay=reserve(principal,'application-message-presets-put',key,digest_payload)
    if replay:return replay
    try:
        with session() as db, db.begin():
            uid=authorize(db,principal,write=True)
            lock(db,'application-presets:'+str(uid))
            row=db.get(ApplicationMessagePresets,uid)
            version=row.version if row else 1
            if data.expected_version!=version:fail('REVISION_CONFLICT')
            items=[dict(id=str(v.id),text=beta_text.normalize(v.text,preset=True)) for v in data.items]
            if items!=(row.items if row else []):
                if version>=2147483647:fail('REVISION_CONFLICT')
                if row is None:
                    row=ApplicationMessagePresets(user_id=uid,version=version,items=[],saved_at=None)
                    db.add(row)
                row.items=items;row.version+=1;row.saved_at=now(db)
            result=PresetDocument.model_validate(document(row)).model_dump(mode='json')
            db.flush()
            return commit_result(db,ticket,200,result)
    except Exception:
        release(ticket)
        raise


from app.raid_rooms.cycle_router import CycleRoute


class PresetRoute(CycleRoute):
    def allowed_query(self,request):return set()
    def repeated_query(self,request):return set()


router=APIRouter(prefix='/v2/me/application-message-presets',tags=['application-message-presets'],route_class=PresetRoute)
errors={code:{'model':cycle_wire.Error} for code in (400,401,403,404,409,413,429,503)}


@router.get('',response_model=PresetDocument,responses=errors)
def read_presets(principal:Principal):
    return get(principal)


@router.put('',response_model=PresetDocument,responses=errors)
def write_presets(data:PresetPut,principal:Principal,key:Key):
    return put(principal,key,data)[1]
