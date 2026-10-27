"""Legacy intent projection never manufactures a cycle or a participation."""
from app.raid_rooms import cycle_commands as commands,cycles,cycle_wire as wire,cycle_outcomes as outcomes,continuation
from app.raid_rooms.cycle_creation import scope


def get(principal,rid,key):
    with commands.base.snapshot(principal) as (db,uid,stamp):
        outcomes.ready(db);room=commands.base.room(db,uid,rid);member=commands.base.member(db,uid,room)
        value,row=cycles.resolve(db,rid,key,stamp)
        data=continuation.view(db,room,member,value.key)
        data.pop('target_cycle');data['target_cycle_key']=key
        data['permissions']={'choose_continuation':dict(allowed=False,reason='CLIENT_UPGRADE_REQUIRED',next_change_at=None)}
        return wire.OutputContract3GetV2MeRaidRoomsRoomIdContinuationChoices.model_validate(dict(scope=scope(stamp,key,row),data=data)).model_dump(mode='json')
