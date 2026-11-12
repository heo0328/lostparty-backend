#!/usr/bin/env python3
"""Verify the agreed Native handoff; stage and switch local/host static releases.

Does not download arbitrary URLs, run Flutter, change API/DB, or publish releases.
"""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
import subprocess
from datetime import datetime, timezone

BUNDLE = 'lostparty-v2.1.0-web.zip'
FILES = {BUNDLE, BUNDLE + '.sha256', 'release-manifest.json'}
MAX_FILE = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def safe_path(value):
    require(isinstance(value, str) and value and '\\' not in value and ':' not in value
            and '\x00' not in value and not value.startswith('/')
            and value == str(PurePosixPath(value))
            and all(part not in ('', '.', '..') for part in value.split('/')), 'unsafe_path')
    return value


def entries(archive):
    result = {}
    folded = set()
    total = 0
    require(len(archive.infolist()) <= 10000, 'too_many_entries')
    for item in archive.infolist():
        name = safe_path(item.filename)
        mode = item.external_attr >> 16
        require(not item.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                and not item.flag_bits & 1, 'unsupported_entry')
        require(name.casefold() not in folded, 'duplicate_entry')
        folded.add(name.casefold())
        total += item.file_size
        require(item.file_size <= MAX_FILE and total <= MAX_TOTAL, 'archive_too_large')
        result[name] = item
    return result


def bundle_name(receipt):
    """Versioned filename from the trusted pinned receipt, never archive input."""
    version = receipt['web']['version']
    require(isinstance(version, str) and re.fullmatch(
        r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\+[1-9][0-9]*', version),
        'invalid_web_version')
    return 'lostparty-v' + version.split('+')[0] + '-web.zip'


def handoff_files(receipt):
    bundle = bundle_name(receipt)
    return {bundle, bundle + '.sha256', 'release-manifest.json'}


def verify(directory, receipt):
    """Receipt is the pinned Backend handoff record, never supplied by the ZIP."""
    directory = Path(directory)
    require(not directory.is_symlink(), 'symlink_input')
    expected = receipt['web']
    bundle = bundle_name(receipt)
    raw = {}
    for name in handoff_files(receipt):
        path = directory / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE,
                'missing_or_unsafe_handoff_file')
        raw[name] = path.read_bytes()
    require(digest(raw[bundle]) == expected['bundle_sha256'], 'bundle_hash_mismatch')
    require(len(raw[bundle]) == expected['bundle_bytes'], 'bundle_size_mismatch')
    checksum = raw[bundle + '.sha256'].decode('ascii').strip().split()
    require(checksum == [expected['bundle_sha256'], bundle], 'checksum_mismatch')
    manifest = json.loads(raw['release-manifest.json'])
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1 and manifest['version'] == expected['version']
            and manifest['source_commit'] == expected['source']
            and manifest['backend_origin'] == expected['origin']
            and manifest['source_dirty'] is False and manifest['candidate_only'] is False
            and manifest['dirty_status'] == [] and manifest['build_mode'] == 'release'
            and manifest['service_worker'] == 'disabled' and manifest['site_directory'] == 'site',
            'manifest_identity_mismatch')
    listed = {}
    folded = set()
    for item in manifest['files']:
        name = safe_path(item['path'])
        require(name.casefold() not in folded, 'duplicate_manifest_path')
        folded.add(name.casefold())
        require(type(item['bytes']) is int and 0 <= item['bytes'] <= MAX_FILE
                and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'invalid_file_record')
        require(not name.endswith(('.map', '.symbols')) and 'service_worker' not in name,
                'excluded_public_asset')
        listed['site/' + name] = item
    require(len(listed) == expected['site_files'], 'file_count_mismatch')
    with zipfile.ZipFile(io.BytesIO(raw[bundle])) as archive:
        items = entries(archive)
        require(set(items) == set(listed) | {'release-manifest.json'}, 'file_list_mismatch')
        require(archive.read('release-manifest.json') == raw['release-manifest.json'],
                'manifest_bytes_mismatch')
        for name, item in listed.items():
            require(items[name].file_size == item['bytes']
                    and digest(archive.read(name)) == item['sha256'], 'asset_hash_mismatch')
    return raw, manifest


def receive(receipt, destination, *, gh='gh'):
    """Download only the pinned run/artifact, authenticated by the existing CLI."""
    expected=receipt['web'];artifact=expected['artifact_id']
    require(type(artifact) is int and artifact>0, 'invalid_artifact_id')
    repository='heo0328/LostParty_flutter'
    def api(path):
        return subprocess.run([gh,'api',path],capture_output=True,check=True,timeout=120).stdout
    base='repos/'+repository+'/actions/artifacts/'+str(artifact)
    meta=json.loads(api(base))
    expires=datetime.fromisoformat(meta['expires_at'].replace('Z','+00:00'))
    require(meta['id']==artifact and meta['name']==expected['artifact_name']
            and meta['workflow_run']['id']==expected['run_id']
            and meta['workflow_run']['head_sha']==expected['source'], 'artifact_identity_mismatch')
    require(meta['expired'] is False and expires>datetime.now(timezone.utc),'artifact_expired')
    require(meta.get('digest')=='sha256:'+expected['archive_sha256'],'artifact_digest_mismatch')
    destination=Path(destination)
    require(not destination.is_symlink(), 'symlink_destination')
    if destination.exists():
        verify(destination,receipt)
        require(digest((destination/'github-artifact.zip').read_bytes())==expected['archive_sha256'],'cached_archive_mismatch')
        return destination
    archive=api(base+'/zip')
    require(len(archive)<=MAX_FILE and digest(archive)==expected['archive_sha256'],'download_digest_mismatch')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.receive-',dir=destination.parent))
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            require(set(entries(z))==handoff_files(receipt),'handoff_root_mismatch')
            for name in handoff_files(receipt):(temp/name).write_bytes(z.read(name))
        (temp/'github-artifact.zip').write_bytes(archive)
        verify(temp,receipt)
        os.rename(temp,destination)
    finally:
        if temp.exists():shutil.rmtree(temp)
    return destination


