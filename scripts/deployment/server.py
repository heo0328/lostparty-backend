#!/usr/bin/env python3
"""Installed on Lightsail. No migrations, credentials output, or repository checkout."""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import ROOT, canonical, checksum, require, utc, validate_bundle

STATE = Path('/var/lib/lostparty-deploy')
INSTALLED = Path('/usr/local/lib/lostparty-deploy/server.py')


class DeployError(Exception):
    """Controlled error code only: subprocess stderr/env never escapes."""


def atomic(path, value):
    path = Path(path)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def command(args, *, input=None, timeout=120):
    try:
        return subprocess.run(args, input=input, capture_output=True, text=True,
                              check=True, timeout=timeout).stdout
    except (subprocess.SubprocessError, OSError):
        raise DeployError('command_failed') from None


class Platform:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.base = ['docker', 'compose', '--project-directory', str(self.root),
                     '--env-file', str(self.root / '.env.lightsail'), '--profile', 'public']

    def compose(self, file, *args, timeout=120):
        return command(self.base + ['-f', str(file), *args], timeout=timeout)

    def config(self, file):
        return json.loads(self.compose(file, 'config', '--format', 'json'))

    def containers(self):
        result = {}
        for service in ('api', 'db', 'caddy'):
            ids = command(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=lostparty-lightsail',
                           '--filter', 'label=com.docker.compose.service=' + service]).split()
            if len(ids) != 1:
                raise DeployError('unexpected_container_count')
            result[service] = json.loads(command(['docker', 'inspect', ids[0]]))[0]
        return result

    def pull(self, image):
        command(['docker', 'pull', image], timeout=300)

    def image_info(self, image):
        return json.loads(command(['docker', 'image', 'inspect', image]))[0]

    def image_revision(self, image):
        code = "from alembic.config import Config; from alembic.script import ScriptDirectory; print(ScriptDirectory.from_config(Config('alembic.ini')).get_current_head())"
        # No environment, network, DB or host keys mounted into this process.
        return command(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                        '--entrypoint', 'python', image, '-c', code]).strip()

    def db_revision(self, api_id):
        code = "from app.core.database import engine; from sqlalchemy import text;\nwith engine().connect() as c:\n c.exec_driver_sql('SET TRANSACTION READ ONLY'); r=c.execute(text('SELECT version_num FROM alembic_version')).scalars().all(); assert len(r)==1; print(r[0])"
        return command(['docker', 'exec', api_id, 'python', '-c', code]).strip()

    def protected_files(self):
        paths = [self.root / '.env.lightsail', *(self.root / '.secrets/lightsail').glob('*')]
        return {str(p): (checksum(p.read_bytes()), p.stat().st_mode, p.stat().st_uid, p.stat().st_gid)
                for p in paths if p.is_file()}

    def replace(self, compose):
        self.compose(compose, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                     '--force-recreate', '--wait', '--wait-timeout', '100', 'api', timeout=115)

    def probes(self):
        for path, expected in (('/health', 200), ('/v1/raid-catalog', 200), ('/v1/me', 401)):
            try:
                response = urllib.request.urlopen('https://lostparty.duckdns.org' + path, timeout=5)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                if response.code != expected:
                    raise DeployError('https_probe_failed')
                if path == '/health' and json.load(response) != {'status': 'ok', 'database': 'ok'}:
                    raise DeployError('database_health_failed')

    def healthy(self, expected_image):
        containers = self.containers()
        api = containers['api']
        return (all(c['State']['Running'] for c in containers.values()) and
                containers['db']['State'].get('Health', {}).get('Status') == 'healthy' and api['Image'] == self.image_info(expected_image)['Id'] and
                api['State'].get('Health', {}).get('Status') == 'healthy')


