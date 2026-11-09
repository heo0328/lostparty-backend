"""Legacy intent projection never manufactures a cycle or a participation."""
from app.raid_rooms.admissions import cycle_commands as commands
from app.raid_rooms.common import cycles
from app.raid_rooms.schemas import cycle_wire as wire
from app.raid_rooms.outcomes import cycle_outcomes as outcomes
from app.raid_rooms.admissions import continuation
from app.raid_rooms.admissions.cycle_creation import scope


def get(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        outcomes.ready(db);room=commands.base.room(db,uid,rid);member=commands.base.member(db,uid,room)
        value,row=cycles.resolve(db,rid,key,stamp)
        data=continuation.view(db,room,member,value.key)
        data.pop('target_cycle');data['target_cycle_key']=key
        data['permissions']={'choose_continuation':dict(allowed=False,reason='CLIENT_UPGRADE_REQUIRED',next_change_at=None)}
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdContinuationChoices.model_validate(dict(scope=scope(stamp,key,row),data=data)).model_dump(mode='json')
