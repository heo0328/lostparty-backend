from app.raid_rooms.schemas.application_presets import PresetDocument

"""Small account-owned collection with durable replay, CAS and no GET writes."""

from copy import deepcopy

from app.core.database import session
from app.core.database import now

from app.game_accounts.common.support import authorize
from app.game_accounts.common.support import reserve
from app.game_accounts.common.support import commit_result
from app.game_accounts.common.support import release
from app.game_accounts.common.support import lock
from app.game_accounts.common.support import fail

from app.raid_rooms.common import beta_text
from app.raid_rooms.common import beta_profile

from app.raid_rooms.models.beta_models import ApplicationMessagePresets

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
