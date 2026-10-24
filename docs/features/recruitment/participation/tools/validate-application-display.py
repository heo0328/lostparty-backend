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


def validate_detail_references(response):
    """Check current placement links; historical rounds need not be current."""
    data, scope = response['data'], response['scope']
    room = data['room']
    items = {i['item_id']: i for i in room['items']}
    assert len(items) == len(room['items']), 'Duplicate room item'
    games = {i['item_id']: i for i in room['game_items']}
    assert len(games) == len(room['game_items']) and games == items, 'Room/game item mismatch'
    rounds = {i['round_id']: i for i in items.values()}
    assert len(rounds) == len(items), 'Duplicate current round'
    members = {m['cycle_member_id']: m for m in data['members'] if m['cycle_member_id'] is not None}
    assert len(members) == sum(m['cycle_member_id'] is not None for m in data['members']), 'Duplicate cycle member'
    assignments = {}
    for member in data['members']:
        for assignment in member['assignments']:
            assert assignment['assignment_id'] not in assignments, 'Duplicate assignment'
            assignments[assignment['assignment_id']] = (member, assignment)
            assert assignment['item_id'] in items, 'Assignment references missing room item'
            item = items[assignment['item_id']]
            if assignment['state'] != 'completed':
                assert assignment['round_id'] == item['round_id'], 'Current assignment round mismatch'
                assert assignment['party_no'] <= min(room['app_capacity'], item['game_party_size']) // 4
    coordinates = set()
    placed = set()
    leader = data['leadership']
    assert room['leadership'] == leader, 'Leadership projections disagree'
    if leader['leader_cycle_member_id'] is not None:
        assert leader['leader_cycle_member_id'] in members, 'Leader references missing cycle member'
        assert members[leader['leader_cycle_member_id']]['membership_id'] == leader['leader_membership_id']
    mine = data['my_membership']
    if mine is not None and mine['cycle_member_id'] is not None:
        assert mine['cycle_member_id'] in members, 'Own participation references missing cycle member'
        member = members[mine['cycle_member_id']]
        assert member['membership_id'] == mine['membership_id'] and member['is_me'], 'Own participation mismatch'
    assert data['my_target_role'] == room['my_target_role'], 'Own role projections disagree'
    for slot in data['formation_slots']:
        assert slot['target_cycle_key'] == scope['target_cycle_key'], 'Formation target mismatch'
        assert slot['round_id'] in rounds, 'Formation references missing current round'
        coordinate = (slot['round_id'], slot['party_no'], slot['slot_no'])
        assert coordinate not in coordinates, 'Duplicate formation position'
        coordinates.add(coordinate)
        item = rounds[slot['round_id']]
        assert slot['party_no'] <= min(room['app_capacity'], item['game_party_size']) // 4
        aid = slot['assignment_id']
        if aid is None:
            assert slot['status'] == 'empty' and not slot['is_leader'], 'Empty formation mismatch'
            continue
        assert aid in assignments and aid not in placed, 'Formation assignment missing or duplicated'
        placed.add(aid)
        member, assignment = assignments[aid]
        assert assignment['state'] == 'active' and slot['status'] == 'participating'
        assert coordinate == (assignment['round_id'], assignment['party_no'], assignment['slot_no']), 'Formation placement mismatch'
        assert slot['is_leader'] == (member['cycle_member_id'] == leader['leader_cycle_member_id'])
    for slot in data['formation_history']:
        assert slot['target_cycle_key'] == scope['target_cycle_key']
        # A completed round can precede the item's current round. Never require
        # its UUID to equal the current round or resurrect a departed member.
        if slot['assignment_id'] in assignments:
            _, assignment = assignments[slot['assignment_id']]
            assert assignment['state'] == 'completed'
            assert (slot['round_id'], slot['party_no'], slot['slot_no']) == (
                assignment['round_id'], assignment['party_no'], assignment['slot_no'])


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
        validate_detail_references(response)
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
    bad(detail, lambda r: r['data']['room'].update(items=[]))
    bad(detail, lambda r: r['data']['room'].update(game_items=[]))
    bad(detail, lambda r: r['data']['room']['items'].append(deepcopy(r['data']['room']['items'][0])))
    bad(detail, lambda r: r['data']['members'][0]['assignments'][0].update(round_id='00000000-0000-0000-0000-000000000099'))
    bad(detail, lambda r: r['data']['formation_slots'][0].update(round_id='00000000-0000-0000-0000-000000000099'))
    bad(detail, lambda r: r['data']['formation_slots'][0].update(assignment_id='00000000-0000-0000-0000-000000000099'))
    bad(detail, lambda r: r['data']['formation_slots'][0].update(slot_no=2))
    bad(detail, lambda r: r['data']['leadership'].update(leader_membership_id='00000000-0000-0000-0000-000000000099'))
    rejected = 0
    for value in mutations:
        try:
            validate(value)
        except (ValidationError, AssertionError):
            rejected += 1
        else:
            raise AssertionError('Invalid authored vector accepted')
    originals = json.loads((BASE / 'examples/application-display-v1.invalid-examples.json').read_text())['examples']
    for case in originals:
        VALIDATOR.validate(case['response'])  # the old structural check alone was insufficient
        try:
            validate_detail_references(case['response'])
        except AssertionError:
            pass
        else:
            raise AssertionError('Original inconsistent detail accepted')
    print(json.dumps(dict(authored_examples=len(EXAMPLES), invalid_vectors_rejected=rejected,
                         original_invalid_details_rejected=len(originals),
                         copied_components_preserved=True, runtime_api_db_tests_executed=False)))


if __name__ == '__main__':
    main()
