#!/usr/bin/env python3
"""Administrator-only 0035->0036 transition; never exposed by restricted SSH.

preflight is read-only (except image pull). apply requires the reviewed immutable
release, staged web, and a fresh backup receipt with verified PC copy. Public
maintenance remains enabled until the separate open command after joint review.
"""
import argparse
import ipaddress
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from common import checksum, validate_manifest
from deployment_plan import load
from server import Platform, atomic, command, service_identity
from web_release import stage, switch, validate_active

NEW_ANDROID = '574337852234-2m3nnr5jaa46okro5vpbvsgddgrloob3.apps.googleusercontent.com'
WEB_CLIENT = '574337852234-vdkvdobbq8es2rdpumc1icqt6ja3a3cr.apps.googleusercontent.com'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def candidate_config(baseline, manifest, web_root, caddy_file, probe_ip="127.0.0.1"):
    data = copy.deepcopy(baseline)
    api = data['services']['api']
    api['image'] = manifest['image']
    api.pop('build', None)
    env = api['environment']
    require(env.get('GOOGLE_CLIENT_ID') == WEB_CLIENT, 'audience_drift')
    azp = [s for s in env.get('GOOGLE_AZP_ALLOWLIST', '').split(',') if s]
    require(len(azp) == len(set(azp)), 'duplicate_existing_azp')
    if NEW_ANDROID not in azp:
        azp.append(NEW_ANDROID)
    env['GOOGLE_AZP_ALLOWLIST'] = ','.join(azp)
    require(str(ipaddress.ip_address(probe_ip)) == probe_ip, 'exact_probe_address_required')
    data['services']['caddy'].setdefault('environment',{})['MAINTENANCE_PROBE_IPS']=probe_ip
    mounts = data['services']['caddy']['volumes']
    require(not any(m.get('target') == '/srv/web' for m in mounts), 'unexpected_web_baseline')
    files = [m for m in mounts if m.get('target') == '/etc/caddy/Caddyfile']
    require(len(files) == 1 and files[0].get('read_only') is True, 'caddy_mount_drift')
    files[0]['source'] = str(caddy_file)
    mounts.append({'type': 'bind', 'source': str(web_root), 'target': '/srv/web', 'read_only': True})
    return data


def check_backup(receipt, current, protected, now=None):
    now = now or datetime.now(timezone.utc)
    require(receipt['source'] == current['source'] and receipt['image'] == current['image']
            and receipt['db_revision'] == '0035_cycle_group_policy', 'backup_identity_mismatch')
    age = (now - datetime.fromisoformat(receipt['created_at'].replace('Z', '+00:00'))).total_seconds()
    require(0 <= age <= 3600, 'fresh_backup_required')
    path = Path(receipt['archive'])
    require(path.is_file() and checksum(path.read_bytes()) == receipt['archive_sha256'], 'backup_hash_mismatch')
    require(receipt['pc_archive_sha256'] == receipt['archive_sha256']
            and receipt['pc_copy_verified'] is True, 'pc_backup_confirmation_required')
    require(receipt['dump_catalog_verified'] is True, 'dump_verification_required')
    # Same keys/config as at backup capture; no values are printed.
    require(receipt['protected_files'] == {p: list(v) for p, v in protected.items()}, 'backup_configuration_drift')


