"""Validate review artifacts, not runtime HTTP or cryptographic implementation."""
from copy import deepcopy
import json
from pathlib import Path
from datetime import datetime
import re
from jsonschema import Draft202012Validator

if 'BUNDLE' in globals():
    api, examples = BUNDLE['api'], BUNDLE['examples']
else:
    root = Path(__file__).resolve().parents[1] / 'examples'
    api = json.loads((root / 'roster-participation-candidate.openapi.json').read_text())
    examples = json.loads((root / 'roster-participation-candidate.examples.json').read_text())

schemas = api['components']['schemas']
assert api['x-candidate-status'].startswith('unimplemented-review-only')
assert len(api['x-baseline-sha256']) == 64
for schema in schemas.values():
    Draft202012Validator.check_schema(schema)


def validate(name, value):
    schema = {'$ref': '#/components/schemas/' + name, 'components': api['components']}
    errors = list(Draft202012Validator(schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER).iter_errors(value))
    return errors


def semantic(case):
    """Backend fixture invariants; deliberately not a Dart parser substitute."""
    value = case['response']

    def numbers(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if child is not None and not isinstance(child, str) and (key.endswith(('_revision', '_generation', '_count', '_no'))
                        or key in ('revision', 'generation')):
                    assert type(child) is int, (key, child, type(child).__name__)
                numbers(child)
        elif isinstance(node, list):
            for child in node:
                numbers(child)
    numbers(value)
    if 'participation_context' not in value:
        if case.get('name', case.get('source')) == 'old_beta_list_one_restricted_item':
            for row in value['data']['items']:
                if row['content'] is not None:
                    content = row['content']
                    for key in ('room_id', 'room_cycle_id', 'target_generation', 'target_cycle_key', 'target_revision'):
                        assert content[key] == row['target'][key] == content['room'][key]
                    assert content['membership_id'] == row['viewer']['membership_id']
                    assert content['cycle_member_id'] == row['viewer']['cycle_member_id']
                    assert content['target_role'] == row['viewer']['role'] == content['room']['my_target_role']
        return
    ctx, data = value['participation_context'], value['data']
    actors = ctx.get('members', [ctx.get('actor')])
    for actor in actors:
        active, preserved = actor['active_assignments'], actor['preserved_assignments']
        ids = [a['assignment_id'] for a in active + preserved]
        assert len(ids) == len(set(ids))
        for key in ('target_cycle_key', 'room_cycle_id', 'target_generation'):
            scope = data['target'] if 'target' in data else value['scope']
            assert scope[key] == actor[key]
        assert (data['target']['room_id'] if 'target' in data else data['room_id']) == actor['room_id']
        assert actor['current_character']['character_id'] == active[0]['character_id']
    if 'content' in data:
        actor = actors[0]
        body = data['content']
        inner = body['data']
        catalog = {r['raid_id']: r for r in examples['catalog_fixture']['raids']}
        for key in ('items', 'game_items'):
            for item in inner['room'][key]:
                assert re.fullmatch(r'[a-z0-9_]{1,64}', item['raid_id'])
                raid = catalog[item['raid_id']]
                assert item['difficulty_id'] in raid['difficulties']
                assert item['game_party_size'] == raid['party_size']
        assert inner['room']['items'] == inner['room']['game_items']
        for key in ('target_cycle_key', 'room_cycle_id', 'target_generation', 'target_revision'):
            assert data['target'][key] == body['scope'][key] == inner['room'][key]
        assert data['target']['room_id'] == inner['room']['room_id']
        assert data['viewer']['role'] == inner['my_target_role'] == inner['room']['my_target_role']
        assert data['permissions']['view_detail']['allowed']
        assert inner['permissions']['view_detail']['allowed'] and inner['room']['permissions']['view_detail']['allowed']
        own = inner['my_membership']
        assert own['membership_id'] == data['viewer']['membership_id'] == actor['membership_id']
        assert own['cycle_member_id'] == data['viewer']['cycle_member_id'] == actor['cycle_member_id']
        for member in inner['members']:
            if member['cycle_member_id'] == actor['cycle_member_id']:
                assert member['character'] == actor['current_character']
                assert {a['assignment_id'] for a in member['assignments']} == {
                    a['assignment_id'] for a in actor['active_assignments'] + actor['preserved_assignments']}
        for issue in value['character_issue_context']['selected_target_issues']:
            selected = next(a for a in actors if a['cycle_member_id'] == issue['cycle_member_id'])
            for key in ('room_id', 'target_cycle_key', 'room_cycle_id', 'target_generation'):
                assert issue[key] == selected[key]
            active = {a['assignment_id']: a for a in selected['active_assignments']}
            assert set(issue['assignment_ids']) <= active.keys()
            assert all(active[i]['character_id'] == issue['character_id'] for i in issue['assignment_ids'])
    elif 'issued_at' in data:
        positive = case if 'query' in case else next(c for c in examples['examples'] if c['name'] == case['source'])
        assert positive['query']['include_session_display'] == 'true'
        assert data['expected_cycle_key'] == data['target_cycle_key'] == value['scope']['target_cycle_key']
        assert data['expected_target_revision'] == value['scope']['target_revision']
        parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
        assert parse(data['issued_at']) <= parse(value['scope']['server_now']) < parse(data['expires_at'])
        assert data['permissions']['change_character']['allowed']
        actor = ctx['actor']
        assert {(t['item_id'], t['round_id']) for t in data['targets']} == {
            (a['item_id'], a['round_id']) for a in actor['active_assignments']}
        display = data['session_display']
        assert display['kind'] == 'existing' and display['selection_mode'] == 'select_session_ids'
        assert display['plan_revision'] == data['plan_revision']
        assert {s['session_id'] for s in display['sessions']} == {
            s['session_id'] for s in data['session_choices']}
        for key in ('target_cycle_key', 'room_cycle_id', 'target_generation'):
            assert display[key] == actor[key]
    else:
        assert data['actor']['assignments'] == ctx['actor']['active_assignments']


for case in examples['examples']:
    errors = validate(case['component'], case['response'])
    assert not errors, (case['name'], [('/'.join(map(str, e.absolute_path)), e.message) for e in errors[:3]])
    semantic(case)
for case in examples['negative_examples']:
    assert validate(case['component'], case['response']), case['name']
for case in examples['semantic_negative_examples']:
    # These fixtures intentionally pass JSON Schema: the extra semantic layer
    # must catch what the previous schema-only validation missed.
    assert not validate(case['component'], case['response']), case['name']
    try:
        semantic(case)
    except (AssertionError, KeyError, ValueError):
        pass
    else:
        raise AssertionError(('semantic negative accepted', case['name']))

# Every generated component mapping resolves and no request repeats a query key.
for path, selectors in api['x-opt-in-response-map'].items():
    for selector in selectors:
        for component in selector.values():
            assert component in schemas, (path, component)
for item in api['paths'].values():
    for method, op in item.items():
        if method not in ('get', 'post', 'put', 'delete', 'patch'):
            continue
        names = [(p['name'], p['in']) for p in op.get('parameters', []) if '$ref' not in p]
        assert len(names) == len(set(names))

cases = {c['name']: c for c in examples['examples']}
page = cases['old_beta_list_one_restricted_item']['response']
restricted, normal = page['data']['items']
assert restricted['content'] is None
assert all(not p['allowed'] and p['reason'] == 'CLIENT_UPGRADE_REQUIRED'
           for p in restricted['permissions'].values())
assert normal['content'] is not None and normal['permissions']['view_plan']['allowed']
assert 'participation_context' not in page and 'character_issues' not in page

change = cases['new_profile_exact_active_and_preserved']['response']['actor']
m, p = change['active_assignments'], change['preserved_assignments']
assert m and len({v['assignment_id'] for v in m}) == len(m)
assert len({v['assignment_id'] for v in p}) == len(p)
assert not ({v['assignment_id'] for v in m} & {v['assignment_id'] for v in p})
assert change['current_character']['character_id'] == m[0]['character_id']
assert all(v['state'] != 'active' for v in p)
candidate = cases['full_new_candidates_empty_but_exact_actor']['response']
assert candidate['data']['actor']['assignments'] == m
preview = cases['full_new_beta_character_preview']['response']
assert {(v['item_id'], v['round_id']) for v in preview['data']['targets']} == {
    (v['item_id'], v['round_id']) for v in m}

# Bootstrap and the characters endpoint use identical DTOs and cache scope.
bootstrap = cases['bootstrap_presence_in_same_character_dto']['response']
characters = cases['characters_presence_same_scope']['response']
assert bootstrap['registrations'][0]['characters'] == characters
assert characters['roster_presence_scope']['roster_revision'] == characters['roster_revision']

print(json.dumps(dict(status='PASS', schema_components=len(schemas),
    positive_examples=len(examples['examples']), negative_examples=len(examples['negative_examples']),
    semantic_negative_examples=len(examples['semantic_negative_examples']),
    semantic_checks=['legacy item-only restriction', 'M/P disjointness and actor/preview target agreement',
        'bootstrap/characters identical presence scope', 'response component mapping and unique query parameters',
        'catalog raid/difficulty/party size', 'admission existing kind/selection mode/plan/session binding'],
    runtime_http_tests_executed=False, signature_cas_tests_executed=False), ensure_ascii=False))
