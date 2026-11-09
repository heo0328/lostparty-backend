"""Keep published OpenAPI component IDs stable across internal package moves.

Only schema keys and schema references are mapped. Example values, descriptions,
model identity and the public contract snapshots are never rewritten.
"""

# Explicit internal-module -> published-module identity; do not infer by suffix.
_MODULE_IDS = {
    'app__raid_rooms__schemas__completion_correction_schemas': 'app__raid_rooms__completion_correction_schemas',
    'app__raid_rooms__schemas__admission_candidate_schemas': 'app__raid_rooms__admission_candidate_schemas',
    'app__raid_rooms__schemas__application_display_schemas': 'app__raid_rooms__application_display_schemas',
    'app__raid_rooms__models__completion_correction_models': 'app__raid_rooms__completion_correction_models',
    'app__raid_rooms__schemas__cycle_group_context_schemas': 'app__raid_rooms__cycle_group_context_schemas',
    'app__raid_rooms__participation__roster_participation': 'app__raid_rooms__roster_participation',
    'app__raid_rooms__schemas__membership_action_schemas': 'app__raid_rooms__membership_action_schemas',
    'app__raid_rooms__contracts__availability_contract': 'app__raid_rooms__availability_contract',
    'app__raid_rooms__models__cycle_application_models': 'app__raid_rooms__cycle_application_models',
    'app__raid_rooms__models__membership_action_models': 'app__raid_rooms__membership_action_models',
    'app__raid_rooms__schemas__session_display_schemas': 'app__raid_rooms__session_display_schemas',
    'app__raid_rooms__admissions__application_presets': 'app__raid_rooms__application_presets',
    'app__raid_rooms__participation__character_change': 'app__raid_rooms__character_change',
    'app__raid_rooms__group_links__group_link_display': 'app__raid_rooms__group_link_display',
    'app__raid_rooms__schemas__participation_commands': 'app__raid_rooms__participation_commands',
    'app__raid_rooms__schemas__weekly_summary_schemas': 'app__raid_rooms__weekly_summary_schemas',
    'app__raid_rooms__schemas__atomic_member_schemas': 'app__raid_rooms__atomic_member_schemas',
    'app__raid_rooms__models__cycle_lifecycle_models': 'app__raid_rooms__cycle_lifecycle_models',
    'app__raid_rooms__schemas__resume_review_schemas': 'app__raid_rooms__resume_review_schemas',
    'app__raid_rooms__contracts__admission_contract': 'app__raid_rooms__admission_contract',
    'app__raid_rooms__schemas__availability_schemas': 'app__raid_rooms__availability_schemas',
    'app__raid_rooms__models__cycle_planning_models': 'app__raid_rooms__cycle_planning_models',
    'app__raid_rooms__group_links__group_connection': 'app__raid_rooms__group_connection',
    'app__game_accounts__schemas__bootstrap_schemas': 'app__game_accounts__bootstrap_schemas',
    'app__raid_rooms__schemas__application_presets': 'app__raid_rooms__application_presets',
    'app__raid_rooms__schemas__continuation_router': 'app__raid_rooms__continuation_router',
    'app__raid_rooms__models__cycle_consent_models': 'app__raid_rooms__cycle_consent_models',
    'app__raid_rooms__schemas__cycle_group_schemas': 'app__raid_rooms__cycle_group_schemas',
    'app__raid_rooms__models__cycle_outcome_models': 'app__raid_rooms__cycle_outcome_models',
    'app__raid_rooms__models__roster_participation': 'app__raid_rooms__roster_participation',
    'app__raid_rooms__schemas__group_link_display': 'app__raid_rooms__group_link_display',
    'app__game_accounts__schemas__profile_schemas': 'app__game_accounts__profile_schemas',
    'app__game_accounts__rosters__roster_presence': 'app__game_accounts__roster_presence',
    'app__raid_rooms__schemas__admission_schemas': 'app__raid_rooms__admission_schemas',
    'app__raid_rooms__schemas__candidate_schemas': 'app__raid_rooms__candidate_schemas',
    'app__raid_rooms__models__cycle_group_models': 'app__raid_rooms__cycle_group_models',
    'app__raid_rooms__schemas__management_router': 'app__raid_rooms__management_router',
    'app__raid_rooms__api__weekly_summary_router': 'app__raid_rooms__weekly_summary_router',
    'app__game_accounts__models__roster_presence': 'app__game_accounts__roster_presence',
    'app__raid_rooms__schemas__character_change': 'app__raid_rooms__character_change',
    'app__raid_rooms__schemas__group_connection': 'app__raid_rooms__group_connection',
    'app__raid_rooms__models__integrated_models': 'app__raid_rooms__integrated_models',
    'app__raid_rooms__participation__management': 'app__raid_rooms__management',
    'app__raid_rooms__contracts__roster_openapi': 'app__raid_rooms__roster_openapi',
    'app__raid_rooms__schemas__schedule_schemas': 'app__raid_rooms__schedule_schemas',
    'app__game_accounts__schemas__batch_schemas': 'app__game_accounts__batch_schemas',
    'app__raid_rooms__api__application_presets': 'app__raid_rooms__application_presets',
    'app__raid_rooms__api__availability_router': 'app__raid_rooms__availability_router',
    'app__raid_rooms__schemas__command_schemas': 'app__raid_rooms__command_schemas',
    'app__raid_rooms__admissions__continuation': 'app__raid_rooms__continuation',
    'app__raid_rooms__api__continuation_router': 'app__raid_rooms__continuation_router',
    'app__raid_rooms__schemas__schedule_output': 'app__raid_rooms__schedule_output',
    'app__raid_rooms__schemas__schedule_router': 'app__raid_rooms__schedule_router',
    'app__game_accounts__api__bootstrap_router': 'app__game_accounts__bootstrap_router',
    'app__game_accounts__api__lifecycle_router': 'app__game_accounts__lifecycle_router',
    'app__game_accounts__models__power_success': 'app__game_accounts__power_success',
    'app__raid_rooms__schemas__member_schemas': 'app__raid_rooms__member_schemas',
    'app__game_accounts__power__power_success': 'app__game_accounts__power_success',
    'app__raid_rooms__api__completion_router': 'app__raid_rooms__completion_router',
    'app__raid_rooms__schemas__cycle_schemas': 'app__raid_rooms__cycle_schemas',
    'app__raid_rooms__api__management_router': 'app__raid_rooms__management_router',
    'app__raid_rooms__models__schedule_heads': 'app__raid_rooms__schedule_heads',
    'app__raid_rooms__schemas__search_router': 'app__raid_rooms__search_router',
    'app__game_accounts__api__profile_router': 'app__game_accounts__profile_router',
    'app__raid_rooms__api__admission_router': 'app__raid_rooms__admission_router',
    'app__raid_rooms__schemas__beta_schemas': 'app__raid_rooms__beta_schemas',
    'app__raid_rooms__schemas__continuation': 'app__raid_rooms__continuation',
    'app__raid_rooms__schemas__http_schemas': 'app__raid_rooms__http_schemas',
    'app__raid_rooms__models__resume_models': 'app__raid_rooms__resume_models',
    'app__raid_rooms__models__source_models': 'app__raid_rooms__source_models',
    'app__raid_rooms__outcomes__completion': 'app__raid_rooms__completion',
    'app__raid_rooms__models__cycle_models': 'app__raid_rooms__cycle_models',
    'app__raid_rooms__api__schedule_router': 'app__raid_rooms__schedule_router',
    'app__raid_rooms__models__weekly_links': 'app__raid_rooms__weekly_links',
    'app__game_accounts__api__batch_router': 'app__game_accounts__batch_router',
    'app__raid_rooms__models__beta_models': 'app__raid_rooms__beta_models',
    'app__raid_rooms__schemas__completion': 'app__raid_rooms__completion',
    'app__raid_rooms__schemas__cycle_wire': 'app__raid_rooms__cycle_wire',
    'app__raid_rooms__schemas__management': 'app__raid_rooms__management',
    'app__game_accounts__schemas__schemas': 'app__game_accounts__schemas',
    'app__raid_rooms__api__member_router': 'app__raid_rooms__member_router',
    'app__raid_rooms__api__search_router': 'app__raid_rooms__search_router',
    'app__game_accounts__common__support': 'app__game_accounts__support',
    'app__raid_rooms__schemas__commands': 'app__raid_rooms__commands',
    'app__raid_rooms__api__cycle_router': 'app__raid_rooms__cycle_router',
    'app__game_accounts__models__models': 'app__game_accounts__models',
    'app__raid_rooms__outcomes__resume': 'app__raid_rooms__resume',
    'app__raid_rooms__schemas__schemas': 'app__raid_rooms__schemas',
    'app__raid_rooms__schemas__resume': 'app__raid_rooms__resume',
    'app__raid_rooms__api__roster_api': 'app__raid_rooms__roster_api',
    'app__raid_rooms__models__models': 'app__raid_rooms__models',
    'app__game_accounts__api__router': 'app__game_accounts__router',
    'app__raid_rooms__api__router': 'app__raid_rooms__router',
}


