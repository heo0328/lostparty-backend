"""Current cycle boundary rules and historical SQL fixture helpers."""
import uuid
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy import select
from app.core.database import now
from app.game_accounts.common.support import GameError
from app.raid_rooms.common import cycles
from app.raid_rooms.models.integrated_models import RecruitmentRound as Round
from app.raid_rooms.models.integrated_models import RecruitmentMembership as Member
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.integrated_models import RecruitmentItem as Item
from app.raid_rooms.models.weekly_links import WeeklyOccupancy
from app.raid_weekly.models import WeeklyState


def next_rounds(db, rid, key):
    original = list(db.scalars(select(Round).where(Round.room_id == rid)))
    for old in original:
        db.add(Round(id=uuid.uuid4(), room_id=rid, item_id=old.item_id, cycle_key=key,
            difficulty_id=old.difficulty_id, catalog_version=old.catalog_version,
            game_party_size=old.game_party_size, revision=1, state='active', created_at=now(db)))
    db.flush()


def add_next_bundle(db, rid, current, uid):
    membership = db.scalar(select(Member).where(Member.room_id == rid, Member.user_id == uid))
    assignments = list(db.scalars(select(Assignment).join(Round, Round.id == Assignment.round_id)
        .where(Assignment.membership_id == membership.id, Round.cycle_key == current)))
    for old in assignments:
        rd = db.scalar(select(Round).where(Round.item_id == old.item_id, Round.cycle_key == current+timedelta(days=7)))
        item = db.get(Item, old.item_id)
        stamp = now(db)
        fields = {c.name: getattr(old, c.name) for c in Assignment.__table__.columns
                  if c.name not in ('record_created_at', 'record_updated_at')}
        fields.update(id=uuid.uuid4(), round_id=rd.id, joined_at=stamp)
        assignment = Assignment(**fields)
        db.add(assignment)
        db.add(WeeklyState(user_id=uid, character_id=old.character_id, raid_id=item.raid_id,
            cycle_key=rd.cycle_key, revision=2, active_party_id=rid, active_difficulty_id=rd.difficulty_id,
            joined_at=stamp, updated_at=stamp))
        db.flush()
        db.add(WeeklyOccupancy(user_id=uid, character_id=old.character_id, raid_id=item.raid_id,
            cycle_key=rd.cycle_key, room_id=rid, item_id=old.item_id, round_id=rd.id,
            assignment_id=assignment.id, joined_at=stamp))
    db.flush()
    return membership


@pytest.mark.parametrize('utc,key,phase,playable', [
    ('2026-10-20T20:59:59+00:00','2026-10-14','current',True),
    ('2026-10-20T21:00:00+00:00','2026-10-21','current',False),
    ('2026-10-21T00:59:59+00:00','2026-10-21','current',False),
    ('2026-10-21T01:00:00+00:00','2026-10-21','current',True),
    ('2026-10-21T01:00:00+00:00','2026-10-28','future',False),
])
def test_six_and_ten_hour_boundaries(utc,key,phase,playable):
    stamp = datetime.fromisoformat(utc)
    assert cycles.target(stamp,key).phase == phase
    if playable:
        assert cycles.require_playable(stamp,key).key.isoformat() == key
    else:
        with pytest.raises(GameError, match='TARGET_NOT_PLAYABLE'):
            cycles.require_playable(stamp,key)


@pytest.mark.parametrize('key', ['2026-11-04','2026-10-14','2026-10-22','20261021','invalid',None])
def test_invalid_and_out_of_window_target(key):
    with pytest.raises(GameError):
        cycles.target(datetime(2026,10,21,1,tzinfo=timezone.utc),key)
