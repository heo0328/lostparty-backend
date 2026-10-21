import json,copy
from pathlib import Path
x=json.loads(Path('docs/design/issue13-two-cycle.full.openapi.json').read_text(encoding='utf-8'));S=x['components']['schemas']
prev=json.loads(Path('docs/design/issue13-two-cycle.examples.json').read_text(encoding='utf-8'))
def migrate(v):
 if isinstance(v,dict):return {k:migrate(w) for k,w in v.items()}
 if isinstance(v,list):return [migrate(w) for w in v]
 return 'two-cycle-contract-4' if v=='two-cycle-contract-3' else v
cases=migrate(prev['cases'])
# Keep only original16 fixtures when regenerating this file.
cases=cases[:16]
def case(name,schema,value,valid=True,**extra):
 cases.append(dict(name=name,schema=schema,value=copy.deepcopy(value),schema_valid=valid,**extra))
def r(n):return S[n]
def resolve(z):return resolve(S[z['$ref'].split('/')[-1]]) if '$ref'in z else z
ids=['00000000-0000-4000-8000-'+str(i).zfill(12) for i in range(1,40)]
C='2026-10-21';N='2026-10-28';now='2026-10-21T03:00:00Z';expires='2026-10-21T03:02:00Z';token='synthetic-schema-token-not-usable'
def witness(z):
 z=resolve(z)
 if 'const'in z:return z['const']
 if 'anyOf'in z:
  return witness(next((w for w in z['anyOf'] if w.get('type')=='null'),z['anyOf'][0]))
 if 'enum'in z:return z['enum'][0]
 t=z.get('type')
 if t=='null':return None
 if t=='object':return {k:witness(z['properties'][k]) for k in z.get('required',[])}
 if t=='array':return [witness(z['items']) for _ in range(z.get('minItems',0))]
 if t in ('number','integer'):return max(1,z.get('minimum',0))
 if t=='boolean':return False
 if t=='string':
  if z.get('format')=='uuid':return ids[0]
  if z.get('format')=='date-time':return now
  if z.get('format')=='date':return C
  return 'x'*max(1,z.get('minLength',0))
 raise ValueError(z)
sel=copy.deepcopy(cases[1]['value']['selection']);nextsel=copy.deepcopy(sel);nextsel['character_id']=ids[20]
combat=dict(input_mode='shared',dealer_min=None,support_min=None)
create=dict(title='합성 모집 제목',scope='public',group_id=None,admission_mode='leader_only',app_mode='single',items=[dict(raid_id='sample_raid',difficulty_id='sample_normal',duration_minutes=None,expected_weekly_revision=7,party_no=1)],selection=sel,selection_context=dict(context_token=token+'-off-C'),experience_level=None,combat_requirement=combat,continuation=dict(enabled=False,next_selection=None),schedule_groups=[],expected_cycle_key=C,expected_catalog_version='synthetic-catalog',expected_group_revision=None,target_cycle_key=C,expected_target_revision=None)
createname=x['paths']['/v2/raid-rooms']['post']['requestBody']['content']['application/json']['schema']['$ref'].split('/')[-1]
case('create_title_success_checkbox_off',createname,create)
checked=copy.deepcopy(create);checked['continuation']=dict(enabled=True,next_selection=sel);checked['selection_context']['context_token']=token+'-on-C'
case('create_checkbox_C_and_N_single_command',createname,checked,contract_effect='All C/N writes and ACK commit together; no partial success')
alt=copy.deepcopy(checked);alt['continuation']['next_selection']=nextsel;alt['selection_context']['context_token']=token+'-on-C-alt'
case('create_checkbox_N_alternative_character',createname,alt)
checkedN=copy.deepcopy(create);checkedN['target_cycle_key']=N;checkedN['continuation']['enabled']=True;checkedN['items'][0]['expected_weekly_revision']=9;checkedN['selection_context']['context_token']=token+'-on-N'
case('create_selected_N_checkbox_no_C_plus14',createname,checkedN,contract_effect='Exactly N, no C+14; next_selection=null')
for title,tag in [('', 'empty'),(None,'null'),('x'*61,'too_long')]:
 z=copy.deepcopy(create);z['title']=title;case('create_title_'+tag+'_rejected',createname,z,False)