def preflight(platform, state, manifest, plan):
    current = json.loads((state / 'current.json').read_text())
    # A stale normal-deploy recovery journal could otherwise restore a0035
    # predecessor after this forward migration. Resolve it BEFORE transition.
    for journal in state.glob('*/result.json'):
        require(json.loads(journal.read_text()).get('status')!='in_progress','unfinished_deployment_journal')
    require(current['tag'] == 'v2.0.0', 'unexpected_current_release')
    require(manifest['tag'] == 'v2.1.0' and manifest['db_revision'] == plan['to_db_revision'], 'candidate_identity')
    require(platform.healthy(current['image']), 'baseline_unhealthy')
    before = platform.containers()
    require(platform.db_revision(before['api']['Id']) == plan['from_db_revision'], 'unexpected_db_revision')
    baseline = platform.config(current['compose'])
    for service in ('db','caddy'):
        require(platform.image_info(baseline['services'][service]['image'])['Id']==before[service]['Image'],
                'baseline_infrastructure_image_drift')
    expected_env = [k + '=' + str(v) for k,v in baseline['services']['api']['environment'].items()]
    require(set(expected_env).issubset(before['api']['Config']['Env']), 'live_environment_drift')
    require(before['api']['Config']['Cmd'] == baseline['services']['api']['command'], 'live_command_drift')
    require(shutil.disk_usage(platform.root).free >= 3*1024**3, 'insufficient_disk')
    platform.probes()
    platform.pull(manifest['image'])
    image = platform.image_info(manifest['image'])
    labels = image['Config'].get('Labels', {})
    require(image['Architecture'] == 'amd64' and image['Os'] == 'linux'
            and labels.get('org.opencontainers.image.revision') == manifest['source']
            and labels.get('org.opencontainers.image.version') == manifest['tag'], 'image_identity_mismatch')
    require(platform.image_revision(manifest['image']) == plan['to_db_revision'], 'image_revision_mismatch')
    return current, baseline, before


def table_snapshot(platform, candidate):
    """Private count/digest evidence while all app writers are stopped."""
    code = """import json,re
from sqlalchemy import text
from app.core.database import engine
with engine().connect() as c:
 c.exec_driver_sql('SET TRANSACTION READ ONLY')
 names=c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'alembic_version' ORDER BY tablename")).scalars().all()
 result={}
 for name in names:
  assert re.fullmatch('[a-z_][a-z0-9_]*',name)
  result[name]=list(c.exec_driver_sql('SELECT count(*), md5(coalesce(string_agg(md5(t::text), chr(10) ORDER BY md5(t::text)), chr(10))) FROM public.'+name+' AS t').one())
 print(json.dumps(result))
"""
    return json.loads(platform.compose(candidate,'run','--rm','--no-deps','--entrypoint','python','api','-c',code))


