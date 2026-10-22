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
class Submission(CanonicalCycles,wire.InputContract3PutV2MeRaidRoomsRoomIdAvailabilitySubmission):pass
class Confirm(CanonicalCycles,wire.InputContract3PostV2RaidSessionsSessionIdParticipationConfirmations):pass
class EditGroups(CanonicalCycles,wire.InputContract3PutV2RaidRoomsRoomIdScheduleGroups):pass
class SelectGroup(CanonicalCycles,wire.InputContract3PostV2RaidScheduleGroupsGroupIdSelections):pass
class Propose(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdScheduleProposals):pass
class Respond(CanonicalCycles,wire.InputContract3PostV2RaidScheduleProposalsProposalIdResponses):pass

class Outcome(CanonicalCycles,wire.InputContract3PostV2RaidRoundsRoundIdCompletion):pass
class PersonalOutcome(CanonicalCycles,wire.InputContract3PostV2RaidRoundsRoundIdPersonalCompletion):pass
class Closure(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdWeeklyIncompleteClosures):pass
class Resume(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdWeeklyResumeProposals):pass
class Manual(CanonicalCycles,wire.ManualCompletionCommand):pass
class TargetSettings(CanonicalCycles,wire.InputContract3PutV2RaidRoomsRoomIdSettings):pass
class Formation(CanonicalCycles,wire.InputContract3PutV2RaidRoomsRoomIdFormation):pass
class Removal(CanonicalCycles,wire.InputContract3PostV2RaidRoomsRoomIdRemovals):pass
class CommonSettings(CanonicalCycles,wire.CommonSettingsCommand):pass
class GlobalMembership(CanonicalCycles,wire.GlobalMembershipCommand):pass
