#!/usr/bin/env python3
"""Administrator-only v2.3.0/0036 -> v2.4.0/0038 reset, never auto-deployed.

prepare stops writers and captures their final dump. apply cannot reset until
an independently copied stopped dump is confirmed. No automatic old-API restart
after a reset; rollback restores that dump under maintenance before restarting.
"""
import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

from backup import require
from common import canonical, checksum, contract_probe, validate_manifest
from deployment_plan import load
from server import Platform, atomic, command, infrastructure, service_identity
from web_release import pointer, set_pointer, stage, switch, validate_active

STATE = Path('/var/lib/lostparty-deploy')
WEB = Path('/var/lib/lostparty-web')
OLD_SOURCE = '05daa424f06aa34edd76867bac1c78f9d558b51a'
OLD_REVISION = '0036_roster_presence'
NEW_REVISION = '0038_analysis_candidates'
DB = 'lostparty'
ACK = 'reset-production-lostparty-all-users-and-sessions'
SNAPSHOT_SQL = r"""BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT format(
 $snapshot$SELECT json_build_object('table',%L,'value',count(*)::text || ':' || md5(coalesce(string_agg(h,'' ORDER BY h),''))) FROM (SELECT md5(to_jsonb(t)::text) h FROM public.%I t) s;$snapshot$,
 tablename,tablename)
FROM pg_tables WHERE schemaname='public' ORDER BY tablename
\gexec
COMMIT;
"""


def age(created):
    seconds=(datetime.now(timezone.utc)-datetime.fromisoformat(created.replace('Z','+00:00'))).total_seconds()
    require(0 <= seconds <= 3600,'fresh_stopped_backup_required')


def binary(args, data=None):
    """Dump/restore bytes never enter logs or exceptions."""
    result=subprocess.run(args,input=data,capture_output=True,timeout=180)
    require(result.returncode==0,'private_database_command_failed')
    return result.stdout


def database_identity(containers):
    db=containers['db']
    env=dict(item.split('=',1) for item in db['Config']['Env'] if '=' in item)
    labels=db['Config'].get('Labels') or {}
    require(labels.get('com.docker.compose.project')=='lostparty-lightsail'
            and labels.get('com.docker.compose.service')=='db'
            and env.get('POSTGRES_DB')==DB,'production_database_identity_mismatch')
    return db['Id']


def sql(dbid, query, *, database='postgres'):
    require(database in ('postgres',DB),'unexpected_database')
    return command(['docker','exec','-i',dbid,'psql','-X','-qAt','-U','postgres',
                    '-d',database,'-v','ON_ERROR_STOP=1'],input=query).strip()


def no_writers(platform, record):
    require(checksum(Path(record['candidate_compose']).read_bytes())==record['candidate_compose_sha256'],'candidate_configuration_changed')
    containers=platform.containers()
    require(not containers['api']['State']['Running'],'api_must_be_stopped')
    require(service_identity(containers['db'])==tuple_identity(record['db_identity']), 'database_container_changed')
    require(service_identity(containers['caddy'])==tuple_identity(record['caddy_identity']), 'caddy_container_changed')
    require(platform.protected_files()=={p:tuple(v) for p,v in record['protected_files'].items()},'protected_files_changed')
    dbid=database_identity(containers)
    require(sql(dbid,"SELECT count(*) FROM pg_stat_activity WHERE datname='lostparty';")=='0','database_clients_still_connected')
    return dbid


def tuple_identity(value):
    return (value[0],value[1],value[2])


def private_snapshot(dbid):
    # One psql connection gives every table the same read-only snapshot. %I/%L
    # quote catalog identifiers/literals; gexec runs only generated SELECTs.
    rows=sql(dbid,SNAPSHOT_SQL,database=DB).splitlines()
    result={}
    for raw in rows:
        row=json.loads(raw);name=row['table'];value=row['value']
        require(re.fullmatch('[a-z_][a-z0-9_]*',name) and name not in result,'unsafe_table_identifier')
        require(re.fullmatch('[0-9]+:[0-9a-f]{32}',value),'invalid_table_snapshot')
        result[name]=value
    return result


def check_backup(receipt, current, protected):
    require(receipt['source']==current['source'] and receipt['image']==current['image']
            and receipt['db_revision']==OLD_REVISION,'backup_identity_mismatch')
    age(receipt['created_at'])
    require(receipt['protected_files']=={p:list(v) for p,v in protected.items()},'backup_configuration_drift')
    require(receipt['pc_copy_verified'] is True and receipt['pc_archive_sha256']==receipt['archive_sha256']
            and receipt['dump_catalog_verified'] is True,'verified_pc_backup_required')
    archive=Path(receipt['archive'])
    require(archive.is_file() and not archive.is_symlink()
            and checksum(archive.read_bytes())==receipt['archive_sha256'],'backup_archive_mismatch')


