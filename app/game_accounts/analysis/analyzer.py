"""Pure server analysis port of Native 302243fb; never performs HTTP or DB I/O."""
import json
import re
from functools import lru_cache
from pathlib import Path

RULES_VERSION = 'lostparty-server-role-analysis-v1'
HYBRID_CLASSES = frozenset(('바드', '발키리', '도화가', '홀리나이트'))


class AnalysisUnavailable(ValueError):
    """Safe, bounded error code; never attach provider input."""


def rows(value):
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def mapping(value):
    return value if isinstance(value, dict) else {}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def plain(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', value).replace('&nbsp;', ' ').replace('|', ' ')).strip()


@lru_cache(maxsize=1)
def catalog():
    value = json.loads(Path(__file__).with_name('catalog.json').read_text())
    if value.get('schemaVersion') != 2 or not isinstance(value.get('classes'), list):
        raise AnalysisUnavailable('ANALYSIS_UNAVAILABLE')
    return value


def decimal(value):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if not isinstance(value, str):
        raise AnalysisUnavailable('ANALYSIS_UNAVAILABLE')
    normalized = value.replace(',', '').strip()
    if len(normalized) > 32 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', normalized):
        raise AnalysisUnavailable('ANALYSIS_UNAVAILABLE')
    return normalized


def tooltip_strings(value):
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return
        try:
            decoded = json.loads(value)
        except (ValueError, RecursionError):
            decoded = None
        if isinstance(decoded, (dict, list)):
            yield from tooltip_strings(decoded)
        else:
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from tooltip_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from tooltip_strings(child)


def analyze(raw, *, server_name, character_name, class_name, lifecycle_revision, fetched_at, source=None):
    """Return (detected role, summary, detail), or fail without replacing a head."""
    if not isinstance(raw, dict):
        raise AnalysisUnavailable('UPSTREAM_INVALID_RESPONSE')
    if any(not isinstance(v,str) or not v.strip() for v in (server_name,character_name,class_name)):
        raise AnalysisUnavailable('UPSTREAM_INVALID_RESPONSE')
    profile = mapping(raw.get('ArmoryProfile'))
    if any(profile.get(k) != expected for k, expected in (
            ('ServerName', server_name), ('CharacterName', character_name), ('CharacterClassName', class_name))):
        raise AnalysisUnavailable('UPSTREAM_INVALID_RESPONSE')
    data = catalog() if source is None else source
    definitions = data['classes']
    definition = next((d for d in definitions if class_name.strip().lower() in
                       [n.strip().lower() for n in [d['apiClassName'], *d.get('aliases', [])]]), None)
    if definition is None:
        raise AnalysisUnavailable('ROLE_DETECTION_UNAVAILABLE')
    active = set()
    for effect in rows(mapping(raw.get('ArkPassive')).get('Effects')):
        description = effect.get('Description')
        match = re.search(r'\d+티어\s+(.+?)\s+Lv\.\d+', plain(description)) if isinstance(description, str) else None
        if match:
            active.add(match[1].strip())
    # Preserve observed names for grid conditions and add explicit catalog aliases.
    for b in definition['enlightenmentBranches']:
        if any(alias in active for alias in b.get('aliases', [])):
            active.add(b['tier1NodeName'])
    branches = [b for b in definition['enlightenmentBranches'] if b['tier1NodeName'] in active]
    branch = branches[0] if len(branches) == 1 else None
    related = list(dict.fromkeys(n for b in branches for n in b['relatedPassiveNodes'] if n in active))
    role = branch['inferredRole'] if class_name.strip() in HYBRID_CLASSES and branch and related else (
        'dealer' if class_name.strip() not in HYBRID_CLASSES else None)
    if role is None:
        raise AnalysisUnavailable('ROLE_DETECTION_UNAVAILABLE')
    detection = dict(status='detected' if branch else 'ambiguous' if branches else 'branch_not_found',
        catalog_version=data['catalogVersion'], class_id=definition['classId'],
        branch_id=branch['branchId'] if branch else None, branch_display_name=branch['displayName'] if branch else None,
        detected_role=role, matched_tier1_node=branch['tier1NodeName'] if branch else None, matched_related_nodes=related)
    skill_rows = rows(raw.get('ArmorySkills'))
    skill_names = {s['Name'] for s in skill_rows if isinstance(s.get('Name'), str)}
    rune_count = sum(isinstance(s.get('Rune'), dict) for s in skill_rows)
    notices = []
    def notice(code, message, severity='warning'):
        notices.append(dict(code=code, severity=severity, message=message))
    if rune_count != 8:
        notice('rune_count', f'장착된 룬이 {rune_count}개입니다. 일반 스킬 8개의 룬 설정을 확인해 주세요.')
    specials = definition.get('specialSkills', [])
    branch_id = branch['branchId'] if branch else None
    catalog_skills = set()
    for skill in specials:
        if branch_id is None or branch_id in skill['relatedBranchIds']:
            catalog_skills.update([skill['name'], *skill.get('aliases', [])])
    for target in definition.get('gemSkillTargets', []):
        if branch_id is None or any(s['skillId'] in target['relatedSpecialSkillIds'] and
                                   branch_id in s['relatedBranchIds'] for s in specials):
            catalog_skills.update([target['name'], *target.get('aliases', [])])
    known = {name.strip().lower(): d['apiClassName'] for d in definitions
             for name in [d['apiClassName'], *d.get('aliases', [])]}
    known[class_name.strip().lower()] = class_name.strip()
    armory_gem = mapping(raw.get('ArmoryGem'))
    slots = {g['Slot']: g for g in rows(armory_gem.get('Gems'))
             if type(g.get('Slot')) is int and type(g.get('Level')) is int}
    gems = []
    for effect in rows(mapping(armory_gem.get('Effects')).get('Skills')):
        slot, name = effect.get('GemSlot'), effect.get('Name')
        if type(slot) is not int or not isinstance(name, str):
            continue
        category = 'normal' if name in skill_names else 'passive_or_identity' if name in catalog_skills else 'unknown'
        classes = sorted({known[m[1].strip().lower()] for text in tooltip_strings([
            slots.get(slot, {}).get('Tooltip'), effect.get('Tooltip'), effect.get('Description')])
            for m in re.finditer(r'\[([^\[\]]+)\]', plain(text)) if m[1].strip().lower() in known})
        validation = ('unavailable' if not classes else 'foreign_class' if class_name.strip().lower() not in
                      [c.lower() for c in classes] else 'same_class_target_unverified' if category == 'unknown' else 'verified')
        gems.append(dict(slot=slot, level=slots.get(slot, {}).get('Level', 0), target=name,
            descriptions=[plain(v) for v in effect.get('Description', []) if isinstance(v, str)] if isinstance(effect.get('Description'), list) else [],
            category=category, validation_status=validation))
        if validation == 'foreign_class':
            notice(f'foreign_class_gem_{slot}', f'{name} 보석은 다른 직업 보석입니다: {", ".join(classes)}')
        elif validation == 'same_class_target_unverified':
            notice(f'unmatched_skill_gem_{slot}', f'{name} 보석은 현재 스킬 또는 등록 특수 스킬에 없습니다.')
    for slot in slots:
        if not any(g['slot'] == slot for g in gems):
            notice(f'unmapped_gem_{slot}', f'{slot}번 보석의 적용 효과를 확인할 수 없습니다.')
    gems.sort(key=lambda g: g['slot'])
    equipped = len(armory_gem['Gems']) if isinstance(armory_gem.get('Gems'), list) else None
    available = isinstance(mapping(armory_gem.get('Effects')).get('Skills'), list)
    cores, conditions = [], []
    sun = moon = None
    for core in rows(mapping(raw.get('ArkGrid')).get('Slots')):
        name, grade, point = core.get('Name'), core.get('Grade'), core.get('Point')
        if isinstance(name, str) and isinstance(grade, str) and type(point) is int and name.startswith(('질서의 해', '질서의 달')):
            if point < 0:
                raise AnalysisUnavailable('ANALYSIS_UNAVAILABLE')
            if name.startswith('질서의 해'):
                sun = max(point, sun) if sun is not None else point
            else:
                moon = max(point, moon) if moon is not None else point
            recommended = 17 if grade in ('유물', '고대') else 14
            cores.append(dict(name=name, grade=grade, point=point, minimum_point=14, recommended_point=recommended))
            if point < 14:
                notice('ark_grid_required_point', f'{name}이 {point}P입니다. 필수 14P 효과가 활성화되지 않았습니다.')
            elif point < recommended:
                notice('ark_grid_relic_point', f'{name}이 {point}P입니다. 유물 이상 코어의 17P 효과가 활성화되지 않았습니다.')
        if not isinstance(name, str) or not isinstance(core.get('Tooltip'), str):
            continue
        try:
            decoded = json.loads(core['Tooltip'])
        except (ValueError, RecursionError):
            raise AnalysisUnavailable('ANALYSIS_UNAVAILABLE') from None
        condition = None
        for element in mapping(decoded).values():
            if mapping(element).get('type') != 'ItemPartBox':
                continue
            parts = [plain(t) for t in strings(element.get('value')) if plain(t)]
            index = next((i for i, t in enumerate(parts) if '코어 옵션 발동 조건' in t), None)
            if index is not None and index + 1 < len(parts):
                condition = ' '.join(parts[index+1:]).strip()
                break
        if condition is None:
            continue
        required = []
        exclusive = re.search(r'^(.+?)\s*전용', condition)
        if exclusive and exclusive[1].strip():
            required.append(exclusive[1].strip())
        for m in re.finditer(r'(?:아크 패시브\s*)?\d+티어\s+(.+?)\s+활성화 필요', condition):
            if m[1].strip() and m[1].strip() not in required:
                required.append(m[1].strip())
        missing = [n for n in required if n not in active]
        conditions.append(dict(core_name=name, condition_text=condition, required_passive_names=required, missing_passive_names=missing))
        if not required:
            notice('unreadable_ark_grid_condition', f'{name}의 발동 조건을 자동으로 판독하지 못했습니다.', 'info')
        elif missing:
            notice('inactive_ark_grid_condition', f'{name}에 필요한 아크패시브가 활성화되지 않았습니다: {", ".join(missing)}')
    if sun is None:
        notice('ark_grid_missing_order_sun', '질서의 해 코어가 없습니다. 필수 14P 효과를 확인해 주세요.')
    if moon is None:
        notice('ark_grid_missing_order_moon', '질서의 달 코어가 없습니다. 필수 14P 효과를 확인해 주세요.')
    issues = {}
    def issue(code, severity='error'):
        issues[code] = dict(code=code, severity=severity)
    if equipped is not None and equipped < 11:
        issue('GEM_SLOT_COUNT')
    if any(g['validation_status'] == 'foreign_class' for g in gems):
        issue('FOREIGN_CLASS_GEM')
    if any(g['validation_status'] == 'same_class_target_unverified' for g in gems):
        issue('UNMATCHED_SKILL_GEM')
    if equipped is None or not available or any(g['validation_status'] == 'unavailable' for g in gems):
        issue('GEM_UNAVAILABLE', 'warning')
    if sun is None or moon is None or sun < 14 or moon < 14:
        issue('ARK_GRID_MINIMUM')
    if any(c['missing_passive_names'] for c in conditions):
        issue('ARK_GRID_CONDITION')
    if rune_count != 8:
        issue('RUNE_COUNT', 'warning')
    if any(c['point'] < c['recommended_point'] and c['point'] >= 14 for c in cores):
        issue('ARK_GRID_RELIC_POINT', 'warning')
    status = 'error' if any(i['severity'] == 'error' for i in issues.values()) else 'review' if issues else 'clean'
    power, level = decimal(profile.get('CombatPower')), decimal(profile.get('ItemAvgLevel'))
    stamp = fetched_at.isoformat() if hasattr(fetched_at, 'isoformat') else fetched_at
    summary = dict(source='server_analysis', analysis_rules_version=RULES_VERSION, analyzed_at=stamp,
        combat_power=power, item_level=level, combat_power_observed_at=stamp if power is not None else None,
        item_level_observed_at=stamp if level is not None else None, integrity_status=status,
        catalog_version=data['catalogVersion'], issues=list(issues.values()), observed_lifecycle_revision=lifecycle_revision)
    detail = dict(detection=detection, rune_count=rune_count, equipped_gem_count=equipped,
        gem_effects_source_available=available, gems=gems, ark_grid_core_points=cores,
        ark_grid_conditions=conditions, ark_grid_minimum=dict(order_sun_point=sun, order_moon_point=moon, required_point=14), notices=notices)
    return role, summary, detail
