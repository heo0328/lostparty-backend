#!/usr/bin/env python3
"""Real Docker API replacement/rollback in a UUID sandbox; no production endpoints/DB."""
import argparse
import copy
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import patch

import server
from common import IMAGE, checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    name = 'lostparty-deploy-test-' + uuid.uuid4().hex[:10]
    prefix = [args.docker, 'compose', '--project-name', name]
    image_names = [name + ':old', name + ':good', name + ':bad']
    source = 'a' * 40
    digest_ref = IMAGE + '@sha256:' + 'b' * 64
    original_command = server.command
    def command(argv, **kwargs):
        if argv[0] == 'docker':
            argv = [args.docker, *argv[1:]]
        return original_command(argv, **kwargs)
    with tempfile.TemporaryDirectory(prefix=name) as directory:
        root = Path(directory)
        project_compose = root / 'sandbox.json'
        state = root / 'state'; state.mkdir()
        image = [image_names[1]]
        class Sandbox(server.Platform):
            def __init__(self):
                self.root = root
                self.base = prefix + ['--project-directory', str(root)]
            def containers(self):
                result = {}
                for s in ('api', 'db', 'caddy'):
                    cid = command(prefix + ['-f', str(project_compose), 'ps', '-q', s]).strip()
                    result[s] = json.loads(command(['docker', 'inspect', cid]))[0]
                return result
            def pull(self, ref):
                pass  # Local sandbox images only, never production GHCR.
            def image_info(self, ref):
                result = json.loads(command(['docker', 'image', 'inspect', image[0] if ref == digest_ref else ref]))[0]
                return result
            def image_revision(self, ref):
                return '0035_cycle_group_policy'
            def db_revision(self, cid):
                return '0035_cycle_group_policy'  # No real application DB in this control smoke test.
            def replace(self, file):
                config = json.loads(Path(file).read_text())
                if config['services']['api']['image'] == digest_ref:
                    config['services']['api']['image'] = image[0]
                mapped = Path(file).with_name(Path(file).stem + '-sandbox.json')
                mapped.write_text(json.dumps(config))
                self.compose(mapped, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                             '--force-recreate', '--wait', '--wait-timeout', '10', 'api', timeout=20)
            def healthy(self, ref):
                api = self.containers()['api']
                return api['Image'] == self.image_info(ref)['Id'] and api['State'].get('Health', {}).get('Status') == 'healthy'
            def probes(self):
                cid = self.containers()['api']['Id']
                command(['docker', 'exec', cid, 'python', '-c', "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"])
        platform = Sandbox()
        try:
            with patch('server.command', side_effect=command):
                for tag, healthy in zip(image_names, [True, True, False]):
                    (root / 'serve.py').write_text("from http.server import BaseHTTPRequestHandler,HTTPServer\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  self.send_response(" + ('200' if healthy else '503') + ");self.end_headers();self.wfile.write(b'{}')\n def log_message(self,*a): pass\nHTTPServer(('0.0.0.0',8000),H).serve_forever()\n")
                    (root / 'Dockerfile').write_text('FROM python:3.12-slim-bookworm\nCOPY serve.py /serve.py\nCMD ["python","/serve.py"]\n')
                    command(['docker', 'build', '--label', 'org.opencontainers.image.revision=' + source, '--label', 'org.opencontainers.image.version=' + ('v0.1.1' if tag.endswith(':bad') else 'v0.1.0'), '-t', tag, str(root)], timeout=180)
                config = {'name': name, 'services': {
                    'api': {'image': image_names[0], 'command': ['python', '/serve.py', 'app.main:create_two_cycle_app'], 'healthcheck': {'test': ['CMD', 'python', '-c', "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1)"], 'interval': '1s', 'timeout': '2s', 'retries': 2}},
                    'db': {'image': image_names[0], 'command': ['sleep', '600']},
                    'caddy': {'image': image_names[0], 'command': ['sleep', '600']}}}
                project_compose.write_text(json.dumps(config))
                command(prefix + ['-f', str(project_compose), 'up', '-d', '--wait', '--wait-timeout', '30'], timeout=45)
                frozen = root / 'baseline.json'
                server.atomic(frozen, platform.config(project_compose))
                before = platform.containers()
                old_image_id = json.loads(command(['docker', 'image', 'inspect', image_names[0]]))[0]['Id']
                frozen_config = platform.config(project_compose)
                frozen_config['services']['api']['image'] = old_image_id
                server.atomic(frozen, frozen_config)
                current = {'tag': None, 'source': 'e' * 40, 'image': old_image_id, 'compose': str(frozen)}
                server.atomic(state / 'current.json', current)
                raw = project_compose.read_text()
                bundle = {'manifest': {'schema': 1, 'repository': 'heo0328/lostparty-backend', 'tag': 'v0.1.0',
                          'source': source, 'image': digest_ref, 'db_revision': '0035_cycle_group_policy',
                          'contract_sha256': {'openapi.yaml': 'c' * 64, 'two-cycle.openapi.yaml': 'd' * 64},
                          'compose_sha256': checksum(raw.encode()), 'built_at_utc': '2026-11-01T00:00:00Z'},
                          'compose': raw, 'attempt': '123-1',
                          'run_url': 'https://github.com/heo0328/lostparty-backend/actions/runs/123/attempts/1'}
                good = server.execute(bundle, platform, state)
                assert good['status'] == 'success', good
                platform.replace(frozen)
                server.atomic(state / 'current.json', current)
                config['services']['api']['command'][-1] = 'app.main:create_app'
                raw = json.dumps(config)
                bundle['compose'] = raw
                bundle['manifest'].update(schema=2, compose_sha256=checksum(raw.encode()),
                    contract_sha256={'openapi.yaml': 'd' * 64, 'legacy.openapi.yaml': 'c' * 64})
                bundle['attempt'] = '123-2'
                modern = server.execute(bundle, platform, state)
                assert modern['status'] == 'success', modern
                # Exercise the first-rollout rollback target: cached untagged image ID, not a registry tag.
                platform.replace(frozen)
                server.atomic(state / 'current.json', current)
                image[0] = image_names[2]
                bundle['attempt'] = '123-3'; bundle['manifest']['tag'] = 'v0.1.1'
                bad = server.execute(bundle, platform, state)
                assert bad['status'] == 'failed' and bad['rollback'] == 'success', bad
                after = platform.containers()
                assert before['db']['Id'] == after['db']['Id'] and before['caddy']['Id'] == after['caddy']['Id']
                assert platform.healthy(old_image_id)
                assert after['api']['Config']['Cmd'] == config['services']['api']['command'][:-1] + ['app.main:create_two_cycle_app']
                print(json.dumps({'isolated_docker': name, 'schema1_deploy': 'PASS', 'schema2_alias_deploy': 'PASS', 'schema2_unhealthy_api_rollback': 'PASS', 'untagged_image_id_rollback': 'PASS', 'db_caddy_preserved': True, 'production_used': False}))
        finally:
            subprocess.run(prefix + ['-f', str(project_compose), 'down', '--remove-orphans', '--timeout', '5'], capture_output=True)
            subprocess.run([args.docker, 'image', 'rm', *image_names], capture_output=True)


if __name__ == '__main__':
    main()
