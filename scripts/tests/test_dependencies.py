"""Lock failures that would otherwise silently change installation."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_dependencies as check


class LockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('requirements.txt', 'requirements-dev.txt', 'requirements.in', 'requirements-dev.in'):
            (self.root / name).write_text((check.ROOT / name).read_text())

    def test_changed_direct_version_requires_lock_update(self):
        path = self.root / 'requirements.in'
        path.write_text(path.read_text().replace('fastapi==0.115.12', 'fastapi==0.115.13'))
        with self.assertRaisesRegex(ValueError, 'differs from lock'):
            check.locked(self.root)

    def test_missing_hash_is_rejected(self):
        path = self.root / 'requirements.txt'
        path.write_text(path.read_text().replace(' --hash=sha256:', ' # ', 1))
        with self.assertRaises(ValueError):
            check.locked(self.root)

    def test_test_lock_cannot_override_runtime(self):
        path = self.root / 'requirements-dev.txt'
        path.write_text(path.read_text() + next(line for line in (self.root / 'requirements.txt').read_text().splitlines() if line.startswith('fastapi==')) + '\n')
        with self.assertRaisesRegex(ValueError, 'override'):
            check.locked(self.root)

    def test_installed_drift_is_rejected(self):
        with patch.object(check.metadata, 'distributions', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'Installed package set differs'):
                check.verify_installed({'fastapi': ('0.115.12', '')})


if __name__ == '__main__':
    unittest.main()
