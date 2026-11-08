"""Build a review-only OpenAPI candidate; never modifies executable contracts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parents[1] / 'examples'
baseline = (ROOT / 'openapi/two-cycle.openapi.yaml').read_bytes()
frozen = OUT / 'roster-participation-candidate.openapi.json'
if frozen.exists():
    expected = json.loads(frozen.read_text()).get('x-baseline-sha256')
    if expected and hashlib.sha256(baseline).hexdigest() != expected:
        raise SystemExit('Frozen review baseline differs from executable OpenAPI; preserve accepted artifacts. Use the implementation contract/tests for current behavior.')
api = json.loads(baseline)
api['info'] = dict(title='Issue17 review-only contract candidate', version='roster-participation-1.candidate')
api['x-candidate-status'] = 'unimplemented-review-only; Native acceptance and executable API checks pending'
api['x-baseline-sha256'] = hashlib.sha256(baseline).hexdigest()
schemas = api['components']['schemas']


def ref(name):
    return {'$ref': '#/components/schemas/' + name}


def obj(properties):
    return dict(type='object', additionalProperties=False, properties=properties, required=list(properties))


def null(value):
    return {'anyOf': [value, {'type': 'null'}]}


def array(value, minimum=0, maximum=200):
    return dict(type='array', items=value, minItems=minimum, maxItems=maximum)


UUID = dict(type='string', format='uuid')
TIME = dict(type='string', format='date-time')
KEY = dict(type='string', format='date')
REV = dict(type='integer', minimum=1, maximum=2147483647)
COUNT = dict(type='integer', minimum=0, maximum=2147483647)
BOOL = dict(type='boolean')
HASH = dict(type='string', pattern='^[0-9a-f]{64}$')
PROFILE = dict(type='string', const='roster-character-issues-1')
PART = dict(type='string', const='remaining-active-1')
schemas['RosterIssueOwnCycle'] = obj(dict(target_cycle_key=KEY, has_issues=BOOL, affected_room_count=COUNT))
schemas['RosterIssueSummary'] = obj(dict(profile=PROFILE, current_cycle_key=KEY, next_cycle_key=KEY,
    has_issues=BOOL, affected_room_count=COUNT, affected_target_count=COUNT,
    cycles=array(ref('RosterIssueOwnCycle'), 2, 2), evaluated_at=TIME, issues_revision=HASH))
schemas['RosterIssueTargetSummary'] = obj(dict(target_cycle_key=KEY,
    state=dict(type='string', enum=['ready', 'not_authorized']), has_issues=null(BOOL),
    affected_participant_count=null(COUNT)))
schemas['RosterIssueTargetSummary']['allOf'] = [
    {'if': {'properties': {'state': {'const': 'not_authorized'}}},
     'then': {'properties': {'has_issues': {'type': 'null'}, 'affected_participant_count': {'type': 'null'}}},
     'else': {'properties': {'has_issues': BOOL, 'affected_participant_count': COUNT}}}]
schemas['RosterCharacterIssue'] = obj(dict(code=dict(type='string', const='ROSTER_CHARACTER_MISSING'),
    room_id=UUID, target_cycle_key=KEY, room_cycle_id=UUID, target_generation=REV,
    cycle_member_id=UUID, character_id=UUID, character_name=null(dict(type='string', maxLength=64)),
    assignment_ids=dict(**array(UUID, 1, 200), uniqueItems=True), observed_at=TIME, registration_id=null(UUID)))
schemas['RosterIssuePage'] = obj(dict(profile=PROFILE, evaluated_at=TIME, issues_revision=HASH,
    items=array(ref('RosterCharacterIssue'), 0, 10000)))
schemas['RosterIssueRoomContext'] = obj(dict(profile=PROFILE, evaluated_at=TIME, issues_revision=HASH,
    target_summaries=array(ref('RosterIssueTargetSummary'), 2, 2),
    selected_target_issues=null(array(ref('RosterCharacterIssue'), 0, 10000))))
schemas['RosterPresence'] = obj(dict(state=dict(type='string', enum=['present', 'missing', 'unknown']),
    observed_at=null(TIME)))
schemas['RosterPresence']['allOf'] = [
    {'if': {'properties': {'state': {'const': 'unknown'}}},
     'then': {'properties': {'observed_at': {'type': 'null'}}},
     'else': {'properties': {'observed_at': TIME}}}]
schemas['RosterPresenceScope'] = obj(dict(profile=dict(type='string', const='roster-presence-1'),
    registration_id=UUID, registration_version=REV, ownership_revision=null(REV), roster_revision=REV,
    presence_revision=HASH, evaluated_at=TIME))

active = obj(dict(assignment_id=UUID, revision=REV, item_id=UUID, round_id=UUID, character_id=UUID,
    selected_role=dict(type='string', enum=['dealer', 'support']), party_no=dict(type='integer', minimum=1, maximum=2),
    slot_no=dict(type='integer', minimum=1, maximum=4)))
schemas['RosterActiveAssignment'] = active
schemas['RosterPreservedAssignment'] = deepcopy(active)
schemas['RosterPreservedAssignment']['properties']['state'] = dict(type='string', enum=[
    'completed', 'stopped_incomplete', 'left', 'legacy_ended'])
schemas['RosterPreservedAssignment']['required'].append('state')
schemas['RosterCurrentCharacter'] = obj(dict(character_id=UUID,
    selected_role=dict(type='string', enum=['dealer', 'support']),
    display=obj(dict(server_name=null(dict(type='string', maxLength=64)),
        character_name=null(dict(type='string', maxLength=64)), class_name=null(dict(type='string', maxLength=64))))))
schemas['RosterParticipationMember'] = obj(dict(room_id=UUID, target_cycle_key=KEY, room_cycle_id=UUID,
    target_generation=REV, membership_id=UUID, cycle_member_id=UUID, cycle_member_revision=REV,
    active_assignments=array(ref('RosterActiveAssignment')), preserved_assignments=array(ref('RosterPreservedAssignment')),
    current_character=null(ref('RosterCurrentCharacter')), binding_revision=HASH))
schemas['RosterParticipationChangeContext'] = obj(dict(profile=PART,
    actor=ref('RosterParticipationMember'), evaluated_at=TIME))
schemas['RosterParticipationReadContext'] = obj(dict(profile=PART, evaluated_at=TIME,
    members=array(ref('RosterParticipationMember'), 0, 400)))


def extend(name, prefix, fields):
    target = prefix + name
    value = deepcopy(schemas[name])
    value['title'] = target
    value.setdefault('properties', {}).update(fields)
    value['required'] = list(dict.fromkeys([*value.get('required', []), *fields]))
    schemas[target] = value
    return target


def parameter(name, values):
    return dict(name=name, **{'in': 'query'}, required=False,
        schema=dict(type='string', enum=values),
        description='Review-only opt-in. Absent preserves legacy shape; declaration is not authorization.')


maps = {}
for path, item in api['paths'].items():
    if path.startswith('/v2/') and ('raid-rooms' in path or 'raid-room-' in path):
        for method, op in item.items():
            if method not in ('get', 'post', 'put', 'delete', 'patch'):
                continue
            op.setdefault('parameters', []).append(parameter('participation_profile', ['remaining-active-1']))
            op['x-roster-participation-policy'] = 'Target-generation capability; original ACK replay precedes new execution checks.'
    if 'get' not in item:
        continue
    op = item['get']
    warn = path.endswith('/raid-room-memberships') or path.endswith('/detail') or path.endswith('/plan')
    change = path.endswith('/admission-character-candidates') or path.endswith('/admission-context')
    if not warn and not change:
        continue
    response = op['responses']['200']['content']['application/json']['schema']
    originals = response.get('anyOf', [response])
    branches = deepcopy(originals)
    selection = []
    for branch in originals:
        if '$ref' not in branch:
            continue
        name = branch['$ref'].rsplit('/', 1)[1]
        ptype = 'RosterParticipationChangeContext' if change else 'RosterParticipationReadContext'
        pn = extend(name, 'Participation_', {'participation_context': ref(ptype)})
        branches.append(ref(pn)); selection.append(dict(base=name, participation=pn))
        if warn:
            field = 'character_issues' if path.endswith('/raid-room-memberships') else 'character_issue_context'
            kind = 'RosterIssuePage' if field == 'character_issues' else 'RosterIssueRoomContext'
            wn = extend(name, 'RosterIssues_', {field: ref(kind)})
            both = extend(pn, 'RosterIssues_', {field: ref(kind)})
            branches.extend([ref(wn), ref(both)])
            selection[-1].update(warnings=wn, both=both)
    op['responses']['200']['content']['application/json']['schema'] = {'anyOf': branches}
    if warn:
        op.setdefault('parameters', []).append(parameter('include_character_issues', ['true', 'false']))
    maps[path] = selection

char = extend('LifecycleCharacterOut', 'RosterPresence_', {'roster_presence': ref('RosterPresence')})
chars = extend('LifecycleCharactersOut', 'RosterPresence_', {'roster_presence_scope': ref('RosterPresenceScope')})
schemas[chars]['properties']['items']['items'] = ref(char)
registration = deepcopy(schemas['BootstrapRegistration'])
registration['properties']['characters'] = ref(chars)
registration['title'] = 'RosterPresence_BootstrapRegistration'
schemas['RosterPresence_BootstrapRegistration'] = registration
boot = deepcopy(schemas['AccountBootstrap'])
boot['properties']['registrations']['items'] = ref('RosterPresence_BootstrapRegistration')
boot['title'] = 'RosterPresence_AccountBootstrap'
schemas['RosterPresence_AccountBootstrap'] = boot
for path, base, enhanced in [('/v2/me/account-bootstrap', 'AccountBootstrap', 'RosterPresence_AccountBootstrap'),
        ('/v2/me/game-accounts/{registration_id}/characters', 'LifecycleCharactersOut', chars)]:
    op = api['paths'][path]['get']
    op.setdefault('parameters', []).append(parameter('include_roster_presence', ['true', 'false']))
    op['responses']['200']['content']['application/json']['schema'] = {'anyOf': [ref(base), ref(enhanced)]}
    maps[path] = [dict(base=base, presence=enhanced)]
api['paths']['/v2/me/raid-room-character-issues'] = {'get': dict(
    operationId='roster_character_issue_summary_candidate', tags=['review-only'],
    security=[{'HTTPBearer': []}], responses={
        '200': {'description': 'Own C/N confirmed-missing issue summary', 'content': {
            'application/json': {'schema': ref('RosterIssueSummary')}}},
        **{str(code): {'description': 'Existing error boundary', 'content': {
            'application/json': {'schema': ref('GameErrorOut')}}} for code in (400, 401, 403, 409, 503)}
    })}
api['x-opt-in-response-map'] = maps


def example(schema):
    if '$ref' in schema:
        return example(schemas[schema['$ref'].rsplit('/', 1)[1]])
    if 'const' in schema:
        return deepcopy(schema['const'])
    if 'enum' in schema:
        return deepcopy(schema['enum'][0])
    if 'anyOf' in schema or 'oneOf' in schema:
        choices = schema.get('anyOf', schema.get('oneOf'))
        return example(next((v for v in choices if v.get('type') == 'null'), choices[0]))
    kind = schema.get('type')
    if kind == 'object' or 'properties' in schema:
        return {k: example(schema['properties'][k]) for k in schema.get('required', [])}
    if kind == 'array':
        return [example(schema['items']) for _ in range(schema.get('minItems', 0))]
    if kind == 'null':
        return None
    if kind == 'boolean':
        return False
    if kind == 'integer':
        return int(schema.get('minimum', 0))
    if kind == 'number':
        return schema.get('minimum', 0)
    if schema.get('format') == 'uuid':
        return str(uuid.UUID(int=1, version=4))
    if schema.get('format') == 'date-time':
        return '2026-11-08T10:00:00Z'
    if schema.get('format') == 'date':
        return '2026-11-04'
    pattern = schema.get('pattern', '')
    if '[0-9a-f]' in pattern:
        return 'a' * 64
    if '[0-9]' in pattern or '[1-9]' in pattern:
        return '1'
    return 'sample'[:schema.get('maxLength', 64)].ljust(schema.get('minLength', 0), 'x')


def uid(n):
    return str(uuid.UUID(int=n, version=4))


cases = []


def add(name, component, response, *, path, status=200, query=None, notes=''):
    cases.append(dict(name=name, path=path, method='get', query=query or {}, status=status,
        component=component, response=response, notes=notes))


summary = example(ref('RosterIssueSummary'))
summary.update(next_cycle_key='2026-11-11', cycles=[
    dict(target_cycle_key=k, has_issues=False, affected_room_count=0) for k in ('2026-11-04', '2026-11-11')])
add('own_summary_normal_zero', 'RosterIssueSummary', summary, path='/v2/me/raid-room-character-issues')
context = dict(profile='roster-character-issues-1', evaluated_at='2026-11-08T10:00:00Z', issues_revision='a'*64,
    target_summaries=[dict(target_cycle_key='2026-11-04', state='ready', has_issues=True, affected_participant_count=1),
        dict(target_cycle_key='2026-11-11', state='not_authorized', has_issues=None, affected_participant_count=None)],
    selected_target_issues=[])
issue = example(ref('RosterCharacterIssue'))
issue.update(room_id=uid(10), room_cycle_id=uid(20), cycle_member_id=uid(30), character_id=uid(40),
    character_name='옛캐릭터', assignment_ids=[uid(50)], registration_id=None)
context['selected_target_issues'] = [issue]
add('room_other_member_missing_opposite_unauthorized', 'RosterIssueRoomContext', context,
    path='/v2/raid-rooms/{room_id}/detail', query=dict(include_character_issues='true'),
    notes='Exact root character_issue_context fragment; not a complete HTTP envelope.')

# A complete legacy-shaped beta membership page, including one restricted item.
page = example(ref('Beta_MembershipActionMembershipPage'))
entry_name = schemas['Beta_MembershipActionMembershipPageData']['properties']['items']['items']['$ref'].rsplit('/', 1)[1]
restricted = example(ref(entry_name))
restricted['target'].update(room_id=uid(10), room_cycle_id=uid(20), target_generation=1,
    target_revision=5, target_state='open', generation_state='open')
restricted['viewer'].update(cycle_member_id=uid(30), cycle_member_revision=3,
    cycle_member_state='participating', role='none', mode='recovery')
restricted['recovery'].update(state='unverified', reason='CLIENT_UPGRADE_REQUIRED', revision=None,
    remaining_review_reasons=['CLIENT_UPGRADE_REQUIRED'], menu_access=False)
for permission in [*restricted['permissions'].values(), restricted['recovery']['can_request_recovery']]:
    permission.update(allowed=False, reason='CLIENT_UPGRADE_REQUIRED', next_change_at=None)
restricted['content'] = None
normal = deepcopy(restricted)
normal['target'].update(room_id=uid(11), room_cycle_id=uid(21))
normal['viewer'].update(cycle_member_id=uid(31), role='member', mode='participant')
normal['recovery'].update(state='none', reason=None, remaining_review_reasons=[])
normal['content'] = example(ref('Beta_BMembership'))
normal['content'].update(room_id=uid(11), membership_id=normal['viewer']['membership_id'],
    cycle_member_id=uid(31), cycle_member_revision=3, room_cycle_id=uid(21), target_generation=1,
    target_revision=5, recovery_only=False, history_only=False, target_role='member',
    target_participation_state='participating')
for name in ('view_detail', 'view_plan'):
    normal['permissions'][name].update(allowed=True, reason=None)
normal['content']['permissions']['view_plan'].update(allowed=True, reason=None)
page['group_policy_version'] = 'cycle-group-policy-1'
page['data'].update(items=[restricted, normal], next_cursor=None, membership_head=5)
add('old_beta_list_one_restricted_item', 'Beta_MembershipActionMembershipPage', page,
    path='/v2/me/raid-room-memberships', query=dict(reader_profile='membership-actions-1',
        contract_profile='beta-recruitment-1', group_policy_version='cycle-group-policy-1', target_cycle_key='2026-11-04'),
    notes='Full legacy DTO; no new fields. Capability restriction is projection only, not persisted room/member review.')

actor = example(ref('RosterParticipationMember'))
m = example(ref('RosterActiveAssignment'))
m.update(assignment_id=uid(51), item_id=uid(61), round_id=uid(71), character_id=uid(41))
p = dict(example(ref('RosterPreservedAssignment')), assignment_id=uid(50), item_id=uid(60), round_id=uid(70),
    character_id=uid(40), state='completed')
actor.update(room_id=uid(10), room_cycle_id=uid(20), cycle_member_id=uid(30),
    active_assignments=[m], preserved_assignments=[p], current_character=dict(character_id=uid(41),
        selected_role='dealer', display=dict(server_name='예시', character_name='새캐릭터', class_name='예시직업')))
change = dict(profile='remaining-active-1', actor=actor, evaluated_at='2026-11-08T10:00:00Z')
add('new_profile_exact_active_and_preserved', 'RosterParticipationChangeContext', change,
    path='/v2/raid-rooms/{room_id}/admission-context', query=dict(intent='change_character',
        participation_profile='remaining-active-1'), notes='Exact participation_context fragment; actor.assignments/targets/POST must equal M.')

# Complete wire envelopes: metadata is root-level, never inserted into beta data.
detail_name = 'RosterIssues_Participation_Beta_MembershipActionDetailProfile'
detail = example(ref(detail_name))
detail['group_policy_version'] = 'cycle-group-policy-1'
detail['data']['content'] = example(ref('Beta_OutputContract3GetV2RaidRoomsRoomIdDetail'))
detail['data']['target'].update(room_id=uid(10), room_cycle_id=uid(20), target_generation=1,
    target_state='open', generation_state='open')
detail['data']['viewer'].update(membership_id=actor['membership_id'], cycle_member_id=uid(30),
    cycle_member_revision=actor['cycle_member_revision'], mode='participant', role='member', cycle_member_state='participating')
detail['character_issue_context'] = deepcopy(context)
detail['participation_context'] = dict(profile='remaining-active-1', evaluated_at=change['evaluated_at'], members=[actor])
add('full_new_beta_detail_both_opt_ins', detail_name, detail, path='/v2/raid-rooms/{room_id}/detail',
    query=dict(reader_profile='membership-actions-1', contract_profile='beta-recruitment-1',
        group_policy_version='cycle-group-policy-1', include_character_issues='true',
        participation_profile='remaining-active-1', target_cycle_key='2026-11-04'),
    notes='Full response; validate this declared component before extracting the two known metadata roots.')
preview_name = 'Participation_Beta_AdmissionDisplayContext'
preview = example(ref(preview_name))
preview['group_policy_version'] = 'cycle-group-policy-1'
preview['participation_context'] = deepcopy(change)
preview['data']['targets'] = [dict(item_id=m['item_id'], round_id=m['round_id'], party_no=m['party_no'],
    expected_round_revision=1, expected_weekly_revision=1)]
preview['data']['selection']['character_id'] = uid(42)
add('full_new_beta_character_preview', preview_name, preview, path='/v2/raid-rooms/{room_id}/admission-context',
    query=dict(intent='change_character', contract_profile='beta-recruitment-1',
        group_policy_version='cycle-group-policy-1', participation_profile='remaining-active-1',
        target_cycle_key='2026-11-04', character_id=uid(42), selected_role='dealer', include_session_display='true'),
    notes='Full preview shape; replace only actor.active_assignments. The context token shown is synthetic, not executable.')
candidate_name = 'Participation_AdmissionCandidatePage'
candidate = example(ref(candidate_name))
candidate['participation_context'] = deepcopy(change)
candidate['data'].update(room_id=uid(10), intent='change_character',
    actor=dict(membership_id=actor['membership_id'], cycle_member_id=actor['cycle_member_id'],
        cycle_member_revision=actor['cycle_member_revision'], assignments=[m]),
    raw_candidate_count=0, eligible_candidate_count=0, items=[], exclusion_summary=[])
add('full_new_candidates_empty_but_exact_actor', candidate_name, candidate,
    path='/v2/raid-rooms/{room_id}/admission-character-candidates',
    query=dict(intent='change_character', participation_profile='remaining-active-1', target_cycle_key='2026-11-04'),
    notes='Independent empty-candidate snapshot; not permission to submit the separate preview fixture.')

legacy_examples = json.loads((ROOT / 'docs/features/recruitment/membership-actions/examples/membership-actions-contract.json').read_text())['examples']
record = deepcopy(next(v['value'] for v in legacy_examples if v['name'] == 'ended_completed_plan'))
add('original_record_reader_without_participation_profile', 'MembershipActionPlanProfile', record,
    path='/v2/me/raid-rooms/{room_id}/plan', query=dict(reader_profile='membership-actions-1'),
    notes='Historical record remains per-assignment; no active-current-character assertion.')
ack = example(ref('OutputContract3PostV2RaidRoomsRoomIdJoin'))
add('stored_original_ack_replay', 'OutputContract3PostV2RaidRoomsRoomIdJoin', ack,
    path='/v2/raid-rooms/{room_id}/character-changes',
    notes='Stored minimal ACK bytes replay unchanged; no new metadata or capability requirement.')
cases[-1]['method'] = 'post'

bootstrap_cases = json.loads((ROOT / 'docs/features/rosters/bootstrap/examples/account-bootstrap.json').read_text())
boot_sample = deepcopy(bootstrap_cases['owned_activity_defaults'])
if 'response' in boot_sample:
    boot_sample = boot_sample['response']
if 'value' in boot_sample:
    boot_sample = boot_sample['value']
for bundle in boot_sample['registrations']:
    values = bundle['characters']
    values['roster_presence_scope'] = dict(profile='roster-presence-1', registration_id=values['registration_id'],
        registration_version=values['registration_version'], ownership_revision=values['ownership_revision'],
        roster_revision=values['roster_revision'], presence_revision='b'*64, evaluated_at=boot_sample['server_now'])
    for char in values['items']:
        char['roster_presence'] = dict(state='unknown', observed_at=None)
add('bootstrap_presence_in_same_character_dto', 'RosterPresence_AccountBootstrap', boot_sample,
    path='/v2/me/account-bootstrap', query=dict(include_roster_presence='true'))
add('characters_presence_same_scope', chars, deepcopy(boot_sample['registrations'][0]['characters']),
    path='/v2/me/game-accounts/{registration_id}/characters', query=dict(include_roster_presence='true'))

error = example(ref('GameErrorOut'))
error['error'].update(code='CLIENT_UPGRADE_REQUIRED', message='Client upgrade required')
add('old_profile_mixed_detail_rejected', 'GameErrorOut', error,
    path='/v2/raid-rooms/{room_id}/detail', status=409)

# Semantic fixtures use the existing serializer layout, not schema-minimum values
# as evidence of a valid read. Keep the base strict DTOs unchanged.
leadership = dict(leader_cycle_member_id=actor['cycle_member_id'],
    leader_membership_id=actor['membership_id'], leadership_revision=1)


def target_scope(value, actual=actor):
    value.update(target_cycle_key=actual['target_cycle_key'], room_cycle_id=actual['room_cycle_id'],
        target_generation=actual['target_generation'], target_revision=5)
    if 'playable_from' in value:
        value['playable_from'] = '2026-11-04T01:00:00Z'


def readable(permissions):
    for name, value in permissions.items():
        value.update(allowed=name in ('view_detail', 'view_plan', 'read_action_menu'),
            reason=None if name in ('view_detail', 'view_plan', 'read_action_menu') else 'RECRUITMENT_COMMAND_NOT_READY',
            next_change_at=None)


target_scope(detail['data']['target'])
detail['data']['target']['leadership'] = deepcopy(leadership)
detail['data']['viewer'].update(role='leader', joined_order='1')
readable(detail['data']['permissions'])
body = detail['data']['content']
target_scope(body['scope'])
room = body['data']['room']
room.update(room_id=actor['room_id'], revision=1, app_member_count=1,
    room_cycle_id=actor['room_cycle_id'], target_cycle_key=actor['target_cycle_key'],
    target_generation=1, target_revision=5, my_target_role='leader', leadership=deepcopy(leadership))
room['schedule_summary']['mode'] = 'unscheduled'
readable(room['permissions'])
body['data'].update(my_target_role='leader', leadership=deepcopy(leadership))
body['data']['access'].update(state='allowed', policy_snapshot='a'*64)
readable(body['data']['permissions'])
member = example(ref('BRoomMember'))
member.update(membership_id=actor['membership_id'], revision=1, group_member=False,
    character=deepcopy(actor['current_character']), is_me=True, status='valid', status_reason=None,
    target_role='leader', cycle_member_id=actor['cycle_member_id'], cycle_member_revision=1,
    joined_order='1', target_state='participating', assignments=[dict(
        assignment_id=v['assignment_id'], item_id=v['item_id'], round_id=v['round_id'],
        state='active' if v is m else 'completed', party_no=v['party_no'], slot_no=v['slot_no']) for v in (m,p)])
body['data']['members'] = [member]
body['data']['my_membership'] = {k: member[k] for k in schemas['BAppRaidRoomsAdmissionSchemasMyMembership']['required']}
body['data']['room']['game_items'] = []
catalog = json.loads((ROOT / 'app/raids/catalog.json').read_text())
catalog_items = [('serca', 'normal'), ('horizon_cathedral', 'stage1')]
for v, (raid_id, difficulty_id) in zip((m,p), catalog_items):
    item = example(ref('BCardItem'))
    item.update(item_id=v['item_id'], round_id=v['round_id'], raid_id=raid_id,
        difficulty_id=difficulty_id, game_party_size=4)
    body['data']['room']['game_items'].append(item)
room['items'] = deepcopy(room['game_items'])
# This full detail represents the viewer's current missing character, not P.
full_issue = detail['character_issue_context']['selected_target_issues'][0]
full_issue.update(character_id=m['character_id'], character_name=actor['current_character']['display']['character_name'],
    assignment_ids=[m['assignment_id']], registration_id=uid(1))

target_scope(preview['scope'])
preview['data'].update(room_id=actor['room_id'], expected_cycle_key=actor['target_cycle_key'],
    expected_target_revision=5, catalog_version=catalog['catalog_version'], policy_snapshot='a'*64,
    context_token='v1.'+'a'*64, expires_at='2026-11-08T10:05:00Z', leadership=deepcopy(leadership),
    permissions=dict(change_character=dict(allowed=True, reason=None, next_change_at=None)))
preview['data']['session_display'] = dict(kind='existing', selection_mode='select_session_ids',
    target_cycle_key=actor['target_cycle_key'], room_cycle_id=actor['room_cycle_id'],
    target_generation=1, display_revision='c'*64, plan_revision=1, sessions=[], previews=[])
target_scope(candidate['scope'])
candidate['data']['catalog_version'] = catalog['catalog_version']
# The empty-candidate case is an independent source snapshot.

# An unrelated normal list row remains a genuinely readable live membership.
normal_entry = page['data']['items'][1]
normal_body = normal_entry['content']
normal_body.update(ended_at=None, joined_order='1', cycle_member_revision=3)
normal_body['room'] = deepcopy(room)
normal_body['room'].update(room_id=uid(11), room_cycle_id=uid(21), my_target_role='member', app_member_count=2)
normal_leader = dict(leader_cycle_member_id=uid(101), leader_membership_id=uid(102), leadership_revision=1)
normal_body['room']['leadership'] = deepcopy(normal_leader)
normal_entry['target']['leadership'] = deepcopy(normal_leader)
normal_entry['viewer']['joined_order'] = '1'
readable(normal_entry['permissions'])
normal_assignment = example(ref('BOwnAssignment'))
normal_assignment.update(assignment_id=uid(151), item_id=m['item_id'], round_id=m['round_id'],
    character_id=uid(141), cycle_member_id=uid(31), state='active')
normal_body['assignments'] = [normal_assignment]
ack['scope'].update(room_cycle_id=actor['room_cycle_id'], target_generation=1, target_revision=5)
ack['data'].update(room_id=actor['room_id'])

manifest = dict(status='unimplemented-review-only', examples=cases,
    semantic_rules=['M/P disjoint and revision-bound', 'C/N authorization independent',
        'opaque revision equality only', 'explicit unknown is not healthy',
        'stored original ACK is returned without adding opt-in metadata'])
manifest['negative_examples'] = [
    dict(name='unauthorized_is_not_false_zero', component='RosterIssueTargetSummary',
        response=dict(target_cycle_key='2026-11-11', state='not_authorized', has_issues=False, affected_participant_count=0)),
    dict(name='unknown_presence_has_no_observation', component='RosterPresence',
        response=dict(state='unknown', observed_at='2026-11-08T10:00:00Z')),
    dict(name='legacy_ack_must_not_acquire_metadata', component='OutputContract3PostV2RaidRoomsRoomIdJoin',
        response=dict(ack, participation_context=change)),
]
manifest['semantic_negative_examples'] = []


def reject(name, source, pointer, value):
    bad = deepcopy(next(c for c in cases if c['name'] == source))
    parent = bad['response']
    parts = pointer.split('/')
    for key in parts[:-1]:
        parent = parent[int(key)] if isinstance(parent, list) else parent[key]
    parent[parts[-1]] = value
    manifest['semantic_negative_examples'].append(dict(name=name, source=source,
        component=bad['component'], response=bad['response']))


dn = 'full_new_beta_detail_both_opt_ins'
pn = 'full_new_beta_character_preview'
reject('completed_P_is_not_action_warning', dn,
    'character_issue_context/selected_target_issues/0/assignment_ids', [p['assignment_id']])
reject('nested_room_mismatch', dn, 'data/content/data/room/room_id', uid(999))
reject('nested_generation_mismatch', dn, 'data/content/scope/target_generation', 2)
reject('successful_detail_read_denied', dn, 'data/permissions/view_detail/allowed', False)
reject('viewer_role_mismatch', dn, 'data/content/data/my_target_role', 'member')
reject('double_revision_is_not_Dart_int', 'old_beta_list_one_restricted_item',
    'data/items/0/viewer/membership_revision', 1.0)
reject('preview_room_mismatch', pn, 'data/room_id', uid(999))
reject('preview_invalid_cycle', pn, 'data/expected_cycle_key', 'sample')
reject('preview_not_future_expiry', pn, 'data/expires_at', preview['data']['issued_at'])
reject('preview_command_permission_missing', pn, 'data/permissions', {})
reject('detail_invalid_raid_identifier', dn, 'data/content/data/room/items/0/raid_id', 'synthetic-3d')
reject('detail_unknown_catalog_raid', dn, 'data/content/data/room/items/0/raid_id', 'unknown_raid')
reject('admission_none_is_not_existing', pn, 'data/session_display',
    dict(preview['data']['session_display'], kind='none', selection_mode='no_session_selection'))
reject('admission_display_plan_mismatch', pn, 'data/session_display/plan_revision', 2)
manifest['catalog_fixture'] = dict(version=catalog['catalog_version'], raids=[
    dict(raid_id=r['raid_id'], party_size=r['party_size'], difficulties=[d['difficulty_id'] for d in r['difficulties']])
    for r in catalog['raids']])
OUT.mkdir(parents=True, exist_ok=True)
for name, data in [('roster-participation-candidate.openapi.json', api), ('roster-participation-candidate.examples.json', manifest)]:
    path = OUT / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(name, hashlib.sha256(path.read_bytes()).hexdigest())
