"""Strict request semantics layered over the generated fixed wire contract."""
from datetime import date
from pydantic import field_validator
from app.raid_rooms import cycle_wire as wire


class CanonicalCycles:
    @field_validator('target_cycle_key','expected_cycle_key',mode='before',check_fields=False)
    @classmethod
    def canonical_cycle(cls,value):
        if not isinstance(value,str):raise ValueError('canonical cycle string required')
        try:parsed=date.fromisoformat(value)
        except ValueError:raise ValueError('invalid cycle') from None
        if parsed.isoformat()!=value or parsed.isoweekday()!=3:raise ValueError('Wednesday required')
        return value


class Create(CanonicalCycles,wire.InputContract3PostV2RaidRooms):pass
class Admission(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdJoin):pass
class Approve(CanonicalCycles,wire.InputContract3PostV2RaidRoomApplicationsApplicationIdApprove):pass
class Withdraw(CanonicalCycles,wire.InputContract3PostV2RaidRoomApplicationsApplicationIdWithdraw):pass
class Search(CanonicalCycles,wire.InputContract3PostV2RaidRoomsSearch):pass
class Continue(CanonicalCycles,wire.ContinueCommand):pass
class Decline(CanonicalCycles,wire.ScopedCommand):pass
class Cancel(CanonicalCycles,wire.CancellationCommand):pass
class Open(CanonicalCycles,wire.OpeningCommand):pass
class Transfer(CanonicalCycles,wire.TransferCommand):pass
class Character(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdCharacterChanges):pass