def preflight(platform, state, manifest, receipt):
    validate_manifest(manifest)
    require(manifest['schema']==2 and manifest['tag']=='v2.4.0'
            and manifest['db_revision']==NEW_REVISION,'unexpected_reset_candidate')
    current=json.loads((state/'current.json').read_text())
    require(current['tag']=='v2.3.0' and current['source']==OLD_SOURCE
            and current['configuration_revision']=='lightsail-web-2.1.0','unexpected_reset_baseline')
    require(not any(json.loads(p.read_text()).get('status')=='in_progress' for p in state.glob('*/result.json')),'unfinished_deployment')
    require(platform.healthy(current['image']),'baseline_unhealthy')
    containers=platform.containers();database_identity(containers)
    api_env=dict(item.split('=',1) for item in containers['api']['Config']['Env'] if '=' in item)
    require('DATABASE_URL' not in api_env and api_env.get('POSTGRES_DB')==DB,'api_database_target_drift')
    require(sql(containers['db']['Id'],"SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='lostparty';")=='postgres','unexpected_database_owner')
    require(sql(containers['db']['Id'],"SELECT count(*) FROM pg_roles WHERE rolname='lostparty_app' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole;")=='1','unexpected_app_role')
    require(platform.db_revision(containers['api']['Id'])==OLD_REVISION,'unexpected_live_revision')
    baseline=platform.config(current['compose'])
    for service in ('api','db','caddy'):
        expected=baseline['services'][service]
        require(containers[service]['Image']==platform.image_info(expected['image'])['Id'],'live_image_drift')
        require(set(k+'='+str(v) for k,v in expected.get('environment',{}).items()).issubset(containers[service]['Config']['Env']),'live_environment_drift')
    require(containers['api']['Config']['Cmd']==baseline['services']['api']['command'],'live_command_drift')
    require(any(m['Destination']=='/run/secrets' and m['RW'] is False for m in containers['api']['Mounts']),'secret_mount_drift')
    mounts=baseline['services']['caddy']['volumes']
    require(any(m.get('target')=='/srv/web' and m.get('source')==str(WEB) and m.get('read_only') is True for m in mounts),'web_mount_drift')
    require(receipt['web']['version']=='2.4.0+9','unexpected_native_version')
    require(pointer(WEB,'current') is not None and not (WEB/'maintenance').exists(),'unexpected_maintenance_state')
    platform.probes();platform.pull(manifest['image'])
    image=platform.image_info(manifest['image']);labels=image['Config'].get('Labels') or {}
    require(image['Architecture']=='amd64' and image['Os']=='linux'
            and labels.get('org.opencontainers.image.revision')==manifest['source']
            and labels.get('org.opencontainers.image.version')==manifest['tag'],'candidate_image_mismatch')
    require(platform.image_revision(manifest['image'])==NEW_REVISION,'candidate_head_mismatch')
    return current,baseline,containers


def closed_edge(platform):
    import urllib.error
    import urllib.request
    try:response=urllib.request.urlopen('https://lostparty.duckdns.org/health',timeout=10)
    except urllib.error.HTTPError as error:response=error
    with response:
        require(response.status==503 and response.read().strip()==b'Maintenance','public_maintenance_not_closed')


def write_record(directory, record, **changes):
    record.update(changes);atomic(directory/'result.json',record)


