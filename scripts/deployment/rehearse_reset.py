#!/usr/bin/env python3
"""Synthetic-only DB reset/restore rehearsal. Never accepts a production DB/host."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import uuid
from unittest.mock import patch

import reset_release

ROOT = Path(__file__).resolve().parents[2]
OLD_IMAGE = 'ghcr.io/heo0328/lostparty-backend@sha256:71e30188a79d903efbe52ba5a590add4d400c47ee7d5d35f3a26646cfe834d9d'
DB = 'lostparty_test'
APP_URL = 'postgresql+psycopg://lostparty_app:test-only-password@test-db/lostparty_test'

SNAPSHOT = """
import json
from sqlalchemy import text,inspect
from app.core.database import engine
with engine().connect().execution_options(isolation_level='REPEATABLE READ') as c:
 c.exec_driver_sql('SET TRANSACTION READ ONLY')
 result={}
 for name in sorted(inspect(c).get_table_names(schema='public')):
  q=engine().dialect.identifier_preparer.quote(name)
  result[name]=list(c.exec_driver_sql("SELECT count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM (SELECT md5(to_jsonb(t)::text) h FROM public."+q+" t) s").one())
 print(json.dumps(result))
"""
KEYS = """
import json,hashlib
from pathlib import Path
print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/tmp/auth-test-keys').iterdir() if p.is_file()}))
"""
PREPARE_KEYS = """
import os
import re
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
p=Path('/tmp/auth-test-keys');p.mkdir(exist_ok=True);os.chmod(p,0o700);os.chown(p,10001,10001)
private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
values={'jwt.pem':private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()),
'recovery.key':os.urandom(32),'lostark-credential.key':os.urandom(32),'lostark-fingerprint.key':os.urandom(32),
'lostark-api-token':b'synthetic.rehearsal.token'}
for name,value in values.items():
 f=p/name
 with f.open('xb') as stream:stream.write(value)
 os.chmod(f,0o600);os.chown(f,10001,10001)
"""
SEED = """
INSERT INTO users(id,status,created_at,updated_at,last_login_at)
 VALUES('11111111-1111-4111-8111-111111111111','active',now(),now(),now());
INSERT INTO auth_sessions(id,user_id,remember_me,created_at,absolute_expires_at,idle_expires_at)
 VALUES('22222222-2222-4222-8222-222222222222','11111111-1111-4111-8111-111111111111',true,now(),now()+interval '1 day',now()+interval '1 day');
INSERT INTO lostark_credentials(user_id,version) VALUES('11111111-1111-4111-8111-111111111111',1);
INSERT INTO game_accounts(id,owner_id,ownership_revision,roster_revision,verified_at)
 VALUES('33333333-3333-4333-8333-333333333333','11111111-1111-4111-8111-111111111111',1,1,now());
