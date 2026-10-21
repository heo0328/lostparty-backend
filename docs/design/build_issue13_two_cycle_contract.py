import json,copy,re,hashlib,argparse,subprocess
from pathlib import Path
arguments=argparse.ArgumentParser(description='Reproduce the immutable 0.4.1 design from its cc003e9 runtime baseline')
arguments.add_argument('--base-openapi',type=Path,help='cc003e9 OpenAPI file for an archive without Git history')
options=arguments.parse_args()
base=json.loads((options.base_openapi or Path('openapi/openapi.yaml')).read_text(encoding='utf-8'))
# The executable contract grows during W2. Reproduction must still use the
# reviewed immutable base, never import newly implemented routes into the draft.
if options.base_openapi is None and hashlib.sha256(json.dumps(base,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()!='be0bf3e1c871e031088fb7bd7bd63f3c510624e5c27125c13a4b507cdb074f40':
 base=json.loads(subprocess.check_output(['git','show','cc003e94996bb4e2fdaef6911df24d055ae831b8:openapi/openapi.yaml'],text=True))
core=json.loads(Path('docs/design/issue13-two-cycle.openapi.json').read_text(encoding='utf-8'))
# Run from repository root. Inputs are immutable contract snapshots, not runtime server calls.
canonical=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert hashlib.sha256(canonical(base)).hexdigest()=='be0bf3e1c871e031088fb7bd7bd63f3c510624e5c27125c13a4b507cdb074f40', 'Use cc003e9 original OpenAPI'
assert hashlib.sha256(canonical({'paths':core['paths'],'schemas':core['components']['schemas']})).hexdigest()=='4b768aa0dc3255c4cf78eb98dd09b41279f90327a744af69440166876d7c9d05', 'Use comment73+76 merged core2 snapshot'
S=copy.deepcopy(core['components']['schemas']);P=copy.deepcopy(core['paths'])
def ref(n):return {'$ref':'#/components/schemas/'+n}
def obj(p):return {'type':'object','additionalProperties':False,'properties':p,'required':list(p)}
def nl(p):return {'anyOf':[p,{'type':'null'}]}
def ar(p,lo=0,hi=None):
 d={'type':'array','items':p,'minItems':lo}
 if hi is not None:d['maxItems']=hi
 return d
def en(*v):return {'type':'string','enum':list(v)}
u={'type':'string','format':'uuid'};dt={'type':'string','format':'date-time'};string={'type':'string'};boolean={'type':'boolean'}
ver=ref('Version');ck=ref('CycleKey')
def walk(v,fn):
 if isinstance(v,dict):
  for k,w in list(v.items()):
   if k=='$ref':v[k]=fn(w)
   else:walk(w,fn)
 elif isinstance(v,list):
  for w in v:walk(w,fn)
for n,z in base['components']['schemas'].items():
 z=copy.deepcopy(z);walk(z,lambda q:q.replace('#/components/schemas/','#/components/schemas/B_'));S['B_'+n]=z
S['B_MyMembership']=S['B_app__raid_rooms__admission_schemas__MyMembership']
# Imported base types are retained only when transitively used by a path.
def props(n):return S['B_'+n]['properties']
def add(n,k,v):props(n)[k]=v;S['B_'+n].setdefault('required',[]).append(k) if k not in S['B_'+n].get('required',[]) else None
def drop(n,k):
 props(n).pop(k,None)
 if k in S['B_'+n].get('required',[]):S['B_'+n]['required'].remove(k)
def rename(n,a,b):
 if a in props(n):v=props(n)[a];drop(n,a);add(n,b,v)
S['JoinedOrder']={'type':'string','pattern':'^[1-9][0-9]{0,18}$','maxLength':19,'description':'Canonical positive decimal; value <=9223372036854775807. Compare as integer/BigInt, not lexical string; no JS-number coercion. Server enforces bound.'}
max_order='9223372036854775807'
order_patterns=['[1-9][0-9]{0,17}']
for at,ch in enumerate(max_order):
 low=1 if at==0 else 0; high=int(ch)-1
 if high>=low:
  digit=str(low) if low==high else '['+str(low)+'-'+str(high)+']'
  tail=len(max_order)-at-1
  order_patterns.append(max_order[:at]+digit+('[0-9]{'+str(tail)+'}' if tail else ''))
order_patterns.append(max_order)
S['JoinedOrder']['pattern']='^(?:'+'|'.join(order_patterns)+')$'
S['LeadershipCandidate']['properties']['joined_order']=ref('JoinedOrder')
S['Scope']['properties']['policy_version']={'type':'string','const':'two-cycle-contract-3'}
S['Scope']['properties'].update({'room_cycle_id':nl(u),'target_generation':nl(ver)});S['Scope']['required']+=['room_cycle_id','target_generation']
S['Cycles']['properties']['policy_version']={'type':'string','const':'two-cycle-contract-3'}
S['Leadership']['properties'].update({'leader_membership_id':nl(u)});S['Leadership']['required'].append('leader_membership_id')
S['Error']['properties']['error']['properties'].update({'retry_after_seconds':nl({'type':'integer','minimum':1}),'retry_at':nl(dt)})
S['OpeningContextData']['properties']['opening_effect']=en('create_and_join','reopen_and_join','already_open')
S['OpeningContextData']['properties'].update({'prospective_room_cycle_id':u,'prospective_generation':ver,'prospective_target_revision':ver,'item_settings':ar(obj({'item_id':u,'difficulty_id':string,'catalog_version':string,'duration_minutes':nl({'type':'integer','minimum':10,'maximum':1440,'multipleOf':5})}),1,5)})
S['OpeningContextData']['required']+=['prospective_room_cycle_id','prospective_generation','prospective_target_revision','item_settings']
# Explicit reopening separates ordinary ON/no-op from cancelled-generation replacement.
opening_get=P['/v2/me/raid-rooms/{room_id}/opening-context']['get']
opening_get['parameters'].append({'name':'intent','in':'query','required':True,'schema':en('open','reopen')})
opening_get['description']='C leader only; T=N. intent=open permits missing/open N; cancelled N requires explicit intent=reopen. Server mints prospective IDs/revisions without DB writes; client copies them. Existing open N noop never replaces its leader. No automatic enrolment/confirmation of copied sessions.'
S['OpeningCommand']['properties']['intent']=en('open','reopen');S['OpeningCommand']['required'].append('intent')
P['/v2/raid-rooms/{room_id}/recruitment-openings']['post']['description']='Atomic explicit opening/reopening + source C leader actual participant. intent bound to token. Reopen preserves RoomCycle ID, increments generation and allocates new Round IDs. Never restores cancelled participants/reservations/consents. Existing open N is no-op; original ACK first.'
P['/v2/me/raid-rooms/{room_id}/participation-cancellation-context']['get']['description']='Only N cancellation. Auto successor or last-one close_target is adopted by comment78. Last-one cancels N only; Room and C preserved. Successor changes require refreshed context. Persistent relationship is retained and is not automatic quota recovery.'
P['/v2/raid-rooms/{room_id}/participation-cancellations']['post']['description']='Atomic N bundle cancellation with context-selected automatic successor or last-one target closure. Cancelled future target is not current-week incomplete result. No global membership/room deletion or automatic quota recovery.'
# Consistent canonical role/leader projections.
for n in ['Card','Detail','Plan','Settings']:
 add(n,'leadership',ref('Leadership'));add(n,'my_target_role',en('leader','member','none'))
for n in ['Detail','Plan']:
 add(n,'formation_slots',ar(ref('FormationSlot'),0,40));add(n,'formation_history',ar(ref('FormationSlot'),0,40));add(n,'unplaced_assignments',ar(ref('UnplacedAssignment'),0,40))
for n in ['Card','Plan','TimeContext','OverlapPage','Context','AssignmentView']:
 rename(n,'cycle_key','target_cycle_key')
for n in ['Card','Plan']:
 add(n,'target_state',en('open','completed','stopped_incomplete','cancelled','review_required'))
props('Card')['phase']=en('current','future','ended')
props('Card')['app_member_count']={'type':'integer','minimum':0,'maximum':8,'description':'Distinct target cycle members holding active assignment leases, including review-held slots, not persistent global member count or legacy choices.'}
add('Card','target_revision',ver);add('Card','room_cycle_id',u);add('Card','target_generation',ver)
for n in ['RoomMember','MyMembership','Membership']:
 rename(n,'room_role','target_role');props(n)['target_role']=en('leader','member','none')
 add(n,'cycle_member_id',nl(u));add(n,'cycle_member_revision',nl(ver));add(n,'joined_order',nl(ref('JoinedOrder')))
for k in ['current_week_state','next_week_choice_state']:drop('Membership',k)
add('Membership','target_participation_state',en('participating','completed','stopped','cancelled','legacy_intent','not_selected','review_required'))
add('Membership','target_cycle_key',ck);add('Membership','room_cycle_id',nl(u));add('Membership','target_generation',nl(ver));add('Membership','target_revision',nl(ver))
add('RoomMember','target_state',en('participating','completed','stopped','review_required'))
for n in ['ApplicationView','Application','ApplicationAck','OwnAssignment','Projection','SubmissionOut','ProjectionMember']:
 add(n,'target_cycle_key',ck)
add('Projection','room_cycle_id',u);add('Projection','target_generation',ver);add('Projection','target_revision',ver)
add('ApplicationView','target_generation',ver);add('Application','target_generation',ver)
for n in ['ProjectionMember','TimeMember','OwnAssignment']:
 add(n,'cycle_member_id',u)
# Target revisions named in legacy-derived fields retain their local meaning.
for n in ['AdmissionContext','CreationContext']:
 add(n,'target_cycle_key',ck);add(n,'expected_target_revision',nl(ver) if n=='CreationContext' else ver)
for n in ['AdmissionContext','CreationContext']:
 add(n,'issued_at',dt);add(n,'expires_at',dt)
S['B_ContextRef']['properties']['context_token']={'type':'string','minLength':1,'maxLength':4096}
props('AdmissionContext')['session_choices']=ar(obj({'session_id':u,'required':boolean,'join_deadline':nl(dt),'permission':ref('Permission')}),0,64)
# Initial checkbox shape; contract4 atomic-create rules are finalized below.
S['B_Continuation-Input']=obj({'enabled':boolean,'next_selection':nl(ref('Selection'))})
drop('Defaults','auto_open_default');add('Defaults','opening_mode',{'type':'string','const':'explicit'})
props('Settings')['continuation']=obj({'enabled':boolean,'opening_mode':{'type':'string','const':'explicit'},'revision':ver})
# No implicit future mutation/leave through completion or character replacement.
S['B_Personal']=copy.deepcopy(S['B_ContextRequest'])
drop('Change','choices')
# Do not carry old keep/release and global transfer-resolution semantics into v2 context.
for k in ['continuation','leadership']:drop('Context',k)
add('Context','leadership',ref('Leadership'))
props('Context')['effect_scope']=en('target_cycle','personal_item','item_round')
# Typed historical build preserved from v1; it remains an opaque client-owned analysis snapshot.
# Every live path has explicit target binding; group-filter authority is target-independent.
patterns=('raid-rooms','raid-room-','raid-schedule-','raid-sessions','raid-rounds')
excluded={('/v1/me/raid-rooms/{room_id}/continuation-choices','put'),('/v1/raid-rooms/{room_id}/continuation-settings','put'),('/v1/raid-rooms/{room_id}/transfer-leadership','post'),('/v1/raid-rooms/{room_id}/visibility','put')}
source_map=[]
def target_param():return {'name':'target_cycle_key','in':'query','required':True,'schema':ck}
def addfield(schema,k,v):
 schema['properties'][k]=v
 if k not in schema.get('required',[]):schema.setdefault('required',[]).append(k)
for path,methods in base['paths'].items():
 if not any(p in path for p in patterns):continue
 for method,raw in methods.items():
  if (path,method) in excluded:source_map.append((method.upper(),path,'replaced'));continue
  newpath=path.replace('/v1/','/v2/',1)
  if newpath in P and method in P[newpath]:source_map.append((method.upper(),path,'core override'));continue
  o=copy.deepcopy(raw);walk(o,lambda q:q.replace('#/components/schemas/','#/components/schemas/B_'))
  o['operationId']='contract3_'+method+'_'+newpath.replace('/','_').replace('{','').replace('}','')
  o['description']='Contract4 target adapter. Same actual T for path IDs/rounds/sessions/application and body/query. Target permissions/leadership and per-cycle settings/members/plan revisions; no cross-cycle writes.'
  if method=='get' and not path.endswith('/raid-room-filter-context'):
   o.setdefault('parameters',[]).append(target_param())
   o['parameters']=[z for z in o['parameters'] if z['name']!='target_cycle']
  if path.endswith('/raid-room-applications') or path.endswith('/applications'):
   for z in o.get('parameters',[]):
    if z['name']=='state':
     z['schema']['enum']=['pending','accepted','rejected','withdrawn','expired','cancelled','all']
  rb=o.get('requestBody',{}).get('content',{}).get('application/json')
  if rb:
   oldref=rb['schema']['$ref'].split('/')[-1];newname='Input_'+o['operationId'];sc=copy.deepcopy(S[oldref]);S[newname]=sc;rb['schema']=ref(newname)
   if 'expected_membership_revision' in sc['properties']:
    sc['properties']['expected_cycle_member_revision']=sc['properties'].pop('expected_membership_revision');sc['required'].remove('expected_membership_revision');sc['required'].append('expected_cycle_member_revision')
   if path.endswith('/removals'):
    sc['properties']['target_cycle_member_id']=sc['properties'].pop('target_membership_id');sc['required'].remove('target_membership_id');sc['required'].append('target_cycle_member_id')
    sc['properties']['expected_removed_cycle_member_revision']=sc['properties'].pop('expected_target_revision');sc['required'].remove('expected_target_revision');sc['required'].append('expected_removed_cycle_member_revision')
   addfield(sc,'target_cycle_key',ck)
   if not path.endswith('/search'):
    addfield(sc,'expected_cycle_key',ck)
    addfield(sc,'expected_target_revision',nl(ver) if path=='/v1/raid-rooms' else ver)
    if method in ('post','put','patch') and any(t in path for t in ('/approve','/reject','/schedule-groups','/selections','/schedule-proposals','/weekly-resume-proposals','/settings','/formation','/removals')):
     addfield(sc,'expected_leadership_revision',ver)
   if path.endswith('/leave') or path.endswith('/end'):addfield(sc,'context_token',{'type':'string','minLength':1,'maxLength':4096})
  # Scope/data universally on single-target recruitment responses, raw filter context exempt.
  for status,rsp in o['responses'].items():
   if status.startswith('2') and 'content' in rsp:
    if path.endswith('/raid-room-filter-context'):continue
    content=rsp['content'].get('application/json')
    if content:
     out='Output_'+o['operationId'];S[out]=obj({'scope':ref('Scope'),'data':content['schema']});content['schema']=ref(out)
   elif not status.startswith('2'):
    rsp['content']={'application/json':{'schema':ref('Error')}}
  P.setdefault(newpath,{})[method]=o;source_map.append((method.upper(),path,newpath))
# Helpers for final schemas/operations.
proto=copy.deepcopy(P['/v2/me/raid-rooms/{room_id}/opening-context']['get'])
room={'name':'room_id','in':'path','required':True,'schema':u};key={'name':'Idempotency-Key','in':'header','required':True,'schema':u}
def op(path,method,out,parameters,inp=None,description=''):
 o=copy.deepcopy(proto);o['operationId']='contract3_'+method+'_'+path.replace('/','_').replace('{','').replace('}','');o['description']=description;o['parameters']=parameters;o['responses']['200']['content']['application/json']['schema']=ref(out)
 if inp:o['requestBody']={'required':True,'content':{'application/json':{'schema':ref(inp)}}}
 P.setdefault(path,{})[method]=o
S['B_Choices']['properties']['target_cycle_key']=S['B_Choices']['properties'].pop('target_cycle');S['B_Choices']['required'].remove('target_cycle');S['B_Choices']['required'].append('target_cycle_key')
# New context for G1 common operations and original global cleanup; no new relationship-termination UI.
S['CommonImpact']=obj({'target_cycle_key':ck,'room_cycle_id':u,'generation':ver,'target_revision':ver,'leadership':ref('Leadership'),'member_count':{'type':'integer','minimum':0,'maximum':8},'assignment_count':{'type':'integer','minimum':0,'maximum':40},'reservation_count':{'type':'integer','minimum':0}})
S['CommonContextData']=obj({'room_id':u,'command':en('edit_common_settings','leave','end'),'room_revision':ver,'persistent_membership_revision':ver,'context_token':{'type':'string','minLength':1,'maxLength':4096},'issued_at':dt,'expires_at':dt,'impact_cycles':ar(ref('CommonImpact'),0,2),'permission':ref('Permission')})
S['CommonContext']=obj({'scope':ref('Scope'),'data':ref('CommonContextData')})
S['CommonSettingsCommand']=obj({'expected_cycle_key':ck,'target_cycle_key':ck,'expected_target_revision':ver,'expected_room_revision':ver,'context_token':{'type':'string','minLength':1,'maxLength':4096},'title':{'type':'string','minLength':1,'maxLength':60},'scope':en('public','group'),'group_id':nl(u),'expected_group_revision':nl(ver)})
op('/v2/me/raid-rooms/{room_id}/common-context','get','CommonContext',[room,target_param(),{'name':'command','in':'query','required':True,'schema':en('edit_common_settings','leave','end')}],description='G1 current C leader, or N leader only if no C cycle exists. Closed/review C does NOT delegate to N. Context binds both cycles/common room impacts. Global leave/end retain existing safe guards; no new relation termination entrypoint.')
op('/v2/raid-rooms/{room_id}/common-settings','put','Ack',[room,key],'CommonSettingsCommand','G1 title/visibility edit. group_id immutable; expected group qualification/revision checked. Both-cycle impact token required. N leader transfer cannot grant C/common permission.')
# Manual completion preserves stable body semantics plus explicit actual target and10:00guard.
manual_path='/v1/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion'
manual=copy.deepcopy(base['paths'][manual_path]['put']);walk(manual,lambda q:q.replace('#/components/schemas/','#/components/schemas/B_'))
mi=copy.deepcopy(S['B_ManualCompletionIn']);addfield(mi,'target_cycle_key',ck);S['ManualCompletionCommand']=mi;manual['requestBody']['content']['application/json']['schema']=ref('ManualCompletionCommand');manual['operationId']='contract3_manual_completion'
S['ManualCompletionResult']=obj({'scope':ref('Scope'),'data':ref('B_WeeklyEntry')})
manual['responses']['200']['content']['application/json']['schema']=ref('ManualCompletionResult')
for code,rsp in manual['responses'].items():
 if not code.startswith('2'):rsp['content']={'application/json':{'schema':ref('Error')}}
manual['description']='T=C and now>=Wednesday10:00 only, including false/correction. Manual source only; party completion never erased. Read original ACK before new-cycle eligibility checks.'
P[manual_path.replace('/v1/','/v2/') ]={'put':manual}
# Creation context: IDs not needed for a new room; POST201 allocates room UUID from existing Create fields.
# Existing target-bound wrappers remain canonical. Core metadata/summary are multi-cycle exceptions.
# All local references named B_Permission reuse canonical permission semantics.
S['B_Permission']=copy.deepcopy(S['Permission'])
# Add target leadership revision on source/member contexts, target-local versions distinct from global room version.
add('AdmissionContext','leadership',ref('Leadership'))
# B_Context's actor revision is persistent and must not substitute cycle participation authority.
add('Context','actor_cycle_member_id',u);add('Context','actor_cycle_member_revision',ver)
# Canonical structural bounds: stored ordinal string is NOT a slot number.
S['B_Assignment']['properties']['party_no']={'type':'integer','minimum':1,'maximum':2};S['B_Assignment']['properties']['slot_no']={'type':'integer','minimum':1,'maximum':4}
S['B_CardItem']['properties']['round_id']=u;S['B_CardItem']['required'].append('round_id')
# Rename old effects and obsolete future choice fallback in descriptions.
P['/v2/me/raid-rooms/{room_id}/continuation-choices']['get']['description']='Read-only legacy intents/declines for actual T; not proof of confirmed participation. No v2 PUT intent endpoint and no auto-open settings endpoint. Actual target assignment/weekly summary is authoritative.'
# Request bounded fields retain previous scalar rules; explicit new target filters never added post-page.
for n in ['SubmissionOut']:
 add(n,'cycle_member_id',u);add(n,'cycle_member_revision',ver)
rename('Placement','membership_id','cycle_member_id');rename('Placement','expected_revision','expected_cycle_member_revision')
S['Source']['properties'].update({'source_cycle_member_id':u,'source_cycle_member_revision':ver});S['Source']['required']+=['source_cycle_member_id','source_cycle_member_revision']
def permissions(*names):return obj({n:ref('Permission') for n in names})
props('Card')['permissions']=permissions('view_detail','view_plan')
props('Detail')['permissions']=permissions('view_detail','view_plan')
props('Plan')['permissions']=permissions('edit_schedule_groups','cancel_target_participation','transfer_leadership','open_next_cycle','reopen_next_cycle','view_common_context','leave_global','end_global')
props('Settings')['permissions']=permissions('edit_settings','edit_common_settings','open_next_cycle','reopen_next_cycle')
props('Membership')['permissions']=permissions('view_plan')
props('CreationContext')['permissions']=permissions('create')
props('TimeContext')['permissions']=permissions('view_schedule_context')
props('Review')['permissions']=permissions('approve','reject')
props('AdmissionContext')['permissions']={'type':'object','additionalProperties':False,'properties':{n:ref('Permission') for n in ['join','apply','change_character']},'minProperties':1,'maxProperties':1}
# Contract4: native comment80 corrections. Preserve approved creation UX.
S['Scope']['properties']['policy_version']={'type':'string','const':'two-cycle-contract-4'}
S['Cycles']['properties']['policy_version']={'type':'string','const':'two-cycle-contract-4'}
S['GlobalScope']=obj({'server_now':dt,'current_cycle_key':ck,'policy_version':{'type':'string','const':'two-cycle-contract-4'}})
S['GlobalMembershipCommand']=obj({'expected_cycle_key':ck,'expected_room_revision':ver,'expected_persistent_membership_revision':ver,'context_token':{'type':'string','minLength':1,'maxLength':4096}})
S['GlobalMembershipAckData']=obj({'command_id':u,'outcome':en('applied','noop'),'executed_at':dt,'room_id':u,'membership_id':u,'persistent_membership_revision':ver,'affected_cycle_keys':dict(ar(ck,0,2),uniqueItems=True),'room_ended':boolean,'revisions':ar(ref('Revision'))})
S['GlobalMembershipAck']=obj({'scope':ref('GlobalScope'),'data':ref('GlobalMembershipAckData')})
S['CommonContext']=obj({'scope':ref('GlobalScope'),'data':ref('CommonContextData')})
add_common={'expected_cycle_key':ck,'authorization_cycle_key':nl(ck),'current_settings':obj({'title':{'type':'string','minLength':1,'maxLength':60},'scope':en('public','group'),'group_id':nl(u),'group_revision':nl(ver)})}
S['CommonContextData']['properties'].update(add_common);S['CommonContextData']['required']+=list(add_common)
for k,v in {'members_revision':ver,'plan_revision':ver,'actor_cycle_member_id':nl(u),'actor_cycle_member_revision':nl(ver)}.items():
 S['CommonImpact']['properties'][k]=v;S['CommonImpact']['required'].append(k)
# Global target-free cleanup: no fabricated cycle/round/member/plan CAS.
for suffix in ['leave','end']:
 o=P['/v2/raid-rooms/{room_id}/'+suffix]['post']
 o['requestBody']['content']['application/json']['schema']=ref('GlobalMembershipCommand')
 o['responses']['200']['content']['application/json']['schema']=ref('GlobalMembershipAck')
 o['description']='Global '+suffix+' uses only current C expectation, room/persistent-membership CAS and command-bound common context. All actual effects are in the opaque token; no required target participation. N-tab cancellation uses participation-cancellations. Original ACK replay first.'
o=P['/v2/me/raid-rooms/{room_id}/common-context']['get']
o['parameters']=[p for p in o['parameters'] if p['name']!='target_cycle_key']
o['description']='Own persistent membership required. leave: no unresolved leadership in any live T; other T effects explicitly confirmed. end: G1 plus safe global-last-member and no other actual T participants. edit_common_settings: G1. Exposes every required body CAS, no GET writes or fabricated target rows.'
for k in ['target_cycle_key','expected_target_revision']:
 S['CommonSettingsCommand']['properties'].pop(k,None);S['CommonSettingsCommand']['required'].remove(k)
# Comment82: common settings is a global command, including its success ACK.
S['CommonSettingsAckData']=obj({'command_id':u,'outcome':en('applied','noop'),'executed_at':dt,'room_id':u,'room_revision':ver,'affected_cycle_keys':dict(ar(ck,0,2),uniqueItems=True)})
S['CommonSettingsAck']=obj({'scope':ref('GlobalScope'),'data':ref('CommonSettingsAckData')})
o=P['/v2/raid-rooms/{room_id}/common-settings']['put']
o['responses']['200']['content']['application/json']['schema']=ref('CommonSettingsAck')
o['description']='Global common-settings command; G1 authority is C leader, or N leader only if the C cycle row is absent (never closed/review C fallback). Uses room CAS and all-impact context token. 200 CommonSettingsAck has GlobalScope, post-command room_revision and actual affected_cycle_keys; no target scope or fabricated cycle. Changes only common settings, not cycle leadership/participation/reservations/completion. No-op keeps room_revision and affected_cycle_keys=[]. Same key and immutable body replay original 200 before context expiry/week/authority revalidation, including original scope and affected cycles.'
# Error detail may identify C/N failure without claiming a partial success.
S['ErrorDetails']['properties']['failed_cycle_key']=nl(ck);S['ErrorDetails']['required'].append('failed_cycle_key')
# The checkbox remains a single user action: atomic primary and optional N creation.
S['B_Continuation-Input']=obj({'enabled':boolean,'next_selection':nl(ref('Selection'))})
S['B_Continuation-Input']['allOf']=[{'if':{'properties':{'enabled':{'const':False}},'required':['enabled']},'then':{'properties':{'next_selection':{'type':'null'}}}}]
S['ProspectiveCreateItem']=obj({'item_id':u,'round_id':u,'raid_id':string,'difficulty_id':string,'party_no':{'type':'integer','minimum':1,'maximum':2},'expected_round_revision':{'type':'integer','const':1},'expected_weekly_revision':ver})
S['ProspectiveCreateCycle']=obj({'target_cycle_key':ck,'room_cycle_id':u,'generation':{'type':'integer','const':1},'initial_target_revision':{'type':'integer','const':1},'selection':ref('Selection'),'targets':ar(ref('ProspectiveCreateItem'),1,5),'permission':ref('Permission'),'conflicts':ar(ref('Conflict'),0,5)})
creation_fields={'prospective_room_id':u,'target_creation':ref('ProspectiveCreateCycle'),'next_cycle_creation':nl(ref('ProspectiveCreateCycle')),'continuation_effect':en('target_only','target_and_next','target_is_next')}
for k,v in creation_fields.items():add('CreationContext',k,v)
o=P['/v2/me/raid-room-creation-context']['get']
o['parameters'] += [{'name':'continuation_enabled','in':'query','required':False,'schema':{'type':'boolean','default':False}},{'name':'next_character_id','in':'query','required':False,'schema':u},{'name':'next_selected_role','in':'query','required':False,'schema':en('dealer','support')}]
o['description']='Preflight primary actual T and checkbox choice. T=C + checked: qualify C and N, mint one room/two cycle graphs in token. Optional next character+role together for approved conflict alternative. T=N: only N, never C+14, checkbox effect target_is_next. GET does not allocate DB rows or slots. POST validates final schedules and commits all-or-nothing.'
S['CreatedCycle']=obj({'target_cycle_key':ck,'room_cycle_id':u,'generation':ver,'target_revision':ver,'leader_cycle_member_id':u})
S['CreateAckData']=copy.deepcopy(S['AckData'])
S['CreateAckData']['properties'].update({'created_cycles':dict(ar(ref('CreatedCycle'),1,2),uniqueItems=True),'continuation_effect':en('target_only','target_and_next','target_is_next')});S['CreateAckData']['required']+=['created_cycles','continuation_effect']
S['CreateAck']=obj({'scope':ref('Scope'),'data':ref('CreateAckData')})
o=P['/v2/raid-rooms']['post'];o['responses']['201']['content']['application/json']['schema']=ref('CreateAck')
o['description']='Single atomic create. Checked C creation commits one room + C and N leader bundle assignments/weekly occupancies + immutable ACK in one transaction. Any N failure rolls back C too. T=N creates only N, never C+14. Same key/body replays original ACK, never creates a duplicate room; checkbox remains part of original form.'
# Multi-select experience is an OR filter; [] means no filtering, not IS NULL.
S['ExperienceFilterValue']=en('tryLevel','clearExp','multiClearExp','semiExperienced','experienced','unrestricted')
S['ExperienceFilterValues']=dict(ar(ref('ExperienceFilterValue'),0,6),uniqueItems=True,default=[],description='OR values; []/omitted means no filter; unrestricted matches stored null. Null/duplicates/unknown enum rejected; sorting of valid values alone does not stale the cursor.')
o=P['/v2/raid-rooms/search']['post'];name=o['requestBody']['content']['application/json']['schema']['$ref'].split('/')[-1]
S[name]['properties']['experience_levels']=ref('ExperienceFilterValues')
o['description']='SQL target/visibility + existing filters + experience_levels OR, then exact remaining-slot and member-count order, then pagination. Normalize validated experience values into cursor binding; no client page-local filtering.'
o=P['/v2/raid-rooms']['get'];o['parameters'].append({'name':'experience_levels','in':'query','required':False,'style':'form','explode':True,'schema':ref('ExperienceFilterValues')})
o['description']='Same SQL experience filter as POST search. Omitted list=[]; repeat experience_levels query key for OR. Empty query value, CSV, duplicate value, null string or unknown enum =>400. Repeated keys allowed only for declared array parameters.'

# Prune unused base schemas: complete artifact contains only references reachable from paths.
x={'openapi':'3.1.0','info':{'title':'Issue13 full two-cycle recruitment contract candidate4 — NOT implemented runtime','version':'0.4.1','description':'Policies L1 core/G1/A1 adopted in Flutter comment78. Full target recruitment surface and manual completion; review candidate, not native implementation handoff/test readiness. Runtime openapi/openapi.yaml unchanged.'},'x-status':'full-contract-candidate-not-implemented','x-policy-source':'https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6307975683','x-source-implementation':'cc003e94996bb4e2fdaef6911df24d055ae831b8','paths':P,'components':{'securitySchemes':copy.deepcopy(base['components']['securitySchemes']),'schemas':S}}
# Avoid legacy runtime op names and generated /v1 auto tag semantics.
for path,methods in P.items():
 for method,o in methods.items():
  o['tags']=['two-cycle-contract-3']
  for status,rs in o['responses'].items():
   rs.setdefault('headers',{})['Cache-Control']={'schema':{'type':'string','const':'no-store'}}
  if method in ('post','put') and not path.endswith(('/search','raid-weekly-summary')):
   assert any(z['name']=='Idempotency-Key' for z in o.get('parameters',[])),path
seen=set()
def trace(v):
 if isinstance(v,dict):
  if '$ref'in v:
   name=v['$ref'].split('/')[-1]
   assert name in S,name
   if name not in seen:seen.add(name);trace(S[name])
  for a in v.values():trace(a)
 elif isinstance(v,list):
  for a in v:trace(a)
trace(P)
# FormationProjection documents detail/plan correspondence and remains a typed contract component.
for a in ['FormationProjection']:seen.add(a);trace(S[a])
x['components']['schemas']={k:S[k] for k in sorted(seen)}
p=Path('docs/design/issue13-two-cycle.full.openapi.json');p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
Path('docs/design/issue13-two-cycle.route-map.json').write_text(json.dumps(source_map,ensure_ascii=False,indent=2),encoding='utf-8')
print('FULL',len(P),'paths',sum(map(len,P.values())),'operations',len(x['components']['schemas']),'schemas','compactchars',len(json.dumps(x,ensure_ascii=False,separators=(',',':'))))
# Shared errors keep the published standalone contract compact and consistent.
failures={}
for path,methods in x['paths'].items():
 for method,o in methods.items():
  o['responses'].pop('422',None)
  for status,rsp in list(o['responses'].items()):
   if not status.startswith('2'):
    name='Failure'+status
    failures[name]={'description':'See contract4 error/action table. Original ACK replay first; only REQUEST_IN_PROGRESS has Retry-After:2.','headers':{'Cache-Control':{'schema':{'type':'string','const':'no-store'}},'Retry-After':{'description':'REQUEST_IN_PROGRESS only; otherwise omitted.','schema':{'type':'integer','minimum':1}}},'content':{'application/json':{'schema':ref('Error')}}}
    o['responses'][status]={'$ref':'#/components/responses/'+name}
  # Full surface unified with core mutation ACKs.
  for status,rsp in o['responses'].items():
   if status.startswith('2') and 'content' in rsp:
    rs=rsp['content'].get('application/json',{}).get('schema',{})
    if '$ref' in rs:
     sn=rs['$ref'].split('/')[-1]
     sc=x['components']['schemas'].get(sn,{})
     if sc.get('properties',{}).get('data')==ref('B_Ack'):sc['properties']['data']=ref('AckData')
x['components']['responses']=failures
# Visit schema positions, never property-name maps or instance data.
def clean(v):
 if not isinstance(v,dict):return
 v.pop('title',None)
 for keyword in ('properties','patternProperties','$defs','definitions','dependentSchemas'):
  for schema in v.get(keyword,{}).values():clean(schema)
 for keyword in ('additionalProperties','unevaluatedProperties','items','contains','not','if','then','else','propertyNames'):
  if isinstance(v.get(keyword),dict):clean(v[keyword])
 for keyword in ('allOf','anyOf','oneOf','prefixItems'):
  for schema in v.get(keyword,[]):clean(schema)
# Preserve document title, strip schema presentation metadata.
for v in x['components']['schemas'].values():clean(v)
p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('COMPACT',len(json.dumps(x,ensure_ascii=False,separators=(',',':'))),'characters')
