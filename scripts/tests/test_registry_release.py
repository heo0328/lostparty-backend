"""First-publication registry auth and failure semantics; no credentials/network used."""
import io
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
from release import IMAGE, registry_digest, safe_failure


class Response(io.BytesIO):
    headers = {'Docker-Content-Digest': 'sha256:' + 'a' * 64}


class RegistryTests(unittest.TestCase):
    def test_publisher_requests_push_scope_before_first_package_exists(self):
        with patch.dict(os.environ, {'GITHUB_ACTOR': 'test-owner', 'GH_TOKEN': 'synthetic-token'}), patch('release.urllib.request.urlopen', side_effect=[Response(b'{"token":"synthetic-registry-token"}'), Response(b'')]) as request:
            self.assertEqual(registry_digest(IMAGE + ':sha-' + 'b' * 40), 'sha256:' + 'a' * 64)
        first = request.call_args_list[0].args[0]
        self.assertTrue(first.full_url.endswith(':pull,push'))
        self.assertTrue(first.has_header('Authorization'))

    def test_anonymous_probe_never_sends_github_credentials(self):
        with patch('release.urllib.request.urlopen', side_effect=[Response(b'{"token":"synthetic-registry-token"}'), Response(b'')]) as request:
            registry_digest(IMAGE + '@sha256:' + 'a' * 64, anonymous=True)
        first = request.call_args_list[0].args[0]
        self.assertTrue(first.full_url.endswith(':pull'))
        self.assertFalse(first.has_header('Authorization'))

    def test_only_missing_manifest_is_treated_as_absent(self):
        for status in [404, 401, 503]:
            error = urllib.error.HTTPError('https://ghcr.io', status, 'synthetic', {}, None)
            with self.subTest(status=status), patch.dict(os.environ, {'GITHUB_ACTOR': 'test-owner', 'GH_TOKEN': 'synthetic-token'}), patch('release.urllib.request.urlopen', side_effect=[Response(b'{"token":"synthetic-registry-token"}'), error]):
                if status == 404:
                    self.assertIsNone(registry_digest(IMAGE + ':v0.1.0'))
                else:
                    with self.assertRaises(ValueError):
                        registry_digest(IMAGE + ':v0.1.0')


class SafeFailureTests(unittest.TestCase):
    def test_exception_text_and_response_are_never_exposed(self):
        import json
        import subprocess
        secret = 'synthetic-secret-canary'
        for error in [RuntimeError(secret), ValueError(secret), KeyError(secret),
                      subprocess.CalledProcessError(7, ['private', secret], output=secret, stderr=secret),
                      urllib.error.HTTPError('https://private/' + secret, 403, secret, {}, None)]:
            with self.subTest(kind=type(error).__name__):
                self.assertNotIn(secret, json.dumps(safe_failure(error)))
        self.assertEqual(safe_failure(KeyError('GH_TOKEN'))['missing_environment_name'], 'GH_TOKEN')
        self.assertEqual(safe_failure(urllib.error.HTTPError('https://private', 403, secret, {}, None))['http_status'], 403)

    def test_control_location_is_reported_without_traceback_source(self):
        with patch('release.urllib.request.urlopen', side_effect=OSError('synthetic-secret-canary')), patch.dict(os.environ, {'GITHUB_ACTOR': 'test', 'GH_TOKEN': 'synthetic-secret-canary'}):
            try:
                registry_digest(IMAGE + ':v0.1.0')
            except OSError as error:
                result = safe_failure(error)
        self.assertEqual(result['location']['function'], 'registry_digest')
        self.assertNotIn('synthetic-secret-canary', str(result))