def prepare(platform, state, manifest, receipt, handoff, backup):
    current,baseline,containers=preflight(platform,state,manifest,receipt)
    protected=platform.protected_files();check_backup(backup,current,protected)
    stage(handoff,receipt,WEB)
    directory=state/'reset-2.4.0';directory.mkdir(mode=0o700,exist_ok=False)
    candidate=copy.deepcopy(baseline);candidate['services']['api']['image']=manifest['image']
    candidate['services']['api'].pop('build',None)
    require(infrastructure(candidate)==infrastructure(baseline),'unexpected_configuration_change')
    compose=directory/'candidate.compose.json';atomic(compose,candidate)
    record=dict(status='in_progress',phase='preparing',manifest=manifest,receipt=receipt,
                previous_good=current,protected_files={p:list(v) for p,v in protected.items()},
                db_identity=list(service_identity(containers['db'])),caddy_identity=list(service_identity(containers['caddy'])),
                previous_web=pointer(WEB,'current'),candidate_compose=str(compose),
                candidate_compose_sha256=checksum(compose.read_bytes()),reset_started=False,public_open=False)
    atomic(directory/'result.json',record)
    (WEB/'maintenance').touch(mode=0o644,exist_ok=False)
    try:
        closed_edge(platform)
        platform.compose(current['compose'],'stop','api')
        dbid=no_writers(platform,record)
        snapshot=private_snapshot(dbid)
        dump=binary(['docker','exec',dbid,'pg_dump','-U','postgres','-Fc','--lock-wait-timeout=5000',DB])
        require(dump.startswith(b'PGDMP'),'invalid_stopped_dump')
        require(b'alembic_version' in binary(['docker','exec','-i',dbid,'pg_restore','--list'],dump),'invalid_stopped_dump_catalog')
        path=directory/'stopped.database.dump'
        with path.open('xb') as stream:stream.write(dump)
        path.chmod(0o600)
        no_writers(platform,record)
        write_record(directory,record,phase='stopped_backup_pending',stopped_dump_sha256=checksum(dump),
                     stopped_at=datetime.now(timezone.utc).isoformat(),snapshot=snapshot)
    except Exception:
        write_record(directory,record,phase='prepare_failed')
        raise  # Keep maintenance and stopped writers; operator chooses rollback.
    return record


def confirm_stopped(directory, record, digest):
    require(record['phase']=='stopped_backup_pending','unexpected_reset_phase')
    age(record['stopped_at'])
    require(digest==record['stopped_dump_sha256']==checksum((directory/'stopped.database.dump').read_bytes()),'stopped_pc_copy_mismatch')
    write_record(directory,record,phase='stopped_pc_confirmed',stopped_pc_confirmed=True)


def recreate(dbid):
    # No FORCE: an unexpected writer must prevent destruction.
    sql(dbid,"DROP DATABASE IF EXISTS lostparty;")
    sql(dbid,"CREATE DATABASE lostparty OWNER postgres;")
    sql(dbid,"REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE, CREATE ON SCHEMA public TO lostparty_app;",database=DB)


def candidate_checks(platform, record, contracts):
    containers=platform.containers();api=containers['api'];manifest=record['manifest']
    require(platform.healthy(manifest['image']),'candidate_unhealthy')
    require(platform.db_revision(api['Id'])==NEW_REVISION,'candidate_database_revision_mismatch')
    actual=json.loads(command(['docker','exec',api['Id'],'python','-c',contract_probe(2)]))
    require(actual==contracts,'candidate_contract_mismatch')
    code="import urllib.request,urllib.error;\ntry: urllib.request.urlopen('http://127.0.0.1:8000/v1/me',timeout=5)\nexcept urllib.error.HTTPError as e: assert e.code==401\nelse: raise AssertionError('unauthenticated me accepted')"
    command(['docker','exec',api['Id'],'python','-c',code])
    response=command(['docker','exec',containers['caddy']['Id'],'wget','-q','-O','-','http://127.0.0.1:8081/health'])
    require(json.loads(response)=={'status':'ok','database':'ok'},'candidate_health_mismatch')
    require(platform.protected_files()=={p:tuple(v) for p,v in record['protected_files'].items()},'protected_files_changed')
    for name in ('db','caddy'):
        require(service_identity(containers[name])==tuple_identity(record[name+'_identity']),'infrastructure_changed')
    closed_edge(platform)


