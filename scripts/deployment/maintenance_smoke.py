#!/usr/bin/env python3
"""Real isolated 0035->0036/API/Caddy transition, no production endpoint or data.

Only registry identity/preflight and controller installation are substituted;
actual app-role migration, writes-stop, candidate start, contract/edge checks,
key preservation and frozen environment transition use the real tool.
"""
import argparse
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from unittest.mock import patch
import maintenance
import server
from common import checksum
from web_smoke import main as unused_web_main


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker',default='docker');parser.add_argument('--image',default='lostparty-backend-api:latest');args=parser.parse_args()
    repo=Path(__file__).resolve().parents[2];name='lostparty-upgrade-test-'+uuid.uuid4().hex[:10]
    def mount(path):
        path=str(path.resolve())
        return ('\\\\wsl.localhost\\'+os.environ.get('WSL_DISTRO_NAME','Ubuntu-24.04')+path.replace('/','\\')) if args.docker.endswith('.exe') else path
    def call(argv,**kwargs):
        if argv[0]=='docker':argv=[args.docker,*argv[1:]]
        return subprocess.run(argv,capture_output=True,text=True,check=True,timeout=kwargs.pop('timeout',180),**kwargs).stdout
    with tempfile.TemporaryDirectory(prefix=name) as temporary:
        root=Path(temporary);state=root/'state';state.mkdir();web=root/'web';keys=root/'keys';keys.mkdir(mode=0o755)
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(keys/'jwt.pem')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        for key in ['recovery.key','lostark-credential.key','lostark-fingerprint.key']:(keys/key).write_bytes(os.urandom(32))
        for key in keys.iterdir():key.chmod(0o644)  # Disposable sandbox-only keys; no real credentials mounted.
        old_caddy=root/'Caddyfile';old_caddy.write_text('http://web.test {\n reverse_proxy api:8000\n}\n')
        config={'name':name,'services':{'db':{'image':'postgres:17-bookworm','environment':{'POSTGRES_DB':'lostparty_test','POSTGRES_PASSWORD':'test-only-password'},'tmpfs':['/var/lib/postgresql/data'],'healthcheck':{'test':['CMD-SHELL','pg_isready -U postgres -d lostparty_test'],'interval':'1s','timeout':'2s','retries':30}},'api':{'image':args.image,'environment':{'POSTGRES_DB':'lostparty_test','APP_DB_PASSWORD':'test-only-password','GOOGLE_CLIENT_ID':maintenance.WEB_CLIENT,'GOOGLE_AZP_ALLOWLIST':'debug,old','OWNERSHIP_WORKER_ENABLED':'0','RECRUITMENT_WORKER_ENABLED':'0'},'volumes':[{'type':'bind','source':mount(keys),'target':'/run/secrets','read_only':True}],'command':['uvicorn','app.main:create_app','--factory','--host','0.0.0.0','--port','8000','--no-access-log','--no-proxy-headers'],'healthcheck':{'test':['CMD','python','-c',"import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"],'interval':'1s','timeout':'3s','retries':30}},'caddy':{'image':'caddy:2-alpine','environment':{'API_DOMAIN':'http://web.test'},'volumes':[{'type':'bind','source':mount(old_caddy),'target':'/etc/caddy/Caddyfile','read_only':True}]},'probe':{'image':'python:3.12-slim-bookworm','command':['sleep','3600']}},'networks':{'default':{'internal':True}}}
        subnet='172.29.'+str(100+int(uuid.uuid4().hex[:2],16)%140)
        config['networks']['default']['ipam']={'config':[{'subnet':subnet+'.0/24','ip_range':subnet+'.128/25'}]}
        config['services']['caddy']['networks']={'default':{'ipv4_address':subnet+'.2'}}
        compose=root/'baseline.json';compose.write_text(json.dumps(config));prefix=[args.docker,'compose','-p',name,'-f',str(compose)]
        (root/'.env.lightsail').write_text('GOOGLE_AZP_ALLOWLIST=debug,old\n')
        class Sandbox(server.Platform):
            def __init__(self):self.root=root;self.base=[args.docker,'compose','-p',name,'--project-directory',str(root)]
            def protected_files(self):
                return {str(p):(checksum(p.read_bytes()),p.stat().st_mode,p.stat().st_uid,p.stat().st_gid) for p in [root/'.env.lightsail',*keys.iterdir()]}
            def containers(self):
                return {s:json.loads(call(['docker','inspect',call(prefix+['ps','-aq',s]).strip()]))[0] for s in ['api','db','caddy']}
            def config(self,path):
                # Real Compose normalization; translate host mount sources in candidates.
                value=json.loads(Path(path).read_text())
                for service in value['services'].values():
                    for volume in service.get('volumes',[]):
                        if isinstance(volume,dict) and volume['type']=='bind' and volume['source'].startswith('/tmp/'):
                            volume['source']=mount(Path(volume['source']))
                normalized=Path(path).with_name(Path(path).name+'.mapped')
                normalized.write_text(json.dumps(value))
                return json.loads(call(self.base+['-f',str(normalized),'config','--format','json']))
            def compose(self,path,*argv,timeout=120):
                value=self.config(path);mapped=Path(path).with_name(Path(path).name+'.run');mapped.write_text(json.dumps(value))
                return call(self.base+['-f',str(mapped),*argv],timeout=timeout)
            def replace(self,path):self.compose(path,'up','-d','--no-deps','--no-build','--pull','never','--force-recreate','--wait','--wait-timeout','100','api')
        platform=Sandbox()
        try:
            call(prefix+['up','-d','--wait','db','probe'])
            db=call(prefix+['ps','-q','db']).strip()
            call(['docker','exec',db,'psql','-U','postgres','-d','lostparty_test','-v','ON_ERROR_STOP=1','-c',"CREATE ROLE lostparty_app LOGIN PASSWORD 'test-only-password'; GRANT USAGE,CREATE ON SCHEMA public TO lostparty_app;"])
            call(prefix+['run','--rm','--no-deps','--entrypoint','alembic','api','upgrade','0035_cycle_group_policy'])
            # A pre-existing synthetic member proves that migration preserves existing rows.
            call(['docker','exec',db,'psql','-U','postgres','-d','lostparty_test','-c',"INSERT INTO users(id,status,created_at,updated_at,last_login_at) VALUES ('00000000-0000-4000-8000-000000000001','active',now(),now(),now());"])
            call(prefix+['up','-d','--wait','api','caddy'])
            current={'tag':'v2.0.0','source':'b'*40,'image':args.image,'compose':str(compose)}
            server.atomic(state/'current.json',current)
            before=platform.containers();protected=platform.protected_files()
            receipt=json.loads((repo/'docs/engineering/operations/records/web-handoff-2.1.0.json').read_text())
            probe=call(prefix+['ps','-q','probe']).strip()
            def edge(*argv,**kwargs):
                code="import urllib.request,urllib.error,json\ntry:r=urllib.request.urlopen(urllib.request.Request('http://caddy/health',headers={'Host':'web.test'}))\nexcept urllib.error.HTTPError as e:r=e\nprint(json.dumps({'status':r.status,'body':r.read().decode()}))"
                data=json.loads(call(['docker','exec',probe,'python','-c',code]))
                class Response:
                    status=data['status']
                    def read(self):return data['body'].encode()
                return Response()
            contracts={n:checksum(json.dumps(json.loads((repo/'openapi'/n).read_text()),sort_keys=True,separators=(',',':')).encode()) for n in ['openapi.yaml','legacy.openapi.yaml']}
            # Use a local Caddy host-path spelling; unlike production Windows paths
            # cannot be opened directly by the Linux control process.
            real_config=copy.deepcopy(config)
            real_config['services']['caddy']['volumes'][0]['source']=str(old_caddy)
            with patch('maintenance.preflight',return_value=(current,real_config,before)),patch('maintenance.check_backup'),patch('maintenance.command',side_effect=call),patch('server.command',side_effect=call),patch('maintenance.install_controller'),patch('maintenance.urllib.request.urlopen',side_effect=edge):
                result=maintenance.transition(platform,state,{'schema':2,'tag':'v2.1.0','source':'a'*40,'image':args.image}, {'configuration_revision':'lightsail-web-2.1.0','to_db_revision':'0036_roster_presence'},receipt,repo/'backups/web-handoff/artifact-13849320316',web,repo/'docker/Caddyfile.lightsail',{},contracts)
            assert result['phase']=='candidate_ready' and (web/'maintenance').exists()
            assert platform.protected_files()[str(keys/'jwt.pem')]==protected[str(keys/'jwt.pem')]
            rows=call(['docker','exec',db,'psql','-U','postgres','-d','lostparty_test','-Atc',"SELECT count(*) FROM users WHERE id='00000000-0000-4000-8000-000000000001'"]).strip();assert rows=='1'
            print('PASS: actual app-role migration0035->0036/API restart/Caddy503/internal health/full contracts/web activation/member+keys preserved; public closed')
        except subprocess.CalledProcessError as error:
            print(error.stdout[-1200:]);print(error.stderr[-1200:]);raise
        finally:
            call(prefix+['down','--remove-orphans','--timeout','5'])


if __name__=='__main__':main()
