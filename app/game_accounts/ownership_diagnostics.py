"""Manual equipment observation, without DB writes or granting ownership."""
import getpass
import json
import sys
import warnings
from time import monotonic

from app.game_accounts.equipment import (SLOTS, parse_equipment, required_slots,
                                         compare_equipment, InvalidSnapshot)
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable


class ObservationRejected(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class EquipmentProbe:
    """All identifying values remain in memory; only bounded fixed reports escape."""
    def __init__(self, provider, name, clock=monotonic):
        self._provider, self._name, self._clock = provider, name, clock
        self._baseline = self._server = self._slots = self._deadline = None
        self._stage = 'new'
        self._changed_match = False
        self._calls = 0

    def _read(self):
        if self._deadline is not None and self._clock() >= self._deadline:
            raise ObservationRejected('OBSERVATION_EXPIRED')
        self._calls += 1
        raw = self._provider.armory(self._name)
        profile = raw.get('ArmoryProfile') if isinstance(raw, dict) else None
        if (not isinstance(profile, dict) or profile.get('CharacterName') != self._name or
                not isinstance(profile.get('ServerName'), str) or
                not 1 <= len(profile['ServerName'].strip()) <= 64):
            raise ObservationRejected('PROFILE_MISMATCH')
        if self._server is not None and profile['ServerName'] != self._server:
            raise ObservationRejected('PROFILE_MISMATCH')
        try:
            gear = parse_equipment(raw.get('ArmoryEquipment'))
        except InvalidSnapshot:
            raise ObservationRejected('EQUIPMENT_INVALID') from None
        return profile['ServerName'], gear

    def _report(self, stage, **values):
        return dict(check='equipment_observation', stage=stage, provider_calls=self._calls,
                    ownership_proof=False, canonical_binding=False, retirement_proof=False, **values)

    def baseline(self):
        if self._stage != 'new':
            raise ObservationRejected('INVALID_STAGE')
        server, gear = self._read()
        if set(gear) != set(SLOTS):
            raise ObservationRejected('BASELINE_INCOMPLETE')
        self._server, self._baseline = server, gear
        self._slots = required_slots(gear)
        self._deadline = self._clock() + 600
        self._stage = 'baseline'
        return self._report('baseline', status='observed', requested_slots=list(self._slots),
                            equipped_slot_count=len(gear))

    def changed(self):
        if self._stage != 'baseline':
            raise ObservationRejected('INVALID_STAGE')
        _, gear = self._read()
        verdict = compare_equipment(self._baseline, self._slots, gear)
        self._changed_match = verdict == 'EQUIPMENT_MATCHED'
        self._stage = 'changed'
        return self._report('changed', status='observed', comparison=verdict,
                            requested_absent=all(slot not in gear for slot in self._slots),
                            non_requested_unchanged=all(gear.get(slot) == self._baseline[slot]
                                                       for slot in SLOTS if slot not in self._slots))

    def restored(self):
        if self._stage != 'changed':
            raise ObservationRejected('INVALID_STAGE')
        _, gear = self._read()
        matched = gear == self._baseline
        self._stage = 'done'
        return self._report('restored', status='ready_for_review' if matched and self._changed_match else 'not_ready',
                            all_six_restored=matched, requested_change_observed=self._changed_match)


def emit(report):
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def main():
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        emit({'status': 'not_ready', 'reason': 'INTERACTIVE_TERMINAL_REQUIRED'})
        return 2
    try:
        with warnings.catch_warnings():
            # Never fall back to echoing credentials when terminal control fails.
            warnings.simplefilter('error', getpass.GetPassWarning)
            token = getpass.getpass('Lost Ark JWT (hidden, local only): ')
            name = getpass.getpass('Test character name (hidden, local only): ').strip()
        probe = EquipmentProbe(LostArkProvider(token), name)
        input('장비 6부위를 장착한 상태에서 Enter (API 1회): ')
        emit(probe.baseline())
        input('위 requested_slots만 직접 해제하고 API 반영 시간을 기다린 뒤 Enter (API 1회, 자동반복 없음): ')
        emit(probe.changed())
        input('장비를 원래대로 모두 장착하고 API 반영 시간을 기다린 뒤 Enter (API 1회): ')
        report = probe.restored()
        emit(report)
        return 0 if report['status'] == 'ready_for_review' else 1
    except (EOFError, KeyboardInterrupt):
        emit({'status': 'cancelled', 'reminder': 'Restore equipment manually if changed'})
        return 2
    except ObservationRejected as error:
        reason = error.reason
    except ProviderUnavailable as error:
        safe = {'LOSTARK_KEY_REJECTED', 'UPSTREAM_RATE_LIMITED', 'UPSTREAM_UNAVAILABLE',
                'UPSTREAM_INVALID_RESPONSE', 'UPSTREAM_RESPONSE_TOO_LARGE', 'UPSTREAM_BUSY',
                'UPSTREAM_NOT_CONFIGURED'}
        reason = error.reason if error.reason in safe else 'CHECK_UNAVAILABLE'
    except Exception:
        reason = 'CHECK_UNAVAILABLE'
    emit({'status': 'failed', 'reason': reason, 'reminder': 'Restore equipment manually if changed'})
    return 1


if __name__ == '__main__':
    sys.exit(main())
