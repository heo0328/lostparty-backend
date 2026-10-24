"""Host-only orchestration safety tests; no Docker/DB/keys required."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import isolated_checks as checks
import verify_isolated as runner

ENV = {
    'DATABASE_URL': 'postgresql+psycopg://postgres:test-only-password@test-db/lostparty_test',
    'AUTH_SECRET_DIR': '/tmp/auth-test-keys', 'LOSTPARTY_ISOLATED_TEST': '1',
    'OWNERSHIP_WORKER_ENABLED': '0', 'RECRUITMENT_WORKER_ENABLED': '0',
}


class SafetyTests(unittest.TestCase):
    def test_only_explicit_test_environment_is_accepted(self):
        with patch.dict(os.environ, ENV, clear=True):
            checks.require_test_environment()
        for field, value in (
            ('DATABASE_URL', 'postgresql+psycopg://postgres:test-only-password@db/lostparty_test'),
            ('DATABASE_URL', 'postgresql+psycopg://postgres:test-only-password@test-db/development'),
            ('DATABASE_URL', ENV['DATABASE_URL'] + '?host=db'),
            ('AUTH_SECRET_DIR', '/run/secrets'), ('LOSTPARTY_ISOLATED_TEST', '0'),
            ('RECRUITMENT_WORKER_ENABLED', '1'),
        ):
            with self.subTest(field=field, value=value), patch.dict(os.environ, ENV | {field: value}, clear=True):
                with self.assertRaises(ValueError):
                    checks.require_test_environment()

    def test_selection_cannot_inject_options_or_cross_suites(self):
        for name in ('--override-ini=addopts=anything', '../tests/test_auth.py',
                     'tests/test_application_item_level.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checks.selected_tests('legacy', [name])
        self.assertEqual(checks.selected_tests('legacy', ['tests/test_auth.py::test_unknown']),
                         ['tests/test_auth.py::test_unknown'])

    def test_all_suite_includes_each_named_set_and_current_test_files(self):
        all_files = set(checks.SUITES['all'])
        self.assertEqual(all_files, {str(p.relative_to(checks.ROOT)) for p in (checks.ROOT / 'tests').glob('test_*.py')})
        for name in ('legacy', 'two-cycle'):
            self.assertTrue(set(checks.SUITES[name]) <= all_files)
            checks.selected_tests(name, [])

    def test_compose_overrides_are_removed(self):
        with patch.dict(os.environ, {'COMPOSE_FILE': 'compose.yaml', 'COMPOSE_PROJECT_NAME': 'live'}, clear=True):
            env = runner.docker_environment()
        self.assertEqual(env, {'COMPOSE_DISABLE_ENV_FILE': '1'})

    def test_failure_is_preserved_and_cleanup_uses_same_unique_project(self):
        with patch.object(runner.subprocess, 'run'), patch.object(runner.subprocess, 'call', side_effect=[5, 0]) as call:
            self.assertEqual(runner.main(['legacy', 'tests/test_auth.py']), 5)
        test_cmd, cleanup_cmd = [c.args[0] for c in call.call_args_list]
        self.assertEqual(test_cmd[:6], cleanup_cmd[:6])
        self.assertTrue(test_cmd[3].startswith('lostparty-check-'))
        self.assertIn('--no-deps', test_cmd)
        self.assertIn('down', cleanup_cmd)
        self.assertNotIn('--volumes', cleanup_cmd)

    def test_build_failure_still_cleans_project_and_skips_tests(self):
        with patch.object(runner.subprocess, 'run', side_effect=subprocess.CalledProcessError(17, 'build')), \
                patch.object(runner.subprocess, 'call', return_value=0) as call:
            self.assertEqual(runner.main(['contracts']), 17)
        self.assertEqual(call.call_count, 1)
        self.assertIn('down', call.call_args.args[0])

    def test_cleanup_failure_is_not_a_success(self):
        with patch.object(runner.subprocess, 'run'), patch.object(runner.subprocess, 'call', side_effect=[0, 1]):
            self.assertNotEqual(runner.main(['contracts']), 0)

    def test_contract_only_never_starts_db(self):
        with patch.object(runner.subprocess, 'run') as run, patch.object(runner.subprocess, 'call', return_value=0):
            self.assertEqual(runner.main(['contracts']), 0)
        self.assertEqual(run.call_count, 1)
        self.assertIn('build', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
