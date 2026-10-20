"""Opaque AEAD completion/closure snapshots; no other member ledger CAS on wire."""
import os,json,base64,hashlib,hmac,uuid
from datetime import datetime,timedelta,date
from sqlalchemy import select
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from fastapi.encoders import jsonable_encoder
from app.core.config import settings
from app.game_accounts.support import fail
from app.game_accounts.lifecycle import digest
from app.raid_rooms import admission_service as base,scheduling as graph
from app.raid_rooms.integrated_models import RecruitmentAssignment as Assignment,RecruitmentRound as Round,RecruitmentItem as Item
from app.raid_rooms.source_models import RoomSettings,ContinuationChoice as Choice,TimeReservation as Reservation,SegmentDurationEvidence
from app.raid_rooms.integrated_models import RecruitmentSegment as Segment
from app.raid_rooms.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState

# Four existing 30-second command leases provide a bounded user-confirmation
# window without equating read snapshots with permanent execution authority.
LIFETIME_SECONDS=120
MAX_TOKEN_BYTES=4096


def seal(value):
    kid=settings.recovery_kid
    key=hmac.new(settings.recovery_key(),b'recruitment-command-aead-v1',hashlib.sha256).digest()
    nonce=os.urandom(12);aad=('rc1.'+kid).encode()
    return aad.decode()+'.'+base64.urlsafe_b64encode(nonce+AESGCM(key).encrypt(nonce,json.dumps(jsonable_encoder(value),sort_keys=True,separators=(',',':')).encode(),aad)).decode().rstrip('=')


def unseal(value):
    try:
        if len(value)>MAX_TOKEN_BYTES:raise ValueError()
        version,kid,encoded=value.split('.')
        if version!='rc1':raise ValueError()
        key=hmac.new(settings.recovery_key(kid),b'recruitment-command-aead-v1',hashlib.sha256).digest()
        raw=base64.b64decode(encoded+'='*((-len(encoded))%4),altchars=b'-_',validate=True)
        return json.loads(AESGCM(key).decrypt(raw[:12],raw[12:],(version+'.'+kid).encode()))
    except (ValueError,TypeError,KeyError,InvalidTag,OSError,UnicodeDecodeError):fail('CONTEXT_INVALID',400)


