"""Synthetic persisted head fixture, without a second power-success producer."""
import copy
from tests.game_accounts.analysis.test_analyzer import fixture, CASES, run_analysis


def detail_for(summary,role='dealer'):
    _,_,detail=run_analysis(fixture(CASES[0]))
    detail['detection']['detected_role']=role
    detail['detection']['catalog_version']=summary.get('catalog_version') or '2026.09.12.2'
    return copy.deepcopy(detail)
