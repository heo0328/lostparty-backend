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
    from app.raid_rooms import cycle_group_policy as policy
    if policy.enabled(db):
        from app.raid_rooms.cycle_models import RoomCycle
        from datetime import date
        key=result['scope'].get('target_cycle_key') or result['scope'].get('view_cycle_key')
        key=date.fromisoformat(key) if isinstance(key,str) else key
        rows=list(db.scalars(select(RoomCycle).where(RoomCycle.room_id.in_(set(room_ids)),RoomCycle.cycle_key==key)))
        by_room={row.room_id:row for row in rows}
        locators={}
        for item in result.get('data',{}).get('items',[]):
            locator=item.get('target',item)
            rid=locator.get('room_id')
            from uuid import UUID
            row=by_room.get(UUID(str(rid))) if rid else None
            if row is None:continue
            generation=locator.get('target_generation',row.generation)
            locators[(row.id,generation)]=policy.metadata(db,row,generation=generation)
        links=list(locators.values()) if locators else [policy.metadata(db,row) for row in rows]
        gids={v['group_id'] for v in links if v['group_id'] is not None}
        groups={g.id:g for g in db.scalars(select(Group).where(Group.id.in_(gids)))} if gids else {}
        labels=[dict(group_id=gid,name=groups[gid].name if gid in groups else None,
            state='unavailable' if gid not in groups else 'ended' if groups[gid].ended_at else 'active') for gid in sorted(gids,key=str)]
        value=jsonable_encoder(dict(result,cycle_groups=links,group_states=labels))
        if len(json.dumps(value,ensure_ascii=False).encode())>1024*1024:fail('SERVICE_UNAVAILABLE',503)
        return value
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
