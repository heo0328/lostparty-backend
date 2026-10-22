#!/usr/bin/env python3
"""Back up the named development source READ ONLY; rehearse only in fresh tmpfs.

Private archives/manifests stay in ignored backups/ (0700/0600). Only aggregate
proof is printed. Source containers are never stopped, migrated or recreated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import shutil
import uuid

ROOT=Path(__file__).resolve().parents[1]
HELPER=(ROOT/'scripts/recruitment_snapshot.py').read_text()
SOURCE_API='lostparty-backend-api-1'
SOURCE_DB='lostparty-backend-db-1'
SOURCE_REVISION=['0023_recruitment_resume']
DIAGNOSTIC=None


class PreflightError(Exception):pass


def run(args,*,input=None,binary=False):
    result=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=not binary,cwd=ROOT)
    if result.returncode:
        if DIAGNOSTIC is not None:
            with DIAGNOSTIC.open('wb') as stream:stream.write(result.stderr if binary else result.stderr.encode())
        operation=next((v for v in args[1:] if v in {'inspect','up','down','ps','cp','psql','pg_restore','run','extract','audit','legacy','prepared','alembic','rm'}),'private helper')
        raise PreflightError('Command failed ('+operation+'); raw output suppressed to protect source data')
    return result.stdout


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        os.chmod(path,0o600);json.dump(value,stream,indent=2);stream.write('\n')


def compare(reference,actual,*,migration=False):
    if not migration and set(reference)!=set(actual):raise PreflightError('Restore table set differs')
    for name,value in reference.items():
        if migration and name=='alembic_version':continue
        if actual.get(name)!=value:raise PreflightError('Source row/column/record timestamp preservation failed')


def require_checkpoint_state(source,quiesced):
    if quiesced and source['State']['Running']:
        raise PreflightError('Checkpoint mode requires the API to already be stopped by the operator')


def main():
    global DIAGNOSTIC
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='docker')
    parser.add_argument('--image',required=True,help='Separately built latest candidate image; never retag the live API')
    parser.add_argument('--report',required=True,help='Public aggregate JSON output, without source rows/keys/digests')
    parser.add_argument('--quiesced-checkpoint',action='store_true',help='Only after the operator stops the API and all writers; this tool never stops them')
    args=parser.parse_args();docker=args.docker
    if subprocess.run(['git','check-ignore','-q','backups/preflight-probe'],cwd=ROOT).returncode:
        raise PreflightError('Private backup directory must be git-ignored')
    dockerignore=(ROOT/'.dockerignore').read_text().splitlines()
    if 'backups' not in dockerignore:raise PreflightError('Private backups must be excluded from Docker build contexts')
    previous=os.umask(0o077)
    nonce=uuid.uuid4().hex[:12];project='lostparty-preflight-'+nonce
    backup=ROOT/'backups'/project;backup.mkdir(mode=0o700,parents=True,exist_ok=False)
    DIAGNOSTIC=backup/'diagnostic.private.txt'
    password=uuid.uuid4().hex;role='lostparty_app';target='preflight_29';rollback='preflight_recovery_23'
    snapshot=None;started=False;runners=[]
    source=json.loads(run([docker,'inspect',SOURCE_API]))[0]
    source_db=json.loads(run([docker,'inspect',SOURCE_DB]))[0]
    require_checkpoint_state(source,args.quiesced_checkpoint)
    old_image=source['Image']
    if old_image==run([docker,'image','inspect','--format','{{.Id}}',args.image]).strip():
        raise PreflightError('Candidate image must be distinct from live image')
    try:
        # A separate read-only reader also works while the original API is stopped.
        networks=list(source['NetworkSettings']['Networks'])
        if len(networks)!=1 or networks[0] not in source_db['NetworkSettings']['Networks']:
            raise PreflightError('Unexpected development source network; review before backup')
        source_reader=project+'-source-reader'
        env=[]
        for value in source['Config']['Env']:env.extend(['-e',value])
        run([docker,'run','-d','--name',source_reader,'--network',networks[0],
            '--read-only','--volumes-from',SOURCE_API+':ro','--tmpfs','/tmp:mode=1777',
            '--cap-drop','ALL','--security-opt','no-new-privileges:true',*env,
            '-e','OWNERSHIP_WORKER_ENABLED=0','-e','RECRUITMENT_WORKER_ENABLED=0',old_image,'sleep','infinity'])
        runners.append(source_reader)
        # Hold one exported MVCC snapshot through fingerprint + pg_dump.
        snapshot=subprocess.Popen([docker,'exec','-i',source_reader,'python','-c',HELPER,'snapshot'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        line=snapshot.stdout.readline()
        if not line:raise PreflightError('Source snapshot failed; raw output suppressed')
        reference=json.loads(line)
        if reference['revision']!=SOURCE_REVISION:raise PreflightError('Unexpected source revision; stop for review')
        if not re.fullmatch(r'[0-9A-Fa-f-]+',reference['snapshot']):raise PreflightError('Invalid exported snapshot')
        archive=backup/'database.dump'
        with archive.open('xb') as stream:
            dumped=subprocess.run([docker,'exec',SOURCE_DB,'sh','-c',
                'exec pg_dump -U postgres -d "$POSTGRES_DB" --format=custom --snapshot="$1"',
                'sh',reference['snapshot']],stdout=stream,stderr=subprocess.PIPE,cwd=ROOT)
        if dumped.returncode:raise PreflightError('Snapshot dump failed; raw output suppressed')
        key_archive=backup/'auth-keys.tar'
        with key_archive.open('xb') as stream:
            exported=subprocess.run([docker,'exec',source_reader,'python','-c',HELPER,'keys'],stdout=stream,stderr=subprocess.PIPE,cwd=ROOT)
        if exported.returncode:raise PreflightError('Key backup failed; raw output suppressed')
        snapshot.stdin.write('complete\n');snapshot.stdin.flush();snapshot.stdin.close()
        if snapshot.wait(timeout=30):raise PreflightError('Source changed during backup or coordinator failed')
        save(backup/'source-manifest.private.json',reference)
        # Deployment settings contain credentials; keep them private alongside keys.
        save(backup/'source-runtime.private.json',{
            'api':{k:source[k] for k in ('Image','Config','Mounts')},
            'db':{k:source_db[k] for k in ('Image','Config','Mounts')}})
        if (ROOT/'.env').is_file():
            shutil.copyfile(ROOT/'.env',backup/'environment.private');(backup/'environment.private').chmod(0o600)
        archive_hash=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
        compose=[docker,'compose','-p',project,'-f','compose.preflight.yaml']
        started=True;run(compose+['up','-d','--wait','db'])
        db_name=run(compose+['ps','-q','db']).strip()
        network=project+'_isolated'
        if not json.loads(run([docker,'network','inspect',network]))[0]['Internal']:
            raise PreflightError('Restore network must prohibit external provider access')
        setup=f'''CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE {target} OWNER {role};
CREATE DATABASE {rollback} OWNER {role};'''
        run([docker,'exec','-i',db_name,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],input=setup)
        # pg_restore authenticates as the restricted LOGIN, not postgres/SET ROLE.
        def restore(database):
            run([docker,'exec','-i','-e','PGPASSWORD='+password,db_name,'pg_restore','-h','127.0.0.1','-U',role,
                '-d',database,'--no-owner','--no-acl','--exit-on-error'],input=archive.read_bytes(),binary=True)
            # Match the live topology: app owns objects, not the database/public schema.
            run([docker,'exec','-i',db_name,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],
                input=f'ALTER DATABASE {database} OWNER TO postgres;')
            run([docker,'exec','-i',db_name,'psql','-U','postgres','-d',database,'-v','ON_ERROR_STOP=1'],
                input=f'GRANT USAGE, CREATE ON SCHEMA public TO {role};')
        def runner(image,database,suffix):
            name=project+'-'+suffix
            url=f'postgresql+psycopg://{role}:{password}@db/{database}'
            run([docker,'run','-d','--name',name,'--network',network,'--read-only','--tmpfs','/tmp:mode=1777',
                '--tmpfs','/run/secrets:mode=0700,uid=10001,gid=10001','--cap-drop','ALL','--security-opt','no-new-privileges:true',
                '-e','DATABASE_URL='+url,'-e','POSTGRES_DB='+database,'-e','APP_DB_PASSWORD='+password,'-e','AUTH_SECRET_DIR=/run/secrets','-e','OWNERSHIP_WORKER_ENABLED=0',
                '-e','RECRUITMENT_WORKER_ENABLED=0',image,'sleep','infinity'])
            runners.append(name)
            run([docker,'exec','-i',name,'python','-c',
                "import os,sys; fd=os.open('/tmp/auth-keys.tar',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,'wb'); f.write(sys.stdin.buffer.read()); f.close()"],
                input=key_archive.read_bytes(),binary=True)
            run([docker,'exec',name,'python','-c',HELPER,'extract','/tmp/auth-keys.tar'])
            return name
        def audit(name,mode='audit'):
            return json.loads(run([docker,'exec',name,'python','-c',HELPER,mode]))
        restore(target);candidate=runner(args.image,target,'candidate')
        restored=audit(candidate);compare(reference['tables'],restored['tables'])
        if reference['sequences']!=restored['sequences'] or reference['database_profile']!=restored['database_profile']:
            raise PreflightError('Restore sequences or encoding/collation differ')
        if reference['keys']!=restored['keys']:raise PreflightError('Restored key content differs')
        # Migration executes ONLY in the newly named, isolated restore database.
        run([docker,'exec',candidate,'alembic','upgrade','0029_cycle_outcomes'])
        migrated=audit(candidate);compare(reference['tables'],migrated['tables'],migration=True)
        if any(migrated['sequences'].get(k)!=v for k,v in reference['sequences'].items()):
            raise PreflightError('Migration altered source sequence state')
        prepared=audit(candidate,'prepared')
        if not prepared['restricted_login']:raise PreflightError('Readiness must use restricted LOGIN')
        if prepared['explicit_cycles'] or prepared['executable_members'] or prepared['new_consents']:
            raise PreflightError('Legacy backup must not manufacture authority/participation/consent')
        projected=audit(candidate,'projections')
        audit(candidate,'worker')
        after_reads=audit(candidate)
        compare(migrated['tables'],after_reads['tables'])
        # Recover into a separate fresh 0023 DB; no downgrade or source overwrite.
        restore(rollback);old=runner(old_image,rollback,'recovery')
        recovered=audit(old);compare(reference['tables'],recovered['tables'])
        if reference['sequences']!=recovered['sequences'] or reference['database_profile']!=recovered['database_profile']:
            raise PreflightError('Recovery sequences or encoding/collation differ')
        if reference['keys']!=recovered['keys']:raise PreflightError('Recovery key content differs')
        old_ready=audit(old,'legacy')
        old_projected=audit(old,'old_projections')
        compare(reference['tables'],audit(old)['tables'])
        source_after=json.loads(run([docker,'inspect',SOURCE_API]))[0]
        source_db_after=json.loads(run([docker,'inspect',SOURCE_DB]))[0]
        source_status=json.loads(run([docker,'exec',source_reader,'python','-c',HELPER,'status']))
        if source_status['revision']!=SOURCE_REVISION or source_status['keys']!=reference['keys']:
            raise PreflightError('Live source revision or key content changed during rehearsal')
        if (backup/'environment.private').is_file() and (ROOT/'.env').read_bytes()!=(backup/'environment.private').read_bytes():
            raise PreflightError('Development environment changed during rehearsal')
        if source_after['Id']!=source['Id'] or source_after['Image']!=old_image or source_db_after['Id']!=source_db['Id']:
            raise PreflightError('Live source identity changed during rehearsal')
        report=dict(source_revision=reference['revision'],source_paths=old_ready['paths'],source_image=old_image,
            candidate_image=run([docker,'image','inspect','--format','{{.Id}}',args.image]).strip(),
            source_tables=len(reference['tables']),source_rows=sum(t['rows'] for t in reference['tables'].values()),
            source_aggregate=reference['aggregate'],restored_all_rows_columns_timestamps=True,keys_preserved=True,
            key_files=len(reference['keys']),sequence_count=len(reference['sequences']),sequences_preserved=True,
            database_profile=reference['database_profile'],migrated_old_tables_preserved=True,prepared=prepared,
            projections=projected,legacy_projections=old_projected,read_projections_and_worker_unchanged=True,
            private_runtime_config_backed_up=True,private_environment_file_backed_up=(backup/'environment.private').is_file(),
            recovery_0023_all_rows_columns_timestamps=True,recovery_old_image_ready=True,
            archive_sha256=archive_hash,source_containers_unchanged=True,
            consistent_snapshot=True,source_writes_paused=not source['State']['Running'],
            cutover_checkpoint=args.quiesced_checkpoint,backup_relative_path=str(backup.relative_to(ROOT)),
            limitations=[('Operator-declared checkpoint; all external writers must remain stopped' if args.quiesced_checkpoint else 'Snapshot is a rehearsal, not a quiesced cutover checkpoint'),
                'No real API/worker cutover or Flutter/provider/device acceptance',
                'Post-snapshot writes require a new checkpoint and approved recovery handling',
                'Sequence reads are not MVCC-snapshot-isolated; strict equality was verified for this rehearsal'])
        save(backup/'result.private.json',report)
    finally:
        if snapshot is not None and snapshot.poll() is None:
            snapshot.stdin.close();snapshot.wait(timeout=30)
        for name in reversed(runners):run([docker,'rm','-f',name])
        if started:run([docker,'compose','-p',project,'-f','compose.preflight.yaml','down'])
        os.umask(previous)

    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status='PASS',report=str(path),tables=report['source_tables'],rows=report['source_rows'],
        restore=True,migration_preservation=True,recovery=True,source_unchanged=True)))

if __name__=='__main__':
    try:main()
    except PreflightError as error:
        print('FAIL: '+str(error),file=sys.stderr)
        sys.exit(1)
    except (ValueError,TimeoutError,subprocess.TimeoutExpired):
        print('FAIL: preflight stopped; source data/keys and command output suppressed',file=sys.stderr)
        sys.exit(1)