z=copy.deepcopy(create);del z['title'];case('create_title_missing_rejected',createname,z,False)
z=copy.deepcopy(create);z['experience_level']='unrestricted';case('create_search_sentinel_not_a_creation_experience',createname,z,False)
z=copy.deepcopy(create);z['continuation']['next_selection']=sel;case('unchecked_next_selection_rejected',createname,z,False)
settings=dict(expected_cycle_key=C,expected_room_revision=7,context_token=token,title='합성 공통 제목 변경',scope='public',group_id=None,expected_group_revision=None)
case('common_title_update_success','CommonSettingsCommand',settings)
z=copy.deepcopy(settings);del z['title'];case('common_title_missing_rejected','CommonSettingsCommand',z,False)
z=copy.deepcopy(settings);z['title']='';case('common_title_empty_rejected','CommonSettingsCommand',z,False)
card=witness(r('B_Card'));card.update(room_id=ids[5],title='합성 카드 제목',group_id=None,app_capacity=8,app_member_count=1,leader_display=None,created_at=now,scope='public',target_cycle_key=C,room_cycle_id=ids[6],target_revision=1,target_generation=1,continuation_enabled=True,my_target_role='leader',leadership=dict(leader_cycle_member_id=ids[7],leader_membership_id=ids[8],leadership_revision=1),combat_requirement=combat)
item=dict(item_id=ids[3],raid_id='sample_raid',difficulty_id='sample_normal',game_party_size=8,round_id=ids[4]);card['items']=card['game_items']=[item]
case('card_success_title_present','B_Card',card)
z=copy.deepcopy(card);del z['title'];case('card_title_missing_rejected','B_Card',z,False)
permission=dict(allowed=True,reason=None,next_change_at=None)
base_scope=dict(server_now=now,current_cycle_key=C,target_cycle_key=C,playable_from='2026-10-21T01:00:00Z',phase='current',target_revision=1,room_cycle_id=ids[6],target_generation=1,policy_version='two-cycle-contract-4')
card_out=x['paths']['/v2/raid-rooms/{room_id}']['get']['responses']['200']['content']['application/json']['schema']['$ref'].split('/')[-1]
case('card_wrapped_success',card_out,dict(scope=base_scope,data=card))
# Full read-only primary+next preflight, including typed default/comparison structures.
cd=witness(r('B_CreationContext'));cd.update(expected_cycle_key=C,target_cycle_key=C,server_time=now,catalog_version='synthetic-catalog',context_token=token,selection=sel,targets=[dict(raid_id='sample_raid',difficulty_id='sample_normal',expected_weekly_revision=7)],group_revision=None,expected_target_revision=None,issued_at=now,expires_at=expires,prospective_room_id=ids[5],continuation_effect='target_and_next',permissions=dict(create=permission))
primary=dict(target_cycle_key=C,room_cycle_id=ids[6],generation=1,initial_target_revision=1,selection=sel,targets=[dict(item_id=ids[3],round_id=ids[4],raid_id='sample_raid',difficulty_id='sample_normal',party_no=1,expected_round_revision=1,expected_weekly_revision=7)],permission=permission,conflicts=[])
future=copy.deepcopy(primary);future.update(target_cycle_key=N,room_cycle_id=ids[9]);future['targets'][0].update(round_id=ids[10],expected_weekly_revision=9)
cd.update(target_creation=primary,next_cycle_creation=future,context_token=token+'-on-C')
case('create_context_checked_primary_and_next','B_CreationContext',cd)
blocked=copy.deepcopy(cd);blocked['permissions']['create']=dict(allowed=False,reason='WEEKLY_ALREADY_PARTICIPATING',next_change_at=None);blocked['next_cycle_creation']['permission']=blocked['permissions']['create'];blocked['next_cycle_creation']['conflicts']=[dict(room_id=ids[17],room_title='본인 권한 내 합성 B방',target_cycle_key=N,raid_id='sample_raid',character_id=sel['character_id'],can_view_detail=True)]
case('create_context_N_preflight_blocked_no_rows','B_CreationContext',blocked,scenario='Schema-valid denial example, not executed business check')
ack=dict(command_id=ids[11],outcome='applied',executed_at=now,room_id=ids[5],target_cycle_key=C,revisions=[],created_cycles=[dict(target_cycle_key=C,room_cycle_id=ids[6],generation=1,target_revision=1,leader_cycle_member_id=ids[7]),dict(target_cycle_key=N,room_cycle_id=ids[9],generation=1,target_revision=1,leader_cycle_member_id=ids[12])],continuation_effect='target_and_next')
case('create_atomic_success_ACK_C_N','CreateAck',dict(scope=base_scope,data=ack))
onlyC=copy.deepcopy(cd);onlyC.update(next_cycle_creation=None,continuation_effect='target_only',context_token=token+'-off-C')
case('create_context_unchecked_C_only','B_CreationContext',onlyC)
ackC=copy.deepcopy(ack);ackC.update(created_cycles=[ackC['created_cycles'][0]],continuation_effect='target_only')
case('create_unchecked_C_only_ACK','CreateAck',dict(scope=base_scope,data=ackC))
onlyN=copy.deepcopy(cd);onlyN.update(target_cycle_key=N,targets=[dict(raid_id='sample_raid',difficulty_id='sample_normal',expected_weekly_revision=9)],target_creation=future,next_cycle_creation=None,continuation_effect='target_is_next',context_token=token+'-on-N')
case('create_context_selected_N_no_extra_cycle','B_CreationContext',onlyN)
ackN=copy.deepcopy(ack);ackN.update(target_cycle_key=N,created_cycles=[ackN['created_cycles'][1]],continuation_effect='target_is_next')
scopeN=copy.deepcopy(base_scope);scopeN.update(target_cycle_key=N,playable_from='2026-10-28T01:00:00Z',phase='future',room_cycle_id=ids[9])
case('create_selected_N_only_ACK_no_C_plus14','CreateAck',dict(scope=scopeN,data=ackN))
# Global CAS binding: request values derive solely from the displayed common context.
gscope=dict(server_now=now,current_cycle_key=C,policy_version='two-cycle-contract-4')
def context(command,impacts,allowed=True,reason=None,auth=None):
 return dict(scope=gscope,data=dict(room_id=ids[5],command=command,room_revision=7,persistent_membership_revision=3,context_token=token+'-'+command,issued_at=now,expires_at=expires,impact_cycles=impacts,permission=dict(allowed=allowed,reason=reason,next_change_at=None),expected_cycle_key=C,authorization_cycle_key=auth,current_settings=dict(title='합성 공통 제목',scope='public',group_id=None,group_revision=None)))