def stage(directory, receipt, root):
    bundle = bundle_name(receipt)
    raw, manifest = verify(directory, receipt)
    root = Path(root)
    require(not root.is_symlink(), 'symlink_root')
    root.mkdir(parents=True, exist_ok=True)
    releases = root / 'releases'
    require(not releases.is_symlink(), 'symlink_releases')
    releases.mkdir(exist_ok=True)
    name = receipt['web']['bundle_sha256']
    require(re.fullmatch('[0-9a-f]{64}', name), 'invalid_release_id')
    target = releases / name
    if target.exists() or target.is_symlink():
        require(target.is_dir() and not target.is_symlink() and (target/'site').is_dir()
                and not any(p.is_symlink() for p in target.rglob('*')), 'unsafe_existing_release')
        # Never silently reuse damaged or replaced staged files.
        verify(target, receipt)
        expected = {item['path']: item for item in manifest['files']}
        actual = {str(p.relative_to(target / 'site')): p for p in (target / 'site').rglob('*') if not p.is_dir()}
        require(set(actual) == set(expected), 'staged_file_list_mismatch')
        for path, file in actual.items():
            require(not file.is_symlink() and digest(file.read_bytes()) == expected[path]['sha256'],
                    'staged_asset_mismatch')
        return name
    temp = Path(tempfile.mkdtemp(prefix='.stage-', dir=releases))
    try:
        for file, data in raw.items():
            (temp / file).write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(raw[bundle])) as archive:
            for item in manifest['files']:
                file = temp / 'site' / item['path']
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(archive.read('site/' + item['path']))
        # Public site only. Original bundle and manifest remain outside Caddy root.
        for path in temp.rglob('*'):
            path.chmod(0o755 if path.is_dir() else 0o644)
        temp.chmod(0o755)
        os.rename(temp, target)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return name


def pointer(root, name):
    path = root / name
    if not path.is_symlink():
        require(not path.exists(), 'pointer_not_symlink')
        return None
    value = os.readlink(path)
    require(re.fullmatch(r'releases/[0-9a-f]{64}/site', value), 'unsafe_pointer')
    require((root / value).is_dir() and (root / value).resolve().is_relative_to(root.resolve()),
            'missing_pointer_target')
    return value


def set_pointer(root, name, value):
    temp = root / ('.' + name + '-' + uuid.uuid4().hex)
    try:
        temp.symlink_to(value)
        os.replace(temp, root / name)
    finally:
        if temp.is_symlink():
            temp.unlink()


def switch(root, receipt=None, *, compatible=False, rollback=False):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'invalid_root')
    # Same root lock protects concurrent activations and rollback.
    with (root / '.web.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = pointer(root, 'current')
        if rollback:
            target = pointer(root, 'previous')
            if target:
                set_pointer(root, 'current', target)
            elif current:
                (root / 'current').unlink()  # First deployment returns to API-only.
            return target
        require(compatible, 'backend_compatibility_confirmation_required')
        name = receipt['web']['bundle_sha256']
        staged = root / 'releases' / name
        stage(staged, receipt, root)  # Reverify both original ZIP and extracted assets.
        target = 'releases/' + name + '/site'
        if current == target:
            return target
        if current:
            set_pointer(root, 'previous', current)
        set_pointer(root, 'current', target)
        return target


def validate_active(root, receipt):
    root=Path(root)
    expected='releases/'+receipt['web']['bundle_sha256']+'/site'
    require(pointer(root,'current')==expected,'expected_web_not_active')
    stage((root/expected).parent,receipt,root)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['receive', 'verify', 'stage', 'activate', 'rollback'])
    parser.add_argument('--handoff', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--backend-compatible', action='store_true')
    args = parser.parse_args()
    if args.action == 'rollback':
        result = switch(args.root, rollback=True)
    else:
        require(args.receipt is not None, 'receipt_required')
        receipt = json.loads(args.receipt.read_text())
        if args.action == 'receive':
            result=str(receive(receipt,args.root))
        elif args.action == 'verify':
            verify(args.handoff, receipt); result = 'verified'
        elif args.action == 'stage':
            result = stage(args.handoff, receipt, args.root)
        else:
            result = switch(args.root, receipt, compatible=args.backend_compatible)
    print(json.dumps({'action': args.action, 'result': result}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Web release operation failed; no implicit replacement or activation') from None
