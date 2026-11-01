#!/usr/bin/env python3
"""Runner-only restricted SSH. The production environment key stays in a temporary 0700 directory."""
import json
import os
import shlex
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

from common import canonical, validate_bundle, validate_manifest, require


def run(args, *, input=None, timeout=60):
    try:
        return subprocess.run(args, input=input, text=True, capture_output=True,
                              check=True, timeout=timeout).stdout
    except (subprocess.SubprocessError, OSError):
        raise RuntimeError('remote_control_failed') from None


def main():
    manifest = validate_manifest(json.loads(Path('dist/release.json').read_text()))
    expected_source = run(['git', 'rev-parse', 'HEAD']).strip()
    if manifest['source'] != expected_source or manifest['tag'] != os.environ['GITHUB_REF_NAME']:
        raise ValueError('release_identity_mismatch')
    bundle = validate_bundle({'manifest': manifest, 'compose': Path('dist/compose.lightsail.yaml').read_text(),
                              'attempt': os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'],
                              'run_url': 'https://github.com/heo0328/lostparty-backend/actions/runs/' + os.environ['GITHUB_RUN_ID'] + '/attempts/' + os.environ['GITHUB_RUN_ATTEMPT']})
    with tempfile.TemporaryDirectory(prefix='lostparty-ssh-') as directory:
        p = Path(directory); os.chmod(p, 0o700)
        (p / 'key').write_text(os.environ['LIGHTSAIL_DEPLOY_SSH_KEY'])
        os.chmod(p / 'key', 0o600)
        known_hosts = os.environ['LIGHTSAIL_SSH_KNOWN_HOSTS']
        lines = [line.split() for line in known_hosts.splitlines() if line.strip()]
        if not lines or any(len(line) != 3 or line[0] != '54.253.176.103' for line in lines):
            raise ValueError('pinned_host_keys_required')
        (p / 'known_hosts').write_text(known_hosts)
        ssh = ['ssh', '-i', str(p / 'key'), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
               '-o', 'UserKnownHostsFile=' + str(p / 'known_hosts'), 'lostparty-deploy@54.253.176.103']
        remote = []  # ssh_entrypoint.py permits only submit/preflight/status, never a shell.
        # A previous submit may have succeeded even when SSH returned an error.
        try:
            run(ssh + [shlex.join(remote + ['submit'])], input=canonical(bundle).decode())
        except RuntimeError:
            pass
        deadline = time.monotonic() + 850
        failures = 0
        while time.monotonic() < deadline:
            try:
                result = json.loads(run(ssh + [shlex.join(remote + ['status', bundle['attempt']])]))
                failures = 0
            except (RuntimeError, ValueError):
                failures += 1
                if failures > 6:
                    raise RuntimeError('status_unavailable_check_server_journal') from None
                time.sleep(5); continue
            if result['status'] in ('success', 'failed'):
                Path('dist/deployment-result.json').write_text(json.dumps(result, indent=2) + '\n')
                with open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a') as stream:
                    stream.write('```json\n' + json.dumps(result, indent=2) + '\n```\n')
                print(json.dumps(result))
                if result['status'] != 'success':
                    raise RuntimeError('deployment_failed_check_result')
                return
            time.sleep(5)
        raise RuntimeError('deployment_pending_check_server_journal')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Deployment failed or status unknown; consult server journal/Actions summary. No automatic blind retry.') from None
