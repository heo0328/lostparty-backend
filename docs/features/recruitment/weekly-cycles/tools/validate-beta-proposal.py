"""Static proposal DTO/state checks only; no app import, DB, keys or provider."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import unicodedata
import sys
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def aligned(value):
    value = stamp(value)
    if value.second or value.microsecond or value.minute % 5:
        raise ValueError('Time must align with a five-minute tick')
    return value


def config(value, context):
    count = value['early_additional_members']
    if value['early_coordination_enabled']:
        if type(count) is not int or not 1 <= count < context.get('capacity', 8):
            raise ValueError('Invalid additional-member threshold')
    elif count is not None:
        raise ValueError('Disabled coordination requires null threshold')
    if 'base_starts_at' in value:
        aligned(value['base_starts_at'])


def memo(value, *, preset=False):
    if value is None:
        return
    if len(value.encode('utf-8')) > 4096:
        raise ValueError('Memo byte limit')
    # Structural validation rejects control/linebreak characters before trim.
    whitespace = '\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'
    normalized = unicodedata.normalize('NFC', value).strip(whitespace)
    if preset and not normalized:
        raise ValueError('Preset cannot normalize to empty')
    # Deliberately no len() surrogate for extended grapheme segmentation.


def semantics(name, value, context):
    if name in ('BetaScheduleConfig', 'BetaScheduleTarget', 'BetaScheduleEditRequest'):
        config(value, context)
        if name == 'BetaScheduleEditRequest' and value['accept_immediate_confirmation'] != value['early_coordination_enabled']:
            raise ValueError('Explicit immediate-effect confirmation required for ON')
    if name == 'BetaCreateRequest':
        for target in value['beta_schedule_targets']:
            config(target, context)
        keys = [v['target_cycle_key'] for v in value['beta_schedule_targets']]
        expected = [value['target_cycle_key']]
        if value['target_cycle_key'] == value['expected_cycle_key'] and value['continuation']['enabled']:
            expected.append((datetime.fromisoformat(value['target_cycle_key']) + timedelta(days=7)).date().isoformat())
        if sorted(keys) != sorted(expected):
            raise ValueError('Creation targets must match actual C/N selection')
    if name in ('PresetPut', 'PresetDocument'):
        if len({v['id'] for v in value['items']}) != len(value['items']):
            raise ValueError('Duplicate preset ID')
        for item in value['items']:
            memo(item['text'], preset=True)
    if name == 'BetaApplyRequest':
        memo(value.get('application_memo'))
    if name == 'BetaSearchRequest':
        for interval in value.get('departure_windows', []):
            if not timedelta(0) < aligned(interval['ends_at']) - aligned(interval['starts_at']) <= timedelta(days=1):
                raise ValueError('Invalid filter interval')
    if name != 'BetaScheduleView':
        return
    config(value, context)
    start, end = aligned(value['base_starts_at']), aligned(value['base_ends_at'])
    if not timedelta(0) < end - start <= timedelta(days=1) or stamp(value['base_deadline_at']) != start - timedelta(minutes=30):
        raise ValueError('Invalid base promise')
    state = value['coordination_state']
    actual, actual_end = value['confirmed_starts_at'], value['confirmed_ends_at']
    if (actual is None) != (actual_end is None):
        raise ValueError('Confirmed interval must be present or absent together')
    confirmed = state in ('early_confirmed', 'base_confirmed', 'proposal_confirmed')
    if confirmed and actual is None or state in ('base_committed', 'coordinating', 'deadline_pending', 'needs_review') and actual is not None:
        raise ValueError('State/confirmed mismatch')
    effective, effective_end = (aligned(actual), aligned(actual_end)) if actual else (start, end)
    if effective_end <= effective:
        raise ValueError('Non-positive effective duration')
    if state == 'early_confirmed' and effective >= start:
        raise ValueError('Automatic coordination must be earlier')
    if state == 'base_confirmed' and (effective, effective_end) != (start, end):
        raise ValueError('Fallback must preserve base promise')
    if (stamp(value['effective_starts_at']), stamp(value['effective_ends_at'])) != (effective, effective_end):
        raise ValueError('Effective interval mismatch')
    if stamp(value['admission_deadline']) != effective - timedelta(minutes=30):
        raise ValueError('Admission cutoff mismatch')
    observed = stamp(value['evaluated_at'])
    pending = state in ('base_committed', 'coordinating', 'deadline_pending')
    due = pending and observed >= start - timedelta(minutes=30)
    status = 'due_unprocessed' if due else 'not_due' if pending else 'obsolete' if state in ('early_confirmed', 'proposal_confirmed', 'ended') else 'processed'
    transition = ('departure_review_due' if observed >= start else 'base_confirmation_due') if due else None
    if value['deadline_status'] != status or value['pending_transition'] != transition:
        raise ValueError('Due/persisted state confused')
    if (state == 'deadline_pending') != due:
        raise ValueError('Due views must use deadline_pending')
    if value['coordination_active'] != (state == 'coordinating' and not due):
        raise ValueError('Coordination active mismatch')
    if state == 'coordinating' and not value['early_coordination_enabled'] or state == 'base_committed' and value['early_coordination_enabled']:
        raise ValueError('Coordination configuration mismatch')
    if (value['review_reason'] is not None) != (state == 'needs_review'):
        raise ValueError('Review reason mismatch')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stdin', action='store_true')
    args = parser.parse_args()
    if args.stdin:
        payload = json.load(sys.stdin)
    else:
        root = Path(__file__).resolve().parents[5]
        folder = root / 'docs/features/recruitment/weekly-cycles/proposals'
        base = root / 'openapi/two-cycle.openapi.yaml'
        payload = {'schema': json.loads((folder/'beta-recruitment-v1.schema.json').read_text()),
                   'examples': json.loads((folder/'beta-recruitment-v1.examples.json').read_text()),
                   'base_sha256': hashlib.sha256(base.read_bytes()).hexdigest()}
    schema = payload['schema']
    Draft202012Validator.check_schema(schema)
    assert schema['x-base-openapi-sha256'] == payload['base_sha256'], 'Base contract changed; review proposal inheritance'
    counts = {True: 0, False: 0}
    for case in payload['examples']['cases']:
        valid = True
        try:
            Draft202012Validator({**schema, '$ref':'#/$defs/'+case['schema']}, format_checker=FormatChecker()).validate(case['value'])
            semantics(case['schema'], case['value'], case['context'])
        except (ValueError, ValidationError):
            valid = False
        assert valid == case['valid'], 'Unexpected proposal result: '+case['name']
        counts[valid] += 1
    print(json.dumps({'static_cases':sum(counts.values()),'accepted':counts[True],'rejected':counts[False],
        'components':len(schema['$defs']),'grapheme_vectors_not_executed':len(payload['examples']['grapheme_vectors']),
        'runtime_api_db_tests':False}))


if __name__ == '__main__':
    main()
