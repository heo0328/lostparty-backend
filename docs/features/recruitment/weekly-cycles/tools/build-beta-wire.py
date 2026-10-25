"""Build the review-only full wire bundle. Never imports or changes the server."""
import argparse
from copy import deepcopy
import hashlib
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
FOLDER = ROOT / 'docs/features/recruitment/weekly-cycles/proposals'
PROFILE = 'beta-recruitment-1'


def refs(value, prefix, replacement):
    if isinstance(value, dict):
        return {k: (v.replace(prefix, replacement) if k == '$ref' else refs(v, prefix, replacement)) for k, v in value.items()}
    if isinstance(value, list):
        return [refs(v, prefix, replacement) for v in value]
    return value


def ref(name):
    return {'$ref': '#/$defs/' + name}


def nullable(name):
    return {'anyOf': [ref(name), {'type': 'null'}]}


def build():
    source = FOLDER / 'beta-recruitment-v2.base-openapi.json.gz'
    source_bytes = gzip.decompress(source.read_bytes())
    base = json.loads(source_bytes)
    original = refs(base['components']['schemas'], '#/components/schemas/', '#/$defs/')
    proposed = json.loads((FOLDER/'beta-recruitment-v1.schema.json').read_text())['$defs']
    proposed = refs(proposed, '#/$defs/', '#/$defs/Proposed_')
    definitions = {**deepcopy(original), **{'Proposed_'+k: v for k, v in proposed.items()}}
    additions = {}

    def add(name, **fields):
        additions.setdefault(name, {}).update(fields)

    schedule = nullable('Proposed_BetaScheduleView')
    identity = nullable('Proposed_RecruitmentIdentity')
    memo = nullable('Proposed_MemoStored')
    for name in ['BCard', 'BDetail', 'ApplicationDisplayDetail', 'ResumePlanData', 'BTimeContext',
                 'AdmissionDisplayData', 'ContinuationDisplayData', 'BApplication', 'ApplicationDisplayItem',
                 'BApplicationView', 'BReview', 'BMembership', 'MembershipActionMembershipEntry',
                 'MembershipActionDetailProfileData', 'MembershipActionPlanProfileData']:
        add(name, beta_schedule=schedule)
    for name in ['BDetail', 'ApplicationDisplayDetail', 'ResumePlanData',
                 'MembershipActionDetailProfileData', 'MembershipActionPlanProfileData']:
        add(name, recruitment_identity=identity)
    for name in ['BApplication', 'ApplicationDisplayItem', 'BApplicationView', 'ApplicationDisplayOwnApplication']:
        add(name, application_memo=memo)
    for name in ['BSubmissionOut']:
        add(name, availability_copy=nullable('Proposed_AvailabilityCopyView'))
    add('BCreationContext', beta_schedule_targets={'type':'array','minItems':1,'maxItems':2,'items':ref('Proposed_BetaScheduleTarget')})
    add('OpeningDisplayData', beta_schedule_config=ref('Proposed_BetaScheduleConfig'))
    assert set(additions) <= set(original), set(additions) - set(original)

    # Clone every affected closed ancestor. Original schemas remain byte-for-byte
    # structural equivalents, so old ACKs and legacy DTOs never grow new keys.
    changed = set(additions)
    def names(value):
        if isinstance(value, dict):
            result = {value['$ref'].rsplit('/',1)[-1]} if '$ref' in value else set()
            for v in value.values(): result |= names(v)
            return result
        if isinstance(value, list):
            return set().union(*(names(v) for v in value)) if value else set()
        return set()
    while True:
        more = {n for n, s in original.items() if names(s) & changed}
        if more <= changed: break
        changed |= more

    def beta(value):
        if isinstance(value, dict):
            return {k: ('#/$defs/Beta_'+v.rsplit('/',1)[-1] if k == '$ref' and v.rsplit('/',1)[-1] in changed else beta(v)) for k,v in value.items()}
        if isinstance(value, list): return [beta(v) for v in value]
        return value
    for name in sorted(changed):
        schema = beta(deepcopy(original[name]))
        schema.setdefault('properties', {}).update(deepcopy(additions.get(name, {})))
        schema.setdefault('required', []).extend(additions.get(name, {}))
        definitions['Beta_'+name] = schema

    safe = {'reject','withdraw','continuation-declines','participation-cancellations','leadership-transfers',
            'formation','removals','common-settings','leave','end','personal-completion-departures',
            'member-removals','membership-actions','completion','personal-completion','completion-corrections',
            'manual-completion'}
    blocked = {'join','applications','approve','continuation-participations','recruitment-openings',
               'character-changes','availability-submission','schedule-groups','schedule-proposals',
               'responses','selections','participation-confirmations','settings'}
    inactive = {'weekly-incomplete-closures','weekly-resume-proposals'}
    overrides = {'POST /v2/raid-rooms':'BetaCreateRequest',
                 'POST /v2/raid-rooms/{room_id}/applications':'BetaApplyRequest',
                 'PUT /v2/raid-rooms/{room_id}/schedule-groups':'BetaScheduleEditRequest',
                 'POST /v2/raid-rooms/search':'BetaSearchRequest'}
    opened = deepcopy(original['Open'])
    opened['properties']['beta_schedule'] = ref('Proposed_BetaScheduleConfig')
    opened['required'].append('beta_schedule')
    definitions['BetaOpenRequest'] = opened
    operations = []
    for path, methods in base['paths'].items():
        related = path.startswith('/v2/') and ('raid-room' in path or 'raid-schedule' in path or 'raid-sessions/' in path or 'raid-rounds/' in path or '/raid-weekly-states/' in path)
        if not related: continue
        for method, raw in methods.items():
            if method not in ('get','post','put','delete','patch'): continue
            op = refs(deepcopy(raw), '#/components/schemas/', '#/$defs/')
            op['method'], op['path'] = method.upper(), path
            op['parameters'] = op.get('parameters', []) + [{'in':'query','name':'contract_profile','required':True,'schema':{'type':'string','const':PROFILE}}]
            name = op['method'] + ' ' + path
            leaf = path.rsplit('/',1)[-1]
            writing = method != 'get' and leaf != 'search'
            if not writing:
                op['responses'] = beta(op['responses'])
                op['x-old-client-on-beta-target'] = 'read_legacy_shape'
            else:
                policy = 'safe_management' if leaf in safe else 'inactive_preserved' if leaf in inactive else 'legacy_create_unchanged' if path == '/v2/raid-rooms' else 'blocked' if leaf in blocked else None
                assert policy, name
                op['x-old-client-on-beta-target'] = policy
                if name in overrides:
                    op['requestBody']['content']['application/json']['schema'] = ref('Proposed_'+overrides[name])
                elif leaf == 'recruitment-openings':
                    op['requestBody']['content']['application/json']['schema'] = ref('BetaOpenRequest')
                elif method == 'put' and leaf == 'availability-submission':
                    op['responses'] = beta(op['responses'])
            if name == 'POST /v2/raid-rooms/search':
                op['requestBody']['content']['application/json']['schema'] = ref('Proposed_BetaSearchRequest')
            if leaf == 'raid-room-creation-context' or leaf == 'opening-context':
                next_allowed = leaf == 'raid-room-creation-context'
                for prefix in ['', 'next_'] if next_allowed else ['']:
                    for key, rule in [('base_starts_at',{'type':'string','format':'date-time'}),
                                      ('early_coordination_enabled',{'type':'boolean'}),
                                      ('early_additional_members',{'type':'integer','minimum':1,'maximum':7})]:
                        op['parameters'].append({'name':prefix+key,'in':'query','required':not prefix and key!='early_additional_members','schema':rule})
            if name == 'GET /v2/raid-rooms':
                search = definitions['Proposed_BetaSearchRequest']['properties']
                for key in ['departure_windows','schedule_states']:
                    op['parameters'].append({'name':key,'in':'query','required':False,'content':{'application/json':{'schema':deepcopy(search[key])}}})
            op['x-beta-errors'] = {'400':['INVALID_REQUEST'], '409':[]}
            if writing:
                op['x-beta-errors']['409'] += ['CLIENT_UPGRADE_REQUIRED'] if op['x-old-client-on-beta-target']=='blocked' else []
                if leaf in {'schedule-groups','schedule-proposals','selections'}:
                    op['x-beta-errors']['409'] += ['BETA_SCHEDULE_REQUIRED','SCHEDULE_REVIEW_REQUIRED']
                if leaf == 'applications': op['x-beta-errors']['400'].append('APPLICATION_MEMO_TOO_LONG')
            operations.append(op)

    # New self-owned resource: intentionally does not take profile or actual T.
    template = next(o for o in operations if o['method']=='GET' and o['path']=='/v2/me/raid-room-applications')
    for method in ['GET','PUT']:
        op = {'method':method,'path':'/v2/me/application-message-presets','operationId':'beta_application_message_presets_'+method.lower(),
              'security':[{'HTTPBearer':[]}], 'parameters':[], 'responses':deepcopy(template['responses']),
              'x-old-client-on-beta-target':'not_target_scoped',
              'x-beta-errors':{'400':['INVALID_REQUEST','APPLICATION_MEMO_TOO_LONG','APPLICATION_PRESET_LIMIT_EXCEEDED'],
                               '409':['REVISION_CONFLICT','IDEMPOTENCY_CONFLICT','IDEMPOTENCY_EXPIRED','REQUEST_IN_PROGRESS']}}
        op['responses']['200']['content']['application/json']['schema'] = ref('Proposed_PresetStoredDocument')
        if method == 'PUT':
            op['parameters'].append({'name':'Idempotency-Key','in':'header','required':True,'schema':{'type':'string','format':'uuid','pattern':proposed['PresetItem']['properties']['id']['pattern']}})
            op['requestBody']={'required':True,'content':{'application/json':{'schema':ref('Proposed_PresetPut')}}}
        operations.append(op)
    stored = deepcopy(definitions['Proposed_PresetDocument'])
    stored_item = deepcopy(definitions['Proposed_PresetItem'])
    stored_item['properties']['text'] = ref('Proposed_MemoStored')
    definitions['Proposed_PresetStoredItem'] = stored_item
    stored['properties']['items']['items'] = ref('Proposed_PresetStoredItem')
    definitions['Proposed_PresetStoredDocument'] = stored
    # Retain only the complete transitive closure consumed by these operations.
    used = names(operations)
    while True:
        more = set().union(*(names(definitions[n]) for n in used))
        if more <= used: break
        used |= more
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','contract_version':'beta-recruitment-wire-2',
            'status':'review_only_not_runtime','profile':PROFILE,'base_openapi_sha256':hashlib.sha256(source_bytes).hexdigest(),
            'securitySchemes':deepcopy(base['components']['securitySchemes']),
            'operations':operations,'$defs':{n:definitions[n] for n in sorted(used)}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check',action='store_true');args=parser.parse_args()
    target = FOLDER/'beta-recruitment-v2.wire.json'
    data = json.dumps(build(),ensure_ascii=False,indent=2)+'\n'
    if args.check:
        assert target.read_text()==data, 'Stale beta wire: rebuild and review diff'
    else: target.write_text(data)
    print('Beta wire bundle '+('verified' if args.check else 'built'))


if __name__=='__main__': main()
