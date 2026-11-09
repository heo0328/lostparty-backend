"""Test selection, publication gates and immutable evidence; no production access."""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
import validation
import release


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'VERSION').write_text('0.1.2\n')
        (self.root / 'tests').mkdir()
        for name in ('test_a.py', 'test_b.py'):
            (self.root / 'tests' / name).write_text('')
        self.plan = {'version': '0.1.2', 'mode': 'selected', 'baseline_tag': 'v0.1.1',
                     'change': 'isolated fix', 'impact': 'one feature', 'reason': 'bounded',
                     'tests': ['tests/test_a.py']}

    def load(self, plan=None):
        (self.root / validation.PLAN).write_text(json.dumps(self.plan if plan is None else plan))
        return validation.load_plan(self.root)

    def test_absent_defaults_full_and_preserves_no_plan_hash(self):
        plan = validation.load_plan(self.root)
        self.assertEqual(plan['mode'], 'full')
        self.assertIsNone(plan['plan_sha256'])

    def test_nested_feature_tests_are_selectable_without_weakening_path_checks(self):
        feature = self.root / 'tests' / 'raid_rooms' / 'participation'
        feature.mkdir(parents=True)
        (feature / 'test_nested.py').write_text('')
        selected = 'tests/raid_rooms/participation/test_nested.py'
        self.assertIn(selected, validation.all_tests(self.root))
        self.assertEqual(self.load({**self.plan, 'tests': [selected]})['tests'], [selected])
        for invalid in ('../' + selected, selected + '::test_any', selected.replace('test_nested', 'missing')):
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                self.load({**self.plan, 'tests': [invalid]})

    def test_exact_files_only_and_stale_or_invalid_plan_rejected(self):
        self.assertEqual(self.load()['tests'], ['tests/test_a.py'])
        for key, value in [('version', '0.1.1'), ('mode', 'skip'), ('tests', []),
                           ('tests', ['--collect-only']), ('tests', ['tests/test_a.py::test_x']),
                           ('tests', ['../tests/test_a.py']), ('tests', ['tests/missing.py']),
                           ('tests', ['tests/test_a.py'] * 2), ('reason', '')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.load({**self.plan, key: value})
        with self.assertRaises(ValueError):
            self.load({**self.plan, 'mode': 'full'})

    def test_protected_paths_and_renames_require_full(self):
        plan = self.load()
        protected = ['app/auth/router.py', 'app/core/database.py', 'app/main.py',
                     'app/groups/feature_models.py', 'app/game_accounts/verification/ownership_policy.py',
                     'alembic/versions/change.py', 'requirements.txt', 'Dockerfile',
                     '.github/workflows/a.yml', 'scripts/deployment/server.py',
                     'compose.lightsail.yaml', 'tests/conftest.py', '.dockerignore']
        for path in protected:
            with self.subTest(path=path), patch('release.api', return_value={'draft': False, 'prerelease': False}), \
                    patch('validation.subprocess.call', return_value=0), \
                    patch('validation.git', return_value=path), self.assertRaises(ValueError):
                validation.validate_baseline(plan)
        with patch('release.api', return_value={'draft': False, 'prerelease': False}), \
                patch('validation.subprocess.call', return_value=0), \
                patch('validation.git', return_value='app/raids/router.py') as diff:
            validation.validate_baseline(plan)
        self.assertIn('--no-renames', diff.call_args.args)

    def test_baseline_must_be_published_and_ancestor(self):
        plan = self.load()
        for result in (None, {'draft': True, 'prerelease': False}, {'draft': False, 'prerelease': True}):
            with patch('release.api', return_value=result), self.assertRaises(ValueError):
                validation.validate_baseline(plan)
        with patch('release.api', return_value={'draft': False, 'prerelease': False}), \
                patch('validation.subprocess.call', return_value=1), self.assertRaises(ValueError):
            validation.validate_baseline(plan)

    def test_selected_executes_only_explicit_files_and_propagates_failure(self):
        plan = self.load()
        with patch('validation.load_plan', return_value=plan), \
                patch.object(sys, 'argv', ['validation.py', 'regress']), \
                patch('validation.subprocess.call', return_value=7) as call:
            self.assertEqual(validation.main(), 7)
        command = call.call_args.args[0]
        self.assertIn('tests/test_a.py', command)
        self.assertNotIn('tests/test_b.py', command)

    def test_skipped_failed_or_cancelled_jobs_never_pass_gate(self):
        for verify in ('success', 'failure', 'skipped', 'cancelled', ''):
            for regression in ('success', 'failure', 'skipped', 'cancelled', ''):
                self.assertEqual(validation.successful(verify, regression),
                                 verify == regression == 'success')

    def evidence(self):
        plan = self.load()
        with patch.dict(os.environ, {'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'}), \
                patch('validation.git', return_value='a' * 40):
            return plan, validation.record(plan, 'success', 'success')

    def test_evidence_binds_source_plan_tests_mode_and_results(self):
        plan, evidence = self.evidence()
        self.assertEqual(evidence['checks']['docker_replace_rollback'], 'skipped')
        validation.verify_record(evidence, plan, 'a' * 40)
        for key, value in [('source', 'b' * 40), ('plan_sha256', 'b' * 64),
                           ('mode', 'full'), ('executed_tests', []), ('result', 'failure'),
                           ('run_url', 'https://untrusted.invalid')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validation.verify_record({**evidence, key: value}, plan, 'a' * 40)

    def test_existing_planned_release_requires_immutable_evidence(self):
        from test_deployment import MANIFEST, SOURCE, COMPOSE
        manifest = {**MANIFEST, 'compose_sha256': release.checksum(COMPOSE.encode())}
        temp_dist = self.root / 'dist'
        temp_dist.mkdir()
        (temp_dist / 'release.json').write_text(json.dumps(manifest))
        (temp_dist / 'compose.lightsail.yaml').write_text(COMPOSE)
        self.load()
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            with patch('release.api', return_value={'draft': False, 'prerelease': False, 'assets': []}), \
                    patch('release.run') as run, self.assertRaises(ValueError):
                release.existing('v0.1.0', SOURCE)
            self.assertFalse(any('create' in c.args[0] or 'upload' in c.args[0] or 'edit' in c.args[0]
                                 for c in run.call_args_list))
            # Legacy source without a plan remains readable and never gets evidence backfilled.
            (self.root / validation.PLAN).unlink()
            with patch('release.api', return_value={'draft': False, 'prerelease': False, 'assets': []}), \
                    patch('release.run'):
                self.assertEqual(release.existing('v0.1.0', SOURCE), manifest)
        finally:
            os.chdir(previous)

    def test_workflow_manual_publication_and_gate_wiring(self):
        workflow = (validation.ROOT / '.github/workflows/backend-release.yml').read_text()
        self.assertIn("github.event_name == 'push' && needs.validation.result == 'success'", workflow)
        self.assertIn("if: steps.plan.outputs.mode == 'full'", workflow)
        self.assertIn('shard: ${{ fromJSON(needs.verify.outputs.shards) }}', workflow)
        self.assertIn('name: ${{ needs.validation.outputs.artifact }}', workflow)
        self.assertNotIn('overwrite: true', workflow)

    def reuse_proof(self):
        prior = {'schema': 1, 'version': '0.1.1', 'mode': 'full',
                 'source': validation.REUSE['source'], 'result': 'success',
                 'checks': dict.fromkeys(('source', 'static', 'contracts', 'regression', 'docker_replace_rollback'), 'success'),
                 'run_url': f"https://github.com/{validation.REPOSITORY}/actions/runs/41417066498/attempts/1",
                 'executed_tests': ['tests/test_a.py', 'tests/test_b.py']}
        raw = json.dumps(prior)
        proof = {k: v for k, v in validation.REUSE.items() if k != 'version'}
        proof.update(record_json=raw, record_sha256=validation.checksum(raw.encode()))
        self.enterContext(patch.dict(validation.REUSE, {'record_sha256': proof['record_sha256']}))
        self.enterContext(patch('validation.all_tests', return_value=prior['executed_tests']))
        return proof

    def test_reuse_version_and_empty_new_test_list_are_required(self):
        plan = {**self.plan, 'mode': 'reuse', 'tests': []}
        self.assertEqual(self.load(plan)['mode'], 'reuse')
        with self.assertRaises(ValueError):
            self.load({**plan, 'tests': ['tests/test_a.py']})
        (self.root / 'VERSION').write_text('0.1.3\n')
        with self.assertRaises(ValueError):
            self.load({**plan, 'version': '0.1.3'})

    def test_reuse_rejects_executable_changes_in_either_source_comparison(self):
        validation.check_reuse_changes(['docs/project/DEV_LOG.md', 'AGENTS.md'],
                                       list(validation.RELEASE_PREPARATION))
        for path in ['app/groups/admissions.py', 'alembic/change.py', 'requirements.txt',
                     'Dockerfile', 'compose.lightsail.yaml', '.dockerignore', 'tests/test_a.py',
                     'scripts/deployment/server.py', 'docs/tools/change.py']:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validation.check_reuse_changes([path], [])
                with self.assertRaises(ValueError):
                    validation.check_reuse_changes([], [path])

    def test_reuse_proof_binds_bytes_identity_and_original_full_success(self):
        proof = self.reuse_proof()
        validation.verify_reuse_proof(proof)
        for key, value in [('source', 'b' * 40), ('approved_source', 'c' * 40),
                           ('artifact_id', 1), ('record_json', proof['record_json'] + ' ')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validation.verify_reuse_proof({**proof, key: value})
        for key, value in [('result', 'failure'), ('mode', 'selected'), ('executed_tests', [])]:
            bad = json.loads(proof['record_json']); bad[key] = value
            raw = json.dumps(bad); checksum = validation.checksum(raw.encode())
            with patch.dict(validation.REUSE, {'record_sha256': checksum}), self.assertRaises(ValueError):
                validation.verify_reuse_proof({**proof, 'record_json': raw, 'record_sha256': checksum})

    def test_reuse_fetch_requires_successful_run_and_unexpired_bound_artifact(self):
        proof = self.reuse_proof()
        plan = self.load({**self.plan, 'mode': 'reuse', 'tests': []})
        run = {'status': 'completed', 'conclusion': 'success', 'head_sha': validation.REUSE['source'],
               'repository': {'full_name': validation.REPOSITORY}, 'path': '.github/workflows/backend-release.yml'}
        artifact = {'expired': False, 'name': 'validation-41417066498-1',
                    'workflow_run': {'id': 41417066498, 'head_sha': validation.REUSE['source']}}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('validation.json', proof['record_json'])
        with patch('validation.git', side_effect=['docs/project/DEV_LOG.md', 'VERSION']), \
                patch('validation.subprocess.call', return_value=0), \
                patch('release.api', side_effect=[run, artifact]), \
                patch('validation.subprocess.check_output', return_value=buffer.getvalue()):
            self.assertEqual(validation.reuse_evidence(plan), proof)
        for bad in (None, {**run, 'conclusion': 'failure'}, {**run, 'head_sha': 'b' * 40}):
            with patch('validation.git', return_value=''), patch('validation.subprocess.call', return_value=0), \
                    patch('release.api', return_value=bad), self.assertRaises(ValueError):
                validation.reuse_evidence(plan)
        with patch('validation.git', return_value=''), patch('validation.subprocess.call', return_value=0), \
                patch('release.api', side_effect=[run, {**artifact, 'expired': True}]), \
                patch('validation.subprocess.check_output') as download, self.assertRaises(ValueError):
            validation.reuse_evidence(plan)
        download.assert_not_called()
        with patch('validation.subprocess.call', return_value=1), patch('release.api') as api, self.assertRaises(ValueError):
            validation.reuse_evidence(plan)
        api.assert_not_called()

    def test_reuse_record_is_explicit_and_prior_evidence_survives_offline(self):
        proof = self.reuse_proof()
        plan = self.load({**self.plan, 'mode': 'reuse', 'tests': []})
        with patch.dict(os.environ, {'GITHUB_RUN_ID': '456', 'GITHUB_RUN_ATTEMPT': '1'}), \
                patch('validation.git', return_value='d' * 40), \
                patch('validation.reuse_evidence', return_value=proof):
            data = validation.record(plan, 'success', 'success')
        self.assertEqual(data['schema'], 2)
        self.assertEqual(data['executed_tests'], [])
        self.assertEqual(data['checks']['regression'], 'reused')
        with patch('release.api') as api:
            validation.verify_record(data, plan, 'd' * 40)
        api.assert_not_called()
        for changes in ({'schema': 1}, {'source': 'a' * 40}, {'reused_validation': {}},
                        {'checks': {**data['checks'], 'regression': 'success'}}):
            with self.assertRaises(ValueError):
                validation.verify_record({**data, **changes}, plan, 'd' * 40)

    def test_reuse_regression_checks_provenance_without_running_pytest(self):
        proof = self.reuse_proof()
        plan = self.load({**self.plan, 'mode': 'reuse', 'tests': []})
        with patch('validation.load_plan', return_value=plan), \
                patch.object(sys, 'argv', ['validation.py', 'regress']), \
                patch('validation.reuse_evidence', return_value=proof), \
                patch('validation.subprocess.call') as call:
            self.assertEqual(validation.main(), 0)
        call.assert_not_called()
        workflow = (validation.ROOT / '.github/workflows/backend-release.yml').read_text()
        self.assertIn("if: steps.plan.outputs.mode != 'reuse'", workflow)
        self.assertIn('actions: read', workflow)

    def test_reuse_prepare_schedules_one_provenance_job(self):
        proof = self.reuse_proof()
        plan = self.load({**self.plan, 'mode': 'reuse', 'tests': []})
        output = self.root / 'output'
        with patch('validation.load_plan', return_value=plan), \
                patch.object(sys, 'argv', ['validation.py', 'prepare']), \
                patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), \
                patch('validation.validate_baseline'), \
                patch('validation.reuse_evidence', return_value=proof):
            self.assertEqual(validation.main(), 0)
        self.assertEqual(output.read_text(), 'mode=reuse\nshards=[0]\n')


class LocalReuseTests(unittest.TestCase):
    def proof(self):
        return {k: v for k, v in validation.LOCAL_REUSE.items() if k != 'version'} | {
            'record_json': {p: (validation.ROOT / p).read_text() for p in validation.LOCAL_REUSE['records']}}

    def test_pinned_local_records_and_ancestry_are_required(self):
        proof = self.proof()
        self.assertEqual(validation.verify_reuse_proof(proof, '2.0.0'), proof)
        for key, value in [('source', 'a' * 40), ('approved_source', 'b' * 40),
                           ('records', {}), ('record_json', {})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validation.verify_reuse_proof({**proof, key: value}, '2.0.0')
        bad = copy.deepcopy(proof)
        path = next(iter(bad['record_json']))
        bad['record_json'][path] += ' '
        with self.assertRaises(ValueError):
            validation.verify_local_proof(bad)
        with patch('validation.subprocess.call', return_value=1), self.assertRaises(ValueError):
            validation.local_reuse_evidence()
        with patch('validation.subprocess.call', return_value=0), \
                patch('validation.git', side_effect=['app/main.py', 'VERSION']), self.assertRaises(ValueError):
            validation.local_reuse_evidence()

    def test_local_release_records_scoped_reuse_without_claiming_full_tests(self):
        plan = validation.load_plan()
        self.assertEqual(plan['version'], '2.0.0')
        with patch.dict(os.environ, {'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'}), \
                patch('validation.git', return_value='a' * 40), \
                patch('validation.reuse_evidence', return_value=self.proof()):
            evidence = validation.record(plan, 'success', 'success')
        self.assertEqual(evidence['executed_tests'], [])
        self.assertEqual(evidence['checks']['regression'], 'reused')
        self.assertEqual(evidence['checks']['docker_replace_rollback'], 'skipped')
        validation.verify_record(evidence, plan, 'a' * 40)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'VERSION').write_text('2.0.1')
            (root / validation.PLAN).write_text(json.dumps({k: v for k, v in plan.items() if k != 'plan_sha256'} | {'version': '2.0.1'}))
            with self.assertRaises(ValueError):
                validation.load_plan(root)


if __name__ == '__main__':
    unittest.main()
