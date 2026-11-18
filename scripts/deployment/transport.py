#!/usr/bin/env python3
"""Runner-only restricted SSH. The production environment key stays in a temporary 0700 directory."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from common import REPOSITORY, SHA, TAG, canonical, require, validate_bundle, validate_manifest

DEPLOY_HOST = '54.116.243.121'


def run(args, *, input=None, timeout=60):
    try:
        return subprocess.run(args, input=input, text=True, capture_output=True,
                              check=True, timeout=timeout).stdout
    except subprocess.CalledProcessError as error:
        if error.returncode == 255 and 'Permission denied (publickey' in (error.stderr or ''):
            raise RuntimeError('ssh_public_key_authentication_failed') from None
        raise RuntimeError('remote_control_failed') from None
    except (subprocess.SubprocessError, OSError):
        raise RuntimeError('remote_control_failed') from None


def pinned_host_keys(value):
    lines = [line.split() for line in value.splitlines() if line.strip()]
    if not lines or any(len(line) != 3 or line[0] != DEPLOY_HOST for line in lines):
        raise ValueError('pinned_seoul_host_keys_required')
    return value


def report(result, bundle):
    manifest = bundle['manifest']
    if (result.get('attempt') != bundle['attempt']
            or any(result.get(key) != manifest[key] for key in ('tag', 'source', 'image'))):
        raise ValueError('deployment_result_identity_mismatch')
    Path('dist/deployment-result.json').write_text(json.dumps(result, indent=2) + '\n')
    with open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a') as stream:
        stream.write('```json\n' + json.dumps(result, indent=2) + '\n```\n')
    print(json.dumps(result))
    if result['status'] != 'success':
        raise RuntimeError('deployment_failed_check_result')


def main():
    mode = require(os.environ['DEPLOYMENT_MODE'], r'preflight|deploy')
    tag = require(os.environ['RELEASE_TAG'], TAG)
    manifest = validate_manifest(json.loads(Path('dist/release.json').read_text()))
    expected_source = require(run(['git', 'rev-parse', 'refs/tags/' + tag + '^{commit}']).strip(), SHA)
    if manifest['source'] != expected_source or manifest['tag'] != tag:
        raise ValueError('release_identity_mismatch')
    bundle = validate_bundle({'manifest': manifest, 'compose': Path('dist/compose.lightsail.yaml').read_text(),
                              'attempt': os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'],
                              'run_url': f'https://github.com/{REPOSITORY}/actions/runs/' + os.environ['GITHUB_RUN_ID'] + '/attempts/' + os.environ['GITHUB_RUN_ATTEMPT']})
    with tempfile.TemporaryDirectory(prefix='lostparty-ssh-') as directory:
        p = Path(directory); os.chmod(p, 0o700)
        (p / 'key').write_text(os.environ['LIGHTSAIL_DEPLOY_SSH_KEY'])
        os.chmod(p / 'key', 0o600)
        (p / 'known_hosts').write_text(pinned_host_keys(os.environ['LIGHTSAIL_SSH_KNOWN_HOSTS']))
        ssh = ['ssh', '-F', '/dev/null', '-i', str(p / 'key'), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
               '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UserKnownHostsFile=' + str(p / 'known_hosts'),
               'lostparty-deploy@' + DEPLOY_HOST]
        if mode == 'preflight':
            result = json.loads(run(ssh + ['preflight'], input=canonical(bundle).decode(), timeout=120))
            if result.get('mode') != 'preflight_only':
                raise ValueError('preflight_result_required')
            report(result, bundle)
            return
        # A previous submit may have succeeded even when SSH returned an error.
        try:
            run(ssh + ['submit'], input=canonical(bundle).decode())
        except RuntimeError:
            pass
        deadline = time.monotonic() + 850
        failures = 0
        while time.monotonic() < deadline:
            try:
                result = json.loads(run(ssh + ['status ' + bundle['attempt']]))
                failures = 0
            except (RuntimeError, ValueError):
                failures += 1
                if failures > 6:
                    raise RuntimeError('status_unavailable_check_server_journal') from None
                time.sleep(5); continue
            if result['status'] in ('success', 'failed'):
                report(result, bundle)
                return
            time.sleep(5)
        raise RuntimeError('deployment_pending_check_server_journal')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if isinstance(error, RuntimeError) and error.args == ('ssh_public_key_authentication_failed',):
            raise SystemExit('The Seoul deployment account did not accept the configured SSH key.') from None
        raise SystemExit('Deployment failed or status unknown; consult server journal/Actions summary. No automatic blind retry.') from None