def impact(t,own=True,leader=False):
 return dict(target_cycle_key=t,room_cycle_id=ids[6 if t==C else 9],generation=1,target_revision=4,leadership=dict(leader_cycle_member_id=ids[7] if leader else ids[15],leader_membership_id=ids[8] if leader else ids[16],leadership_revision=2),member_count=1,assignment_count=1,reservation_count=0,members_revision=4,plan_revision=5,actor_cycle_member_id=ids[7] if own else None,actor_cycle_member_revision=4 if own else None)
bindings=[]
for name,command,impacts,allowed,reason,auth in [
 ('leave_persistent_only_no_cycle','leave',[],True,None,None),
 ('leave_zero_active_effect_after_N_cancel','leave',[],True,None,None),
 ('leave_explicit_global_ordinary_C_N','leave',[impact(C),impact(N)],True,None,None),
 ('leave_leader_unresolved_denied','leave',[impact(C,leader=True)],False,'LEADERSHIP_RESOLUTION_REQUIRED',None),
 ('end_global_last_member_N_only','end',[impact(N,leader=True)],True,None,N),
 ('end_other_T_participant_denied','end',[impact(C,leader=True),impact(N,own=False)],False,'ROOM_LAST_MEMBER_REQUIRED',C)]:
 ctx=context(command,impacts,allowed,reason,auth);req=dict(expected_cycle_key=ctx['data']['expected_cycle_key'],expected_room_revision=ctx['data']['room_revision'],expected_persistent_membership_revision=ctx['data']['persistent_membership_revision'],context_token=ctx['data']['context_token'])
 case(name+'_context','CommonContext',ctx,scenario='Guard outcome is illustrative; server not run')
 case(name+'_request','GlobalMembershipCommand',req,expected_server_allowed=allowed)
 bindings.append(dict(context_case=name+'_context',request_case=name+'_request',mapping={'expected_cycle_key':'expected_cycle_key','expected_room_revision':'room_revision','expected_persistent_membership_revision':'persistent_membership_revision','context_token':'context_token'}))
greq=copy.deepcopy(req);greq['expected_cycle_member_revision']=1;case('global_fabricated_target_CAS_rejected','GlobalMembershipCommand',greq,False)
greq=copy.deepcopy(req);greq['target_cycle_key']=C;case('global_unneeded_target_key_rejected','GlobalMembershipCommand',greq,False)
for ended,affected,name in [(False,[],'leave_persistent_only_success_ACK'),(True,[N],'end_global_last_member_success_ACK')]:
 case(name,'GlobalMembershipAck',dict(scope=gscope,data=dict(command_id=ids[11],outcome='applied',executed_at=now,room_id=ids[5],membership_id=ids[8],persistent_membership_revision=4,affected_cycle_keys=affected,room_ended=ended,revisions=[])))
