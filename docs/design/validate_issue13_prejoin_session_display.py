"""Validate proposal fixtures only. No API, database, provider or HMAC execution.

Run from the repository root with jsonschema installed:
python3 docs/design/validate_issue13_prejoin_session_display.py
"""
import copy
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

PATH = Path('docs/design/issue13-prejoin-session-display.draft.json')
DOC = json.loads(PATH.read_text())
VALIDATOR = Draft202012Validator(DOC, format_checker=FormatChecker())


def check_structure(value):
    if isinstance(value, dict):
        if '$ref' in value:
            assert value['$ref'].startswith('#/')
            target = DOC
            for key in value['$ref'][2:].split('/'):
                target = target[key]
        if value.get('additionalProperties') is False:
            assert set(value.get('required', [])) <= set(value.get('properties', {}))
        for child in value.values():
            check_structure(child)
    elif isinstance(value, list):
        for child in value:
            check_structure(child)


def instant(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    assert value.utcoffset() == timedelta(0)
    return value


def validate(value):
    VALIDATOR.validate(value)
    cycle = date.fromisoformat(value['target_cycle_key'])
    assert cycle.isoweekday() == 3
    kst = timezone(timedelta(hours=9))
    first = datetime.combine(cycle, time(6), kst)
    last = first + timedelta(days=7)
    def interval(item):
        start, end = item['starts_at'], item['ends_at']
        if start is not None:
            start = instant(start)
            assert first <= start < last
        if end is not None:
            end = instant(end)
            assert start is not None and start < end <= last
        return start, end
    ids = [s['session_id'] for s in value['sessions']]
    assert ids == sorted(set(ids))
    for item in value['sessions']:
        start, end = interval(item)
        if item['state'] == 'confirmed':
            assert end - start <= timedelta(hours=24)
            assert instant(item['join_deadline']) == start - timedelta(minutes=30)
        else:
            assert item['join_deadline'] is None
    refs = [g['preview_group_ref'] for g in value['previews']]
    assert refs == sorted(set(refs))
    for group in value['previews']:
        if group['day_scope'] == 'any_current_cycle':
            assert group['planning_mode'] == 'coordinated' and group['alternatives'] == []
        refs = [a['preview_ref'] for a in group['alternatives']]
        assert refs == sorted(set(refs))
        for item in group['alternatives']:
            start, _ = interval(item)
            if start is not None:
                assert start.astimezone(kst).isoweekday() == item['weekday']
            if group['planning_mode'] == 'manual':
                expected = 'on_open' if group['occurrence_mode'] == 'each' or len(group['alternatives']) == 1 else 'after_group_selection'
            else:
                expected = 'after_coordination' if group['planning_mode'] == 'coordinated' else 'not_scheduled'
                assert item['time_state'] == 'undetermined'
            assert item['materialization'] == expected


def main():
    Draft202012Validator.check_schema(DOC)
    check_structure(DOC)
    assert DOC['x-status'] == 'proposal-not-implemented'
    assert len(DOC['x-extension']['paths']) == 3
    examples = DOC['x-examples']
    for value in examples.values():
        validate(value)
    invalid = []
    original = examples['admission_confirmed']
    v = copy.deepcopy(original); v['sessions'][0]['starts_at'] = None; invalid.append(v)
    v = copy.deepcopy(original); v['sessions'][0]['ends_at'] = '2026-10-23T09:00:00Z'; invalid.append(v)
    v = copy.deepcopy(original); v['sessions'][0]['revision'] = 0; invalid.append(v)
    v = copy.deepcopy(original); v['busy_intervals'] = []; invalid.append(v)
    v = copy.deepcopy(original); v['target_cycle_key'] = '2026-10-22'; invalid.append(v)
    v = copy.deepcopy(examples['admission_unconfirmed']); v['sessions'][0]['ends_at'] = '2026-10-23T10:30:00Z'; invalid.append(v)
    v = copy.deepcopy(examples['opening_manual']); v['previews'][0]['alternatives'][0]['session_id'] = original['sessions'][0]['session_id']; invalid.append(v)
    v = copy.deepcopy(examples['opening_manual']); v['plan_revision'] = 1; invalid.append(v)
    v = copy.deepcopy(examples['already_open_or_decline']); v['sessions'] = original['sessions']; invalid.append(v)
    v = copy.deepcopy(original); v['display_revision'] = 'invalid'; invalid.append(v)
    v = copy.deepcopy(original); v['sessions'][0]['starts_at'] = '2026-10-23T19:00:00+09:00'; invalid.append(v)
    for value in invalid:
        try:
            validate(value)
        except (AssertionError, ValueError, ValidationError):
            pass
        else:
            raise AssertionError('Invalid fixture unexpectedly accepted')
    # Optional response addition: absent is valid, explicit null is not.
    extension = copy.deepcopy(DOC)
    extension.pop('$ref')
    extension.update(type='object', additionalProperties=False, properties={'session_display': {'$ref': '#/$defs/SessionDisplay'}})
    envelope = Draft202012Validator(extension, format_checker=FormatChecker())
    envelope.validate({})
    envelope.validate({'session_display': original})
    assert list(envelope.iter_errors({'session_display': None}))
    print(f'DRAFT ONLY: schema/refs/closed objects OK; {len(examples)} examples, '
          f'{len(invalid)} rejected fixtures, 3 opt-in presence cases PASS. '
          'No runtime API/DB/token/concurrency tests executed.')


if __name__ == '__main__':
    main()
