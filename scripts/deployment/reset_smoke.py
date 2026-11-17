#!/usr/bin/env python3
"""Real reset CLI + PostgreSQL/API/Caddy in a UUID-only synthetic sandbox.

No production host/target arguments, keys, published ports, registry publication
or project Git commits. A disposable fixture Git repository supplies CLI source
identity; its commit and local image are explicitly NOT release candidates.
"""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import uuid
import zipfile
from datetime import datetime, timezone
from unittest.mock import patch

import backup
import server
from common import canonical, checksum
from rehearse_reset import OLD_IMAGE, PREPARE_KEYS, SEED
from web_release import stage, switch, pointer

ROOT=Path(__file__).resolve().parents[2]
RUN=subprocess.run
ALIAS='ghcr.io/heo0328/lostparty-backend@sha256:'+'f'*64


def validate_database(info, project):
    host=info['HostConfig'];mounts=info.get('Mounts',[]);labels=info['Config'].get('Labels') or {}
    ephemeral=('/var/lib/postgresql/data' in (host.get('Tmpfs') or {}) or
               any(m.get('Type')=='tmpfs' and m.get('Destination')=='/var/lib/postgresql/data' for m in mounts))
    if (not re.fullmatch(r'lostparty-reset-smoke-[0-9a-f]{12}',project)
            or labels.get('com.docker.compose.project')!=project
            or labels.get('com.docker.compose.service')!='db'
            or host.get('PortBindings') or host.get('Binds')
            or any(m.get('Type')!='tmpfs' for m in mounts) or not ephemeral):
        raise RuntimeError('unsafe_reset_smoke_database')


