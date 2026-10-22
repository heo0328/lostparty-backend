"""Validate proposal wire examples only; no server, provider or database access.

Run from the repository root: python3 docs/design/validate_issue13_group_character_candidates.py
Requires jsonschema. Does not validate runtime authorization or pagination SQL.
"""
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


PATH = Path('docs/design/issue13-group-character-candidates.draft.openapi.json')
DOC = json.loads(PATH.read_text())
URI = 'urn:lostparty:group-character-candidates:draft1'
RESOURCE = Resource.from_contents(DOC, default_specification=DRAFT202012)
REGISTRY = Registry().with_resource(URI, RESOURCE)


def validator(name):
    return Draft202012Validator(
        {'$ref': URI + '#/components/schemas/' + name},
        registry=REGISTRY, format_checker=FormatChecker())


def check_refs(value):
    if isinstance(value, dict):
        if '$ref' in value:
            reference = value['$ref']
            assert reference.startswith('#/'), reference
            resolved = DOC
            for key in reference[2:].split('/'):
                resolved = resolved[key.replace('~1', '/').replace('~0', '~')]
        for child in value.values():
            check_refs(child)
    elif isinstance(value, list):
        for child in value:
            check_refs(child)


def check_closed_shapes(value):
    if isinstance(value, dict):
        if value.get('additionalProperties') is False:
            assert set(value.get('required', [])) <= set(value.get('properties', {}))
        for child in value.values():
            check_closed_shapes(child)
    elif isinstance(value, list):
        for child in value:
            check_closed_shapes(child)


def main():
    assert DOC['x-status'] == 'proposal-not-implemented'
    assert len(DOC['paths']) == 1
    check_refs(DOC)
    check_closed_shapes(DOC)
    for schema in DOC['components']['schemas'].values():
        Draft202012Validator.check_schema(schema)
    operation = next(iter(DOC['paths'].values()))['get']
    examples = operation['responses']['200']['content']['application/json']['examples']
    page_validator = validator('CandidatePage')
    for example in examples.values():
        page_validator.validate(example['value'])

    # Negative wire cases: required/null semantics, identity/secret formats,
    # accidental raw identifiers and inconsistent absent source metadata.
    original = examples['single_member']['value']
    invalid = []
    sample = copy.deepcopy(original)
    del sample['candidate_token']
    invalid.append(sample)
    sample = copy.deepcopy(original)
    sample['groups'][0]['user_id'] = 'must-not-be-public'
    invalid.append(sample)
    sample = copy.deepcopy(original)
    sample['candidate_token'] = 'invalid'
    invalid.append(sample)
    sample = copy.deepcopy(original)
    sample['groups'][0]['characters'][0]['character_id'] = 'not-a-uuid'
    invalid.append(sample)
    sample = copy.deepcopy(original)
    sample['groups'][0]['characters'][0]['dealer']['value'] = None
    invalid.append(sample)
    sample = copy.deepcopy(examples['unknown_values']['value'])
    sample['groups'][0]['characters'][0]['item_level_source'] = 'stored_character_summary'
    invalid.append(sample)
    sample = copy.deepcopy(examples['zero_candidates']['value'])
    sample['groups'][0]['continues_on_next'] = True
    invalid.append(sample)
    sample = copy.deepcopy(original)
    sample['groups'][0]['characters'][0]['role_family'] = 'support'
    invalid.append(sample)
    for sample in invalid:
        assert list(page_validator.iter_errors(sample)), 'Invalid fixture unexpectedly accepted'

    binding = validator('SearchCandidateBinding')
    binding.validate({})
    binding.validate({'group_character_candidates_token': 'd' * 64})
    assert list(binding.iter_errors({'group_character_candidates_token': None}))
    assert list(binding.iter_errors({'group_character_candidates_token': 'e' * 63}))
    print(f'Draft only: schemas/refs/closed shapes OK; {len(examples)} response examples, '
          f'{len(invalid)} rejection cases, 4 search-binding cases PASS. '
          'No API/DB/provider tests executed.')


if __name__ == '__main__':
    main()
