#!/usr/bin/env python3
"""Capture existing Backend recovery material; never generates/replaces service keys.

Run as administrator on the existing host. copy-confirm records an independently
computed PC SHA256 after operator transfer, not a promise that a copy was made.
"""
import argparse
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone

from common import checksum
from server import Platform, atomic


def require(condition, code):
    if not condition:
        raise ValueError(code)


def check_recovery_material(revision, names):
    base={'jwt.pem','recovery.key','lostark-fingerprint.key','.env.lightsail'}
    legacy=base|{'lostark-credential.key'}
    if revision=='0035_cycle_group_policy':
        require(names==legacy,'recovery_material_missing')
    elif revision=='0036_roster_presence':
        # Approved pre-cutover server token may already be staged on the old DB.
        require(legacy<=names<=legacy|{'lostark-api-token'},'recovery_material_missing')
    elif revision in ('0037_server_analysis','0038_analysis_candidates'):
        required=base|{'lostark-api-token'}
        require(required<=names<=required|{'lostark-credential.key'},'recovery_material_missing')
    else:
        raise ValueError('unexpected_backup_revision')


def active_web_files(web_root):
    """Read recovery originals without requiring the optional activation tools."""
    current=web_root/'current'
    if not current.is_symlink():
        require(not current.exists(),'unsafe_web_pointer')
        return []
    target=os.readlink(current)
    require(re.fullmatch(r'releases/[0-9a-f]{64}/site',target),'unsafe_web_pointer')
    site=web_root/target
    require(site.is_dir() and site.resolve().is_relative_to(web_root.resolve()),'unsafe_web_pointer')
    manifest=site.parent/'release-manifest.json'
    version=json.loads(manifest.read_text())['version']
    require(isinstance(version,str) and re.fullmatch(
        r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\+[1-9][0-9]*',version),'invalid_web_version')
    bundle=site.parent/('lostparty-v'+version.split('+')[0]+'-web.zip')
    paths=[bundle,Path(str(bundle)+'.sha256'),manifest]
    require(all(p.is_file() and not p.is_symlink() for p in paths),'missing_web_recovery_originals')
    return paths


def capture(platform, state, destination, *, installed=Path('/usr/local/lib/lostparty-deploy'),
            system_files=(Path('/etc/sudoers.d/lostparty-deploy'),Path('/home/lostparty-deploy/.ssh/authorized_keys')),
            web_root=Path('/var/lib/lostparty-web')):
    destination=Path(destination)
    require(destination.resolve().is_relative_to((platform.root/'backups').resolve()),'backup_destination_outside_private_root')
    require(not destination.exists(),'backup_destination_exists')
    current=json.loads((state/'current.json').read_text())
    before=platform.containers()
    protected=platform.protected_files()
    require(platform.healthy(current['image']),'baseline_unhealthy')
    revision=platform.db_revision(before['api']['Id'])
    names={Path(p).name for p in protected}
    check_recovery_material(revision,names)
    env=dict(item.split('=',1) for item in before['db']['Config']['Env'] if '=' in item)
    destination.mkdir(mode=0o700,parents=True)
    dump=subprocess.run(['docker','exec',before['db']['Id'],'pg_dump','-U','postgres',
                         '--format=custom','--lock-wait-timeout=5000',env['POSTGRES_DB']],
                        capture_output=True,check=True,timeout=120).stdout
    catalog=subprocess.run(['docker','exec','-i',before['db']['Id'],'pg_restore','--list'],
                           input=dump,capture_output=True,check=True,timeout=30).stdout
    require(dump.startswith(b'PGDMP') and b'alembic_version' in catalog,'invalid_database_dump')
    private=destination/'content';(private/'database').mkdir(parents=True,mode=0o700)
    (private/'database/database.dump').write_bytes(dump)
    paths=[Path(p) for p in protected]
    paths += [platform.root/'compose.lightsail.yaml',platform.root/'docker/Caddyfile.lightsail',platform.root/'docker/init-db.sh']
    paths += list(state.rglob('*.json'))
    paths += list(installed.glob('*.py'))
    paths += active_web_files(web_root)
    paths += list(system_files)
    recovery_files={}
    for path in paths:
        if not path.exists():continue
        require(path.is_file() and not path.is_symlink(),'unsafe_recovery_file')
        recovery_files[str(path)]=checksum(path.read_bytes())
    require(protected==platform.protected_files(),'backup_source_drift')
    require(json.loads((state/'current.json').read_text())==current,'deployment_changed_during_backup')
    archive=destination/'backend-production.tar'
    info={'created_at':datetime.now(timezone.utc).isoformat(),'source':current['source'],'image':current['image'],'db_revision':revision,'protected_files':{p:list(v) for p,v in protected.items()},'recovery_files':recovery_files,'archive_encrypted':False,'restore_tested':False}
    (private/'BACKUP-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    with tarfile.open(archive,'w') as tar:
        tar.add(private/'database',arcname='recovery/database')
        tar.add(private/'BACKUP-INFO.json',arcname='recovery/BACKUP-INFO.json')
        # Add originals directly so tar records their actual UID/GID/mode.
        sources=[Path(p) for p in recovery_files]
        directories={p.parent for p in sources}|{platform.root,platform.root/'.secrets'}
        for path in sorted(directories):
            if path.is_dir() and not path.is_symlink():
                tar.add(path,arcname='recovery/server/'+str(path).lstrip('/'),recursive=False)
        for path in sources:
            require(checksum(path.read_bytes())==recovery_files[str(path)],'recovery_file_changed')
            tar.add(path,arcname='recovery/server/'+str(path).lstrip('/'),recursive=False)
    require(protected==platform.protected_files(),'backup_source_drift')
    archive.chmod(0o600)
    record={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'source':current['source'],
            'image':current['image'],'db_revision':revision,'archive':str(archive),
            'archive_sha256':checksum(archive.read_bytes()),'dump_catalog_verified':True,
            'dump_catalog_entries':sum(not line.startswith(b';') and bool(line.strip()) for line in catalog.splitlines()),
            'protected_files':{p:list(v) for p,v in protected.items()},'recovery_files':recovery_files,
            'pc_copy_verified':False,'pc_archive_sha256':None,'database_restore_executed':False}
    atomic(destination/'receipt.json',record)
    return record


def confirm(path, provided):
    record=json.loads(Path(path).read_text())
    require(provided==record['archive_sha256']==checksum(Path(record['archive']).read_bytes()),'copy_hash_mismatch')
    record.update(pc_copy_verified=True,pc_archive_sha256=provided)
    atomic(path,record)
    return {'pc_copy_verified':True,'archive_sha256':provided}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['capture','copy-confirm'])
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--receipt',type=Path)
    parser.add_argument('--pc-sha256')
    args=parser.parse_args();require(os.geteuid()==0,'administrator_required')
    os.umask(0o077)
    state=Path('/var/lib/lostparty-deploy')
    with (state/'deploy.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.action=='capture':
            result=capture(Platform(),state,args.directory)
            print(json.dumps({k:result[k] for k in ['archive','archive_sha256','db_revision','pc_copy_verified']}))
        else:print(json.dumps(confirm(args.receipt,args.pc_sha256)))


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Backup operation failed; inspect private files; source keys/data unchanged') from None
