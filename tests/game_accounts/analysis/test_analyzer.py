"""Synthetic Native _hybridBuildFixture port; contains no live armory data."""
import copy
import json
import unittest
from pathlib import Path
from app.game_accounts.analysis.analyzer import analyze, AnalysisUnavailable

CASES = json.loads(Path(__file__).with_name('fixtures').joinpath('hybrid_branches.json').read_text())['cases']
STAMP = '2026-11-16T08:00:00Z'


def fixture(case):
    return {'ArmoryProfile': {'ServerName': '가상서버', 'CharacterName': '가상캐릭터',
            'CharacterClassName': case['className'], 'CombatPower': '1,200.50', 'ItemAvgLevel': '1,700.00'},
        'ArmorySkills': [],
        'ArmoryGem': {'Gems': [{'Slot': 0, 'Level': 10}], 'Effects': {'Skills': [
            {'GemSlot': 0, 'Name': case['gemTarget'], 'Description': []}]}},
        'ArkPassive': {'Effects': [{'Description': f'깨달음 1티어 {case["tier1"]} Lv.1'},
                                  {'Description': f'깨달음 4티어 {case["tier4"]} Lv.1'}]},
        'ArkGrid': {'Slots': [{'Name': '질서의 해 : 계약 fixture', 'Grade': '유물', 'Point': 17,
            'Tooltip': json.dumps({'Element_000': {'type': 'ItemPartBox', 'value': {
                'Element_000': '코어 옵션 발동 조건',
                'Element_001': f'1티어 {case["tier1"]} 활성화 필요 4티어 {case["tier4"]} 활성화 필요'}}})}]}}


def run_analysis(raw):
    return analyze(raw, server_name='가상서버', character_name='가상캐릭터',
                   class_name=raw['ArmoryProfile']['CharacterClassName'], lifecycle_revision=1, fetched_at=STAMP)


class AnalyzerTests(unittest.TestCase):
    def test_eight_native_branch_definitions(self):
        for case in CASES:
            with self.subTest(class_name=case['className'], role=case['role']):
                role, summary, detail = run_analysis(fixture(case))
                self.assertEqual(role, case['role'])
                self.assertEqual(detail['detection']['branch_id'], case['branchId'])
                self.assertEqual(detail['detection']['matched_related_nodes'], [case['tier4']])
                self.assertEqual(detail['gems'][0]['category'], 'passive_or_identity')
                self.assertEqual(detail['ark_grid_conditions'][0]['missing_passive_names'], [])
                self.assertEqual(summary['combat_power'], '1200.50')
                self.assertEqual(summary['integrity_status'], 'error')
                self.assertIn({'code': 'ARK_GRID_MINIMUM', 'severity': 'error'}, summary['issues'])

    def test_clean_and_setting_error_keep_numeric_observation(self):
        case = CASES[0];raw = fixture(case)
        raw['ArmorySkills'] = [{'Name': f'가상스킬{i}', 'Rune': {}} for i in range(8)]
        raw['ArmoryGem']['Gems'] = [{'Slot': i, 'Level': 10, 'Tooltip': '[바드]'} for i in range(11)]
        raw['ArmoryGem']['Effects']['Skills'] = [{'GemSlot': i, 'Name': case['gemTarget'], 'Description': ['효과']} for i in range(11)]
        raw['ArkGrid']['Slots'].append({'Name': '질서의 달 : 계약 fixture', 'Grade': '유물', 'Point': 17})
        _, summary, detail = run_analysis(raw)
        self.assertEqual(summary['integrity_status'], 'clean')
        self.assertEqual(summary['issues'], [])
        self.assertEqual(detail['equipped_gem_count'], 11)
        raw['ArmoryProfile']['CombatPower'] = '0'
        raw['ArmoryGem']['Gems'].pop()
        _, summary, _ = run_analysis(raw)
        self.assertEqual(summary['combat_power'], '0')
        self.assertEqual(summary['integrity_status'], 'error')

    def test_null_and_absent_source_are_not_zero(self):
        raw=fixture(CASES[0]);raw['ArmoryProfile']['CombatPower']=None
        raw.pop('ArmoryGem')
        _, summary, detail = run_analysis(raw)
        self.assertIsNone(summary['combat_power']);self.assertIsNone(summary['combat_power_observed_at'])
        self.assertEqual(summary['analyzed_at'], STAMP)
        self.assertIsNone(detail['equipped_gem_count'])
        raw['ArmoryGem']={'Gems': [], 'Effects': {'Skills': []}}
        _, _, detail = run_analysis(raw)
        self.assertEqual(detail['equipped_gem_count'], 0)
        self.assertTrue(detail['gem_effects_source_available'])

    def test_role_and_identity_fail_without_fallback(self):
        for change in ['tier4', 'ambiguous', 'unsupported', 'identity', 'number']:
            raw=fixture(CASES[0])
            if change=='tier4':raw['ArkPassive']['Effects'].pop()
            elif change=='ambiguous':raw['ArkPassive']['Effects'].append({'Description':'깨달음 1티어 진실된 용맹 Lv.1'})
            elif change=='unsupported':raw['ArmoryProfile']['CharacterClassName']='없는직업'
            elif change=='identity':raw['ArmoryProfile']['CharacterName']='다른캐릭터'
            else:raw['ArmoryProfile']['CombatPower']='NaN'
            with self.subTest(change=change), self.assertRaises(AnalysisUnavailable):run_analysis(raw)

    def test_gem_foreign_and_unknown_target(self):
        raw=fixture(CASES[0]);raw['ArmoryGem']['Gems'][0]['Tooltip']='[홀리나이트]'
        _, summary, detail=run_analysis(raw)
        self.assertEqual(detail['gems'][0]['validation_status'],'foreign_class')
        self.assertIn({'code':'FOREIGN_CLASS_GEM','severity':'error'},summary['issues'])
        raw['ArmoryGem']['Gems'][0]['Tooltip']='[바드]'
        raw['ArmoryGem']['Effects']['Skills'][0]['Name']='없는스킬'
        _, summary, detail=run_analysis(raw)
        self.assertEqual(detail['gems'][0]['validation_status'],'same_class_target_unverified')
        self.assertIn({'code':'UNMATCHED_SKILL_GEM','severity':'error'},summary['issues'])

    def test_grid_recommendation_condition_and_invalid_tooltip(self):
        raw=fixture(CASES[0]);raw['ArkGrid']['Slots'][0]['Point']=14
        _, summary, _=run_analysis(raw)
        self.assertIn({'code':'ARK_GRID_RELIC_POINT','severity':'warning'},summary['issues'])
        raw['ArkGrid']['Slots'][0]['Tooltip']='{'
        with self.assertRaises(AnalysisUnavailable):run_analysis(raw)

    def test_input_is_not_mutated(self):
        raw=fixture(CASES[0]);before=copy.deepcopy(raw)
        run_analysis(raw)
        self.assertEqual(raw,before)