def transition(platform, state, manifest, plan, receipt, handoff, web_root, caddy_source, backup, contracts, probe_ip="127.0.0.1"):
    current, baseline, before = preflight(platform, state, manifest, plan)
    protected = platform.protected_files()
    check_backup(backup, current, protected)
    require(plan['configuration_revision'] == 'lightsail-web-2.1.0', 'configuration_identity')
    stage(handoff, receipt, web_root)  # Safe to stage before maintenance; no active pointer.
    require(not (web_root / 'current').exists() and not (web_root / 'current').is_symlink(), 'first_web_release_only')
    directory = state / 'maintenance-2.1.0'
    require(not directory.exists(), 'existing_transition_requires_recovery_review')
    directory.mkdir(mode=0o700)
    old_caddy = next(m['source'] for m in baseline['services']['caddy']['volumes'] if m['target']=='/etc/caddy/Caddyfile')
    saved_caddy = directory / 'previous.Caddyfile'
    shutil.copy2(old_caddy, saved_caddy)
    new_caddy = directory / 'Caddyfile'
    shutil.copy2(caddy_source, new_caddy)
    # Keep the canonical host path so later standard deployments compare equal.
    config = candidate_config(baseline, manifest, web_root, Path(old_caddy), probe_ip)
    candidate = directory / 'compose.json'
    atomic(candidate, config)
    validation_config=copy.deepcopy(config)
    # One-off validation must not contend for the live Caddy's fixed address.
    for network in validation_config['services']['caddy'].get('networks',{}).values():
        if isinstance(network,dict):
            network.pop('ipv4_address',None);network.pop('ipv6_address',None)
    for mount in validation_config['services']['caddy']['volumes']:
        if mount.get('target')=='/etc/caddy/Caddyfile': mount['source']=str(new_caddy)
    validation_file=directory/'validation.compose.json'
    atomic(validation_file,validation_config)
    platform.compose(validation_file, 'run', '--rm', '--no-deps', '--entrypoint', 'caddy',
                     'caddy', 'validate', '--config', '/etc/caddy/Caddyfile')
    marker = web_root / 'maintenance'
    marker.touch(mode=0o644, exist_ok=False)
    record = {'phase':'prepared', 'db_migration_started':False, 'public_open':False,
              'source':manifest['source'], 'image':manifest['image'], 'previous_good':current,
              'configuration_revision':plan['configuration_revision']}
    record['web']={k:receipt['web'][k] for k in ('source','version','artifact_id','run_id','bundle_sha256') if k in receipt['web']}
    record['apk']={k:receipt.get('apk',{}).get(k) for k in ('source','artifact_id','native_reported_sha256')}
    record['native_acceptance']='pending'
    journal = directory / 'result.json'
    atomic(journal, record)
    try:
        require(checksum(Path(old_caddy).read_bytes())==checksum(saved_caddy.read_bytes()),'caddy_source_drift')
        shutil.copyfile(new_caddy,old_caddy)
        # Recreate ONLY Caddy against the old API and new read-only web mount.
        # The maintenance file starts blocking public traffic before stopping API.
        platform.compose(candidate, 'up', '-d', '--no-deps', '--no-build', '--pull','never', 'caddy')
        # Confirm maintenance edge is actually responding before stopping writers.
        try:
            response = urllib.request.urlopen('https://lostparty.duckdns.org/health', timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        require(response.status == 503 and response.read().strip() == b'Maintenance', 'maintenance_not_active')
        platform.compose(current['compose'], 'stop', 'api')
        record['phase']='api_stopped'; atomic(journal,record)
        original_tables=table_snapshot(platform,candidate)
        require(protected == platform.protected_files(), 'protected_files_changed')
        record.update(phase='migration_started', db_migration_started=True); atomic(journal,record)
        # Disposable candidate process, same limited app role and schema ownership.
        platform.compose(candidate, 'run', '--rm', '--no-deps', '--entrypoint', 'alembic',
                         'api', 'upgrade', plan['to_db_revision'], timeout=180)
        after_tables=table_snapshot(platform,candidate)
        require(all(after_tables.get(name)==value for name,value in original_tables.items()),'existing_table_data_changed')
        record['preserved_existing_table_count']=len(original_tables)
        record['existing_table_counts_and_digests_preserved']=True
        record['phase']='schema_migrated'; atomic(journal,record)
        platform.replace(candidate)
        deadline = time.monotonic()+120
        while not platform.healthy(manifest['image']):
            require(time.monotonic()<deadline,'candidate_health_timeout'); time.sleep(2)
        after = platform.containers()
        require(platform.db_revision(after['api']['Id']) == plan['to_db_revision'], 'migration_not_applied')
        require(service_identity(before['db']) == service_identity(after['db']), 'db_container_changed')
        require(protected == platform.protected_files(), 'protected_files_changed')
        # Exact schemas via internal container execution; HTTP checks follow separately.
        code = "import json,hashlib; from app.main import app,create_two_cycle_app; print(json.dumps({n:hashlib.sha256(json.dumps(a.openapi(),sort_keys=True,separators=(',',':')).encode()).hexdigest() for n,a in [('openapi.yaml',app),('two-cycle.openapi.yaml',create_two_cycle_app())]}))"
        generated = json.loads(command(['docker','exec',after['api']['Id'],'python','-c',code]))
        require(generated == contracts, 'generated_contract_mismatch')
        record['generated_contract_canonical_sha256']=generated
        caddy_id=after['caddy']['Id']
        health=json.loads(command(['docker','exec',caddy_id,'wget','-q','-O','-',
                                  'http://127.0.0.1:8081/health']))
        require(health == {'status':'ok','database':'ok'}, 'internal_edge_health_failed')
        # Keep source environment aligned with the new frozen configuration.
        env_path=platform.root/'.env.lightsail'
        old_env=env_path.read_text()
        (directory/'previous.env').write_text(old_env)
        (directory/'previous.env').chmod(0o600)
        value=config['services']['api']['environment']['GOOGLE_AZP_ALLOWLIST']
        require(len(re.findall(r'^GOOGLE_AZP_ALLOWLIST=',old_env,re.M))==1,'environment_field_missing_or_duplicate')
        new_env=re.sub(r'^GOOGLE_AZP_ALLOWLIST=.*$',lambda _: 'GOOGLE_AZP_ALLOWLIST='+value,old_env,flags=re.M)
        require(len(re.findall(r'^MAINTENANCE_PROBE_IPS=',new_env,re.M))<=1,'duplicate_probe_environment')
        if re.search(r'^MAINTENANCE_PROBE_IPS=',new_env,re.M):
            new_env=re.sub(r'^MAINTENANCE_PROBE_IPS=.*$',lambda _: 'MAINTENANCE_PROBE_IPS='+probe_ip,new_env,flags=re.M)
        else:
            new_env=new_env.rstrip('\n')+'\nMAINTENANCE_PROBE_IPS='+probe_ip+'\n'
        from tempfile import NamedTemporaryFile
        mode=env_path.stat()
        with NamedTemporaryFile(dir=env_path.parent,delete=False) as f:
            f.write(new_env.encode()); temp=Path(f.name)
        os.chmod(temp,mode.st_mode & 0o777); os.chown(temp,mode.st_uid,mode.st_gid)
        os.replace(temp,env_path)
        changed=platform.protected_files()
        require(all(changed.get(p)==v for p,v in protected.items() if p!=str(env_path)), 'service_keys_changed')
        new_current={**manifest,'configuration_revision':plan['configuration_revision'],
                     'compose':str(candidate),'deployed_at_utc':datetime.now(timezone.utc).isoformat(),
                     'public_open':False,'web_status':'candidate','web':record['web'],'apk':record['apk'],'native_acceptance':'pending'}
        atomic(directory/'previous.json',current)
        atomic(state/'current.json',new_current)
        record.update(phase='backend_ready',db_revision=plan['to_db_revision']);atomic(journal,record)
        # Web switch requires new Backend schema/health, and leaves maintenance on.
        switch(web_root, receipt, compatible=True)
        # Check exact staged index bytes and MIME through the running edge.
        index=command(['docker','exec',caddy_id,'wget','-q','-O','-', 'http://127.0.0.1:8081/'])
        require(index.encode()==(web_root/'current/index.html').read_bytes(),'edge_index_mismatch')
        install_controller(Path(__file__).parent, Path('/usr/local/lib/lostparty-deploy'), backup)
        new_current['web_status']='activated_under_maintenance'
        atomic(state/'current.json',new_current)
        record['phase']='candidate_ready';atomic(journal,record)
        return {k:v for k,v in record.items() if k!='previous_good'}
    except Exception:
        record['phase']='failed_forward_repair_required' if record['db_migration_started'] else 'failed_before_migration'
        atomic(journal,record)
        # Never blindly restore old API after migration began; marker remains.
        if not record['db_migration_started']:
            shutil.copyfile(saved_caddy,old_caddy)
            platform.compose(current['compose'], 'up','-d','--no-deps','--no-build','--pull','never','caddy')
            platform.replace(Path(current['compose']))
            # Legacy Caddy cannot enforce the marker after restoration; this is
            # pre-migration rollback to the unchanged old service, not new-publication.
        raise


def install_controller(source_root, installed, backup):
    """No key/account/sudo changes; expected installed bytes must match backup."""
    for name in ('server.py', 'common.py'):
        existing = installed/name
        require(backup['recovery_files'].get(str(existing)) == checksum(existing.read_bytes()), 'controller_drift')
    for name in ('server.py', 'common.py'):
        source = source_root/name
        temp = installed/(name+'.maintenance-new')
        with temp.open('xb') as out:
            out.write(source.read_bytes())
        temp.chmod(0o644)
        os.replace(temp, installed/name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preflight','apply','open'])
    parser.add_argument('--release-root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--handoff',type=Path,required=True)
    parser.add_argument('--backup-receipt',type=Path)
    parser.add_argument('--joint-acceptance',type=Path)
    parser.add_argument('--probe-ip',help='Exact public IP of the approved Native/user test connection; no CIDR')
    args=parser.parse_args()
    require(os.geteuid()==0,'administrator_required')
    require(Path(__file__).resolve()==(args.release_root/'scripts/deployment/maintenance.py').resolve(),'unreviewed_tool_source')
    os.umask(0o077)
    platform=Platform();state=Path('/var/lib/lostparty-deploy');web_root=Path('/var/lib/lostparty-web')
    plan=load(args.release_root)
    manifest=validate_manifest(json.loads(args.manifest.read_text()))
    require(command(['git','-C',str(args.release_root),'rev-parse','HEAD']).strip()==manifest['source'], 'release_source_mismatch')
    command(['git','-C',str(args.release_root),'diff','--exit-code','HEAD','--'])
    require(not command(['git','-C',str(args.release_root),'ls-files','--others','--exclude-standard']).strip(), 'release_untracked_files')
    require(checksum((args.release_root/'compose.lightsail.yaml').read_bytes())==manifest['compose_sha256'],'release_compose_mismatch')
    contracts={}
    for name, expected in manifest['contract_sha256'].items():
        raw=(args.release_root/'openapi'/name).read_bytes()
        require(checksum(raw)==expected,'release_contract_hash_mismatch')
        contracts[name]=checksum(json.dumps(json.loads(raw),sort_keys=True,separators=(',',':')).encode())
    receipt=json.loads((args.release_root/plan['web_receipt']).read_text())
    with (state/'deploy.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.action=='preflight':
            preflight(platform,state,manifest,plan)
            print('{"preflight":"ready","applied":false}');return
        if args.action=='apply':
            require(args.backup_receipt is not None,'backup_receipt_required')
            require(args.probe_ip is not None,'test_connection_ip_required')
            require(ipaddress.ip_address(args.probe_ip).is_global,'public_probe_address_required')
            result=transition(platform,state,manifest,plan,receipt,args.handoff,web_root,
                              args.release_root/'docker/Caddyfile.lightsail',json.loads(args.backup_receipt.read_text()),contracts,args.probe_ip)
            print(json.dumps(result));return
        require(args.joint_acceptance is not None,'joint_acceptance_required')
        accepted=json.loads(args.joint_acceptance.read_text())
        current=json.loads((state/'current.json').read_text())
        require(current['source']==manifest['source'] and current['image']==manifest['image'],'acceptance_source_mismatch')
        require(accepted['backend_source']==manifest['source'] and accepted['web_sha256']==receipt['web']['bundle_sha256']
                and accepted['backend_checks'] is True and accepted['native_checks'] is True
                and accepted['joint_publication_authorized'] is True,'joint_acceptance_incomplete')
        platform.probes() if not (web_root/'maintenance').exists() else None
        require(platform.healthy(manifest['image']),'candidate_unhealthy')
        validate_active(web_root,receipt)
        (web_root/'maintenance').unlink(missing_ok=True)
        try:
            platform.probes()
        except Exception:
            (web_root/'maintenance').touch();raise
        current['public_open']=True
        current['web_status']='public'
        current['joint_acceptance_sha256']=checksum(args.joint_acceptance.read_bytes())
        current['native_acceptance']='operator-confirmed; see acceptance record'
        atomic(state/'current.json',current)
        journal=state/'maintenance-2.1.0/result.json'
        record=json.loads(journal.read_text())
        record.update(phase='public_open',public_open=True,joint_acceptance_sha256=current['joint_acceptance_sha256'])
        atomic(journal,record)
        print('{"public_open":true}')


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Maintenance transition failed; inspect private journal; never downgrade DB automatically') from None