def apply(platform, state, directory, record, contracts, acknowledgment):
    require(acknowledgment==ACK,'explicit_reset_acknowledgment_required')
    require(record['phase']=='stopped_pc_confirmed' and record.get('stopped_pc_confirmed') is True,'stopped_pc_confirmation_required')
    age(record['stopped_at']);closed_edge(platform)
    require(json.loads((state/'current.json').read_text())==record['previous_good'],'current_release_changed')
    dbid=no_writers(platform,record)
    require(checksum((directory/'stopped.database.dump').read_bytes())==record['stopped_dump_sha256'],'stopped_dump_changed')
    require(private_snapshot(dbid)==record['snapshot'],'stopped_database_changed')
    require(sql(dbid,'SELECT version_num FROM alembic_version;',database=DB)==OLD_REVISION,'unexpected_reset_revision')
    write_record(directory,record,phase='reset_started',reset_started=True)
    try:
        recreate(dbid)
        platform.compose(record['candidate_compose'],'run','--rm','--no-deps','--entrypoint','alembic','api','upgrade',NEW_REVISION)
        require(sql(dbid,'SELECT version_num FROM alembic_version;',database=DB)==NEW_REVISION,'migration_failed')
        require(sql(dbid,'SELECT (SELECT count(*) FROM users)+(SELECT count(*) FROM auth_sessions)+(SELECT count(*) FROM game_accounts);',database=DB)=='0','app_data_not_empty')
        platform.replace(record['candidate_compose'])
        candidate_checks(platform,record,contracts)
        switch(WEB,record['receipt'],compatible=True)
        validate_active(WEB,record['receipt'])
        api=platform.containers()['api']
        index=binary(['docker','exec',platform.containers()['caddy']['Id'],'wget','-q','-O','-','http://127.0.0.1:8081/'])
        require(index==(WEB/'current/index.html').read_bytes(),'candidate_web_bytes_mismatch')
        current={**record['manifest'],'configuration_revision':'lightsail-web-2.1.0','compose':record['candidate_compose'],
                 'public_open':False,'web':record['receipt']['web'],'deployed_at_utc':datetime.now(timezone.utc).isoformat()}
        atomic(state/'current.json',current)
        write_record(directory,record,phase='candidate_ready',candidate_api_id=api['Id'])
    except Exception:
        write_record(directory,record,phase='apply_failed_restore_required')
        raise  # No old API restart on new/partially migrated schema.


def rollback(platform, state, directory, record, acknowledgment):
    require(not record.get('public_open'),'rollback_after_publication_requires_new_plan')
    require(acknowledgment==ACK,'explicit_restore_acknowledgment_required')
    require((WEB/'maintenance').is_file(),'maintenance_required')
    closed_edge(platform)
    platform.compose(record['candidate_compose'],'stop','api')
    dbid=no_writers(platform,record)
    if record['reset_started']:
        dump=(directory/'stopped.database.dump').read_bytes()
        require(checksum(dump)==record['stopped_dump_sha256'],'restore_dump_changed')
        exists=sql(dbid,"SELECT count(*) FROM pg_database WHERE datname='lostparty';")=='1'
        unchanged=exists and private_snapshot(dbid)==record['snapshot']
        if not unchanged:
            # Even before opening publicly, unexpected new rows require investigation.
            if exists and sql(dbid,"SELECT CASE WHEN to_regclass('public.users') IS NULL THEN 0 ELSE 1 END;",database=DB)=='1':
                require(sql(dbid,'SELECT count(*) FROM users;',database=DB)=='0','unexpected_new_users_manual_recovery_required')
            recreate(dbid)
            binary(['docker','exec','-i',dbid,'pg_restore','-U','postgres','--exit-on-error','-d',DB],dump)
            require(private_snapshot(dbid)==record['snapshot'],'restored_database_snapshot_mismatch')
    if record['previous_web']:
        set_pointer(WEB,'current',record['previous_web'])
    previous=record['previous_good'];platform.replace(previous['compose'])
    require(platform.healthy(previous['image']),'restored_api_unhealthy')
    require(platform.db_revision(platform.containers()['api']['Id'])==OLD_REVISION,'restored_revision_mismatch')
    atomic(state/'current.json',previous)
    write_record(directory,record,status='rolled_back',phase='rolled_back_under_maintenance')


def open_public(platform, state, directory, record, contracts, accepted):
    require(record['phase']=='candidate_ready','candidate_not_ready')
    require(isinstance(accepted,dict) and set(accepted)=={
                'backend_source','web_sha256','backend_checks','native_checks','joint_publication_authorized'}
            and accepted['backend_source']==record['manifest']['source']
            and accepted['web_sha256']==record['receipt']['web']['bundle_sha256']
            and all(accepted[k] is True for k in ('backend_checks','native_checks','joint_publication_authorized')),
            'joint_acceptance_required')
    candidate_checks(platform,record,contracts);validate_active(WEB,record['receipt'])
    (WEB/'maintenance').unlink()
    try:platform.probes()
    except Exception:
        (WEB/'maintenance').touch();raise
    current=json.loads((state/'current.json').read_text());current['public_open']=True;atomic(state/'current.json',current)
    write_record(directory,record,status='succeeded',phase='public_open',public_open=True)


