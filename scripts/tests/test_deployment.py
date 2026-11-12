"""Deployment control fault injection; never connects to the production Docker/DB."""
import copy
import fcntl
import subprocess
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deployment'))
from common import IMAGE, canonical, checksum, validate_bundle
from release import validate_source
from ssh_entrypoint import arguments
from regression import shard, SUITES
from server import DeployError, Platform, atomic, execute

SOURCE = 'a' * 40
IMAGE_REF = IMAGE + '@sha256:' + 'b' * 64
COMPOSE = 'services: {}\n'
MANIFEST = {'schema': 1, 'repository': 'heo0328/lostparty-backend', 'tag': 'v0.1.0',
            'source': SOURCE, 'image': IMAGE_REF, 'db_revision': '0035_cycle_group_policy',
            'contract_sha256': {'openapi.yaml': 'c' * 64, 'two-cycle.openapi.yaml': 'd' * 64},
            'compose_sha256': checksum(COMPOSE.encode()), 'built_at_utc': '2026-11-01T13:00:00Z'}
BUNDLE = {'manifest': MANIFEST, 'compose': COMPOSE, 'attempt': '123-1',
          'run_url': 'https://github.com/heo0328/lostparty-backend/actions/runs/123/attempts/1'}
CONFIG = {'name': 'lostparty-lightsail', 'services': {
    'api': {'image': 'old', 'build': {'context': '/app'}, 'environment': {'GOOGLE_CLIENT_ID': 'public-web'},
            'volumes': [{'source': '/private/keys', 'target': '/run/secrets', 'read_only': True}]},
    'db': {'image': 'postgres:17'}, 'caddy': {'image': 'caddy:2'}}, 'volumes': {'db': {}}}


