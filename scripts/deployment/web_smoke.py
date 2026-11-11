#!/usr/bin/env python3
"""Real Caddy HTTP/maintenance tests in a UUID sandbox; no host ports or real DB."""
import argparse
import json
import zipfile
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from web_release import stage, switch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--docker',default='docker');parser.add_argument('--synthetic',action='store_true');args=parser.parse_args()
    repo=Path(__file__).resolve().parents[2]
    name='lostparty-web-test-'+uuid.uuid4().hex[:10]
    def call(argv):
        return subprocess.run(argv,capture_output=True,text=True,check=True,timeout=120).stdout
    def mount(path):
        path=str(path.resolve())
        return ('\\\\wsl.localhost\\'+os.environ.get('WSL_DISTRO_NAME','Ubuntu-24.04')+path.replace('/','\\')) if args.docker.endswith('.exe') else path
    with tempfile.TemporaryDirectory(prefix=name) as directory:
        root=Path(directory);web=root/'web'
        receipt=json.loads((repo/'docs/engineering/operations/records/web-handoff-2.1.0.json').read_text())
        handoff=repo/'backups/web-handoff/artifact-13849320316'
        if args.synthetic:
            handoff=root/'synthetic';handoff.mkdir()
            assets={'index.html':b'<html>synthetic smoke</html>','sqlite3.wasm':b'\x00asm\x01\x00\x00\x00'}
            digest=lambda b:hashlib.sha256(b).hexdigest()
            manifest=dict(schema_version=1,version='2.1.0+6',source_commit='a'*40,source_dirty=False,candidate_only=False,dirty_status=[],backend_origin='https://lostparty.duckdns.org',build_mode='release',service_worker='disabled',site_directory='site',files=[dict(path=n,bytes=len(b),sha256=digest(b)) for n,b in assets.items()])
            raw=json.dumps(manifest).encode();(handoff/'release-manifest.json').write_bytes(raw)
            bundle=handoff/'lostparty-v2.1.0-web.zip'
            with zipfile.ZipFile(bundle,'w') as z:
                z.writestr('release-manifest.json',raw)
                for n,b in assets.items():z.writestr('site/'+n,b)
            sha=digest(bundle.read_bytes())
            (handoff/'lostparty-v2.1.0-web.zip.sha256').write_text(sha+'  '+bundle.name+'\n')
            receipt={'web':dict(source='a'*40,version='2.1.0+6',origin='https://lostparty.duckdns.org',bundle_sha256=sha,bundle_bytes=bundle.stat().st_size,site_files=2)}
            print('Synthetic CI fixture; no Native browser claim')
        # Real Native bundle, never rebuilt; local sandbox only.
        stage(handoff,receipt,web);switch(web,receipt,compatible=True)
        code="from http.server import BaseHTTPRequestHandler,HTTPServer\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  status=200 if self.path in ['/health','/v1/probe','/v2/probe'] else 401 if self.path=='/v1/me' else 404\n  body=b'{\"status\":\"ok\",\"database\":\"ok\"}' if self.path=='/health' else b'api'\n  self.send_response(status);self.end_headers();self.wfile.write(body)\n def log_message(self,*args):pass\nHTTPServer(('0.0.0.0',8000),H).serve_forever()"
        config={'name':name,'services':{'api':{'image':'python:3.12-slim-bookworm','entrypoint':['python','-c',code]},'caddy':{'image':'caddy:2-alpine','environment':{'API_DOMAIN':'http://web.test'},'volumes':[{'type':'bind','source':mount(repo/'docker/Caddyfile.lightsail'),'target':'/etc/caddy/Caddyfile','read_only':True},{'type':'bind','source':mount(web),'target':'/srv/web','read_only':True}]}},'networks':{'default':{'internal':True}}}
        compose=root/'compose.json';compose.write_text(json.dumps(config))
        prefix=[args.docker,'compose','-p',name,'-f',str(compose)]
        try:
            call([args.docker,'pull','caddy:2-alpine'])
            call([args.docker,'pull','python:3.12-slim-bookworm'])
            call(prefix+['run','--rm','--no-deps','caddy','caddy','validate','--config','/etc/caddy/Caddyfile'])
            call(prefix+['up','-d'])
            api=call(prefix+['ps','-q','api']).strip();caddy=call(prefix+['ps','-q','caddy']).strip()
            probe="""import urllib.request,urllib.error,json
for path,expected,mime in [('/',200,None),('/screen/nested',200,None),('/missing.js',404,None),('/assets/missing',404,None),('/sqlite3.wasm',200,'application/wasm'),('/v1/probe',200,None),('/v2/probe',200,None),('/health',200,None),('/v1/me',401,None),('/v2/missing',404,None),('/release-manifest.json',404,None)]:
 req=urllib.request.Request('http://caddy'+path,headers={'Host':'web.test'})
 try:r=urllib.request.urlopen(req,timeout=5)
 except urllib.error.HTTPError as e:r=e
 assert r.status==expected,(path,r.status)
 if mime:assert r.headers.get_content_type()==mime,(path,r.headers)
 if path in ['/','/screen/nested','/sqlite3.wasm']:assert r.headers['Cache-Control']=='no-cache'
 print(path,expected,'PASS')
"""
            for attempt in range(20):
                try:result=call([args.docker,'exec',api,'python','-c',probe]);break
                except subprocess.CalledProcessError:
                    if attempt==19:raise
                    time.sleep(.5)
            print(result,end='')
            (web/'maintenance').touch()
            maintenance="import urllib.request,urllib.error\ntry:urllib.request.urlopen(urllib.request.Request('http://caddy/health',headers={'Host':'web.test','X-Forwarded-For':'127.0.0.1'}))\nexcept urllib.error.HTTPError as e:assert e.code==503 and e.read().strip()==b'Maintenance';print('public maintenance503 PASS')\nelse:raise AssertionError('maintenance not applied')"
            print(call([args.docker,'exec',api,'python','-c',maintenance]),end='')
            internal=call([args.docker,'exec',caddy,'wget','-q','-O','-','http://127.0.0.1:8081/health'])
            assert json.loads(internal)=={'status':'ok','database':'ok'}
            print('loopback candidate health PASS')
            # Allow exactly the synthetic test client's real peer IP, then verify
            # candidate health remains available while the marker still exists.
            peer=json.loads(call([args.docker,'inspect',api]))[0]['NetworkSettings']['Networks']
            address=next(iter(peer.values()))['IPAddress']
            config['services']['caddy']['environment']['MAINTENANCE_PROBE_IPS']=address
            compose.write_text(json.dumps(config))
            call(prefix+['up','-d','--no-deps','--force-recreate','caddy'])
            allowed="import urllib.request; r=urllib.request.urlopen(urllib.request.Request('http://caddy/health',headers={'Host':'web.test'})); assert r.status==200; print('exact test peer maintenance access PASS')"
            for attempt in range(20):
                try:print(call([args.docker,'exec',api,'python','-c',allowed]),end='');break
                except subprocess.CalledProcessError:
                    if attempt==19:raise
                    time.sleep(.5)
            (web/'maintenance').unlink()
            switch(web,rollback=True)
            fallback="import urllib.request,urllib.error\nfor p,status in [('/',404),('/health',200)]:\n try:r=urllib.request.urlopen(urllib.request.Request('http://caddy'+p,headers={'Host':'web.test'}))\n except urllib.error.HTTPError as e:r=e\n assert r.status==status,(p,r.status)\nprint('first-web rollback/api preserved PASS')"
            print(call([args.docker,'exec',api,'python','-c',fallback]),end='')
        except subprocess.CalledProcessError as error:
            print(error.stdout[-1500:]);print(error.stderr[-1500:]);raise
        finally:
            call(prefix+['down','--remove-orphans','--timeout','5'])
    print('PASS: UUID Caddy sandbox; no production/local-dev services changed')


if __name__=='__main__':main()
