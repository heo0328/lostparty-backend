#!/usr/bin/env python3
"""Validate, publish once, and reuse immutable GitHub Release metadata."""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from common import IMAGE, REPOSITORY, SHA, TAG, checksum, require, utc, validate_manifest


def run(args, *, input=None):
    return subprocess.check_output(args, input=input, text=True).strip()


def api(path):
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
                                    headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                                             'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError('GitHub request failed') from None


def validate_source(tag, source, version, main, dev, ancestor):
    require(tag, TAG); require(source, SHA)
    if tag != 'v' + version.strip() or main != dev or not ancestor:
        raise ValueError('tag/version/main/dev validation failed')


def existing(tag, source):
    release = api('/releases/tags/' + tag)
    if release is None:
        return None
    if release['draft'] or release['prerelease']:
        raise ValueError('incomplete release; manual investigation required')
    run(['gh', 'release', 'download', tag, '--repo', REPOSITORY, '--pattern', 'release.json',
         '--pattern', 'compose.lightsail.yaml', '--dir', 'dist'])
    m = validate_manifest(json.loads(Path('dist/release.json').read_text()))
    if m['tag'] != tag or m['source'] != source or checksum(Path('dist/compose.lightsail.yaml').read_bytes()) != m['compose_sha256']:
        raise ValueError('immutable release conflict')
    return m


