import copy
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy import func
from app.core.database import session
from app.core.database import now
from app.game_accounts.character_profiles import profiles
from app.game_accounts.models.models import Account
from app.game_accounts.models.models import Character
from app.game_accounts.models.models import Registration
from app.game_accounts.models.models import NameClaim
from app.game_accounts.models.models import CharacterRoleSummary
from app.game_accounts.models.models import RequestResult
from app.game_accounts.models.models import Configuration
from app.game_accounts.models.models import Activity
from app.game_accounts.common.support import GameError
from tests.game_accounts.test_game_accounts import world
from tests.game_accounts.test_game_accounts import register
from tests.game_accounts.test_game_accounts import verify
from tests.game_accounts.test_game_accounts import page
from tests.game_accounts.test_game_accounts import change
from tests.game_accounts.test_game_accounts import another_user
from tests.game_accounts.test_game_accounts import BASE

STAMP = '2026-10-15T12:00:00Z'


def summary():
    return dict(source='server_analysis', analysis_rules_version='flutter-v1', analyzed_at=STAMP,
                combat_power='12345.00', item_level='1700', combat_power_observed_at=STAMP,
                item_level_observed_at=STAMP, integrity_status='clean', catalog_version='2026.09.12.2',
                issues=[], observed_lifecycle_revision=1)


def data():
    return dict(expected_version=1, expected_ownership_revision=1,
                expected_lifecycle_revision=1, summary=summary())


def path(cid): return '/v2/me/characters/'+str(cid)
def get(client, h, cid): return client.get(path(cid)+'/personal-profile', headers=h)
def put(client, h, cid, body=None, role='dealer', key=None):
    # Fixture observation only: exercise the NEW production command/CAS/storage path.
    # No client analysis endpoint or member key is emulated.
    from unittest.mock import patch
    from tests.game_accounts.analysis.test_analyzer import fixture, CASES, run_analysis
    from app.game_accounts.analysis import service as analysis
    payload = data() if body is None else body
    _, _, detail = run_analysis(fixture(CASES[0]))
    detail['detection']['detected_role'] = role
    detail['detection']['catalog_version'] = payload['summary']['catalog_version']
    command = dict(command_id=str(key or uuid.uuid4()), character_id=str(cid),
        expected_ownership_revision=payload['expected_ownership_revision'],
        expected_lifecycle_revision=payload['expected_lifecycle_revision'],
        expected_summary_versions=dict(dealer=payload['expected_version'],support=payload['expected_version']), trigger='manual')
    observed = dict(role=role,summary=payload['summary'],detail=detail)
    with patch.object(analysis, 'collect', return_value=observed):
        response = client.post('/v2/me/character-analysis/refresh',headers=h,json=dict(items=[command]))
    assert response.status_code == 200, response.text
    assert response.json()['items'][0]['state'] == 'saved', response.text
    return response


@pytest.fixture
def owned(client, world):
    h, state = world
    r = register(client, h, main=True)
    verify(client, h, state, r['registration_id'])
    p = page(client, h, r['registration_id'])
    return h, r, p['characters']['items'][0]['character_id']
