#!/usr/bin/env python3
"""Validate authored proposal2 vectors, never the runtime evaluator or a DB."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

BASE = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((BASE / 'examples/candidate-contract-v2.schema.json').read_text())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
DUAL = {'바드', '발키리', '도화가', '홀리나이트'}


def validate(response, query):
    VALIDATOR.validate(response)
    scope, data = response['scope'], response['data']
    assert query['target_cycle_key'] == scope['target_cycle_key']
    assert query['intent'] == data['intent']
    assert data['evaluated_at'] == scope['server_now']
    assert data['eligible_candidate_count'] <= data['raw_candidate_count']
    assert len(data['items']) <= min(query['limit'], data['eligible_candidate_count'])
    assert 1 <= query['limit'] <= 100
    summary = data['exclusion_summary']
    assert len({(v['reason'], v['detail']) for v in summary}) == len(summary)
    assert sum(v['character_count'] for v in summary) == data['raw_candidate_count'] - data['eligible_candidate_count']
    identifiers = [v['character_id'] for v in data['items']]
    assert identifiers == sorted(set(identifiers))
    if query['cursor'] is None and data['next_cursor'] is None:
        assert len(identifiers) == data['eligible_candidate_count']
    if data['eligible_candidate_count'] == 0:
        assert data['next_cursor'] is None and not identifiers
    if data['actor'] is not None:
        assignments = data['actor']['assignments']
        assert len({v['assignment_id'] for v in assignments}) == len(assignments)
        item_ids = [v['item_id'] for v in assignments]
        assert item_ids == sorted(set(item_ids))
    for item in data['items']:
        assert any(v['allowed'] for v in item['roles'].values())
        for name, role in item['roles'].items():
            supported = name == 'dealer' or item['class_name'] in DUAL
            assert role['supported'] == supported
            comparison = role['comparison']
            if not supported:
                assert not role['allowed'] and role['reason'] == 'ROLE_NOT_SUPPORTED' and comparison is None
                continue
            assert comparison['selected_role'] == name
            actual, minimum = comparison['actual'], comparison['requirement']
            if minimum is None:
                expected = 'unrestricted'
            elif actual is None:
                expected = 'missing'
            else:
                expected = 'meets' if Decimal(actual) >= Decimal(minimum) else 'below'
            assert comparison['state'] == expected
            evidence = ('success_summary_version', 'observed_at', 'success_saved_at')
            assert all((comparison[k] is not None) == (actual is not None) for k in evidence)
            if role['allowed']:
                assert role['reason'] is None and expected in ('unrestricted', 'meets')
            if role['reason'] == 'COMBAT_POWER_REQUIRED':
                assert expected in ('missing', 'below')
    return True


def validate_pages(cases):
    first = cases[0]['response']['data']
    key_fields = ('room_id', 'intent', 'eligibility_policy_version', 'actor', 'catalog_version', 'snapshot_token',
                  'raw_candidate_count', 'eligible_candidate_count', 'exclusion_summary')
    identifiers = []
    previous_cursor = None
    previous_scope = None
    for index, case in enumerate(cases):
        data, scope = case['response']['data'], case['response']['scope']
        assert all(data[k] == first[k] for k in key_fields)
        context = {k: v for k, v in scope.items() if k != 'server_now'}
        if previous_scope is not None:
            assert context == previous_scope
        assert case['query']['cursor'] == previous_cursor
        previous_scope = context
        identifiers.extend(v['character_id'] for v in data['items'])
        previous_cursor = data['next_cursor']
        assert (previous_cursor is None) == (index == len(cases) - 1)
    assert identifiers == sorted(set(identifiers))
    assert len(identifiers) == first['eligible_candidate_count']


def main():
    cases = json.loads((BASE / 'examples/candidate-contract-v2.examples.json').read_text())['examples']
    for case in cases:
        validate(case['response'], case['query'])
    pages = [v for v in cases if v.get('pagination_group') == 'three-candidates']
    validate_pages(pages)
    original, query = cases[0]['response'], cases[0]['query']
    mutants = []
    def mutate(fn):
        value = deepcopy(original)
        fn(value)
        mutants.append(value)
    mutate(lambda x: x['data'].update(unknown=True))
    mutate(lambda x: x['data'].pop('actor'))
    mutate(lambda x: x['data'].update(intent='change_character'))
    mutate(lambda x: x['data'].update(eligible_candidate_count=2))
    mutate(lambda x: x['data'].update(raw_candidate_count=2))
    mutate(lambda x: x['data']['items'][0]['roles']['support'].update(supported=True, allowed=True, reason=None,
        comparison=deepcopy(x['data']['items'][0]['roles']['dealer']['comparison'])))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer'].update(allowed=False, reason='ROOM_FULL'))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer'].update(reason='ROOM_FULL'))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer']['comparison'].update(selected_role='support'))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer']['comparison'].update(state='missing'))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer']['comparison'].update(actual='99.999999999999999999999999999', state='below'))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer']['comparison'].update(observed_at=None))
    mutate(lambda x: x['data'].update(next_cursor='x' * 2049))
    mutate(lambda x: x['scope'].update(target_generation=None))
    mutate(lambda x: x['data']['items'].append(deepcopy(x['data']['items'][0])))
    mutate(lambda x: x['data']['items'][0]['roles']['dealer'].update(supported='true'))
    for mutant in mutants:
        try:
            validate(mutant, query)
        except (AssertionError, ValidationError):
            pass
        else:
            raise AssertionError('Invalid authored vector was accepted')
    invalid_pages = deepcopy(pages)
    invalid_pages[-1]['response']['data']['snapshot_token'] = 'c' * 64
    try:
        validate_pages(invalid_pages)
    except AssertionError:
        pass
    else:
        raise AssertionError('Mixed snapshot pages accepted')
    print(json.dumps(dict(authored_examples=len(cases), invalid_response_vectors=len(mutants),
        pagination_groups=1, mixed_snapshot_rejected=True, runtime_api_or_database_tests=False)))


if __name__ == '__main__':
    main()