class FakePlatform:
    def __init__(self, root):
        self.root = root
        self.image = 'old'
        self.calls = []
        self.candidate = copy.deepcopy(CONFIG)
        self.fail_pull = False
        self.fail_new = False
        self.fail_rollback = False
        self.revision = MANIFEST['db_revision']
        self.label = SOURCE
        self.candidate_head = self.revision
        self.files = 'protected'
        self.change_image_default = False
        self.change_operating_env = False

    def config(self, path):
        return copy.deepcopy(CONFIG if str(path) == 'old-compose' else self.candidate)

    def containers(self):
        env = ['GOOGLE_CLIENT_ID=public-web']
        if self.image != 'old' and self.change_image_default:
            env.append('PYTHON_VERSION=new-patch')
        if self.image != 'old' and self.change_operating_env:
            env = ['GOOGLE_CLIENT_ID=unexpected']
        return {s: {'Id': s + ('-new' if s == 'api' and self.image != 'old' else ''),
                    'State': {'StartedAt': 'new' if s == 'api' and self.image != 'old' else 'old'},
                    'Config': {'Env': env}, 'Mounts': ['private-ro']}
                for s in ('api', 'db', 'caddy')}

    def protected_files(self):
        return self.files

    def healthy(self, image):
        return self.image == image

    def probes(self):
        pass

    def db_revision(self, cid):
        self.calls.append('db-read'); return self.revision

    def pull(self, image):
        self.calls.append('pull')
        if self.fail_pull:
            raise DeployError('pull_failed')

    def image_info(self, image):
        return {'Architecture': 'amd64', 'Os': 'linux', 'Config': {'Labels': {'org.opencontainers.image.revision': self.label, 'org.opencontainers.image.version': 'v0.1.0'}}}

    def image_revision(self, image):
        return self.candidate_head

    def replace(self, path):
        self.calls.append('replace:' + str(path))
        if str(path) == 'old-compose':
            if self.fail_rollback:
                raise DeployError('rollback_failed')
            self.image = 'old'
        else:
            self.image = IMAGE_REF
            if self.fail_new:
                raise DeployError('new_api_failed')


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.platform = FakePlatform(self.state)
        atomic(self.state / 'current.json', {'tag': None, 'source': 'e' * 40,
                                           'image': 'old', 'compose': 'old-compose'})
        self.bundle = copy.deepcopy(BUNDLE)

    def deploy(self, preflight=False):
        return execute(self.bundle, self.platform, self.state, preflight=preflight)

    def test_success_and_duplicate_do_not_repeat_replacement(self):
        result = self.deploy()
        self.assertEqual(result['status'], 'success')
        calls = self.platform.calls[:]
        self.assertEqual(self.deploy(), result)
        self.assertEqual(calls, self.platform.calls)
        self.assertEqual(json.loads((self.state / 'current.json').read_text())['image'], IMAGE_REF)

    def test_next_standard_api_release_preserves_web_and_configuration_identity(self):
        current=json.loads((self.state/'current.json').read_text())
        current.update(configuration_revision='lightsail-web-2.1.0',web={'bundle_sha256':'a'*64},apk={'source':'b'*40},public_open=True,native_acceptance='passed-for-old-source',joint_acceptance_sha256='c'*64)
        atomic(self.state/'current.json',current)
        result=self.deploy()
        self.assertEqual(result['status'],'success')
        after=json.loads((self.state/'current.json').read_text())
        for key in ['configuration_revision','web','apk','public_open']:
            self.assertEqual(after[key],current[key])
        self.assertEqual(after['image'],IMAGE_REF)
        self.assertEqual(after['native_acceptance'],'not_checked')
        self.assertNotIn('joint_acceptance_sha256',after)

    def test_image_defaults_can_change_but_operating_env_cannot(self):
        self.platform.change_image_default = True
        self.assertEqual(self.deploy()['status'], 'success')
        self.platform.image = 'old'
        atomic(self.state / 'current.json', {'tag': None, 'image': 'old', 'compose': 'old-compose'})
        self.bundle['attempt'] = '123-2'
        self.platform.change_operating_env = True
        result = self.deploy()
        self.assertEqual((result['error'], result['rollback']), ('api_environment_or_mount_changed', 'success'))

    def test_db_mismatch_does_not_pull_or_replace(self):
        self.platform.revision = 'future'
        result = self.deploy()
        self.assertEqual(result['error'], 'manual_migration_required')
        self.assertEqual(self.platform.calls, ['db-read'])

    def test_image_download_failure_keeps_old_api(self):
        self.platform.fail_pull = True
        self.assertEqual(self.deploy()['rollback'], 'not_needed')
        self.assertEqual(self.platform.image, 'old')

    def test_image_schema_mismatch_keeps_old_api(self):
        self.platform.candidate_head = 'future'
        self.assertEqual(self.deploy()['error'], 'image_schema_mismatch')
        self.assertEqual(self.platform.image, 'old')

    def test_wrong_source_image_keeps_old_api(self):
        self.platform.label = 'f' * 40
        self.assertEqual(self.deploy()['error'], 'image_identity_mismatch')

    def test_new_api_failure_restores_previous_and_stays_failed(self):
        self.platform.fail_new = True
        result = self.deploy()
        self.assertEqual((result['status'], result['rollback']), ('failed', 'success'))
        self.assertEqual(self.platform.image, 'old')
        self.assertEqual(json.loads((self.state / 'current.json').read_text())['image'], 'old')

    def test_health_failure_restores_previous(self):
        with patch('server.health', side_effect=[DeployError('health_timeout'), None]):
            result = self.deploy()
        self.assertEqual(result['error'], 'health_timeout')
        self.assertEqual(result['rollback'], 'success')

    def test_failed_rollback_is_reported(self):
        self.platform.fail_new = self.platform.fail_rollback = True
        self.assertEqual(self.deploy()['rollback'], 'failed')

    def test_infrastructure_and_environment_changes_fail_before_pull(self):
        for field in ('db', 'api'):
            with self.subTest(field=field):
                self.platform.candidate['services'][field]['environment'] = {'UNEXPECTED': 'private-canary'}
                self.bundle['attempt'] = '123-' + str(2 if field == 'db' else 3)
                result = self.deploy()
                self.assertEqual(result['error'], 'manual_infrastructure_change_required')
                self.assertNotIn('private-canary', json.dumps(result))
                self.platform.candidate = copy.deepcopy(CONFIG)
        self.assertNotIn('pull', self.platform.calls)

    def test_preflight_never_pulls_or_replaces(self):
        self.assertEqual(self.deploy(preflight=True)['mode'], 'preflight_only')
        self.assertEqual(self.platform.calls, ['db-read'])

    def test_attempt_cannot_change_after_finish(self):
        self.deploy()
        self.bundle['run_url'] = self.bundle['run_url'].replace('/123/', '/456/')
        with self.assertRaises(DeployError):
            self.deploy()

    def test_preflight_never_recovers_or_restarts_interrupted_deploy(self):
        directory = self.state / '122-1'; directory.mkdir()
        atomic(directory / 'result.json', {'status': 'in_progress',
               'previous_good': {'image': 'old', 'compose': 'old-compose'}})
        with self.assertRaises(DeployError):
            self.deploy(preflight=True)
        self.assertEqual(self.platform.calls, [])

    def test_successful_release_new_attempt_verifies_without_restart(self):
        self.deploy()
        before = [c for c in self.platform.calls if c.startswith('replace:')]
        self.bundle['attempt'] = '123-2'
        self.assertEqual(self.deploy()['mode'], 'already_current')
        self.assertEqual(before, [c for c in self.platform.calls if c.startswith('replace:')])

    def test_process_interruption_reconciles_journal_by_restoring(self):
        record = {'status': 'in_progress', 'request_sha256': checksum(canonical(self.bundle)),
                  'previous_good': {'image': 'old', 'compose': 'old-compose'}}
        directory = self.state / self.bundle['attempt']; directory.mkdir()
        atomic(directory / 'result.json', record)
        self.platform.image = IMAGE_REF
        result = self.deploy()
        self.assertEqual((result['status'], result['rollback']), ('failed', 'success'))
        self.assertEqual(self.platform.image, 'old')

    def test_retries_have_separate_records(self):
        self.platform.fail_pull = True
        self.deploy()
        self.platform.fail_pull = False
        self.bundle['attempt'] = '123-2'
        self.assertEqual(self.deploy()['status'], 'success')
        self.assertEqual(json.loads((self.state / '123-1/result.json').read_text())['status'], 'failed')

    def test_older_release_blocked(self):
        atomic(self.state / 'current.json', {'tag': 'v0.2.0', 'image': 'old', 'compose': 'old-compose'})
        self.assertEqual(self.deploy()['error'], 'older_release_blocked')
        self.assertEqual(self.platform.calls, [])

    def test_disk_guard_does_not_replace(self):
        with patch('server.shutil.disk_usage') as usage:
            usage.return_value.free = 0
            self.assertEqual(self.deploy()['error'], 'insufficient_disk')
        self.assertEqual(self.platform.calls, [])

    def test_malformed_and_tampered_requests(self):
        for key, value in [('tag', 'v1.2.3;env'), ('image', 'evil@sha256:' + 'b' * 64), ('source', '../x')]:
            bad = copy.deepcopy(self.bundle); bad['manifest'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_bundle(bad)
        self.bundle['compose'] += '# tamper'
        with self.assertRaises(ValueError):
            validate_bundle(self.bundle)

    def test_tag_version_and_branch_rules(self):
        validate_source('v0.1.0', SOURCE, '0.1.0\n', SOURCE, SOURCE, True)
        for args in [('v0.01.0', SOURCE, '0.01.0', SOURCE, SOURCE, True),
                     ('v0.1.1', SOURCE, '0.1.0', SOURCE, SOURCE, True),
                     ('v0.1.0', SOURCE, '0.1.0', SOURCE, 'f' * 40, True),
                     ('v0.1.0', SOURCE, '0.1.0', SOURCE, SOURCE, False)]:
            with self.assertRaises(ValueError):
                validate_source(*args)

    def test_host_lock_excludes_concurrent_process(self):
        lock_path = self.state / 'lock'
        with lock_path.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            code = "import fcntl,sys; f=open(sys.argv[1],'w'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
            result = subprocess.run([sys.executable, '-c', code, str(lock_path)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, '-c', code, str(lock_path)], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_new_attempt_recovers_old_interrupted_attempt_first(self):
        directory = self.state / '122-1'; directory.mkdir()
        atomic(directory / 'result.json', {'status': 'in_progress',
               'previous_good': {'image': 'old', 'compose': 'old-compose'}})
        self.platform.image = IMAGE_REF
        self.assertEqual(self.deploy()['status'], 'success')
        prior = json.loads((directory / 'result.json').read_text())
        self.assertEqual((prior['status'], prior['rollback']), ('failed', 'success'))
        self.assertEqual(self.platform.calls[0], 'replace:old-compose')

    def test_ci_shards_cover_every_test_file_exactly_once(self):
        groups = [shard(i, 8) for i in range(8)]
        flattened = [path for group in groups for path in group]
        self.assertEqual(sorted(flattened), sorted(SUITES['all']))
        self.assertEqual(len(set(flattened)), len(flattened))
        self.assertTrue(all(groups))
        with self.assertRaises(ValueError):
            shard(8, 8)

    def test_ssh_account_rejects_shell_and_argument_injection(self):
        for value in ['', 'bash', 'whoami', 'submit;env', 'status 123-1;env',
                      'status ../file', 'status 1-2 extra', 'sudo submit']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                arguments(value)
        self.assertEqual(arguments('submit'), ['submit'])
        self.assertEqual(arguments('preflight'), ['preflight'])
        self.assertEqual(arguments('status 123-1'), ['status', '123-1'])

    def test_docker_replace_has_no_migration_or_dependencies(self):
        platform = Platform('/tmp/isolated-control')
        with patch('server.command', return_value='') as cmd:
            platform.replace('candidate.yaml')
        args = cmd.call_args.args[0]
        for flag in ['--no-deps', '--no-build', '--pull', 'never']:
            self.assertIn(flag, args)
        self.assertEqual(args[-1], 'api')
        self.assertNotIn('alembic', args)


class RuntimeContractVersions(unittest.TestCase):
    def test_manifest_name_meanings_are_versioned(self):
        from common import validate_manifest, contract_names
        old=copy.deepcopy(MANIFEST)
        self.assertEqual(validate_manifest(old),old)
        new=copy.deepcopy(old);new['schema']=2
        new['contract_sha256']={'openapi.yaml':'d'*64,'legacy.openapi.yaml':'c'*64}
        self.assertEqual(validate_manifest(new),new)
        for schema in (1,2):
            bad=copy.deepcopy(new if schema==1 else old);bad['schema']=schema
            with self.assertRaises(ValueError):validate_manifest(bad)
        for schema in (True,False,0,3,'2',None):
            with self.assertRaises(ValueError):contract_names(schema)

    def test_schema2_allows_only_the_equivalent_entrypoint_alias(self):
        from server import infrastructure
        old=copy.deepcopy(CONFIG);new=copy.deepcopy(CONFIG)
        old['services']['api']['command']=['uvicorn','app.main:create_two_cycle_app','--factory','--workers','1']
        new['services']['api']['command']=['uvicorn','app.main:create_app','--factory','--workers','1']
        self.assertNotEqual(infrastructure(old),infrastructure(new))
        self.assertEqual(infrastructure(old,current_entrypoint=True),infrastructure(new,current_entrypoint=True))
        new['services']['api']['command'][-1]='2'
        self.assertNotEqual(infrastructure(old,current_entrypoint=True),infrastructure(new,current_entrypoint=True))

    def test_schema2_deployment_and_rollback_preserve_infrastructure(self):
        from common import validate_bundle
        bundle=copy.deepcopy(BUNDLE);bundle['manifest']['schema']=2
        bundle['manifest']['contract_sha256']={'openapi.yaml':'d'*64,'legacy.openapi.yaml':'c'*64}
        validate_bundle(bundle)
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);state=root/'state';state.mkdir()
                platform=FakePlatform(root);platform.fail_new=fail
                old={'tag':None,'source':'previous','image':'old','compose':'old-compose',
                     'db_revision':MANIFEST['db_revision']}
                atomic(state/'current.json',old)
                with patch('server.health',side_effect=lambda p,image,deadline: (_ for _ in ()).throw(DeployError('health_timeout')) if image==IMAGE_REF and fail else None):
                    result=execute(bundle,platform,state)
                self.assertEqual(result['status'],'failed' if fail else 'success')
                if fail:
                    self.assertEqual(result['rollback'],'success')
                    self.assertEqual(platform.image,'old')

    def test_schema2_rejects_tampered_bundle_and_invalid_contract_hash(self):
        from common import validate_bundle
        bundle=copy.deepcopy(BUNDLE)
        bundle['manifest'].update(schema=2,contract_sha256={'openapi.yaml':'d'*64,'legacy.openapi.yaml':'c'*64})
        bundle['compose']+='tampered'
        with self.assertRaises(ValueError):validate_bundle(bundle)
        bundle['compose']=BUNDLE['compose']
        bundle['manifest']['contract_sha256']['openapi.yaml']='invalid'
        with self.assertRaises(ValueError):validate_bundle(bundle)


if __name__ == '__main__':
    unittest.main()
