"""Publish explicit opt-in variants without changing any default strict DTO."""
from copy import deepcopy
import json
from pathlib import Path


def decorate(api, *, two_cycle=False):
    schemas=api['components']['schemas']
    definitions=json.loads(Path(__file__).with_name('roster_metadata.schema.json').read_text())
    schemas.update(definitions)
    def ref(name):return {'$ref':'#/components/schemas/'+name}
    def extend(name,prefix,fields):
        key=prefix+name
        value=deepcopy(schemas[name]);value['title']=key
        value['properties'].update(fields)
        value['required']=list(dict.fromkeys([*value.get('required',[]),*fields]))
        schemas[key]=value
        return key
    def parameter(op,name,values):
        if not any(p.get('name')==name for p in op.get('parameters',[])):
            op.setdefault('parameters',[]).append(dict(name=name,**{'in':'query'},required=False,
                schema=dict(type='string',enum=values),description='Explicit opt-in; omitted preserves default response.'))
    if not two_cycle:
        char=extend('LifecycleCharacterOut','RosterPresence_',{'roster_presence':ref('RosterPresence')})
        chars=extend('LifecycleCharactersOut','RosterPresence_',{'roster_presence_scope':ref('RosterPresenceScope')})
        schemas[chars]['properties']['items']['items']=ref(char)
        registration=deepcopy(schemas['BootstrapRegistration']);registration['properties']['characters']=ref(chars)
        registration['title']='RosterPresence_BootstrapRegistration';schemas[registration['title']]=registration
        bootstrap=deepcopy(schemas['AccountBootstrap']);bootstrap['properties']['registrations']['items']=ref(registration['title'])
        bootstrap['title']='RosterPresence_AccountBootstrap';schemas[bootstrap['title']]=bootstrap
        for path,base,new in [('/v2/me/account-bootstrap','AccountBootstrap',bootstrap['title']),
                ('/v2/me/game-accounts/{registration_id}/characters','LifecycleCharactersOut',chars)]:
            op=api['paths'][path]['get'];parameter(op,'include_roster_presence',['true','false'])
            op['responses']['200']['content']['application/json']['schema']={'anyOf':[ref(base),ref(new)]}
        return api
    for path,item in api['paths'].items():
        if not path.startswith('/v2/') or not ('raid-rooms' in path or 'raid-room-' in path):continue
        for method,op in item.items():
            if method in ('get','post','put','delete','patch'):parameter(op,'participation_profile',['remaining-active-1'])
        op=item.get('get')
        if not op:continue
        warn=path.endswith(('/raid-room-memberships','/detail','/plan'))
        change=path.endswith(('/admission-character-candidates','/admission-context'))
        if not warn and not change:continue
        schema=op['responses']['200']['content']['application/json']['schema']
        originals=schema.get('anyOf',[schema]);branches=deepcopy(originals)
        for branch in originals:
            if '$ref' not in branch:continue
            name=branch['$ref'].rsplit('/',1)[1]
            pn=extend(name,'Participation_',{'participation_context':ref('RosterParticipationChangeContext' if change else 'RosterParticipationReadContext')})
            branches.append(ref(pn))
            if warn:
                field='character_issues' if path.endswith('/raid-room-memberships') else 'character_issue_context'
                fields={field:ref('RosterIssuePage' if field=='character_issues' else 'RosterIssueRoomContext')}
                branches.extend([ref(extend(name,'RosterIssues_',fields)),ref(extend(pn,'RosterIssues_',fields))])
        op['responses']['200']['content']['application/json']['schema']={'anyOf':branches}
        if warn:parameter(op,'include_character_issues',['true','false'])
    api['paths']['/v2/me/raid-room-character-issues']['get']['responses']['200']['content']['application/json']['schema']=ref('RosterIssueSummary')
    api['x-roster-participation']=dict(required_schema='0036_roster_presence',participation_profile='remaining-active-1',
        default_shape='preserved',capability='affected room/actual week/generation only; original ACK first',
        history='preserved assignments never replaced; current character derives only from active assignments')
    api['x-roster-participation']['next_cycle_selection']=dict(
        scope='new participation/opening after source active assignments become empty; existing target participation preserved',
        unselected=dict(selection=None,permission=dict(allowed=False,reason='CHARACTER_SELECTION_REQUIRED',next_change_at=None)),
        command_status=409,
        recovery='Explicit character_id and selected_role; current ownership/activity/eligibility required; completed history is not a default selection',
        schema='Existing nullable context selection and permission.reason string; command selection remains required; original ACK replay preserved; malformed/null command selection remains 400 INVALID_REQUEST')
    return api
