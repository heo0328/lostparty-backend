"""Validate complete review fixtures, inheritance and metadata boundaries; no HTTP/DB."""
import argparse
from copy import deepcopy
import hashlib
import gzip
import json
from pathlib import Path
import re
import sys
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT=Path(__file__).resolve().parents[5]
FOLDER=ROOT/'docs/features/recruitment/weekly-cycles/proposals'
UUID='00000000-0000-4000-8000-000000000001'


def validator(bundle, schema):
    return Draft202012Validator({'$defs':bundle['$defs'],**schema},format_checker=FormatChecker())


def sample(bundle, schema, depth=0):
    assert depth<60, 'Recursive example requires an explicit fixture'
    if '$ref' in schema: return sample(bundle,bundle['$defs'][schema['$ref'].split('/')[-1]],depth+1)
    if 'const' in schema:return schema['const']
    if 'enum' in schema:return schema['enum'][0]
    if 'anyOf' in schema or 'oneOf' in schema:
        choices=schema.get('anyOf',schema.get('oneOf'))
        choice=next((v for v in choices if v.get('type')=='null'),choices[0])
        return sample(bundle,choice,depth+1)
    t=schema.get('type')
    if t=='null':return None
    if t=='boolean':return False
    if t in ('number','integer'):return schema.get('minimum',0)
    if t=='array':return [sample(bundle,schema['items'],depth+1) for _ in range(schema.get('minItems',0))]
    if t=='object' or 'properties' in schema:
        return {k:sample(bundle,schema['properties'][k],depth+1) for k in schema.get('required',[])}
    if t=='string':
        f=schema.get('format')
        if f=='uuid':return UUID
        if f=='date':return '2026-10-21'
        if f=='date-time':return '2026-10-23T00:00:00Z'
        candidates=['가','sample','1','00001','0'*64,'2026-10-21','0'*schema.get('minLength',1)]
        for v in candidates:
            if len(v)<schema.get('minLength',0) or len(v)>schema.get('maxLength',100000):continue
            if 'pattern' not in schema or re.search(schema['pattern'],v):return v
        raise AssertionError('Need explicit string sample: '+str(schema))
    return {}


