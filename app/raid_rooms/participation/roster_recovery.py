"""Transaction-owned recovery of proven observation-only room review.

Never called by GET/worker. The original immutable review evidence is retained.
Unclassified, mixed-cause, changed-assignment and ownership failures stay blocked.
"""
import app.game_accounts.models.roster_presence as roster_presence_models
from datetime import date
from datetime import timedelta
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.game_accounts.rosters import roster_presence
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import Account
from app.game_accounts.common.support import GameError
from app.raid_rooms.participation import cycle_lifecycle as life
from app.raid_rooms.schedules import cycle_planning as plan
from app.raid_rooms.models.cycle_models import RoomCycle
from app.raid_rooms.models.cycle_models import CycleGeneration
from app.raid_rooms.models.cycle_models import CycleMember
from app.raid_rooms.models.cycle_models import CycleAssignment
from app.raid_rooms.models.cycle_models import LegacyCycleEvidence
from app.raid_rooms.models.integrated_models import RecruitmentRoom as Room
from app.raid_rooms.models.integrated_models import RecruitmentAssignment as Assignment
from app.raid_rooms.models.membership_action_models import LeadershipRecovery
from app.raids.service import cycle


def recover(db, account_id, stamp):
    if not roster_presence.enabled(db):
        return []
    current = date.fromisoformat(cycle(stamp).cycle_key)
    affected = (select(CycleAssignment.cycle_id).join(Assignment, Assignment.id == CycleAssignment.assignment_id)
        .join(Character, Character.id == Assignment.character_id).where(Character.account_id == account_id))
    repaired = []
    for row in db.scalars(select(RoomCycle).where(RoomCycle.id.in_(affected),
            RoomCycle.state == 'review_required', RoomCycle.provenance == 'explicit',
            RoomCycle.cycle_key.in_((current, current + timedelta(days=7))))):
        gen = db.get(CycleGeneration, (row.id, row.generation))
        if gen is None or gen.state != 'review_required' or not row.settings_snapshot:
            continue
        recovery = db.get(LeadershipRecovery, (row.id, row.generation))
        if recovery is not None:
            continue
        if db.scalar(select(CycleMember.id).where(CycleMember.cycle_id == row.id,
                CycleMember.generation == row.generation, CycleMember.state == 'review_required').limit(1)):
            continue
        evidence = list(db.scalars(select(LegacyCycleEvidence).where(LegacyCycleEvidence.cycle_id == row.id)))
        if not evidence:
            continue
        valid = True
        for item in evidence:
            a = db.get(Assignment, item.source_id) if item.source_kind == 'assignment' else None
            link = db.get(CycleAssignment, item.source_id) if a else None
            char = db.get(Character, a.character_id) if a else None
            account = db.get(Account, char.account_id) if char else None
            saved = item.evidence
            if (item.reason not in ('CHARACTER_UNUSABLE', 'OWNERSHIP_REQUIRED') or a is None or link is None
                    or (link.cycle_id, link.generation) != (row.id, row.generation)
                    or set(saved) != {'cycle_member_id', 'revision', 'assignment'}
                    or saved['assignment'] != jsonable_encoder(life.assignment_snapshot(a))
                    or saved['cycle_member_id'] != str(link.cycle_member_id)
                    or account is None or account.owner_id != a.user_id
                    or not roster_presence.retained_revision(db, account, char, a.lifecycle_revision)):
                valid = False
                break
            cm = db.get(CycleMember, link.cycle_member_id)
            if cm is None or saved['revision'] != cm.revision:
                valid = False
                break
        if not valid:
            continue
        room = db.get(Room, row.room_id)
        if room is None or room.ended_at is not None:
            continue
        members = list(db.scalars(select(CycleMember).where(CycleMember.cycle_id == row.id,
            CycleMember.generation == row.generation, CycleMember.state == 'participating')))
        if not members:
            continue
        try:
            for cm in members:
                life.qualify(db, room, row, cm)
        except GameError:
            continue
        db.add(roster_presence_models.RosterRoomRecovery(cycle_id=row.id, generation=row.generation,
            evidence=dict(reason='roster_observation_only', original=[
                dict(source_kind=e.source_kind, source_id=str(e.source_id), reason=e.reason) for e in evidence]),
            observed_at=stamp))
        row.state = gen.state = 'open'
        row.members_revision += 1
        plan.bump(db, row)
        repaired.append(row.id)
    return repaired
