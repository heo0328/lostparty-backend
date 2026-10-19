"""Shared room usage source; explicit callers opt in before public activation."""
from sqlalchemy import select, func
from app.raid_rooms.models import Membership, Room


def count(db, uid):
    return db.scalar(select(func.count()).select_from(Membership).join(Room, Room.id == Membership.room_id)
        .where(Membership.user_id == uid, Membership.ended_at.is_(None), Room.ended_at.is_(None)))


def limits_snapshot(db, uid):
    """Authorized caller supplies a consistent transaction; never inserts or falls back."""
    from app.member_limits import service
    return service.snapshot(db, uid, room_count=count)