def synthetic_web(directory):
    directory.mkdir()
    asset=b'<html>synthetic previous web</html>'
    manifest=dict(schema_version=1,version='2.3.0+8',source_commit='a'*40,
                  backend_origin='https://lostparty.duckdns.org',source_dirty=False,candidate_only=False,
                  dirty_status=[],build_mode='release',service_worker='disabled',site_directory='site',
                  files=[dict(path='index.html',bytes=len(asset),sha256=checksum(asset))])
    raw=canonical(manifest);(directory/'release-manifest.json').write_bytes(raw)
    bundle=directory/'lostparty-v2.3.0-web.zip'
    with zipfile.ZipFile(bundle,'w') as archive:
        archive.writestr('release-manifest.json',raw);archive.writestr('site/index.html',asset)
    digest=checksum(bundle.read_bytes());(directory/(bundle.name+'.sha256')).write_text(digest+'  '+bundle.name+'\n')
    return {'web':dict(version='2.3.0+8',source='a'*40,origin='https://lostparty.duckdns.org',
                       bundle_sha256=digest,bundle_bytes=bundle.stat().st_size,site_files=1)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',default='docker')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    project='lostparty-reset-smoke-'+uuid.uuid4().hex[:12]
    volume=project+'-synthetic-keys';image_tag=project+':fixture'
    env={k:v for k,v in os.environ.items() if not k.startswith('COMPOSE_')}
    env['COMPOSE_DISABLE_ENV_FILE']='1'
    result=dict(schema=1,project=project,synthetic_only=True,production_access=False,
                real_production_cli_executed=False,repository_committed_or_pushed=False,
                registry_publication=False,fixed_release_image_created=False,
                image_dockerfile='Dockerfile',synthetic_cli_entrypoint_executed=True)
    phase='fixture';platform=None;temporary=tempfile.TemporaryDirectory(prefix=project+'-')
    work=Path(temporary.name);web=work/'web';state=work/'state';state.mkdir();source=work/'source';source.mkdir()
    known=set();dbid=None;new_image=None

    def run(argv, *, data=None, text=False, timeout=180, check=True, **kwargs):
        response=RUN(argv,input=data,capture_output=True,text=text,timeout=timeout,env=env,**kwargs)
        if check and response.returncode:
            # Synthetic diagnostics only, private to this UUID directory.
            (work/'last-command.stderr').write_bytes(response.stderr.encode() if text else response.stderr)
            raise RuntimeError('synthetic_command_failed')
        return response

    def output(argv, **kwargs):return run(argv,**kwargs).stdout.decode().strip()
    def inspect(cid):return json.loads(output([args.docker,'inspect',cid]))[0]
    def announce(value):
        nonlocal phase
        phase=value;print(json.dumps({'phase':phase}),flush=True)
    def mount(path):
        path=str(Path(path).resolve())
        return ('\\\\wsl.localhost\\'+os.environ.get('WSL_DISTRO_NAME','Ubuntu-24.04')+path.replace('/','\\')) if args.docker.endswith('.exe') else path

    def normalize(argv):
        argv=list(argv)
        if argv[0]=='docker':argv[0]=args.docker
        if argv[0]==args.docker:
            if len(argv)>2 and argv[1]=='exec':
                index=3 if argv[2]=='-i' else 2
                if argv[index] not in known:raise RuntimeError('foreign_container_refused')
                if argv[index]==dbid:validate_database(inspect(dbid),project)
            argv=[new_image if x==ALIAS else x for x in argv]
        elif argv[0]=='git':
            if argv[1:3]!=['-C',str(source)]:raise RuntimeError('foreign_git_repository_refused')
        else:raise RuntimeError('unreviewed_sandbox_command')
        return argv

    def command(argv, *, input=None, timeout=120):
        return run(normalize(argv),data=input,text=True,timeout=timeout).stdout
    def binary(argv, data=None):return run(normalize(argv),data=data).stdout

    class Sandbox(server.Platform):
        def __init__(self):
            self.root=work
            self.base=[args.docker,'compose','--project-name',project,'--project-directory',str(work)]
            self.last_compose=None
            self.fail_migration=False
            self.fail_public_probe=False

        def mapped(self, config):
            mapped=copy.deepcopy(config)
            mapped['name']=project
            for service in mapped['services'].values():
                if service.get('image')==ALIAS:service['image']=new_image
                for volume_entry in service.get('volumes',[]):
                    if volume_entry.get('type')=='bind':volume_entry['source']=mount(volume_entry['source'])
            return mapped

        def compose(self, file, *arguments, timeout=180):
            config=json.loads(Path(file).read_text());mapped=work/(Path(file).stem+'.mapped.json')
            mapped.write_text(json.dumps(self.mapped(config)))
            self.last_compose=mapped
            if self.fail_migration and arguments[:1]==('run',) and 'alembic' in arguments:
                self.fail_migration=False;raise RuntimeError('injected_migration_interruption')
            return run([*self.base,'-f',str(mapped),*arguments],text=True,timeout=timeout).stdout

        def config(self, file):
            return json.loads(Path(file).read_text())

        def containers(self):
            result={}
            for service in ('api','db','caddy'):
                cid=output([*self.base,'-f',str(self.last_compose),'ps','--all','--quiet',service])
                info=inspect(cid);labels=info['Config'].get('Labels') or {}
                if labels.get('com.docker.compose.project')!=project or labels.get('com.docker.compose.service')!=service:
                    raise RuntimeError('foreign_sandbox_service')
                if service=='db':validate_database(info,project)
                known.add(cid)
                # Only identity labels are adapted; real CID/state/mount/env and
                # PostgreSQL bytes remain the ones checked by the reset tool.
                info['Config']['Labels']={**labels,'com.docker.compose.project':'lostparty-lightsail'}
                result[service]=info
            return result

        def image_info(self, image):
            return json.loads(output([args.docker,'image','inspect',new_image if image==ALIAS else image]))[0]

        def pull(self, image):
            if image!=ALIAS:raise RuntimeError('unexpected_image_pull')

        def probes(self):
            if self.fail_public_probe:
                self.fail_public_probe=False
                raise RuntimeError('injected_public_probe_failure')
            for path,expected in [('/health',200),('/v1/raid-catalog',200),('/v1/me',401)]:
                response=self.edge(path)
                if response['status']!=expected:raise RuntimeError('sandbox_public_probe_failed')

        def edge(self, path):
            probe=output([*self.base,'-f',str(self.last_compose),'ps','--quiet','probe'])
            info=inspect(probe)
            if info['Config']['Labels'].get('com.docker.compose.project')!=project:raise RuntimeError('foreign_probe')
            known.add(probe)
            code="""import json,urllib.request,urllib.error
request=urllib.request.Request('http://caddy'+%r,headers={'Host':'reset.test'})
try:response=urllib.request.urlopen(request,timeout=5)
except urllib.error.HTTPError as error:response=error
print(json.dumps({'status':response.status,'body':response.read().decode()}))
""" % path
            return json.loads(command(['docker','exec',probe,'python','-c',code]))

    try:
        # Copy only non-secret release inputs. No primary-workspace Git writes.
        tools=source/'scripts/deployment';tools.mkdir(parents=True)
        for path in (ROOT/'scripts/deployment').glob('*.py'):shutil.copyfile(path,tools/path.name)
        (source/'openapi').mkdir()
        for name in ('openapi.yaml','legacy.openapi.yaml'):shutil.copyfile(ROOT/'openapi'/name,source/'openapi'/name)
        for name in ('VERSION','release-deployment.json','compose.lightsail.yaml'):shutil.copyfile(ROOT/name,source/name)
        receipt_path=source/'docs/engineering/operations/records/web-handoff-2.4.0.json'
        receipt_path.parent.mkdir(parents=True);shutil.copyfile(ROOT/'docs/engineering/operations/records/web-handoff-2.4.0.json',receipt_path)
        receipt=json.loads(receipt_path.read_text());handoff=ROOT/receipt['web']['local_directory']
        (source/'.gitignore').write_text('__pycache__/\n*.pyc\n')
        run(['git','init','--quiet',str(source)])
        run(['git','-C',str(source),'add','.'])
        run(['git','-C',str(source),'-c','user.name=Synthetic Fixture','-c','user.email=fixture@example.invalid',
             '-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','--quiet','-m','Disposable reset CLI fixture'])
        fixture_sha=output(['git','-C',str(source),'rev-parse','HEAD'])
        result['synthetic_fixture_git_commit']=fixture_sha
        announce('build_fixture_image')
        run([args.docker,'build','-f','Dockerfile','--label','org.opencontainers.image.revision='+fixture_sha,
             '--label','org.opencontainers.image.version=v2.4.0','-t',image_tag,'.'],timeout=360,cwd=ROOT)
        new_image=json.loads(output([args.docker,'image','inspect',image_tag]))[0]['Id']
        result['local_fixture_image']=new_image
        for image in (OLD_IMAGE,'postgres:17-bookworm','caddy:2-alpine'):
            if run([args.docker,'image','inspect',image],check=False).returncode:
                run([args.docker,'pull',image],timeout=300)
        db_image=json.loads(output([args.docker,'image','inspect','postgres:17-bookworm']))[0]['Id']
        caddy_image=json.loads(output([args.docker,'image','inspect','caddy:2-alpine']))[0]['Id']
        run([args.docker,'volume','create','--label','lostparty.synthetic-reset-smoke='+project,volume])
        run([args.docker,'run','--rm','--network','none','--user','0','-v',volume+':/tmp/auth-test-keys',
             '--entrypoint','python',new_image,'-c',PREPARE_KEYS])
        # Private host recovery copies are synthetic and match the mounted volume.
        raw=run([args.docker,'run','--rm','--network','none','-v',volume+':/run/secrets:ro',
                 '--entrypoint','tar',new_image,'-cf','-','-C','/run/secrets','.']).stdout
        secrets=work/'.secrets/lightsail';secrets.mkdir(mode=0o700,parents=True)
        key_names={'jwt.pem','recovery.key','lostark-credential.key','lostark-fingerprint.key','lostark-api-token'}
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for item in archive.getmembers():
                if item.isdir():continue
                name=item.name.removeprefix('./')
                if name not in key_names or not item.isfile():raise RuntimeError('unsafe_synthetic_key_archive')
                path=secrets/name;path.write_bytes(archive.extractfile(item).read());path.chmod(0o600)
        if {p.name for p in secrets.iterdir()}!=key_names:raise RuntimeError('synthetic_keys_missing')
        (work/'.env.lightsail').write_text('SYNTHETIC_RESET_SMOKE=1\n')
        old_receipt=synthetic_web(work/'old-handoff');stage(work/'old-handoff',old_receipt,web);switch(web,old_receipt,compatible=True)
        config={'name':project,'services':{
            'db':{'image':db_image,'environment':{'POSTGRES_DB':'lostparty','POSTGRES_PASSWORD':'test-only-password'},
                  'tmpfs':['/var/lib/postgresql/data'],'healthcheck':{'test':['CMD-SHELL','pg_isready -U postgres -d lostparty'],'interval':'1s','timeout':'3s','retries':60}},
            'api':{'image':OLD_IMAGE,'entrypoint':['uvicorn'],'command':['app.main:create_app','--factory','--host','0.0.0.0'],
                   'environment':{'POSTGRES_DB':'lostparty','APP_DB_PASSWORD':'test-only-password','AUTH_SECRET_DIR':'/run/secrets',
                                  'OWNERSHIP_WORKER_ENABLED':'0','RECRUITMENT_WORKER_ENABLED':'0'},
                   'volumes':[{'type':'volume','source':'synthetic_keys','target':'/run/secrets','read_only':True}],
                   'read_only':True,'tmpfs':['/tmp:size=32m'],
                   'healthcheck':{'test':['CMD','python','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)"],'interval':'1s','timeout':'4s','retries':60}},
            'caddy':{'image':caddy_image,'environment':{'API_DOMAIN':'http://reset.test'},'volumes':[
                {'type':'bind','source':str(ROOT/'docker/Caddyfile.lightsail'),'target':'/etc/caddy/Caddyfile','read_only':True},
                {'type':'bind','source':str(web),'target':'/srv/web','read_only':True}]},
            'probe':{'image':new_image,'entrypoint':['sleep'],'command':['1800']}},
            'volumes':{'synthetic_keys':{'name':volume,'external':True}},'networks':{'default':{'internal':True}}}
        baseline=work/'compose.lightsail.yaml';baseline.write_text(json.dumps(config));platform=Sandbox()
        platform.compose(baseline,'up','-d','--wait','--wait-timeout','90','db','caddy','probe')
        dbid=output([*platform.base,'-f',str(platform.last_compose),'ps','--quiet','db']);known.add(dbid)
        validate_database(inspect(dbid),project)
        network=json.loads(output([args.docker,'network','inspect',project+'_default']))[0]
        if not network['Internal']:raise RuntimeError('sandbox_network_not_internal')
        command(['docker','exec','-i',dbid,'psql','-X','-qAt','-U','postgres','-d','lostparty','-v','ON_ERROR_STOP=1'],
                input="CREATE ROLE lostparty_app LOGIN PASSWORD 'test-only-password' NOSUPERUSER NOCREATEDB NOCREATEROLE; REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE,CREATE ON SCHEMA public TO lostparty_app;")
        platform.compose(baseline,'run','--rm','--no-deps','--entrypoint','alembic','api','upgrade','0036_roster_presence')
        command(['docker','exec','-i',dbid,'psql','-X','-qAt','-U','postgres','-d','lostparty','-v','ON_ERROR_STOP=1'],input=SEED)
        platform.compose(baseline,'up','-d','--wait','--wait-timeout','90','api')
        platform.containers();platform.probes()
        previous=dict(tag='v2.3.0',source='05daa424f06aa34edd76867bac1c78f9d558b51a',image=OLD_IMAGE,
                      db_revision='0036_roster_presence',configuration_revision='lightsail-web-2.1.0',compose=str(baseline),public_open=True)
        server.atomic(state/'current.json',previous)
        manifest=dict(schema=2,repository='heo0328/lostparty-backend',tag='v2.4.0',source=fixture_sha,image=ALIAS,
                      db_revision='0038_analysis_candidates',contract_sha256={n:checksum((source/'openapi'/n).read_bytes()) for n in ('openapi.yaml','legacy.openapi.yaml')},
                      compose_sha256=checksum((source/'compose.lightsail.yaml').read_bytes()),built_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
        manifest_path=work/'release.json';manifest_path.write_text(json.dumps(manifest))
        spec=importlib.util.spec_from_file_location('synthetic_reset_release',tools/'reset_release.py')
        reset=importlib.util.module_from_spec(spec);spec.loader.exec_module(reset)
        reset.STATE=state;reset.WEB=web
        original_run=RUN
        def adapted_run(argv, **kwargs):
            if argv[0]=='docker':argv=normalize(argv)
            return original_run(argv,**kwargs)
        def urlopen(url,timeout=10):
            if url!='https://lostparty.duckdns.org/health':raise RuntimeError('external_network_refused')
            response=platform.edge('/health');body=io.BytesIO(response['body'].encode())
            if response['status']>=400:raise urllib.error.HTTPError(url,response['status'],'synthetic edge',{},body)
            body.status=response['status'];return body
        actions=[]
        def cli(action, *extra, fail=False, uid=0, expected=None):
            argv=['reset_release.py',action,'--release-root',str(source),'--manifest',str(manifest_path),*extra]
            try:
                with patch.object(sys,'argv',argv),patch.object(reset,'Platform',return_value=platform),patch.object(reset.os,'geteuid',return_value=uid),patch.object(reset,'command',side_effect=command),patch.object(reset,'binary',side_effect=binary),patch('urllib.request.urlopen',side_effect=urlopen),patch.object(server,'command',side_effect=command):
                    reset.main()
            except Exception as error:
                if not fail:raise
                if expected is None or str(error)!=expected:raise RuntimeError('unexpected_cli_rejection') from None
                actions.append({'action':action,'rejected_as_expected':True,'reason':expected});return
            if fail:raise RuntimeError('expected_cli_rejection_missing')
            actions.append({'action':action,'completed':True})

        announce('baseline_backup_and_cli_guards')
        with patch.object(backup.subprocess,'run',side_effect=adapted_run),patch.object(server,'command',side_effect=command):
            record=backup.capture(platform,state,work/'backups/before-reset',installed=tools,system_files=[],web_root=web)
        copied=work/'operator-copies';copied.mkdir();shutil.copyfile(record['archive'],copied/'baseline.tar')
        pc_digest=checksum((copied/'baseline.tar').read_bytes());backup.confirm(work/'backups/before-reset/receipt.json',pc_digest)
        protected_before=platform.protected_files()
        cli('preflight',fail=True,uid=10001,expected='administrator_required')
        (source/'unexpected-dirty-file').touch();cli('preflight',fail=True,expected='clean_release_checkout_required');(source/'unexpected-dirty-file').unlink()
        cli('preflight')
        announce('failed_apply_and_restore')
        cli('prepare','--handoff',str(handoff),'--backup-receipt',str(work/'backups/before-reset/receipt.json'))
        journal=state/'reset-2.4.0/result.json'
        cli('apply','--acknowledge',reset.ACK,fail=True,expected='stopped_pc_confirmation_required')
        shutil.copyfile(state/'reset-2.4.0/stopped.database.dump',copied/'stopped.dump')
        pc_digest=checksum((copied/'stopped.dump').read_bytes())
        cli('confirm-stopped-backup','--pc-dump-sha256',pc_digest)
        platform.fail_migration=True;cli('apply','--acknowledge',reset.ACK,fail=True,expected='injected_migration_interruption')
        if platform.containers()['api']['State']['Running'] or platform.edge('/health')['status']!=503:raise RuntimeError('failed_apply_exposed_api')
        if json.loads(journal.read_text())['phase']!='apply_failed_restore_required':raise RuntimeError('failed_apply_journal')
        cli('rollback','--acknowledge',reset.ACK)
        accepted=work/'accepted.json';accepted.write_text(json.dumps(dict(backend_source=previous['source'],web_sha256=old_receipt['web']['bundle_sha256'],backend_checks=True,native_checks=True,joint_publication_authorized=True)))
        cli('open-restored','--joint-acceptance',str(accepted));platform.probes()
        if platform.edge('/')['body'].encode()!=(web/'current/index.html').read_bytes():raise RuntimeError('restored_public_web_mismatch')
        result['failure_kept_public_closed']=True;result['rollback_restored_0036_and_old_web']=True
        result['restored_release_reopened_explicitly']=True
        (state/'reset-2.4.0').rename(state/'previous-failed-reset')

        announce('ready_candidate_rollback')
        cli('prepare','--handoff',str(handoff),'--backup-receipt',str(work/'backups/before-reset/receipt.json'))
        shutil.copyfile(state/'reset-2.4.0/stopped.database.dump',copied/'stopped-2.dump')
        cli('confirm-stopped-backup','--pc-dump-sha256',checksum((copied/'stopped-2.dump').read_bytes()))
        cli('apply','--acknowledge',reset.ACK)
        if platform.edge('/health')['status']!=503:raise RuntimeError('candidate_opened_without_joint_acceptance')
        cli('rollback','--acknowledge',reset.ACK)
        cli('open-restored','--joint-acceptance',str(accepted));platform.probes()
        if platform.edge('/')['body'].encode()!=(web/'current/index.html').read_bytes():raise RuntimeError('restored_public_web_mismatch')
        result['ready_0038_candidate_rollback_restored_old_web']=True
        (state/'reset-2.4.0').rename(state/'previous-ready-candidate-reset')

        announce('successful_apply_and_joint_open')
        cli('prepare','--handoff',str(handoff),'--backup-receipt',str(work/'backups/before-reset/receipt.json'))
        shutil.copyfile(state/'reset-2.4.0/stopped.database.dump',copied/'stopped-3.dump')
        cli('confirm-stopped-backup','--pc-dump-sha256',checksum((copied/'stopped-3.dump').read_bytes()))
        cli('apply','--acknowledge',reset.ACK)
        if platform.edge('/health')['status']!=503:raise RuntimeError('candidate_opened_without_joint_acceptance')
        cli('open','--joint-acceptance',str(accepted),fail=True,expected='joint_acceptance_required')
        accepted.write_text(json.dumps(dict(backend_source=fixture_sha,web_sha256=receipt['web']['bundle_sha256'],backend_checks=True,native_checks=True,joint_publication_authorized=True)))
        platform.fail_public_probe=True;cli('open','--joint-acceptance',str(accepted),fail=True,expected='injected_public_probe_failure')
        if platform.edge('/health')['status']!=503:raise RuntimeError('failed_open_did_not_restore_maintenance')
        result['failed_public_probe_reclosed_edge']=True
        cli('open','--joint-acceptance',str(accepted));platform.probes()
        if platform.edge('/')['body'].encode()!=(web/'current/index.html').read_bytes():raise RuntimeError('public_native_web_mismatch')
        result['successful_apply_0038_and_native_web']=True;result['joint_open_required']=True
        result['native_web_assets_verified']=receipt['web']['site_files']
        if protected_before!=platform.protected_files():raise RuntimeError('synthetic_protected_files_changed')
        final_keys=binary(['docker','exec',platform.containers()['api']['Id'],'python','-c',
            "import hashlib,json;from pathlib import Path;print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/run/secrets').iterdir() if p.is_file()}))"])
        expected_keys={p.name:checksum(p.read_bytes()) for p in secrets.iterdir()}
        if json.loads(final_keys)!=expected_keys:raise RuntimeError('mounted_synthetic_key_bytes_changed')
        result['synthetic_keys_and_environment_preserved']=True
        result['mounted_synthetic_keys_compared']=True
        result['cli_actions']=actions;result['status']='passed'
    except Exception as error:
        result.update(status='failed',failed_phase=phase,error_type=type(error).__name__,
                      error=str(error) if isinstance(error,(ValueError,RuntimeError)) else 'private_synthetic_failure')
    finally:
        cleanup=True
        if platform is not None and platform.last_compose is not None:
            cleanup=run([*platform.base,'-f',str(platform.last_compose),'down','--remove-orphans','--timeout','10'],check=False).returncode==0
        run([args.docker,'volume','rm',volume],check=False)
        cleanup=cleanup and run([args.docker,'volume','inspect',volume],check=False).returncode!=0
        run([args.docker,'image','rm',image_tag],check=False)
        result['cleanup_ok']=cleanup
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
        # Failure diagnostics are copied only into the local private output folder.
        if result.get('status')!='passed' and (work/'last-command.stderr').exists():
            diagnostic=args.output.with_suffix('.stderr.private');shutil.copyfile(work/'last-command.stderr',diagnostic);diagnostic.chmod(0o600)
        temporary.cleanup()
        print(json.dumps(result),flush=True)
    return 0 if result.get('status')=='passed' and result['cleanup_ok'] else 1


if __name__=='__main__':raise SystemExit(main())