def infrastructure(config, *, current_entrypoint=False):
    """Preserve runtime config; schema2 also permits the equivalent factory alias."""
    data = json.loads(json.dumps(config))
    data['services']['api'].pop('image', None)
    data['services']['api'].pop('build', None)
    if current_entrypoint:
        cmd=data['services']['api'].get('command')
        if isinstance(cmd,list):
            data['services']['api']['command']=[
                'app.main:create_app' if arg=='app.main:create_two_cycle_app' else arg for arg in cmd]
    return data


def service_identity(container):
    return (container['Id'], container['State']['StartedAt'], container['Mounts'])


def health(platform, image, deadline):
    while time.monotonic() < deadline:
        try:
            if platform.healthy(image):
                platform.probes()
                return
        except (DeployError, OSError, ValueError):
            pass
        time.sleep(2)
    raise DeployError('health_timeout')


def initial_state(platform):
    containers = platform.containers()
    compose = platform.root / 'compose.lightsail.yaml'
    api = containers['api']
    if not all(c['State']['Running'] for c in containers.values()) or api['State'].get('Health', {}).get('Status') != 'healthy':
        raise DeployError('baseline_unhealthy')
    # Persist an image-ID override: bootstrap source is intentionally untagged.
    config = platform.config(compose)
    config['services']['api']['image'] = api['Image']
    config['services']['api'].pop('build', None)
    frozen = STATE / 'baseline.compose.json'
    atomic(frozen, config)
    source = command(['git', '-C', str(platform.root), 'rev-parse', 'HEAD']).strip()
    return {'tag': None, 'source': source, 'image': api['Image'], 'compose': str(frozen),
            'db_revision': platform.db_revision(api['Id']), 'recorded_at_utc': utc()}


