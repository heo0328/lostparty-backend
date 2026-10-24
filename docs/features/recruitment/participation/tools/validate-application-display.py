#!/usr/bin/env python3
"""Validate authored display proposal vectors; never call runtime APIs or a DB."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

BASE = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((BASE / 'examples/application-display-v1.schema.json').read_text())
EXAMPLES = json.loads((BASE / 'examples/application-display-v1.examples.json').read_text())['examples']
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def validate(case):
    response, kind = case['response'], case['kind']
    VALIDATOR.validate(response)
    root = {'page': 'ApplicationDisplayPageResponse', 'detail': 'ApplicationDisplayDetailResponse', 'error': 'Error'}[kind]
    VALIDATOR.evolve(schema={'$ref': '#/$defs/' + root, '$defs': SCHEMA['$defs']}).validate(response)
    assert case['query']['reader_profile'] == 'application-display-1'
    if kind == 'error':
        assert case['status'] in (400, 401, 403, 404, 409, 413, 503)
        return
    assert case['status'] == 200
    scope, data = response['scope'], response['data']
    assert scope['target_cycle_key'] == case['query']['target_cycle_key']
    if kind == 'detail':
        assert data['room']['target_cycle_key'] == scope['target_cycle_key']
        assert data['room']['target_generation'] == scope['target_generation']
        assert data['room']['room_cycle_id'] == scope['room_cycle_id']
        assert data['access']['evaluated_at'] == scope['server_now']
        own = data['my_application']
        if own is not None and own['state'] == 'pending':
            assert stamp(own['expires_at']) > stamp(scope['server_now'])
        return
    assert data['evaluated_at'] == scope['server_now']
    assert len(data['items']) <= case['query']['limit'] <= 50
    assert len({item['application_id'] for item in data['items']}) == len(data['items'])
    for item in data['items']:
        assert item['target_cycle_key'] == scope['target_cycle_key']
        assert item['target_generation'] == scope['target_generation']
        comparison, analysis = item['comparison'], item['analysis']
        if item['display_reason'] is not None:
            assert comparison is None and analysis is None
            continue
        assert comparison is not None
        assert comparison['selected_role'] == item['selected_role']
        actual, minimum = comparison['actual'], comparison['requirement']
        expected = ('unrestricted' if minimum is None else 'missing' if actual is None else
                    'meets' if Decimal(actual) >= Decimal(minimum) else 'below')
        assert comparison['state'] == expected
        for field in ('success_summary_version', 'observed_at', 'success_saved_at'):
            assert (comparison[field] is None) == (actual is None)
        if actual is None:
            assert comparison['success_issues'] == [] and comparison['power_revision'] == 1
        if analysis is None:
            assert comparison['current_summary_version'] == 1 and comparison['current_issues'] == []
        else:
            assert analysis['version'] == comparison['current_summary_version']
            assert analysis['issues'] == comparison['current_issues']
            pairs = [(v['code'], v['severity']) for v in analysis['issues']]
            assert len(pairs) == len(set(pairs))
            errors = any(v['severity'] == 'error' for v in analysis['issues'])
            state = analysis['integrity_status']
            assert not (state == 'clean' and pairs)
            assert not (state == 'review' and (not pairs or errors))
            assert not (state == 'error' and not errors)
            assert not (state == 'unavailable' and errors)


def main():
    # Existing copied components stay equal to the source contract; this does
    # not modify the runtime contract or validate any HTTP implementation.
    runtime = json.loads((BASE.parents[3] / 'openapi/two-cycle.openapi.yaml').read_text())
    def refs(value):
        if isinstance(value, dict):
            return {k: v.replace('#/components/schemas/', '#/$defs/') if k == '$ref' else refs(v) for k, v in value.items()}
        if isinstance(value, list):
            return [refs(v) for v in value]
        return value
    for name, definition in SCHEMA['$defs'].items():
        if not name.startswith('ApplicationDisplay'):
            assert definition == refs(runtime['components']['schemas'][name]), name
    for case in EXAMPLES:
        validate(case)
    page = next(c for c in EXAMPLES if c['name'] == 'role_success_precision')
    detail = next(c for c in EXAMPLES if c['name'] == 'detail_pending')
    mutations = []
    def bad(source, change):
        value = deepcopy(source)
        change(value['response'])
        mutations.append(value)
    bad(page, lambda r: r['data']['items'][0].pop('analysis'))
    bad(page, lambda r: r['data']['items'][0].update(approve_allowed=True))
    bad(page, lambda r: r['data']['items'][0]['comparison'].update(selected_role='support'))
    bad(page, lambda r: r['data']['items'][0]['comparison'].update(state='below'))
    bad(page, lambda r: r['data']['items'][0].update(display_reason='ROOM_FULL'))
    bad(page, lambda r: r['data']['items'][0].update(display_reason='APPLICATION_CONTEXT_CHANGED'))
    bad(page, lambda r: r['data']['items'][0]['analysis'].update(version=99))
    bad(page, lambda r: r['data']['items'][0]['analysis'].update(integrity_status='error'))
    bad(page, lambda r: r['data']['items'][0]['comparison'].update(observed_at=None))
    bad(page, lambda r: r['data'].update(evaluated_at='2026-10-24T12:01:00Z'))
    bad(detail, lambda r: r['data'].pop('my_application'))
    bad(detail, lambda r: r['data']['my_application'].update(expires_at=r['scope']['server_now']))
    bad(detail, lambda r: r['data']['my_application'].update(state='participating'))
    bad(detail, lambda r: r['data']['my_application'].update(user_id='00000000-0000-0000-0000-000000000001'))
    bad(detail, lambda r: r['data']['room'].update(target_generation=2))
    rejected = 0
    for value in mutations:
        try:
            validate(value)
        except (ValidationError, AssertionError):
            rejected += 1
        else:
            raise AssertionError('Invalid authored vector accepted')
    print(json.dumps(dict(authored_examples=len(EXAMPLES), invalid_vectors_rejected=rejected,
                         copied_components_preserved=True, runtime_api_db_tests_executed=False)))


if __name__ == '__main__':
    main()
