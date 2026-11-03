"""Test selection, publication gates and immutable evidence; no production access."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
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
                     'app/groups/feature_models.py', 'app/game_accounts/ownership_policy.py',
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


if __name__ == '__main__':
    unittest.main()