def execute(bundle, platform, state=STATE, *, preflight=False):
    """Caller holds host lock. Journal survives runner/SSH disconnects."""
    validate_bundle(bundle)
    manifest = bundle['manifest']
    request = state / bundle['attempt']
    request.mkdir(mode=0o700, exist_ok=True)
    result_file = request / ('preflight.json' if preflight else 'result.json')
    signature = checksum(canonical(bundle))
    # Reconcile any older interrupted journal under the same host-wide lock before a new attempt.
    for journal in state.glob('*/result.json'):
        if journal == result_file:
            continue
        prior = json.loads(journal.read_text())
        if prior.get('status') == 'in_progress':
            if preflight:
                raise DeployError('deployment_in_progress_preflight_blocked')
            previous = prior.get('previous_good')
            if previous:
                try:
                    platform.replace(previous['compose'])
                    health(platform, previous['image'], time.monotonic() + 120)
                    atomic(state / 'current.json', previous)
                    prior['rollback'] = 'success'
                except Exception:
                    prior.update(status='failed', error='interrupted', rollback='failed', finished_at_utc=utc())
                    atomic(journal, prior)
                    raise DeployError('previous_attempt_recovery_failed') from None
            prior.update(status='failed', error='interrupted', finished_at_utc=utc())
            atomic(journal, prior)
    if result_file.exists():
        existing = json.loads(result_file.read_text())
        if existing['request_sha256'] != signature:
            raise DeployError('attempt_identity_conflict')
        if existing['status'] != 'in_progress':
            return existing
        # A host/process interruption during replacement is never assumed successful.
        if preflight:
            raise DeployError('incomplete_preflight')
        previous = existing.get('previous_good')
        if previous:
            try:
                platform.replace(previous['compose'])
                health(platform, previous['image'], time.monotonic() + 120)
                atomic(state / 'current.json', previous)
                existing.update(status='failed', error='interrupted', rollback='success', finished_at_utc=utc())
            except Exception:
                existing.update(status='failed', error='interrupted', rollback='failed', finished_at_utc=utc())
            atomic(result_file, existing)
            return existing
    current = json.loads((state / 'current.json').read_text())
    record = {'status': 'in_progress', 'request_sha256': signature, 'started_at_utc': utc(),
              'tag': manifest['tag'], 'source': manifest['source'], 'image': manifest['image'],
              'db_revision': manifest['db_revision'], 'contract_sha256': manifest['contract_sha256'],
              'configuration_revision': current.get('configuration_revision', 'lightsail-release-azp-20261101'),
              'run_url': bundle['run_url'], 'attempt': bundle['attempt'],
              'user_acceptance': 'not_checked', 'rollback': 'not_needed'}
    atomic(result_file, record)
    changed = False
    try:
        if current.get('tag') and tuple(map(int, manifest['tag'][1:].split('.'))) < tuple(map(int, current['tag'][1:].split('.'))):
            raise DeployError('older_release_blocked')
        before = platform.containers()
        protected = platform.protected_files()
        if not platform.healthy(current['image']):
            raise DeployError('current_api_unhealthy_or_drifted')
        baseline = platform.config(current['compose'])
        # Compare frozen baseline to live containers' actual config before replacement.
        live_api = before['api']
        expected_command = baseline['services']['api'].get('command')
        if expected_command is not None and live_api['Config'].get('Cmd') != expected_command:
            raise DeployError('runtime_command_drift')
        expected_env = sorted(k + '=' + str(v) for k, v in baseline['services']['api'].get('environment', {}).items())
        if not set(expected_env).issubset(set(live_api['Config']['Env'])):
            raise DeployError('runtime_environment_drift')
        if shutil.disk_usage(platform.root).free < 3 * 1024 ** 3:
            raise DeployError('insufficient_disk')
        compose = request / 'candidate.compose.yaml'
        compose.write_text(bundle['compose']); os.chmod(compose, 0o600)
        candidate = platform.config(compose)
        if infrastructure(candidate,current_entrypoint=manifest['schema']==2) != infrastructure(baseline,current_entrypoint=manifest['schema']==2):
            raise DeployError('manual_infrastructure_change_required')
        if platform.db_revision(live_api['Id']) != manifest['db_revision']:
            raise DeployError('manual_migration_required')
        if preflight:
            platform.probes()
            record.update(status='success', mode='preflight_only', finished_at_utc=utc())
            atomic(result_file, record)
            return record
        platform.pull(manifest['image'])
        image = platform.image_info(manifest['image'])
        if (image.get('Architecture') != 'amd64' or image.get('Os') != 'linux' or
                image['Config'].get('Labels', {}).get('org.opencontainers.image.revision') != manifest['source'] or
                image['Config'].get('Labels', {}).get('org.opencontainers.image.version') != manifest['tag']):
            raise DeployError('image_identity_mismatch')
        if platform.image_revision(manifest['image']) != manifest['db_revision']:
            raise DeployError('image_schema_mismatch')
        candidate['services']['api']['image'] = manifest['image']
        candidate['services']['api'].pop('build', None)
        final_compose = request / 'compose.json'
        atomic(final_compose, candidate)
        if current.get('tag') == manifest['tag'] and (current['source'] != manifest['source'] or current['image'] != manifest['image']):
            raise DeployError('immutable_release_conflict')
        if current.get('tag') == manifest['tag']:
            platform.probes()
            record.update(status='success', mode='already_current',
                          api_started_at_utc=before['api']['State']['StartedAt'], finished_at_utc=utc())
            atomic(result_file, record)
            return record
        record['previous_good'] = current
        atomic(result_file, record)  # Write-ahead journal, before stopping the old API.
        deadline = time.monotonic() + 120
        changed = True
        platform.replace(final_compose)
        health(platform, manifest['image'], deadline)
        after = platform.containers()
        for service in ('db', 'caddy'):
            if service_identity(before[service]) != service_identity(after[service]):
                raise DeployError('infrastructure_changed')
        # Preserve Compose-managed operating values; image-provided defaults (e.g. Python patch version) may change.
        if not set(expected_env).issubset(set(after['api']['Config']['Env'])) or live_api['Mounts'] != after['api']['Mounts'] or protected != platform.protected_files():
            raise DeployError('api_environment_or_mount_changed')
        new_current = {**manifest, 'native_acceptance': 'not_checked', 'configuration_revision': record['configuration_revision'], 'compose': str(final_compose), 'deployed_at_utc': utc(),
                       'api_started_at_utc': after['api']['State']['StartedAt']}
        # Static web/APK identity survives an API-only update; historical
        # Native acceptance does not become acceptance of this new backend.
        for key in ('web', 'apk', 'public_open', 'web_status'):
            if key in current:
                new_current[key] = current[key]
        atomic(state / 'current.json', new_current)
        record.update(status='success', api_started_at_utc=after['api']['State']['StartedAt'])
    except Exception as error:
        record.update(status='failed', error=str(error) if isinstance(error, DeployError) else 'deployment_failed')
        if changed:
            try:
                platform.replace(current['compose'])
                health(platform, current['image'], time.monotonic() + 120)
                atomic(state / 'current.json', current)
                record['rollback'] = 'success'
            except Exception:
                record['rollback'] = 'failed'
    record['finished_at_utc'] = utc()
    atomic(result_file, record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['bootstrap', 'submit', 'run', 'status', 'preflight'])
    parser.add_argument('attempt', nargs='?')
    args = parser.parse_args()
    os.umask(0o077)
    STATE.mkdir(mode=0o700, exist_ok=True)
    if args.action == 'submit':
        bundle = validate_bundle(json.loads(sys.stdin.buffer.read(100000)))
        attempt = bundle['attempt']
        # Serialize request creation too; a duplicate cannot overwrite an active request.
        with (STATE / 'submit.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            directory = STATE / attempt
            directory.mkdir(mode=0o700, exist_ok=True)
            target = directory / 'request.json'
            if target.exists() and json.loads(target.read_text()) != bundle:
                raise DeployError('attempt_identity_conflict')
            atomic(target, bundle)
            result = directory / 'result.json'
            if not result.exists() or json.loads(result.read_text()).get('status') == 'in_progress':
                active = subprocess.run(['systemctl', 'is-active', '--quiet', 'lostparty-deploy-' + attempt], capture_output=True).returncode == 0
                if active:
                    print(json.dumps({'submitted': attempt})); return
                command(['systemd-run', '--unit=lostparty-deploy-' + attempt, '--collect',
                         '--property=Type=exec', '--property=RuntimeMaxSec=900',
                         '/usr/bin/python3', str(INSTALLED), 'run', attempt])
        print(json.dumps({'submitted': attempt}))
        return
    if args.action == 'status':
        require(args.attempt, r'[0-9]+-[0-9]+')
        result = STATE / args.attempt / 'result.json'
        data = json.loads(result.read_text()) if result.exists() else {'status': 'queued'}
        # Only allowlisted public metadata. Never return frozen Compose/environment.
        data.pop('previous_good', None)
        print(json.dumps(data)); return
    with (STATE / 'deploy.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        platform = Platform()
        if args.action == 'bootstrap':
            if not (STATE / 'current.json').exists():
                atomic(STATE / 'current.json', initial_state(platform))
            print(json.dumps({'bootstrap': 'ready', 'api_changed': False})); return
        if args.action == 'preflight':
            bundle = validate_bundle(json.loads(sys.stdin.buffer.read(100000)))
            result = execute(bundle, platform, preflight=True)
        else:
            require(args.attempt, r'[0-9]+-[0-9]+')
            bundle = json.loads((STATE / args.attempt / 'request.json').read_text())
            result = execute(bundle, platform)
        result.pop('previous_good', None)
        print(json.dumps(result))
        if result['status'] != 'success':
            raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (DeployError, ValueError, OSError):
        print('{"status":"failed","error":"deployment_control_failed"}')
        raise SystemExit(1)