def preserve(schema):
    definitions = schema.get('components', {}).get('schemas', {})
    renames = {}
    for name in definitions:
        for current, published in _MODULE_IDS.items():
            if name.startswith(current + '__'):
                target = published + name[len(current):]
                if target != name:
                    renames[name] = target
                break
    targets = [renames.get(name, name) for name in definitions]
    if len(targets) != len(set(targets)):
        raise ValueError('Published OpenAPI component identity collision')
    mapped = {renames.get(name, name): value for name, value in definitions.items()}
    definitions.clear()
    definitions.update(mapped)

    def reference(value):
        prefix = '#/components/schemas/'
        if value.startswith(prefix):
            key = value[len(prefix):]
            value = prefix + renames.get(key, key)
            if value[len(prefix):] not in definitions:
                raise ValueError('Unresolved OpenAPI component reference: ' + value)
        return value

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == '$ref' and isinstance(child, str):
                    value[key] = reference(child)
                elif key == 'discriminator' and isinstance(child, dict):
                    for tag, ref in child.get('mapping', {}).items():
                        child['mapping'][tag] = reference(ref) if ref.startswith('#/') else renames.get(ref, ref)
                    visit(child)
                elif key in ('schemas', 'properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas') and isinstance(child, dict):
                    for definition in child.values():
                        visit(definition)
                elif key not in ('example', 'examples', 'default', 'const', 'enum'):
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return schema