def cases(bundle):
    result=[]
    error_seen=set()
    for index,op in enumerate(bundle['operations']):
        label=op['method']+' '+op['path']
        params={p['in']+':'+p['name']:sample(bundle,p.get('schema') or p['content']['application/json']['schema']) for p in op['parameters'] if p.get('required')}
        for key,value in list(params.items()):
            if key=='query:items':params[key]='[{"raid_id":"sample-raid","difficulty_id":"normal"}]'
            elif key in ('query:group_ids','query:room_ids'):params[key]=UUID if key.endswith('room_ids') else json.dumps([UUID])
        body=op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema')
        if body:
            result.append({'name':label+' request','operation':index,'kind':'request','parameters':params,'value':sample(bundle,body)})
        for status,response in op['responses'].items():
            schema=response.get('content',{}).get('application/json',{}).get('schema')
            if not schema:continue
            if not status.startswith('2'):
                if status in error_seen:continue
                error_seen.add(status)
            variants=schema.get('anyOf',[schema]) if status.startswith('2') else [schema]
            for variant in variants:
                value=sample(bundle,variant)
                if not status.startswith('2'):
                    value['error']['code']={'400':'INVALID_REQUEST','401':'ACCESS_INVALID','403':'ROOM_LEADER_REQUIRED','404':'ROOM_NOT_FOUND','409':'REVISION_CONFLICT','413':'REQUEST_TOO_LARGE','429':'RATE_LIMITED','503':'SERVICE_UNAVAILABLE'}[status]
                    value['error']['message']='Example only'
                name=variant.get('$ref','').split('/')[-1]
                fixture={'name':label+' '+status+' '+name,'operation':index,'kind':'response','status':status,'schema':variant,'parameters':deepcopy(params),'value':value}
                # Include populated pages, not only empty-envelope shapes.
                def populate(node,s):
                    if '$ref' in s:return populate(node,bundle['$defs'][s['$ref'].split('/')[-1]])
                    if not isinstance(node,dict):return
                    for k,v in node.items():
                        prop=s.get('properties',{}).get(k,{})
                        if k=='items' and prop.get('type')=='array' and not v and 'items' in prop:
                            node[k]=[sample(bundle,prop['items'])]
                        elif isinstance(v,dict):populate(v,prop)
                if status.startswith('2'):populate(value,variant)
                if 'MembershipAction' in name and status.startswith('2'):
                    fixture['parameters']['query:reader_profile']='membership-actions-1'
                if 'ApplicationDisplay' in name and status.startswith('2'):
                    fixture['parameters']['query:reader_profile']='application-display-1'
                if status.startswith('2') and name in ('Beta_MembershipActionDetailProfile','Beta_MembershipActionPlanProfile'):
                    data=value['data']
                    data['content']=None
                    data['record']=sample(bundle,{'$ref':'#/$defs/MembershipActionRecordSnapshot'})
                    data['viewer'].update(mode='record',membership_state='ended',cycle_member_state='completed',role='none')
                    data['viewer']['record_locator']=deepcopy(data['record']['locator'])
                    data['access'].update(basis='target_record',read_only=True)
                    data['beta_schedule']=None
                    data['recruitment_identity']=None
                    fixture['name']+=' record-content-null'
                result.append(fixture)
    # Full envelopes for the newly important nullable/auth placements. These
    # contexts describe intended access, not a simulated server authorization.
    def extra(source, suffix):
        item=deepcopy(next(c for c in result if source(c)))
        item['name']+=' '+suffix
        result.append(item)
        return item
    detail=extra(lambda c:c['kind']=='response' and c.get('status')=='200' and c.get('schema',{}).get('$ref','').endswith('/Beta_OutputContract3GetV2RaidRoomsRoomIdDetail'), 'actual-T-participant')
    detail['access_context']='Current persistent member and participating CM of the exact T/current generation; no opposite-T or historical grant.'
    membership=sample(bundle,{'$ref':'#/$defs/BAppRaidRoomsAdmissionSchemasMyMembership'})
    membership.update(target_role='member',cycle_member_id=UUID,cycle_member_revision=1,joined_order='1')
    detail['value']['data'].update(my_membership=membership,my_target_role='member',recruitment_identity={'number':1201,'password':'00007'})
    schedule_cases=json.loads((FOLDER/'beta-recruitment-v1.examples.json').read_text())['cases']
    schedule=deepcopy(next(c['value'] for c in schedule_cases if c['schema']=='BetaScheduleView' and c['valid']))
    detail['value']['data']['beta_schedule']=schedule
    detail['value']['data']['room']['beta_schedule']=deepcopy(schedule)
    pending=extra(lambda c:c['kind']=='response' and c.get('status')=='200' and c.get('schema',{}).get('$ref','').endswith('/Beta_ApplicationDisplayDetailResponse'), 'own-pending-memo')
    pending['access_context']='Applicant self; no current participating CM; identity must remain null.'
    own=sample(bundle,{'$ref':'#/$defs/Beta_ApplicationDisplayOwnApplication'})
    own.update(state='pending',application_memo='함께 가요!')
    pending['value']['data'].update(my_application=own,recruitment_identity=None)
    review=extra(lambda c:c['kind']=='response' and c.get('status')=='200' and c.get('schema',{}).get('$ref','').endswith('/Beta_OutputContract3GetV2RaidRoomApplicationsApplicationId'), 'authorized-leader-review')
    review['access_context']='Current authorized leader; review branch, no reader_profile or applicant-identity grant.'
    review['value']['data']=sample(bundle,{'$ref':'#/$defs/Beta_BReview'})
    review['value']['data']['application']['application_memo']='함께 가요!'
    for state in ['waiting_members','no_earlier_candidate','pending','unavailable','not_applicable']:
        item=deepcopy(detail);item['name']+=' coordination-wait-'+state
        item['parameters']['query:include_coordination_wait']='true'
        wait=dict(status=state,missing_members=1 if state=='waiting_members' else None)
        item['value']['data']['beta_schedule']['coordination_wait']=wait
        item['value']['data']['room']['beta_schedule']['coordination_wait']=deepcopy(wait)
        result.append(item)
    search=extra(lambda c:c['kind']=='request' and bundle['operations'][c['operation']]['path']=='/v2/raid-rooms/search', 'whole-minute-search')
    search['value']['departure_windows']=[dict(starts_at='2026-10-26T09:03:00Z',ends_at='2026-10-26T11:17:00Z')]
    page=extra(lambda c:c['kind']=='response' and c.get('status')=='200' and bundle['operations'][c['operation']]['path']=='/v2/raid-rooms', 'whole-minute-search')
    page['parameters']['query:departure_windows']=deepcopy(search['value']['departure_windows'])
    return result


