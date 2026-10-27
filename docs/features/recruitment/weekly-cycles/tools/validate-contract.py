"""Validate design contracts/fixtures only. Does not contact an API or database.

Run from the repository root with Python and jsonschema installed.
Optional --baseline diagnoses required/property contradictions in a prior file.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path('docs/features/recruitment/weekly-cycles/examples/baseline')


def schema_children(schema):
    for key in ('properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas'):
        for name, child in schema.get(key, {}).items():
            yield f'{key}/{name}', child
    for key in ('additionalProperties', 'unevaluatedProperties', 'items', 'contains', 'not', 'if', 'then', 'else', 'propertyNames'):
        if isinstance(schema.get(key), dict):
            yield key, schema[key]
    for key in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
        for i, child in enumerate(schema.get(key, [])):
            yield f'{key}/{i}', child


def closed_required_errors(schema, location):
    errors = []
    if not isinstance(schema, dict):
        return errors
    if schema.get('additionalProperties') is False:
        missing = set(schema.get('required', [])) - set(schema.get('properties', {}))
        if missing:
            errors.append(f'{location}: {sorted(missing)}')
    for name, child in schema_children(schema):
        errors.extend(closed_required_errors(child, location + '/' + name))
    return errors


def all_refs(document, value):
    if isinstance(value, dict):
        if '$ref' in value:
            assert value['$ref'].startswith('#/'), value['$ref']
            target = document
            for part in value['$ref'][2:].split('/'):
                target = target[part.replace('~1', '/').replace('~0', '~')]
        for child in value.values():
            all_refs(document, child)
    elif isinstance(value, list):
        for child in value:
            all_refs(document, child)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    document = json.loads((ROOT / 'full.openapi.json').read_text(encoding='utf-8'))
    fixtures = json.loads((ROOT / 'contract-examples.json').read_text(encoding='utf-8'))
    schemas = document['components']['schemas']
    structural_errors = []
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        structural_errors.extend(closed_required_errors(schema, name))
    assert not structural_errors, structural_errors
    # Check schema annotations separately from property names/instance payloads.
    tree = ast.parse(Path('docs/features/recruitment/weekly-cycles/tools/build-contract.py').read_text(encoding='utf-8'))
    cleaner = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'clean')
    namespace = {}
    exec(compile(ast.Module(body=[cleaner], type_ignores=[]), '<schema-cleaner-check>', 'exec'), namespace)
    probe = {'type': 'object', 'title': 'annotation', 'properties': {
        'title': {'type': 'string', 'title': 'field annotation'},
        'default': {'type': 'string'}, 'description': {'type': 'string'}},
        'default': {'title': 'instance default'}, 'examples': [{'title': 'instance example'}]}
    namespace['clean'](probe)
    assert 'title' not in probe and 'title' in probe['properties']
    assert 'title' not in probe['properties']['title']
    assert probe['default']['title'] == 'instance default'
    assert probe['examples'][0]['title'] == 'instance example'
    all_refs(document, document)
    operations = []
    for path, methods in document['paths'].items():
        for method, operation in methods.items():
            operations.append(operation['operationId'])
            params = operation.get('parameters', [])
            assert len(params) == len({(p['in'], p['name']) for p in params}), path
            assert set(re.findall(r'\{(\w+)\}', path)) == {p['name'] for p in params if p['in'] == 'path'}, path
            assert all(p['required'] for p in params if p['in'] == 'path'), path
            if method == 'get' and not path.endswith(('/raid-cycles', '/raid-room-filter-context', '/common-context')):
                assert any(p['name'] == 'target_cycle_key' and p['required'] for p in params), path
            if method in ('post', 'put') and not path.endswith(('/search', 'raid-weekly-summary')):
                assert any(p['name'] == 'Idempotency-Key' and p['required'] for p in params), path
    assert len(operations) == len(set(operations))
    for name in ('Input_contract3_post__v2_raid-rooms', 'CommonSettingsCommand', 'B_Card'):
        assert 'title' in schemas[name]['properties'] and 'title' in schemas[name]['required'], name
    for suffix in ('leave', 'end'):
        body = document['paths']['/v2/raid-rooms/{room_id}/' + suffix]['post']['requestBody']['content']['application/json']['schema']
        assert body == {'$ref': '#/components/schemas/GlobalMembershipCommand'}
    expected_global = {'expected_cycle_key', 'expected_room_revision', 'expected_persistent_membership_revision', 'context_token'}
    assert set(schemas['GlobalMembershipCommand']['required']) == expected_global
    registry = Registry().with_resource('urn:lostparty:contract4', Resource.from_contents(document, default_specification=DRAFT202012))
    by_name = {case['name']: case for case in fixtures['cases']}
    assert len(by_name) == len(fixtures['cases'])
    for case in fixtures['cases']:
        validator = Draft202012Validator({'$ref': 'urn:lostparty:contract4#/components/schemas/' + case['schema']}, registry=registry,
                                        format_checker=Draft202012Validator.FORMAT_CHECKER)
        errors = list(validator.iter_errors(case['value']))
        assert (not errors) == case['schema_valid'], (case['name'], [error.message for error in errors])
    for pair in fixtures['cas_bindings']:
        context = by_name[pair['context_case']]['value']['data']
        request = by_name[pair['request_case']]['value']
        assert set(request) == expected_global
        for field, source in pair['mapping'].items():
            assert request[field] == context[source], (pair['request_case'], field)
    # Resolve the endpoint schemas, so a detached correct component cannot hide a stale route.
    common_path = '/v2/raid-rooms/{room_id}/common-settings'
    common_op = document['paths'][common_path]['put']
    response_schema = common_op['responses']['200']['content']['application/json']['schema']
    assert response_schema == {'$ref': '#/components/schemas/CommonSettingsAck'}
    def check_endpoint(schema, value):
        # Resolve local component references relative to the full contract resource.
        validator = Draft202012Validator({'$ref': 'urn:lostparty:contract4' + schema['$ref']}, registry=registry,
                                        format_checker=Draft202012Validator.FORMAT_CHECKER)
        validator.validate(value)
    flows = fixtures['common_settings_flows']
    assert len(flows) == 2
    for flow in flows:
        ctx = by_name[flow['context_case']]['value']
        req = by_name[flow['request_case']]['value']
        ack = by_name[flow['response_case']]['value']
        context_schema = document['paths']['/v2/me/raid-rooms/{room_id}/common-context']['get']['responses']['200']['content']['application/json']['schema']
        check_endpoint(context_schema, ctx)
        check_endpoint(common_op['requestBody']['content']['application/json']['schema'], req)
        check_endpoint(response_schema, ack)
        for field, source in {'expected_cycle_key': 'expected_cycle_key', 'expected_room_revision': 'room_revision', 'context_token': 'context_token'}.items():
            assert req[field] == ctx['data'][source]
        assert req['expected_group_revision'] == ctx['data']['current_settings']['group_revision']
        assert req['group_id'] == ctx['data']['current_settings']['group_id']
        affected = [cycle['target_cycle_key'] for cycle in ctx['data']['impact_cycles']]
        assert ack['data']['affected_cycle_keys'] == affected
        assert ack['data']['room_id'] == ctx['data']['room_id']
        assert ack['data']['room_revision'] == req['expected_room_revision'] + 1
        assert ctx['data']['authorization_cycle_key'] == affected[0]
    assert [by_name[f['response_case']]['value']['data']['affected_cycle_keys'] for f in flows] == [['2026-10-21', '2026-10-28'], ['2026-10-28']]
    for case in fixtures['cases']:
        if case.get('replay_of'):
            assert case['value'] == by_name[case['replay_of']]['value']
    baseline_count = None
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
        errors = []
        for name, schema in baseline['components']['schemas'].items():
            errors.extend(closed_required_errors(schema, name))
        baseline_count = len(errors)
        print('Baseline closed-object required/property contradictions:', baseline_count)
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    summary = dict(paths=len(document['paths']), operations=len(operations), schemas=len(schemas),
                   fixtures=len(fixtures['cases']), cas_bindings=len(fixtures['cas_bindings']), common_settings_endpoint_flows=len(flows),
                   canonical_sha256=hashlib.sha256(canonical).hexdigest(), baseline_contradictions=baseline_count,
                   runtime_tests_executed=False)
    print(json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    main()
