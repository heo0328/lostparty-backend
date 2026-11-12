"""Transition safety: no old-image restart once forward migration begins."""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import maintenance as m
from backup import confirm, capture
import tarfile
import os


class MaintenanceTests(unittest.TestCase):
    def test_unfinished_normal_deploy_is_resolved_before_forward_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)
            (state/'current.json').write_text(json.dumps({'tag':'v2.0.0'}))
            attempt=state/'123-1';attempt.mkdir()
            (attempt/'result.json').write_text(json.dumps({'status':'in_progress','previous_good':{'db_revision':'0035_cycle_group_policy'}}))
            platform=MagicMock()
            with self.assertRaisesRegex(ValueError,'unfinished_deployment_journal'):
                m.preflight(platform,state,{}, {})
            platform.pull.assert_not_called();platform.replace.assert_not_called()

    def test_backup_requires_current_identity_pc_hash_and_fresh_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'backup.tar';p.write_bytes(b'synthetic archive')
            current={'source':'a'*40,'image':'image'};protected={'key':('hash',384,1,1)}
            record={**current,'db_revision':'0035_cycle_group_policy','created_at':'2026-11-11T01:00:00+00:00','archive':str(p),'archive_sha256':m.checksum(p.read_bytes()),'pc_archive_sha256':m.checksum(p.read_bytes()),'pc_copy_verified':True,'dump_catalog_verified':True,'protected_files':{'key':['hash',384,1,1]}}
            now=datetime(2026,11,11,2,tzinfo=timezone.utc)
            m.check_backup(record,current,protected,now)
            for key,value in [('source','other'),('pc_copy_verified',False),('pc_archive_sha256','wrong'),('created_at','2026-11-07T01:00:00+00:00'),('protected_files',{})]:
                with self.subTest(key=key),self.assertRaises(ValueError):m.check_backup({**record,key:value},current,protected,now)
            receipt=Path(directory)/'receipt.json';receipt.write_text(json.dumps(record))
            with self.assertRaises(ValueError):confirm(receipt,'wrong')

    def test_success_keeps_public_closed_and_aligns_environment_and_baseline(self):
        from test_web_release import bundle
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);state=root/'state';state.mkdir();web=root/'web'
            handoff=root/'handoff';receipt=bundle(handoff)
            old=root/'old.Caddyfile';old.write_text('old')
            new=root/'new.Caddyfile';new.write_text('new')
            env=root/'.env.lightsail';env.write_text('GOOGLE_AZP_ALLOWLIST=debug,old\n')
            current={'tag':'v2.0.0','compose':'old-compose','source':'old','image':'old-image'}
            baseline={'services':{'api':{'image':'old-image','environment':{'GOOGLE_CLIENT_ID':m.WEB_CLIENT,'GOOGLE_AZP_ALLOWLIST':'debug,old'}},'db':{'image':'db'},'caddy':{'volumes':[{'target':'/etc/caddy/Caddyfile','source':str(old),'read_only':True}]}}}
            before={x:{'Id':x,'State':{'StartedAt':'old'},'Mounts':[]} for x in ['api','db','caddy']}
            platform=MagicMock();platform.root=root;platform.protected_files.return_value={}
            platform.healthy.return_value=True;platform.containers.return_value=before
            platform.db_revision.return_value='0036_roster_presence'
            response=MagicMock();response.status=503;response.read.return_value=b'Maintenance'
            contracts={'openapi.yaml':'expected'}
            def command(args,**kwargs):
                if args[-1]=='http://127.0.0.1:8081/health':return '{"status":"ok","database":"ok"}'
                if args[-1]=='http://127.0.0.1:8081/':return 'hello'
                return json.dumps(contracts)
            manifest={'schema':1,'source':'a'*40,'image':'new-image','tag':'v2.1.0'}
            plan={'configuration_revision':'lightsail-web-2.1.0','to_db_revision':'0036_roster_presence'}
            with patch('maintenance.preflight',return_value=(current,baseline,before)),patch('maintenance.check_backup'),patch('maintenance.table_snapshot',return_value={}),patch('maintenance.command',side_effect=command),patch('maintenance.install_controller'),patch('maintenance.urllib.request.urlopen',return_value=response):
                result=m.transition(platform,state,manifest,plan,receipt,handoff,web,new,{},contracts)
            self.assertEqual(result['phase'],'candidate_ready')
            self.assertTrue((web/'maintenance').exists())
            self.assertEqual((web/'current/index.html').read_text(),'hello')
            frozen=json.loads((state/'maintenance-2.1.0/compose.json').read_text())
            self.assertIn(m.NEW_ANDROID,env.read_text())
            self.assertIn(m.NEW_ANDROID,frozen['services']['api']['environment']['GOOGLE_AZP_ALLOWLIST'])
            self.assertEqual(frozen['services']['caddy']['volumes'][0]['source'],str(old))
            self.assertEqual(frozen['services']['caddy']['volumes'][1],{'type':'bind','source':str(web),'target':'/srv/web','read_only':True,'bind':{}})
            self.assertFalse(json.loads((state/'current.json').read_text())['public_open'])

    def test_controller_drift_prevents_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();installed=root/'installed';installed.mkdir()
            for name in ['server.py','common.py']:
                (source/name).write_text('new');(installed/name).write_text('old')
            backup={'recovery_files':{str(installed/name):m.checksum(b'old') for name in ['server.py','common.py']}}
            (installed/'common.py').write_text('unexpected')
            with self.assertRaises(ValueError):m.install_controller(source,installed,backup)
            self.assertEqual((installed/'server.py').read_text(),'old')

    def test_backup_archive_keeps_original_file_modes_and_copy_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);state=root/'state';state.mkdir();secret=root/'.secrets/lightsail';secret.mkdir(parents=True)
            env=root/'.env.lightsail';env.write_text('test-only')
            for name in ['jwt.pem','recovery.key','lostark-credential.key','lostark-fingerprint.key']:
                (secret/name).write_bytes(b'synthetic-not-a-real-key');(secret/name).chmod(0o600)
            current={'source':'a'*40,'image':'old'};(state/'current.json').write_text(json.dumps(current))
            platform=MagicMock();platform.root=root;platform.healthy.return_value=True
            platform.db_revision.return_value='0035_cycle_group_policy'
            platform.containers.return_value={'api':{'Id':'api'},'db':{'Id':'db','Config':{'Env':['POSTGRES_DB=lostparty_test']}}}
            platform.protected_files.side_effect=lambda:{str(p):(m.checksum(p.read_bytes()),p.stat().st_mode,p.stat().st_uid,p.stat().st_gid) for p in [env,*secret.iterdir()]}
            with patch('backup.subprocess.run',side_effect=[MagicMock(stdout=b'PGDMPsynthetic'),MagicMock(stdout=b'alembic_version\nusers\n')]):
                record=capture(platform,state,root/'backups/new',installed=root/'tools',system_files=[],web_root=root/'web')
            with tarfile.open(record['archive']) as archive:
                member=archive.getmember('recovery/server/'+str(secret/'jwt.pem').lstrip('/'))
                self.assertEqual(member.mode,0o600)
                self.assertEqual(member.uid,(secret/'jwt.pem').stat().st_uid)
                self.assertEqual(archive.extractfile(member).read(),b'synthetic-not-a-real-key')
                self.assertIn('recovery/BACKUP-INFO.json',archive.getnames())
            self.assertFalse(record['pc_copy_verified'])
            result=confirm(root/'backups/new/receipt.json',record['archive_sha256'])
            self.assertTrue(result['pc_copy_verified'])

    def transition_failure(self, migrate):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);state=root/'state';state.mkdir();web=root/'web';web.mkdir()
            old=root/'old.Caddyfile';old.write_text('old')
            new=root/'new.Caddyfile';new.write_text('new')
            current={'compose':'old-compose','source':'old','image':'old-image'}
            baseline={'services':{'caddy':{'volumes':[{'target':'/etc/caddy/Caddyfile','source':str(old)}]}}}
            before={};platform=MagicMock();platform.protected_files.return_value={}
            def compose(path,*args,**kwargs):
                if args[:2]==('stop','api') and not migrate:raise RuntimeError('stop failed before migration')
                if args and args[0]=='run' and 'alembic' in args:raise RuntimeError('migration interrupted')
            platform.compose.side_effect=compose
            response=MagicMock();response.status=503;response.read.return_value=b'Maintenance'
            with patch('maintenance.preflight',return_value=(current,baseline,before)),patch('maintenance.check_backup'),patch('maintenance.table_snapshot',return_value={}),patch('maintenance.stage'),patch('maintenance.candidate_config',return_value=baseline),patch('maintenance.urllib.request.urlopen',return_value=response):
                with self.assertRaises(RuntimeError):
                    m.transition(platform,state,{'source':'new','image':'new-image'}, {'configuration_revision':'lightsail-web-2.1.0','to_db_revision':'0036_roster_presence'}, {'web':{}},root,web,new,{}, {})
            record=json.loads((state/'maintenance-2.1.0/result.json').read_text())
            self.assertTrue((web/'maintenance').exists())
            self.assertEqual(record['db_migration_started'],migrate)
            self.assertEqual(platform.replace.called,not migrate)
    def test_failure_before_migration_can_restart_old_api(self):self.transition_failure(False)
    def test_migration_interruption_never_restarts_old_api(self):self.transition_failure(True)
