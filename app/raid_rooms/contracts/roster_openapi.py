"""Publish explicit opt-in variants without changing any default strict DTO."""
from copy import deepcopy
import json
from pathlib import Path


# Reviewed method/template pairs. Keep query opt-in separate from read metadata.
# Runtime/query parity is checked for every route; subclasses with no opt-in stay out.
PARTICIPATION_OPERATIONS = frozenset({
    ('get', '/v2/groups/{group_id}/raid-room-character-candidates'),
    ('get', '/v2/groups/{group_id}/raid-room-member-projections'),
    ('get', '/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context'),
    ('get', '/v2/me/raid-room-applications'),
    ('get', '/v2/me/raid-room-character-issues'),
    ('get', '/v2/me/raid-room-creation-context'),
    ('get', '/v2/me/raid-room-filter-context'),
    ('get', '/v2/me/raid-room-memberships'),
    ('get', '/v2/me/raid-rooms/{room_id}/availability-submission'),
    ('get', '/v2/me/raid-rooms/{room_id}/common-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/continuation-choices'),
    ('get', '/v2/me/raid-rooms/{room_id}/continuation-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/leadership-transfer-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/opening-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/participation-cancellation-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/plan'),
    ('get', '/v2/me/raid-rooms/{room_id}/schedule-context'),
    ('get', '/v2/me/raid-rooms/{room_id}/settings'),
    ('get', '/v2/me/raid-schedule-overlaps'),
    ('get', '/v2/raid-room-applications/{application_id}'),
    ('get', '/v2/raid-rooms'),
    ('get', '/v2/raid-rooms/{room_id}'),
    ('get', '/v2/raid-rooms/{room_id}/admission-character-candidates'),
    ('get', '/v2/raid-rooms/{room_id}/admission-context'),
    ('get', '/v2/raid-rooms/{room_id}/applications'),
    ('get', '/v2/raid-rooms/{room_id}/command-context'),
    ('get', '/v2/raid-rooms/{room_id}/detail'),
    ('get', '/v2/raid-rooms/{room_id}/member-removal-context'),
    ('get', '/v2/raid-rooms/{room_id}/membership-action-context'),
    ('get', '/v2/raid-rooms/{room_id}/personal-completion-departure-context'),
    ('get', '/v2/raid-schedule-groups/{group_id}/candidates'),
    ('post', '/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections'),
    ('post', '/v2/raid-room-applications/{application_id}/approve'),
    ('post', '/v2/raid-room-applications/{application_id}/reject'),
    ('post', '/v2/raid-room-applications/{application_id}/withdraw'),
    ('post', '/v2/raid-rooms'),
    ('post', '/v2/raid-rooms/search'),
    ('post', '/v2/raid-rooms/{room_id}/applications'),
    ('post', '/v2/raid-rooms/{room_id}/character-changes'),
    ('post', '/v2/raid-rooms/{room_id}/continuation-declines'),
    ('post', '/v2/raid-rooms/{room_id}/continuation-participations'),
    ('post', '/v2/raid-rooms/{room_id}/end'),
    ('post', '/v2/raid-rooms/{room_id}/join'),
    ('post', '/v2/raid-rooms/{room_id}/leadership-transfers'),
    ('post', '/v2/raid-rooms/{room_id}/leave'),
    ('post', '/v2/raid-rooms/{room_id}/member-removals'),
    ('post', '/v2/raid-rooms/{room_id}/membership-actions'),
    ('post', '/v2/raid-rooms/{room_id}/participation-cancellations'),
    ('post', '/v2/raid-rooms/{room_id}/personal-completion-departures'),
    ('post', '/v2/raid-rooms/{room_id}/recruitment-openings'),
    ('post', '/v2/raid-rooms/{room_id}/removals'),
    ('post', '/v2/raid-rooms/{room_id}/schedule-proposals'),
    ('post', '/v2/raid-rooms/{room_id}/weekly-incomplete-closures'),
    ('post', '/v2/raid-rooms/{room_id}/weekly-resume-proposals'),
    ('post', '/v2/raid-rounds/{round_id}/completion'),
    ('post', '/v2/raid-rounds/{round_id}/personal-completion'),
    ('post', '/v2/raid-schedule-groups/{group_id}/selections'),
    ('post', '/v2/raid-schedule-proposals/{proposal_id}/responses'),
    ('post', '/v2/raid-sessions/{session_id}/participation-confirmations'),
    ('put', '/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion'),
    ('put', '/v2/me/raid-rooms/{room_id}/availability-submission'),
    ('put', '/v2/raid-rooms/{room_id}/common-settings'),
    ('put', '/v2/raid-rooms/{room_id}/formation'),
    ('put', '/v2/raid-rooms/{room_id}/schedule-groups'),
    ('put', '/v2/raid-rooms/{room_id}/settings'),
})


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
    for method,path in PARTICIPATION_OPERATIONS:
        parameter(api['paths'][path][method],'participation_profile',['remaining-active-1'])
    for path,item in api['paths'].items():
        if not path.startswith('/v2/') or not ('raid-rooms' in path or 'raid-room-' in path):continue
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