def validate(bundle, fixtures):
    baseline=gzip.decompress((FOLDER/'beta-recruitment-v2.base-openapi.json.gz').read_bytes())
    assert bundle['base_openapi_sha256']==hashlib.sha256(baseline).hexdigest()
    Draft202012Validator.check_schema({'$defs':bundle['$defs']})
    for case in fixtures:
        op=bundle['operations'][case['operation']]
        if case['kind']=='request':schema=op['requestBody']['content']['application/json']['schema']
        else:
            # Validate against both selected branch and the actual operation union.
            schema=case['schema']
            validator(bundle,op['responses'][case['status']]['content']['application/json']['schema']).validate(case['value'])
        try:validator(bundle,schema).validate(case['value'])
        except ValidationError as e:raise AssertionError(case['name']+': '+str(e)) from e
        for p in op['parameters']:
            key=p['in']+':'+p['name']
            if p.get('required'):assert key in case['parameters'],case['name']+' missing '+key
            if key in case['parameters']:
                validator(bundle,p.get('schema') or p['content']['application/json']['schema']).validate(case['parameters'][key])
    base=json.loads(baseline)
    for name,schema in base['components']['schemas'].items():
        if name in bundle['$defs']:
            canonical=json.loads(json.dumps(schema).replace('#/components/schemas/','#/$defs/'))
            if name=='AdmissionCandidateData':
                canonical['properties']['intent']['enum']=['apply','join','change_character']  # Issue13/167
            assert bundle['$defs'][name]==canonical,'Unapproved inherited schema change: '+name
    counts={'requests':0,'success_envelopes':0,'error_envelopes':0}
    for case in fixtures:
        key='requests' if case['kind']=='request' else 'success_envelopes' if case['status'].startswith('2') else 'error_envelopes'
        counts[key]+=1
    # Every write ACK except the explicit submission document is unchanged.
    ack_count=0
    for op in bundle['operations']:
        if op['path'] not in base['paths'] or op['method']=='GET' or op['path'].endswith(('/search','availability-submission')):continue
        old=base['paths'][op['path']][op['method'].lower()]
        for status,response in old['responses'].items():
            if not status.startswith('2'):continue
            old_schema=json.dumps(response['content']['application/json']['schema']).replace('#/components/schemas/','#/$defs/')
            assert json.loads(old_schema)==op['responses'][status]['content']['application/json']['schema']
            ack_count+=1
    # Closed envelope rejects metadata at an invented top layer and card secrets.
    negative=0
    for name,key in [('Beta_BCard','recruitment_identity'),('Beta_BDetail','invented'),('Beta_MembershipActionDetailProfileData','application_memo')]:
        schema={'$ref':'#/$defs/'+name};value=sample(bundle,schema);value[key]=None
        assert not validator(bundle,schema).is_valid(value);negative+=1
    print(json.dumps({'operations':len(bundle['operations']),'complete_fixtures':len(fixtures),**counts,
                      'unchanged_ack_operations':ack_count,'negative_metadata_checks':negative,'runtime_api_db_tests':False}))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-examples',action='store_true');args=parser.parse_args()
    bundle=json.loads((FOLDER/'beta-recruitment-v2.wire.json').read_text())
    target=FOLDER/'beta-recruitment-v2.wire-examples.json'
    if args.write_examples:
        fixtures=cases(bundle)
        target.write_text(json.dumps({'notice':'Synthetic full structural fixtures; not server responses or successful runtime workflows. Error messages are placeholders; codes are illustrative.', 'cases':fixtures},ensure_ascii=False,indent=2)+'\n')
    fixtures=json.loads(target.read_text())['cases']
    validate(bundle,fixtures)


if __name__=='__main__':main()
