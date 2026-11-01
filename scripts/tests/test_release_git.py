"""Real, offline Git reproduction of the annotated tag checkout collision."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
from release import refresh_branches


class ReleaseGitTests(unittest.TestCase):
    def test_checkout_commit_tag_does_not_block_branch_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            remote = Path(directory) / 'origin'
            runner = Path(directory) / 'runner'

            def git(path, *args):
                return subprocess.check_output(['git', '-C', str(path), *args],
                                               text=True, stderr=subprocess.PIPE).strip()

            remote.mkdir()
            git(remote, 'init', '-b', 'main')
            git(remote, 'config', 'user.email', 'test@example.invalid')
            git(remote, 'config', 'user.name', 'Offline test')
            git(remote, 'commit', '--allow-empty', '-m', 'release source')
            source = git(remote, 'rev-parse', 'HEAD')
            git(remote, 'branch', 'dev')
            git(remote, 'tag', '-a', 'v0.1.0', '-m', 'immutable release')
            tag_object = git(remote, 'rev-parse', 'refs/tags/v0.1.0')
            git(Path(directory), 'clone', str(remote), str(runner))
            # Exact checkout log operation: replace runner-local annotated ref with commit.
            git(runner, 'fetch', '--no-tags', 'origin',
                '+' + source + ':refs/tags/v0.1.0')
            git(runner, 'checkout', '--detach', 'v0.1.0')
            broken = subprocess.run(['git', '-C', str(runner), 'fetch', 'origin',
                                     'main', 'dev', '--tags'], capture_output=True, text=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn('would clobber existing tag', broken.stderr)
            # Advance validation branches to prove refresh is real, not a skipped fetch.
            git(remote, 'commit', '--allow-empty', '-m', 'branch advance')
            latest = git(remote, 'rev-parse', 'HEAD')
            git(remote, 'branch', '-f', 'dev', latest)
            with patch('release.run', side_effect=lambda args: git(runner, *args[1:])):
                refresh_branches()
            for branch in ('main', 'dev'):
                self.assertEqual(git(runner, 'rev-parse', 'origin/' + branch), latest)
            self.assertEqual(git(runner, 'rev-parse', 'HEAD'), source)
            self.assertEqual(git(runner, 'rev-parse', 'refs/tags/v0.1.0'), source)
            self.assertEqual(git(remote, 'rev-parse', 'refs/tags/v0.1.0'), tag_object)


if __name__ == '__main__':
    unittest.main()
