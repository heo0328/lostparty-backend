"""Input spelling resolution must never weaken canonical identity/proof boundaries."""
import uuid
from sqlalchemy import select
import pytest
from app.core.database import session
from app.game_accounts import verification_context
from app.game_accounts.models import Registration, Verification, VerificationExecution
from tests.test_game_accounts import world, register, start, change, BASE, VERIFY
from tests.test_live_equipment_proof import live, confirm, assert_no_ownership


@pytest.mark.parametrize('name', ['mixedhero', 'MIXEDHERO', 'MiXeDhErO'])
@pytest.mark.parametrize('registered', [True, False])
def test_input_resolves_through_preview_registration_proof_and_owned_refresh(client, live, name, registered):
    h, state = live
    state['canonical'] = 'MixedHero'
    preview = client.post('/v1/game-accounts/preview', headers=h, json={'character_name': name})
    assert preview.status_code == 200
    assert preview.json()['characters'][0]['character_name'] == 'MixedHero'
    r = register(client, h, name) if registered else None
    if r:
        # Existing saved mixed-input registrations also resolve at challenge start.
        with session() as db, db.begin():
            db.get(Registration, uuid.UUID(r['registration_id'])).lookup_name = name
    v = start(client, h, r['registration_id'] if r else None, name=name)
    with session() as db:
        challenge = db.get(Verification, uuid.UUID(v['challenge_id']))
        assert challenge.lookup_name == 'MixedHero'
        assert challenge.identity_snapshot['proof_context']['target'] == ['sample-server', 'MixedHero']
        event = db.scalar(select(VerificationExecution).where(VerificationExecution.operation == 'start'))
        assert event.target_snapshot['context'] == challenge.identity_snapshot['proof_context']
    assert state['urls'][-1].endswith('/armories/characters/MixedHero')
    state['removed'] = v['required_slots']
    key = uuid.uuid4()
    result = confirm(client, h, v, key)
    assert result.status_code == 200 and result.json()['status'] == 'verified'
    calls = len(state['calls'])
    assert confirm(client, h, v, key).json() == result.json()
    assert len(state['calls']) == calls
    rid = client.get(BASE, headers=h).json()['items'][0]['registration_id']
    state['removed'] = ()
    refreshed = change(client, h, 'post', BASE+'/'+rid+'/refresh', {})
    assert refreshed.status_code == 200
    with session() as db:
        assert db.get(Registration, uuid.UUID(rid)).lookup_name == 'MixedHero'


def test_cache_and_idempotency_keep_original_input(client, live):
    h, state = live
    state['canonical'] = 'MixedHero'
    for name, calls in [('mixedhero', 1), ('mixedhero', 1), ('MIXEDHERO', 2)]:
        assert client.post('/v1/game-accounts/preview', headers=h, json={'character_name': name}).status_code == 200
        assert len(state['calls']) == calls
    key = uuid.uuid4()
    data = dict(lookup_character_name='mixedhero', label='sample', is_main=False)
    response = change(client, h, 'post', BASE, data, key)
    assert response.status_code == 201
    with session() as db:
        assert db.get(Registration, uuid.UUID(response.json()['registration_id'])).lookup_name == 'MixedHero'
    calls = len(state['calls'])
    assert change(client, h, 'post', BASE, data, key).json() == response.json()
    assert len(state['calls']) == calls
    conflict = change(client, h, 'post', BASE, dict(data, lookup_character_name='MIXEDHERO'), key)
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'


@pytest.mark.parametrize('kind', ['different', 'ambiguous_case', 'ambiguous_server'])
def test_missing_or_ambiguous_input_rejected_before_armory(client, live, kind):
    h, state = live
    state['canonical'] = 'OtherHero' if kind == 'different' else 'MixedHero'
    if kind != 'different':
        state['extra_rows'] = [dict(ServerName='other-server' if kind == 'ambiguous_server' else 'sample-server',
            CharacterName='MixedHero' if kind == 'ambiguous_server' else 'MIXEDHERO',
            CharacterClassName='sample-class', CharacterLevel=60, ItemAvgLevel='1700')]
    response = change(client, h, 'post', VERIFY, dict(source='direct_input', character_name='mixedhero'))
    assert response.status_code == 503
    assert state['calls'] == ['siblings']
    assert_no_ownership()


@pytest.mark.parametrize('kind', ['profile_case', 'profile_server', 'pinned_case', 'pinned_server'])
def test_case_resolution_does_not_relax_profile_or_pinned_target(client, live, kind):
    h, state = live
    state['canonical'] = 'MixedHero'
    v = start(client, h, name='mixedhero')
    state['removed'] = v['required_slots']
    if kind == 'profile_case': state['profile_name'] = 'mixedhero'
    if kind == 'profile_server': state['profile_server'] = 'other-server'
    if kind == 'pinned_case': state['canonical'] = 'MIXEDHERO'
    if kind == 'pinned_server':
        state['profile_server'] = state['roster_server'] = 'other-server'
    result = confirm(client, h, v)
    if kind.startswith('profile'):
        assert result.status_code == 503
    else:
        assert result.status_code == 200 and result.json()['result_code'] == 'ROSTER_EVIDENCE_PENDING'
    assert_no_ownership()


@pytest.mark.parametrize('name,canonical,accepted', [('한글Ab', '한글aB', True), ('ß', 'ss', False), ('K', 'k', False)])
def test_resolution_is_ascii_only_and_capture_stays_exact(name, canonical, accepted):
    rows = [dict(server_name='server', character_name=canonical)]
    assert verification_context.resolve_input(name, rows) == (canonical if accepted else None)
    assert verification_context.capture(name, rows) is None


@pytest.mark.parametrize('kind', ['submitted_case', 'api_case', 'api_server'])
def test_explicit_registration_target_remains_exact(client, live, kind):
    h, state = live
    state['canonical'] = 'MixedHero'
    r = register(client, h, 'mixedhero')
    if kind == 'api_case': state['canonical'] = 'MIXEDHERO'
    if kind == 'api_server': state['profile_server'] = state['roster_server'] = 'other-server'
    target = dict(server_name='sample-server', character_name='mixedhero' if kind == 'submitted_case' else 'MixedHero')
    response = change(client, h, 'post', VERIFY, dict(source='registration', registration_id=r['registration_id'],
        expected_registration_version=r['version'], target_character=target))
    assert response.status_code == (404 if kind == 'submitted_case' else 409)
    assert_no_ownership()