# N-only cancellation is the safe preservation action, not a global leave alias.
case('N_cancel_preserves_C_request','CancellationCommand',dict(expected_cycle_key=C,target_cycle_key=N,expected_target_revision=4,expected_leadership_revision=2,context_token=token),scenario='Runtime must preserve C; this fixture validates request shape only')
def err(code,failed=None,conflicts=()):return dict(error=dict(code=code,message='합성 거절 예시',request_id=ids[13],details=dict(conflicts=list(conflicts),available_at=None,failed_cycle_key=failed)))
case('create_N_conflict_entire_create_rejected','Error',err('TARGET_CHARACTER_CONFLICT',N,[dict(room_id=ids[17],room_title='본인 권한 내 합성 B방',target_cycle_key=N,raid_id='sample_raid',character_id=sel['character_id'],can_view_detail=True)]),expected_http_status=409,no_committed_cycles=[])
for code,name in [('LEADERSHIP_RESOLUTION_REQUIRED','global_leader_guard_error'),('ROOM_LAST_MEMBER_REQUIRED','global_end_other_T_guard_error'),('TARGET_CONTEXT_STALE','global_stale_context_error')]:case(name,'Error',err(code),expected_http_status=409)
# Search list filtering: absent/empty/all, explicit NULL sentinel and OR values.
searchname=x['paths']['/v2/raid-rooms/search']['post']['requestBody']['content']['application/json']['schema']['$ref'].split('/')[-1]
search=dict(category='all',admission_scope=None,group_ids=[],filter_context_token=None,member_conditions=[],raid_ids=[],difficulty_ids=[],limit=20,cursor=None,target_cycle_key=C)
case('search_experience_omitted_no_filter',searchname,search)
for value,name in [([], 'empty_no_filter'),(['unrestricted'],'stored_null_only'),(['experienced','unrestricted'],'OR_specific_and_stored_null'),(['unrestricted','experienced'],'same_set_reordered')]:
 z=copy.deepcopy(search);z['experience_levels']=value;case('search_experience_'+name,searchname,z)
for value,name in [(None,'null'),(['experienced','experienced'],'duplicate'),(['unknown'],'unknown'),(['null'],'null_string'),([''],'empty_value')]:
 z=copy.deepcopy(search);z['experience_levels']=value;case('search_experience_'+name+'_rejected',searchname,z,False)
# Full common-context -> request -> actual endpoint 200 examples.
common_flows=[]
for name,cycles,auth in [('common_settings_C_N',[C,N],C),('common_settings_N_only',[N],N)]:
 ctx=context('edit_common_settings',[impact(t,leader=True) for t in cycles],auth=auth)
 ctx['data']['context_token']=token+'-'+name
 req=copy.deepcopy(settings)
 for field,source in {'expected_cycle_key':'expected_cycle_key','expected_room_revision':'room_revision','context_token':'context_token'}.items():req[field]=ctx['data'][source]
 ack=dict(scope=copy.deepcopy(gscope),data=dict(command_id=ids[11 if auth==C else 12],outcome='applied',executed_at=now,room_id=ids[5],room_revision=8,affected_cycle_keys=cycles))
 case(name+'_context','CommonContext',ctx)
 case(name+'_request','CommonSettingsCommand',req)
 case(name+'_ACK','CommonSettingsAck',ack)
 common_flows.append(dict(context_case=name+'_context',request_case=name+'_request',response_case=name+'_ACK'))
 # The saved original ACK remains unchanged on replay; not current permission evidence.
 case(name+'_original_ACK_replay','CommonSettingsAck',ack,replay_of=name+'_ACK',scenario='Same key/body after expiry, week change or authority transfer; runtime behavior not executed')
noop=copy.deepcopy(ack);noop['data'].update(outcome='noop',room_revision=7,affected_cycle_keys=[])
case('common_settings_noop_ACK','CommonSettingsAck',noop)
for field in ['room_revision','affected_cycle_keys']:
 bad=copy.deepcopy(ack);del bad['data'][field]
 case('common_settings_missing_'+field+'_rejected','CommonSettingsAck',bad,False)
bad=copy.deepcopy(ack);bad['scope']['target_cycle_key']=N
case('common_settings_fabricated_scope_target_rejected','CommonSettingsAck',bad,False)
bad=copy.deepcopy(ack);bad['data']['target_cycle_key']=N
case('common_settings_fabricated_data_target_rejected','CommonSettingsAck',bad,False)
bad=copy.deepcopy(ack);bad['data']['affected_cycle_keys']=[N,N]
case('common_settings_duplicate_affected_cycle_rejected','CommonSettingsAck',bad,False)
notice='All UUIDs/tokens/catalog names are synthetic. Schema validation is not API/DB/transaction/permission execution. Guard outcomes and SQL/cursor rules are illustrative contract obligations.'
Path('docs/design/issue13-two-cycle.examples.json').write_text(json.dumps(dict(notice=notice,cases=cases,cas_bindings=bindings,common_settings_flows=common_flows,get_query_examples=[dict(query='',meaning='no experience filter'),dict(query='experience_levels=experienced&experience_levels=unrestricted',meaning='OR experienced/SQL NULL')]),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('examples',len(cases),'global context/request source bindings',len(bindings))
