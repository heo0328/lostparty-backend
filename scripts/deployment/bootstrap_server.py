#!/usr/bin/python3
"""Authorized one-time root preparation; consumes public key and reviewed code via stdin."""
import ast
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
from pathlib import Path


def main():
    data = json.load(sys.stdin)
    key = data['public_key'].strip()
    if re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [A-Za-z0-9_.-]+)?', key) is None:
        raise ValueError('invalid public key')
    base = Path('/usr/local/lib/lostparty-deploy')
    base.mkdir(mode=0o755, exist_ok=True)
    for name, source in data['files'].items():
        if name not in ('server.py', 'common.py', 'ssh_entrypoint.py'):
            raise ValueError('unexpected tool')
        ast.parse(source)
        target = base / name
        if target.exists():
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest not in data['expected_existing_hashes'].get(name, []):
                raise ValueError('installed tool changed unexpectedly')
        temporary = base / (name + '.new')
        with temporary.open('x') as stream:
            stream.write(source)
        temporary.chmod(0o644)
        os.replace(temporary, target)
    subprocess.run(['/usr/bin/python3', str(base / 'server.py'), 'bootstrap'], check=True, capture_output=True)
    state = Path('/var/lib/lostparty-deploy')
    marker = state / 'ssh-managed.json'
    try:
        existing = pwd.getpwnam('lostparty-deploy')
    except KeyError:
        existing = None
    fingerprint = hashlib.sha256(key.encode()).hexdigest()
    if existing is not None:
        if not marker.exists() or json.loads(marker.read_text())['key_sha256'] != fingerprint:
            raise ValueError('deployment account/key already exists; manual rotation review required')
    else:
        subprocess.run(['useradd', '--create-home', '--shell', '/bin/sh', 'lostparty-deploy'], check=True, capture_output=True)
    home = Path('/home/lostparty-deploy')
    os.chown(home, 0, 0); home.chmod(0o755)
    ssh = home / '.ssh'; ssh.mkdir(exist_ok=True); os.chown(ssh, 0, 0); ssh.chmod(0o755)
    authorized = ssh / 'authorized_keys'
    content = 'restrict,command="/usr/bin/python3 /usr/local/lib/lostparty-deploy/ssh_entrypoint.py" ' + key + '\n'
    if authorized.exists() and authorized.read_text() != content:
        raise ValueError('existing authorized key differs')
    authorized.write_text(content); os.chown(authorized, 0, 0); authorized.chmod(0o644)
    sudoers = Path('/etc/sudoers.d/lostparty-deploy')
    text = ('lostparty-deploy ALL=(root) NOPASSWD: '
            '/usr/bin/python3 /usr/local/lib/lostparty-deploy/server.py submit, '
            '/usr/bin/python3 /usr/local/lib/lostparty-deploy/server.py preflight, '
            '/usr/bin/python3 /usr/local/lib/lostparty-deploy/server.py status *\n')
    candidate = Path('/etc/sudoers.d/.lostparty-deploy-new')
    if sudoers.exists() and sudoers.read_text() != text:
        raise ValueError('existing sudo permissions differ')
    candidate.write_text(text); candidate.chmod(0o440)
    subprocess.run(['visudo', '-cf', str(candidate)], check=True, capture_output=True)
    os.replace(candidate, sudoers)
    marker.write_text(json.dumps({'user': 'lostparty-deploy', 'key_sha256': fingerprint})); marker.chmod(0o600)
    print(json.dumps({'installed': True, 'user': 'lostparty-deploy', 'forced_command': True,
                      'api_recreated': False, 'aws_iam_used': False}))


if __name__ == '__main__':
    os.umask(0o077)
    try:
        main()
    except Exception:
        raise SystemExit('Server preparation failed; inspect private configuration without printing credentials') from None