"""


def validate_test_database(info, project):
    config=info['HostConfig']
    mounts=info.get('Mounts',[])
    ephemeral=('/var/lib/postgresql/data' in (config.get('Tmpfs') or {}) or
               any(m.get('Type')=='tmpfs' and m.get('Destination')=='/var/lib/postgresql/data' for m in mounts))
    labels=info['Config'].get('Labels') or {}
    if (not re.fullmatch(r'lostparty-rehearsal-[0-9a-f]{12}',project)
            or labels.get('com.docker.compose.project')!=project
            or labels.get('com.docker.compose.service')!='test-db'
            or config.get('PortBindings') or config.get('Binds')
            or any(m.get('Type')!='tmpfs' for m in mounts) or not ephemeral):
        raise RuntimeError('unsafe_rehearsal_db')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = 'lostparty-rehearsal-' + uuid.uuid4().hex[:12]
    volume = project + '-synthetic-keys'
    env = {k:v for k,v in os.environ.items() if not k.startswith('COMPOSE_')}
    env['COMPOSE_DISABLE_ENV_FILE'] = '1'
    temporary=tempfile.TemporaryDirectory(prefix=project+'-')
    override=Path(temporary.name)/'compose-alias.json'
    override.write_text(json.dumps({'services':{'test-db':{'networks':{'isolated':{'aliases':['db']}}}}}))
    base = [args.docker,'compose','--project-name',project,'--file',str(ROOT/'compose.test.yaml'),'--file',str(override)]
    names = [project+'-old-api',project+'-new-api']
    stage = 'build'
    result = dict(schema=1,project=project,synthetic_only=True,old_image=OLD_IMAGE,
                  production_access=False,production_backup_restored=False)
    cleanup_ok = True

    def run(argv, data=None, check=True, timeout=180):
        response = subprocess.run(argv,input=data,capture_output=True,env=env,cwd=ROOT,timeout=timeout)
        if check and response.returncode:
            raise RuntimeError('rehearsal_command_failed')
        return response

    def text(argv, **kw):
        return run(argv,**kw).stdout.decode().strip()

    def runner(*command, root=False):
        return [*base,'run','--rm','-T','--no-deps','--user','0' if root else '10001',
                '-v',volume+':/tmp/auth-test-keys','-e','DATABASE_URL='+APP_URL,'tests',*command]

    def announce(value):
        nonlocal stage
        stage=value
        print(json.dumps(dict(stage=stage)),flush=True)

    def health(name):
        for _ in range(40):
            r=run([args.docker,'exec',name,'python','-c',
                   "import urllib.request;assert urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200"],
                  check=False,timeout=8)
            if r.returncode==0:return
            time.sleep(1)
        raise RuntimeError('rehearsal_api_health_failed')

    def api(image,name):
        run([args.docker,'run','-d','--name',name,'--network',project+'_isolated',
             '--read-only','--tmpfs','/tmp:rw,size=32m',
             '-v',volume+':/tmp/auth-test-keys:ro',
             '-e','DATABASE_URL='+APP_URL,'-e','AUTH_SECRET_DIR=/tmp/auth-test-keys',
             '-e','APP_DB_PASSWORD=test-only-password','-e','POSTGRES_DB='+DB,
             '-e','OWNERSHIP_WORKER_ENABLED=0','-e','RECRUITMENT_WORKER_ENABLED=0',
             '--entrypoint','uvicorn',image,'app.main:create_app','--factory','--host','0.0.0.0'])
        health(name)

    def sql(query):
        return text([args.docker,'exec','-i',dbid,'psql','-X','-qAt','-v','ON_ERROR_STOP=1',
                     '-U','postgres','-d',DB],data=query.encode())

    def reset_database():
        # Recheck the ephemeral identity BEFORE every destructive test-only command.
        info=json.loads(text([args.docker,'inspect',dbid]))[0]
        validate_test_database(info,project)
        # Exercise exactly the administrator reset SQL, mapped only after the
        # UUID/tmpfs guard above. The production tool itself has no target flag.
        allowed={
            'DROP DATABASE IF EXISTS lostparty;':'DROP DATABASE IF EXISTS lostparty_test;',
            'CREATE DATABASE lostparty OWNER postgres;':'CREATE DATABASE lostparty_test OWNER postgres;',
            'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE, CREATE ON SCHEMA public TO lostparty_app;':
                'REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE, CREATE ON SCHEMA public TO lostparty_app;'}
        def isolated_command(argv, *, input):
            assert argv[:4]==['docker','exec','-i',dbid] and input in allowed
            mapped=[args.docker,*argv[1:]]
            database_index=mapped.index('-d')+1
            assert mapped[database_index] in ('lostparty','postgres')
            if mapped[database_index]=='lostparty':mapped[database_index]=DB
            return run(mapped,data=allowed[input].encode()).stdout.decode()
        with patch.object(reset_release,'command',side_effect=isolated_command):
            reset_release.recreate(dbid)
        result['shared_reset_sql_exercised']=True

    def administrator_snapshot():
        info=json.loads(text([args.docker,'inspect',dbid]))[0]
        validate_test_database(info,project)
        def isolated_command(argv, *, input):
            assert argv[:4]==['docker','exec','-i',dbid] and input==reset_release.SNAPSHOT_SQL
            assert argv[argv.index('-d')+1]==DB
            return run([args.docker,*argv[1:]],data=input.encode()).stdout.decode()
        with patch.object(reset_release,'DB',DB),patch.object(reset_release,'command',side_effect=isolated_command):
            return reset_release.private_snapshot(dbid)

    try:
        run([*base,'build','tests'],timeout=300)
        new_image=text([args.docker,'image','inspect',project+'-tests','--format','{{.Id}}'])
        # No floating image reference is used after this point.
        assert new_image
        result['candidate_image']=new_image
        run([*base,'up','-d','--wait','--wait-timeout','90','test-db'])
        dbid=text([*base,'ps','-q','test-db'])
        network=json.loads(text([args.docker,'network','inspect',project+'_isolated']))[0]
        if not network['Internal']:raise RuntimeError('network_not_isolated')
        sql("CREATE ROLE lostparty_app LOGIN PASSWORD 'test-only-password' NOSUPERUSER NOCREATEDB NOCREATEROLE; ALTER DATABASE lostparty_test OWNER TO lostparty_app; GRANT USAGE,CREATE ON SCHEMA public TO lostparty_app;")
        run([args.docker,'volume','create','--label','lostparty.synthetic-rehearsal='+project,volume])
        run(runner('python','-c',PREPARE_KEYS,root=True))
        key_before=json.loads(text(runner('python','-c',KEYS)))
        announce('old_0036_and_backup')
        run(runner('alembic','upgrade','0036_roster_presence'))
        sql(SEED)
        before=json.loads(text(runner('python','-c',SNAPSHOT)))
        administrator_before=administrator_snapshot()
        api(OLD_IMAGE,names[0])
        result['old_api_before_reset_healthy']=True
        blocked=run(runner('alembic','upgrade','0038_analysis_candidates'),check=False)
        assert blocked.returncode!=0
        assert json.loads(text(runner('python','-c',SNAPSHOT)))==before
        result['populated_0037_guard_preserved']=True
        run([args.docker,'rm','-f',names[0]])
        dump=run([args.docker,'exec',dbid,'pg_dump','-U','postgres','-Fc','--lock-wait-timeout=5000',DB]).stdout
        assert dump.startswith(b'PGDMP')
        catalog=run([args.docker,'exec','-i',dbid,'pg_restore','--list'],data=dump).stdout
        assert b'alembic_version' in catalog
        result['synthetic_dump_bytes']=len(dump)
        result['synthetic_dump_sha256']=hashlib.sha256(dump).hexdigest()
        announce('reset_and_new_0038')
        reset_database()
        run(runner('alembic','upgrade','0038_analysis_candidates'))
        assert sql('SELECT version_num FROM alembic_version;')=='0038_analysis_candidates'
        assert sql("SELECT (SELECT count(*) FROM users)+(SELECT count(*) FROM auth_sessions)+(SELECT count(*) FROM game_accounts);")=='0'
        assert sql("SELECT count(*) FROM pg_roles WHERE rolname='lostparty_app' AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole;")=='1'
        api(new_image,names[1])
        assert json.loads(text(runner('python','-c',KEYS)))==key_before
        result.update(new_0038_api_healthy=True,reset_app_user_data_empty=True,role_and_synthetic_keys_preserved=True)
        run([args.docker,'rm','-f',names[1]])
        announce('restore_old_0036')
        reset_database()
        run([args.docker,'exec','-i',dbid,'pg_restore','-U','postgres','--exit-on-error','-d',DB],data=dump)
        after=json.loads(text(runner('python','-c',SNAPSHOT)))
        assert before==after
        assert administrator_before==administrator_snapshot()
        result['shared_snapshot_sql_exercised']=True
        assert sql('SELECT version_num FROM alembic_version;')=='0036_roster_presence'
        api(OLD_IMAGE,names[0])
        assert json.loads(text(runner('python','-c',KEYS)))==key_before
        result.update(old_0036_restored_api_healthy=True,restored_tables_equal=len(before),all_restored_rows_equal=True,
                      external_provider_calls=0,status='passed')
    except Exception as error:
        result.update(status='failed',failed_stage=stage,error_type=type(error).__name__,error=str(error) if isinstance(error,RuntimeError) else 'rehearsal_assertion_failed')
    finally:
        for name in names:
            run([args.docker,'rm','-f',name],check=False)
        down=run([*base,'down','--remove-orphans','--volumes','--timeout','10'],check=False)
        removed=run([args.docker,'volume','rm',volume],check=False)
        cleanup_ok=down.returncode==0 and removed.returncode==0
        temporary.cleanup()
        result['cleanup_ok']=cleanup_ok
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    return 0 if result['status']=='passed' and cleanup_ok else 1


if __name__=='__main__':
    raise SystemExit(main())
