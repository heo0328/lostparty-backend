"""Permission-scoped member references and filtering before pagination."""
import hmac,hashlib,json
from datetime import date
from sqlalchemy import select,or_,and_
from sqlalchemy.orm import aliased
from fastapi.encoders import jsonable_encoder
from app.core.config import settings
from app.game_accounts.support import fail,cursor_encode,cursor_decode
from app.game_accounts.lifecycle import digest
from app.groups.models import Group,GroupMembership
from app.raid_rooms.queries import snapshot
from app.raid_rooms.integrated_models import RecruitmentRoom as Room,RecruitmentMembership as Member,RecruitmentItem as Item,RecruitmentRound as Round,RecruitmentAssignment as Assignment
from app.raid_rooms.models import DirectoryHead
from app.raid_rooms.source_models import RoomSettings,ContinuationChoice as Choice
from datetime import timedelta
from app.raid_rooms import scheduling as graph


def mac(value):
    return hmac.new(settings.recovery_key(),b'recruitment-filter-v1\0'+json.dumps(jsonable_encoder(value),sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()


def filter_context(db,uid,gids,stamp):
    if not gids or len(set(gids))!=len(gids):fail('INVALID_REQUEST',400)
    groups=[];aliases={};displays={}
    for gid in sorted(gids,key=str):
        group=db.get(Group,gid)
        own=db.scalar(select(GroupMembership.id).where(GroupMembership.group_id==gid,GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None)))
        if group is None or group.ended_at is not None or own is None:fail('GROUP_NOT_FOUND',404)
        groups.append(dict(group_id=gid,revision=group.revision,members_revision=group.members_revision))
        for m in db.scalars(select(GroupMembership).where(GroupMembership.group_id==gid,GroupMembership.ended_at.is_(None)).order_by(GroupMembership.id)):
            aliases.setdefault(m.user_id,[]).append(dict(group_id=gid,group_membership_id=m.id))
            displays[m.user_id]=m.display
    source=[str(uid),groups,[[str(u),a] for u,a in sorted(aliases.items(),key=lambda p:str(p[0]))]]
    scope=mac(source);mapping={mac([scope,str(u)]):u for u in aliases}
    public=dict(filter_context_token=mac(['context',scope]),scope_digest=scope,evaluated_at=stamp,groups=groups,
        members=[dict(member_ref=ref,aliases=aliases[u],display=displays[u]) for ref,u in mapping.items()])
    return public,mapping


def get_context(principal,gids):
    with snapshot(principal) as (db,uid,stamp):return filter_context(db,uid,gids,stamp)[0]


def visible(uid):
    return or_(Room.scope=='public',select(Member.id).where(Member.room_id==Room.id,Member.user_id==uid,Member.ended_at.is_(None)).exists(),
        select(GroupMembership.id).where(GroupMembership.group_id==Room.group_id,GroupMembership.user_id==uid,GroupMembership.ended_at.is_(None)).exists()) if uid else Room.scope=='public'


def card(db,room,uid,stamp):
    config=db.get(RoomSettings,room.id);members=graph.members(db,room.id)
    current=date.fromisoformat(graph.raids.cycle(stamp).cycle_key)
    rounds=list(db.scalars(select(Round).where(Round.room_id==room.id,Round.cycle_key==current).order_by(Round.created_at.desc(),Round.id.desc())))
    seen=set();items=[]
    for rd in rounds:
        if rd.item_id in seen:continue
        seen.add(rd.item_id);i=db.get(Item,rd.item_id)
        items.append(dict(item_id=i.id,raid_id=i.raid_id,difficulty_id=rd.difficulty_id,game_party_size=rd.game_party_size))
    sessions=graph.sessions(db,room.id,stamp);starts=[s.starts_at for s in sessions if s.state=='confirmed']
    groups=graph.groups(db,room.id,current.isoformat())
    leader=next((m for m in members if m.id==room.leader_membership_id),None)
    ld=db.scalar(select(Assignment).where(Assignment.membership_id==leader.id).order_by(Assignment.joined_at.desc()).limit(1)) if leader else None
    mine=next((m for m in members if m.user_id==uid),None)
    return dict(room_id=room.id,revision=room.revision,title=room.title,scope=room.scope,group_id=room.group_id,
        admission_mode=config.admission_mode,experience_level=config.experience_level,app_capacity=room.app_capacity,app_member_count=len(members),
        state='ended' if room.ended_at else 'active',items=items,game_items=items,leader_display=ld.display if ld else None,created_at=room.created_at,
        cycle_key=current.isoformat(),phase='ended' if room.ended_at else 'current',restricted=room.migration_state!='ready',
        schedule_summary=dict(mode=groups[0].planning_mode if len(groups)==1 else 'multiple' if groups else 'unscheduled',
            occurrence_mode=groups[0].occurrence_mode if len(groups)==1 else None,confirmed_starts_at=sorted(starts),earliest_start=min(starts) if starts else None,latest_start=max(starts) if starts else None),
        combat_requirement=dict(input_mode=config.combat_input_mode,dealer_min=config.dealer_min,support_min=config.support_min),continuation_enabled=config.continuation_enabled,
        permissions=dict(view_detail=dict(allowed=True,reason=None),view_plan=dict(allowed=mine is not None,reason=None if mine else 'ROOM_MEMBERSHIP_REQUIRED')))


def search(principal,data):
    with snapshot(principal,public=True) as (db,uid,stamp):
        if len(set(data.group_ids))!=len(data.group_ids) or len({c.member_ref for c in data.member_conditions})!=len(data.member_conditions):fail('INVALID_REQUEST',400)
        scope=None;mapping={}
        if data.group_ids:
            if uid is None:fail('AUTH_REQUIRED',401)
            ctx,mapping=filter_context(db,uid,data.group_ids,stamp);scope=ctx['scope_digest']
            if data.filter_context_token is not None and not hmac.compare_digest(ctx['filter_context_token'],data.filter_context_token):fail('FILTER_CONTEXT_STALE')
        if data.member_conditions and (not data.group_ids or data.filter_context_token is None):fail('INVALID_REQUEST',400)
        if not data.group_ids and data.filter_context_token is not None:fail('INVALID_REQUEST',400)
        query=select(Room).where(Room.ended_at.is_(None),visible(uid))
        if data.category=='general':query=query.where(Room.group_id.is_(None))
        elif data.category=='group_linked':query=query.where(Room.group_id.is_not(None))
        if data.admission_scope is not None:query=query.where(Room.scope==data.admission_scope)
        if data.group_ids:query=query.where(Room.group_id.in_(data.group_ids))
        for condition in data.member_conditions:
            subject=mapping.get(condition.member_ref)
            if subject is None:fail('INVALID_REQUEST',400)
            if len(set(condition.character_ids))!=len(condition.character_ids):fail('INVALID_REQUEST',400)
            member=select(Member.id).where(Member.room_id==Room.id,Member.user_id==subject,Member.ended_at.is_(None))
            if condition.character_ids:
                cycle=date.fromisoformat(graph.raids.cycle(stamp).cycle_key);newer=aliased(Round)
                latest=~select(newer.id).where(newer.item_id==Round.item_id,newer.cycle_key==Round.cycle_key,
                    or_(newer.created_at>Round.created_at,and_(newer.created_at==Round.created_at,newer.id>Round.id))).exists()
                current=select(Assignment.id).join(Round,Round.id==Assignment.round_id).where(Assignment.membership_id==Member.id,Round.cycle_key==cycle,latest)
                future=select(Choice.id).where(Choice.membership_id==Member.id,Choice.target_cycle==cycle+timedelta(days=7),Choice.ended_at.is_(None),Choice.character_id.in_(condition.character_ids)).exists()
                member=member.where(or_(current.where(Assignment.character_id.in_(condition.character_ids)).exists(),and_(~current.exists(),future)))
            query=query.where(member.exists())
        if data.raid_ids:query=query.where(select(Item.id).where(Item.room_id==Room.id,Item.raid_id.in_(data.raid_ids)).exists())
        if data.difficulty_ids:query=query.where(select(Round.id).where(Round.room_id==Room.id,Round.cycle_key==date.fromisoformat(graph.raids.cycle(stamp).cycle_key),Round.difficulty_id.in_(data.difficulty_ids)).exists())
        head=db.get(DirectoryHead,1)
        if head is None:fail('SERVICE_UNAVAILABLE',503)
        normalized=data.model_dump(mode='json',exclude={'cursor'})
        for field in ('group_ids','raid_ids','difficulty_ids'):normalized[field]=sorted(normalized[field])
        normalized['member_conditions']=sorted([dict(member_ref=c.member_ref,character_ids=sorted(map(str,c.character_ids))) for c in data.member_conditions],key=lambda c:c['member_ref'])
        binding=digest([str(uid),normalized,scope]);revision=digest([head.revision,graph.raids.cycle(stamp).cycle_key])
        offset=cursor_decode(data.cursor,binding,revision) if data.cursor else 0
        rooms=list(db.scalars(query.order_by(Room.created_at.desc(),Room.id.desc()).offset(offset).limit(data.limit+1)))
        token=cursor_encode(dict(scope=binding,revision=revision,offset=offset+data.limit)) if len(rooms)>data.limit else None
        return dict(items=[card(db,r,uid,stamp) for r in rooms[:data.limit]],directory_revision=head.revision,filter_scope_digest=scope,next_cursor=token,evaluated_at=stamp)