def registry_digest(reference, *, anonymous=False):
    # Differentiate a missing tag (404) from transport/auth failures; never overwrite on uncertainty.
    suffix = reference.removeprefix(IMAGE)
    if not suffix.startswith((':', '@')):
        raise ValueError('unexpected registry reference')
    scope = 'pull' if anonymous else 'pull,push'
    query = 'https://ghcr.io/token?service=ghcr.io&scope=repository:' + REPOSITORY + ':' + scope
    headers = {}
    if not anonymous:
        basic = base64.b64encode((os.environ['GITHUB_ACTOR'] + ':' + os.environ['GH_TOKEN']).encode()).decode()
        headers['Authorization'] = 'Basic ' + basic
    try:
        with urllib.request.urlopen(urllib.request.Request(query, headers=headers), timeout=30) as response:
            token = json.load(response)['token']
    except urllib.error.HTTPError:
        raise ValueError('GHCR anonymous access not enabled' if anonymous else 'GHCR authentication failed') from None
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json'}
    request = urllib.request.Request('https://ghcr.io/v2/' + REPOSITORY + '/manifests/' + suffix[1:], headers=headers, method='HEAD')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return require(response.headers['Docker-Content-Digest'], r'sha256:[0-9a-f]{64}')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise ValueError('registry unavailable or unauthorized') from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['validate', 'publish', 'download'])
    args = parser.parse_args()
    tag = os.environ.get('GITHUB_REF_NAME', '')
    source = run(['git', 'rev-parse', 'HEAD'])
    if args.action == 'validate' and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        if os.environ.get('GITHUB_REF_NAME') != 'chore/release-management':
            print('Manual validation only: no publication or deployment'); return
        # Execute the original immutable tag script under the exact push environment.
        import runpy
        import tempfile
        original = run(['git', 'show', 'v0.1.0:scripts/deployment/release.py'])
        with tempfile.TemporaryDirectory(prefix='tag-validation-') as directory:
            target = Path(directory) / 'original_release.py'
            target.write_text(original)
            def trace(frame, event, arg):
                if event == 'exception' and frame.f_code.co_filename == str(target):
                    kind, error, _ = arg
                    status = getattr(error, 'code', None)
                    print(json.dumps({'diagnostic': 'original_tag_control', 'function': frame.f_code.co_name,
                                      'line': frame.f_lineno, 'exception': kind.__name__,
                                      'http_status': status if type(status) is int else None}), flush=True)
                return trace
            os.environ['GITHUB_EVENT_NAME'] = 'push'
            os.environ['GITHUB_REF_NAME'] = 'v0.1.0'
            print(json.dumps({'diagnostic': 'tag_checkout', 'tag_source': run(['git', 'rev-parse', 'v0.1.0^{}']),
                              'runner_checkout': source}), flush=True)
            # The original main resolves HEAD; validate at the immutable tag commit.
            run(['git', 'checkout', '--detach', 'v0.1.0'])
            sys.settrace(trace)
            try:
                runpy.run_path(str(target), run_name='__main__')
            finally:
                sys.settrace(None)
                run(['git', 'checkout', '--detach', source])
        return
    require(tag, TAG); require(source, SHA)
    Path('dist').mkdir(exist_ok=True)
    if args.action == 'download':
        if existing(tag, source) is None:
            raise ValueError('published release required')
        return
    previous = api('/releases/tags/' + tag)
    if previous is not None:
        m = existing(tag, source)
        print('Existing release reused: ' + m['tag']); return
    run(['git', 'fetch', 'origin', 'main', 'dev', '--tags'])
    main_ref = run(['git', 'rev-parse', 'origin/main'])
    dev_ref = run(['git', 'rev-parse', 'origin/dev'])
    ancestor = subprocess.call(['git', 'merge-base', '--is-ancestor', source, main_ref]) == 0
    validate_source(tag, source, Path('VERSION').read_text(), main_ref, dev_ref, ancestor)
    if args.action == 'validate':
        print('Release source validated'); return
    reference = IMAGE + ':sha-' + source
    version_ref = IMAGE + ':' + tag
    # Reuse an image after an interrupted publication; never rebuild the same source tag.
    digest = registry_digest(reference)
    if digest is None:
        if registry_digest(version_ref) is not None:
            raise ValueError('version image already exists without source image')
        run(['docker', 'build', '--platform', 'linux/amd64',
             '--label', 'org.opencontainers.image.source=https://github.com/' + REPOSITORY,
             '--label', 'org.opencontainers.image.revision=' + source,
             '--label', 'org.opencontainers.image.version=' + tag,
             '--label', 'org.opencontainers.image.created=' + utc(),
             '-t', reference, '.'])
        run(['docker', 'push', reference])
        digest = registry_digest(reference)
        if digest is None:
            raise ValueError('pushed image unavailable')
    image = IMAGE + '@' + digest
    run(['docker', 'pull', image])
    info = json.loads(run(['docker', 'image', 'inspect', image]))[0]
    labels = info['Config'].get('Labels') or {}
    if labels.get('org.opencontainers.image.revision') != source or labels.get('org.opencontainers.image.version') != tag or not labels.get('org.opencontainers.image.created'):
        raise ValueError('source image identity or build time mismatch')
    version_digest = registry_digest(version_ref)
    if version_digest is not None:
        if version_digest != digest:
            raise ValueError('immutable version image conflict')
    else:
        run(['docker', 'tag', image, version_ref]); run(['docker', 'push', version_ref])
    # GHCR's first publication is private by default. Stop before deployment until owner makes it public.
    if registry_digest(image, anonymous=True) != digest:
        raise ValueError('public anonymous pull required')
    code = "from alembic.config import Config; from alembic.script import ScriptDirectory; print(ScriptDirectory.from_config(Config('alembic.ini')).get_current_head())"
    revision = run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--entrypoint', 'python', image, '-c', code])
    compose = Path('compose.lightsail.yaml').read_bytes()
    m = validate_manifest({'schema': 1, 'repository': REPOSITORY, 'tag': tag, 'source': source,
                           'image': image, 'db_revision': revision,
                           'contract_sha256': {p: checksum((Path('openapi') / p).read_bytes())
                                               for p in ['openapi.yaml', 'two-cycle.openapi.yaml']},
                           'compose_sha256': checksum(compose), 'built_at_utc': labels['org.opencontainers.image.created']})
    Path('dist/release.json').write_text(json.dumps(m, indent=2) + '\n')
    Path('dist/compose.lightsail.yaml').write_bytes(compose)
    Path('dist/notes.md').write_text(f"Source: `{source}`\n\nImage: `{image}`\n\nDB: `{revision}`\n\nAPI contracts: https://github.com/{REPOSITORY}/tree/{source}/openapi\n\nImage publication is separate from production deployment and user acceptance. See the production Deployment/Actions result.\n")
    # Create draft first. A crash with partial assets stays visibly incomplete and fails closed.
    run(['gh', 'release', 'create', tag, '--repo', REPOSITORY, '--verify-tag', '--draft',
         '--title', 'Backend ' + tag, '--notes-file', 'dist/notes.md',
         'dist/release.json', 'dist/compose.lightsail.yaml'])
    run(['gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false'])
    print('Published ' + tag)


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit('Release control failed: ' + str(error)) from None
    except Exception:
        raise SystemExit('Release control failed; inspect stage, never print tokens or environment') from None
