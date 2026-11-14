"""Validate policy2 proposal documents; never import app or touch a database."""
import json
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parent


def number(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 128:
        return None
    try:
        with localcontext() as ctx:
            ctx.prec = 128
            value = Decimal(raw)
            if not value.is_finite() or value < 0:
                return None
            if value == 0:
                return '0'
            if not -128 <= value.adjusted() <= 63:
                return None
            value = format(value.normalize(), 'f')
            return value if len(value) <= 64 else None
    except (ValueError, InvalidOperation):
        return None


def descending(raw):
    value = number(raw)
    return value is None, Decimal(value).copy_negate() if value is not None else 0


def selection_key(row):
    return (*descending(row['level']), *descending(row['power']),
            row['name'].encode('utf-16-be'), row['id'])


def select(items, existing=None, main_transition=False):
    candidates = [r for r in items if r['active'] and r['usable']]
    if not main_transition and existing in {r['id'] for r in candidates}:
        return existing
    return min(candidates, key=selection_key)['id'] if candidates else None


def rows_for(context):
    selected = set(context['data']['activity_character_ids'])
    return [dict(id=r['character_id'], name=r['character_name'],
                 level=r['item_level'], power=r['combat_power'],
                 active=r['character_id'] in selected, usable=r['usable'])
            for r in context['data']['characters']]


def check_context(value):
    data = value['data']
    rows = data['characters']
    ids = [r['character_id'] for r in rows]
    assert ids == data['ordered_all_character_ids'] and len(ids) == len(set(ids))
    for row in rows:
        assert row['usable'] == (row['blocked_reason'] is None)
        for field in ('item_level', 'combat_power'):
            observed_value = row[field]
            assert observed_value is None or number(observed_value) == observed_value
            assert (observed_value is None) == (row[field + '_observed_at'] is None)
    representative = data['representative_character_id']
    if not value_scope_main(value):
        assert representative is None
    if representative is not None:
        assert representative in {r['id'] for r in rows_for(value) if r['active'] and r['usable']}


def value_scope_main(value):
    return value['scope']['is_main']


def check_put(body, before):
    chosen = body['activity_character_ids']
    rows = {r['character_id']: r for r in before['data']['characters']}
    assert chosen and len(chosen) == len(set(chosen))
    assert all(cid in rows and rows[cid]['usable'] for cid in chosen)
    representative = body['representative_character_id']
    if before['scope']['is_main']:
        existing = before['data']['representative_character_id']
        assert existing is None or existing in chosen
        if representative is None:
            candidates = [dict(id=r['character_id'], name=r['character_name'],
                               level=r['item_level'], power=r['combat_power'],
                               active=r['character_id'] in chosen, usable=r['usable'])
                          for r in rows.values()]
            representative = select(candidates, existing)
        assert representative in chosen
        movable = set(chosen) - {representative}
    else:
        assert representative is None
        movable = set(chosen)
    if 'ordered_character_ids' in body:
        assert len(body['ordered_character_ids']) == len(movable)
        assert set(body['ordered_character_ids']) == movable
    return representative


def main():
    schema = json.loads((ROOT / 'schema.json').read_text())
    old = json.loads((ROOT.parent / 'schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    def validator(name, source=schema):
        return Draft202012Validator({'$ref': '#/$defs/' + name, '$defs': source['$defs']},
                                   format_checker=FormatChecker())
    examples = json.loads((ROOT / 'examples.json').read_text())
    count = 0
    for context in examples['contexts'].values():
        validator('Context').validate(context)
        check_context(context)
        count += 1
    contexts = examples['contexts']
    mapping = dict(main_keep_valid='main_valid', main_auto_fill='main_missing',
                   main_manual_select='main_valid', subordinate_all_movable='subordinate_raw_hidden',
                   first_selection='initial_unconfigured')
    for name, body in examples['puts'].items():
        validator('PutBody').validate(body)
        check_put(body, contexts[mapping[name]])
        count += 1
    for case in examples['transitions']:
        for field in ('before', 'ack', 'current_get'):
            if field in case:
                validator('Context').validate(case[field])
                check_context(case[field])
        if 'request' in case:
            validator('PutBody').validate(case['request'])
            representative = check_put(case['request'], case['before'])
            assert case['ack']['data']['representative_character_id'] == representative
            assert set(case['ack']['data']['activity_character_ids']) == set(case['request']['activity_character_ids'])
        if case['name'] == 'valid_existing_preserved':
            assert case['ack'] == case['before']
        if case['name'] == 'main_switch_atomic':
            assert case['current_get']['scope']['is_main']
            assert case['current_get']['data']['representative_character_id'] == select(rows_for(case['current_get']), main_transition=True)
            assert case['current_get']['data']['representative_character_id'] != case['stored_raw_before']
            assert case['old_main_registration_version_after'] == case['old_main_registration_version_before'] + 1
            assert not case['group_snapshot_changed']
        count += 1
    for case in examples['policy1_recovery']:
        assert case['business_reexecuted'] is False
        if 'original_body' in case:
            validator('PutBody', old).validate(case['original_body'])
            assert 'policy_version' not in case['original_body']
        if 'original_ack' in case:
            validator('Context', old).validate(case['original_ack'])
            assert list(validator('Context').iter_errors(case['original_ack']))
        if case['server_state'] == 'running_live':
            assert case['code'] == 'REQUEST_IN_PROGRESS' and case['retry_after'] == 2
        if case['server_state'] in ('running_expired', 'retryable', 'absent'):
            assert case['code'] == 'CONTRACT_POLICY_CHANGED'
        count += 1
    for case in examples['errors']:
        validator('Error').validate(case['body'])
        assert case['status'] == 409
        count += 1
    for case in examples['rejections']:
        if case['schema_rejection']:
            assert list(validator('PutBody').iter_errors(case['body']))
        else:
            validator('PutBody').validate(case['body'])
            try:
                check_put(case['body'], contexts[case['context']])
            except AssertionError:
                pass
            else:
                raise AssertionError(case['name'])
        count += 1
    fixtures = json.loads((ROOT / 'selection-fixtures.json').read_text())
    for case in fixtures['normalization']:
        assert number(case['raw']) == case['expected']
        count += 1
    for case in fixtures['cases']:
        assert select(case['items'], case.get('existing'), case.get('main_transition', False)) == case['expected']
        if 'expected_order' in case:
            assert [r['id'] for r in sorted(case['items'], key=selection_key)] == case['expected_order']
        count += 1
    print(json.dumps(dict(document_cases=count, schema='PASS', database_http_runtime_tests=False)))


if __name__ == '__main__':
    main()
