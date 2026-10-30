"""Opt-in group labels for only the authorized page, within its read snapshot."""
import json
from sqlalchemy import select
from fastapi.encoders import jsonable_encoder
from app.groups import features
from app.groups.models import Group,GroupDirectoryHead
from app.game_accounts.lifecycle import digest
from app.game_accounts.support import fail
from app.raid_rooms.integrated_models import RecruitmentRoom as Room


def bind(db,binding,revision,enabled,key):
    if not enabled:return binding,revision
    features.ready(db)
    from app.raid_rooms import cycles
    head=db.get(GroupDirectoryHead,1)
    if head is None:fail('SERVICE_UNAVAILABLE',503)
    return [*binding,'include_group_state=true'],digest([revision,head.revision,cycles.directory_revision(db,key)])


def attach(db,result,room_ids,enabled):
    if not enabled:return result
    ids=set(room_ids)
    links=dict(db.execute(select(Room.id,Room.group_id).where(Room.id.in_(ids))).all()) if ids else {}
    if len(links)!=len(ids):fail('SERVICE_UNAVAILABLE',503)
    gids={gid for gid in links.values() if gid is not None}
    groups={g.id:g for g in db.scalars(select(Group).where(Group.id.in_(gids)))} if gids else {}
    labels=[]
    for gid in sorted(gids,key=str):
        row=groups.get(gid)
        labels.append(dict(group_id=gid,name=row.name if row else None,
            state='unavailable' if row is None else 'ended' if row.ended_at else 'active'))
    value=jsonable_encoder(dict(result,group_states=labels,
        room_groups=[dict(room_id=rid,group_id=links[rid]) for rid in sorted(ids,key=str)]))
    if len(json.dumps(value,ensure_ascii=False).encode())>1024*1024:fail('SERVICE_UNAVAILABLE',503)
    return value