def source(db,room,member,command,round_id,stamp):
    cycle=graph.raids.cycle(stamp).cycle_key;key=date.fromisoformat(cycle)
    settings=db.get(RoomSettings,room.id)
    rounds=list(db.scalars(select(Round).where(Round.room_id==room.id,Round.cycle_key==key,Round.state=='active').order_by(Round.id)))
    if command not in ('close_weekly','complete_item','personal_completion'):fail('INVALID_REQUEST',400)
    if command=='close_weekly':
        if round_id is not None:fail('INVALID_REQUEST',400)
    else:
        if round_id is None:fail('INVALID_REQUEST',400)
        rd=db.get(Round,round_id)
        if rd is None or rd.room_id!=room.id:fail('ROUND_NOT_FOUND',404)
        if rd.cycle_key!=key:fail('CYCLE_CHANGED')
        rounds=[r for r in rounds if r.id==round_id]
    values=list(db.scalars(select(Assignment).where(Assignment.room_id==room.id,Assignment.round_id.in_([r.id for r in rounds]),
        Assignment.state=='active').order_by(Assignment.id)))
    if command=='personal_completion':values=[a for a in values if a.membership_id==member.id]
    reason=None
    if room.ended_at is not None:reason='ROOM_NOT_ACTIVE'
    elif room.migration_state!='ready':reason='ROOM_REVIEW_REQUIRED'
    elif not rounds or not values:reason='ROUND_NOT_ACTIVE'
    elif command=='close_weekly':
        if not settings.continuation_enabled:reason='CONTINUATION_REQUIRED'
        actual=db.scalar(select(Assignment.id).join(Round,Round.id==Assignment.round_id).where(Assignment.membership_id==member.id,Round.cycle_key==key))
        if actual is None:reason='WEEKLY_PARTICIPANT_REQUIRED'
    elif command=='complete_item' and member.id!=room.leader_membership_id:reason='ROOM_LEADER_REQUIRED'
    all_members=graph.members(db,room.id)
    choices=list(db.scalars(select(Choice).where(Choice.room_id==room.id,Choice.ended_at.is_(None)).order_by(Choice.id)))
    reservations=list(db.scalars(select(Reservation).where(Reservation.assignment_id.in_([a.id for a in values])).order_by(Reservation.id)))
    rows=[]
    for a in values:
        rd=db.get(Round,a.round_id);item=db.get(Item,a.item_id)
        state=db.get(WeeklyState,(a.user_id,a.character_id,item.raid_id,rd.cycle_key));link=db.get(WeeklyOccupancy,(a.user_id,a.character_id,item.raid_id,rd.cycle_key))
        rows.append([str(a.id),a.revision,str(a.membership_id),str(a.character_id),a.ownership_revision,a.lifecycle_revision,
            state.revision if state else None,str(state.active_party_id) if state else None,str(link.assignment_id) if link else None])
    segment_rows=[]
    for segment in db.scalars(select(Segment).where(Segment.round_id.in_([r.id for r in rounds])).order_by(Segment.id)):
        evidence=db.get(SegmentDurationEvidence,segment.id)
        segment_rows.append([str(segment.id),str(segment.session_id),str(segment.round_id),segment.ordinal,
            str(segment.starts_at),str(segment.ends_at),segment.duration_minutes,segment.duration_source,
            evidence.item_settings_revision if evidence else None,evidence.duration_policy_version if evidence else None])
    bound=[str(room.id),command,cycle,str(round_id),room.revision,room.members_revision,room.plan_revision,settings.revision,settings.continuation_revision,segment_rows,
        [[str(m.id),m.revision] for m in all_members],[[str(r.id),r.revision,r.state] for r in rounds],rows,
        [[str(c.id),c.revision,c.state] for c in choices],[[str(r.id),r.schedule_revision,str(r.starts_at),str(r.ends_at),str(r.released_at)] for r in reservations]]
    personal_active=list(db.scalars(select(Assignment).join(Round,Round.id==Assignment.round_id).where(Assignment.membership_id==member.id,
        Assignment.state=='active',Round.cycle_key==key)))
    last=command=='personal_completion' and len(personal_active)==len(values)
    own_next=[c for c in choices if c.membership_id==member.id and c.target_cycle==key+timedelta(days=7)]
    room_items=set(db.scalars(select(Item.id).where(Item.room_id==room.id)))
    keep=bool(own_next) and {c.item_id for c in own_next}==room_items and all(c.state=='selected' for c in own_next)
    leaders=[m for m in all_members if m.id!=member.id]
    completed_count=len(list(db.scalars(select(Assignment.id).join(Round,Round.id==Assignment.round_id).where(
        Assignment.room_id==room.id,Assignment.state=='completed',Round.cycle_key==key))))
    public=dict(room_id=room.id,command=command,cycle_key=cycle,actor_membership_id=member.id,actor_membership_revision=member.revision,
        room_revision=room.revision,members_revision=room.members_revision,plan_revision=room.plan_revision,target_round_id=round_id,
        effect_scope='room_current_week' if command=='close_weekly' else 'personal_item' if command=='personal_completion' else 'item_round',
        impact=dict(round_ids=[r.id for r in rounds],membership_count=len({a.membership_id for a in values}),assignment_count=len(values),
            reservation_segment_count=sum(r.released_at is None for r in reservations),completed_preserved_count=completed_count),
        continuation=dict(required=last and settings.continuation_enabled,choices_revision=member.revision if last else None,current_choice='keep' if keep else None),
        leadership=dict(required=last and member.id==room.leader_membership_id,
            transfer_candidates=[dict(membership_id=m.id,revision=m.revision,display=next((a.display for a in db.scalars(select(Assignment).where(Assignment.membership_id==m.id).order_by(Assignment.joined_at.desc()).limit(1))),None)) for m in leaders],
            can_end=len(all_members)==1 and member.id==room.leader_membership_id),permission=dict(allowed=reason is None,reason=reason))
    return public,digest(bound),rounds,values,last,keep


def get(principal,rid,command,round_id=None):
    with base.snapshot(principal) as (db,uid,stamp):
        room=base.room(db,uid,rid);member=base.member(db,uid,room)
        value,binding,*_=source(db,room,member,command,round_id,stamp)
        expires=min(stamp+timedelta(seconds=LIFETIME_SECONDS),graph.raids.cycle(stamp).ends_at)
        value.update(issued_at=stamp,expires_at=expires)
        value['context_token']=seal(dict(actor=str(uid),room=str(rid),command=command,round=str(round_id) if round_id else None,
            cycle=value['cycle_key'],expires_at=expires.isoformat(),digest=binding))
        return value