def open_restored(platform, state, directory, record, accepted):
    """Reopen only the verified old release after an explicit rollback decision."""
    require(record['phase']=='rolled_back_under_maintenance','restored_release_not_ready')
    previous=record['previous_good']
    expected={'backend_source':previous['source'],
              'web_sha256':record['previous_web'].split('/')[1],
              'backend_checks':True,'native_checks':True,'joint_publication_authorized':True}
    require(isinstance(accepted,dict) and set(accepted)==set(expected)
            and accepted['backend_source']==expected['backend_source']
            and accepted['web_sha256']==expected['web_sha256']
            and all(accepted[k] is True for k in ('backend_checks','native_checks','joint_publication_authorized')),
            'restored_publication_acceptance_required')
    require(json.loads((state/'current.json').read_text())==previous,'restored_current_changed')
    require(platform.protected_files()=={p:tuple(v) for p,v in record['protected_files'].items()},'protected_files_changed')
    require(platform.healthy(previous['image']),'restored_api_unhealthy')
    containers=platform.containers()
    require(platform.db_revision(containers['api']['Id'])==OLD_REVISION,'restored_revision_mismatch')
    for name in ('db','caddy'):
        require(service_identity(containers[name])==tuple_identity(record[name+'_identity']),'infrastructure_changed')
    require(pointer(WEB,'current')==record['previous_web'],'restored_web_changed')
    closed_edge(platform)
    response=command(['docker','exec',containers['caddy']['Id'],'wget','-q','-O','-',
                      'http://127.0.0.1:8081/health'])
    require(json.loads(response)=={'status':'ok','database':'ok'},'restored_internal_health_failed')
    (WEB/'maintenance').unlink()
    try:platform.probes()
    except Exception:
        (WEB/'maintenance').touch();raise
    write_record(directory,record,status='rolled_back',phase='restored_public_open',public_open=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preflight','prepare','confirm-stopped-backup','apply','rollback','open','open-restored'])
    parser.add_argument('--release-root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--handoff',type=Path)
    parser.add_argument('--backup-receipt',type=Path)
    parser.add_argument('--pc-dump-sha256')
    parser.add_argument('--acknowledge')
    parser.add_argument('--joint-acceptance',type=Path)
    args=parser.parse_args();require(os.geteuid()==0,'administrator_required');os.umask(0o077)
    require(Path(__file__).resolve()==(args.release_root/'scripts/deployment/reset_release.py').resolve(),'reviewed_release_source_required')
    require(load(args.release_root)['mode']=='publish-only','publish_only_release_required')
    manifest=validate_manifest(json.loads(args.manifest.read_text()))
    require(command(['git','-C',str(args.release_root),'rev-parse','HEAD']).strip()==manifest['source'],'release_checkout_mismatch')
    require(command(['git','-C',str(args.release_root),'status','--porcelain']).strip()=='','clean_release_checkout_required')
    require(checksum((args.release_root/'compose.lightsail.yaml').read_bytes())==manifest['compose_sha256'],'compose_contract_mismatch')
    contracts={}
    for name,digest in manifest['contract_sha256'].items():
        raw=(args.release_root/'openapi'/name).read_bytes();require(checksum(raw)==digest,'contract_file_mismatch')
        contracts[name]=checksum(canonical(json.loads(raw)))
    receipt=json.loads((args.release_root/'docs/engineering/operations/records/web-handoff-2.4.0.json').read_text())
    platform=Platform();directory=STATE/'reset-2.4.0'
    with (STATE/'deploy.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='preflight':preflight(platform,STATE,manifest,receipt)
        elif args.action=='prepare':
            require(args.handoff is not None and args.backup_receipt is not None,'handoff_and_backup_required')
            prepare(platform,STATE,manifest,receipt,args.handoff,json.loads(args.backup_receipt.read_text()))
        else:
            record=json.loads((directory/'result.json').read_text())
            require(record['manifest']==manifest and record['receipt']==receipt,'journal_candidate_mismatch')
            if args.action=='confirm-stopped-backup':confirm_stopped(directory,record,args.pc_dump_sha256)
            elif args.action=='apply':apply(platform,STATE,directory,record,contracts,args.acknowledge)
            elif args.action=='rollback':rollback(platform,STATE,directory,record,args.acknowledge)
            else:
                require(args.joint_acceptance is not None,'joint_acceptance_required')
                accepted=json.loads(args.joint_acceptance.read_text())
                if args.action=='open-restored':open_restored(platform,STATE,directory,record,accepted)
                else:open_public(platform,STATE,directory,record,contracts,accepted)
    print(json.dumps({'action':args.action,'completed':True}))  # No private journal/dump/key fingerprints.


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Reset release step failed; inspect private journal; maintenance is not automatically removed') from None
