"""Reset ordering, immutable backups and failure containment; no production I/O."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import reset_release as reset


def containers():
    return {
        'api':{'Id':'api','State':{'Running':False,'StartedAt':'first'},'Mounts':[]},
        'db':{'Id':'db','State':{'Running':True,'StartedAt':'first'},'Mounts':[],
              'Config':{'Env':['POSTGRES_DB=lostparty'], 'Labels':{
                  'com.docker.compose.project':'lostparty-lightsail','com.docker.compose.service':'db'}}},
        'caddy':{'Id':'caddy','State':{'Running':True,'StartedAt':'first'},'Mounts':[]}}


class ResetReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.directory=self.root/'journal';self.directory.mkdir()
        self.dump=b'PGDMPsynthetic';(self.directory/'stopped.database.dump').write_bytes(self.dump)
        self.record=dict(phase='stopped_pc_confirmed',stopped_pc_confirmed=True,
                         stopped_at=datetime.now(timezone.utc).isoformat(),stopped_dump_sha256=reset.checksum(self.dump),
                         snapshot={'users':'1:synthetic'},protected_files={},
                         db_identity=['db','first',[]],caddy_identity=['caddy','first',[]],
                         candidate_compose='candidate.json',reset_started=False,
                         previous_good={'compose':'old.json','image':'old'},previous_web='releases/'+('a'*64)+'/site',
                         manifest={'image':'new','source':'b'*40},receipt={'web':{'bundle_sha256':'c'*64}},public_open=False)
        self.platform=MagicMock();self.platform.containers.side_effect=lambda:copy.deepcopy(self.live)
        self.platform.protected_files.return_value={};self.live=containers()
        candidate=self.directory/'candidate.json';candidate.write_bytes(b'synthetic config')
        self.record['candidate_compose']=str(candidate)
        self.record['candidate_compose_sha256']=reset.checksum(candidate.read_bytes())
        (self.root/'current.json').write_text(json.dumps(self.record['previous_good']))

    def test_exact_production_identity_only(self):
        self.assertEqual(reset.database_identity(self.live),'db')
        for key,value in [('Env',['POSTGRES_DB=postgres']),('Labels',{}),('Env',['POSTGRES_DB=lostparty_test'])]:
            changed=copy.deepcopy(self.live);changed['db']['Config'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):reset.database_identity(changed)

    def test_snapshot_batches_readonly_and_rejects_duplicate_or_invalid_rows(self):
        row={'table':'users','value':'1:'+'a'*32}
        with patch.object(reset,'sql',return_value=json.dumps(row)) as execute:
            self.assertEqual(reset.private_snapshot('db'),{'users':'1:'+'a'*32})
        execute.assert_called_once_with('db',reset.SNAPSHOT_SQL,database='lostparty')
        self.assertIn('REPEATABLE READ READ ONLY',reset.SNAPSHOT_SQL)
        for raw in [json.dumps(row)+'\n'+json.dumps(row),json.dumps({**row,'table':'invalid.name'}),
                    json.dumps({**row,'value':'unexpected'})]:
            with self.subTest(raw=raw),patch.object(reset,'sql',return_value=raw),self.assertRaises(ValueError):
                reset.private_snapshot('db')

    def test_preflight_rejects_unreviewed_release_or_unfinished_journal_before_pull(self):
        manifest=dict(schema=2,repository='heo0328/lostparty-backend',tag='v2.4.0',
                      source='b'*40,image='ghcr.io/heo0328/lostparty-backend@sha256:'+'c'*64,
                      db_revision=reset.NEW_REVISION,contract_sha256={'openapi.yaml':'a'*64,'legacy.openapi.yaml':'d'*64},
                      compose_sha256='e'*64,built_at_utc='2026-11-17T00:00:00Z')
        current=dict(tag='v2.3.0',source=reset.OLD_SOURCE,configuration_revision='lightsail-web-2.1.0')
        (self.root/'current.json').write_text(json.dumps(current))
        for field,value in [('tag','v2.5.0'),('db_revision',reset.OLD_REVISION),('schema',1)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                reset.preflight(self.platform,self.root,{**manifest,field:value},{})
        self.platform.pull.assert_not_called()
        (self.directory/'result.json').write_text(json.dumps({'status':'in_progress'}))
        with self.assertRaisesRegex(ValueError,'unfinished_deployment'):
            reset.preflight(self.platform,self.root,manifest,{})
        self.platform.pull.assert_not_called();self.platform.containers.assert_not_called()

    def test_prepare_stops_before_final_dump_and_waits_for_pc_confirmation(self):
        state=self.root/'prepare-state';state.mkdir();web=self.root/'prepare-web';web.mkdir()
        baseline={'services':{'api':{'image':'old'},'db':{},'caddy':{}}}
        events=[]
        self.platform.compose.side_effect=lambda *args:events.append('stop')
        previous_web='releases/'+('a'*64)+'/site'
        with patch.object(reset,'WEB',web),patch.object(reset,'preflight',return_value=(self.record['previous_good'],baseline,self.live)),patch.object(reset,'check_backup'),patch.object(reset,'stage'),patch.object(reset,'pointer',return_value=previous_web),patch.object(reset,'closed_edge',side_effect=lambda _:events.append('maintenance_verified')),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'private_snapshot',return_value={'users':'1:synthetic'}),patch.object(reset,'binary',side_effect=lambda *args:events.append('backup') or (b'PGDMPsynthetic' if 'pg_dump' in args[0] else b'alembic_version')):
            record=reset.prepare(self.platform,state,self.record['manifest'],self.record['receipt'],self.root,{})
        self.assertEqual(events,['maintenance_verified','stop','backup','backup'])
        self.assertEqual(record['phase'],'stopped_backup_pending')
        self.assertFalse(record['reset_started']);self.assertFalse(record['public_open'])
        self.assertTrue((web/'maintenance').exists())
        self.assertEqual((state/'reset-2.4.0/stopped.database.dump').stat().st_mode&0o777,0o600)

    def test_prepare_edge_failure_preserves_marker_and_does_not_stop_or_reset(self):
        state=self.root/'prepare-state';state.mkdir();web=self.root/'prepare-web';web.mkdir()
        baseline={'services':{'api':{'image':'old'},'db':{},'caddy':{}}}
        with patch.object(reset,'WEB',web),patch.object(reset,'preflight',return_value=(self.record['previous_good'],baseline,self.live)),patch.object(reset,'check_backup'),patch.object(reset,'stage'),patch.object(reset,'pointer',return_value='previous'),patch.object(reset,'closed_edge',side_effect=RuntimeError('edge not closed')),patch.object(reset,'recreate') as destroy:
            with self.assertRaises(RuntimeError):reset.prepare(self.platform,state,self.record['manifest'],self.record['receipt'],self.root,{})
            destroy.assert_not_called()
        self.platform.compose.assert_not_called()
        self.assertTrue((web/'maintenance').exists())
        journal=json.loads((state/'reset-2.4.0/result.json').read_text())
        self.assertEqual(journal['phase'],'prepare_failed');self.assertFalse(journal['reset_started'])

    def test_writers_connections_container_and_key_drift_refused(self):
        with patch.object(reset,'sql',return_value='0'):
            self.assertEqual(reset.no_writers(self.platform,self.record),'db')
            for change in ('api','db','caddy','keys'):
                with self.subTest(change=change),self.assertRaises(ValueError):
                    original=copy.deepcopy(self.live)
                    try:
                        if change=='api':self.live['api']['State']['Running']=True
                        elif change=='keys':self.platform.protected_files.return_value={'changed':('secret-digest',)}
                        else:self.live[change]['Id']='replaced'
                        reset.no_writers(self.platform,self.record)
                    finally:self.live=original;self.platform.protected_files.return_value={}
        with patch.object(reset,'sql',return_value='1'),self.assertRaisesRegex(ValueError,'clients_still_connected'):
            reset.no_writers(self.platform,self.record)

    def test_stopped_pc_confirmation_rejects_wrong_bytes_and_expiry(self):
        self.record['phase']='stopped_backup_pending'
        with self.assertRaises(ValueError):reset.confirm_stopped(self.directory,self.record,'0'*64)
        self.record['stopped_at']=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        with self.assertRaisesRegex(ValueError,'fresh_stopped_backup'):
            reset.confirm_stopped(self.directory,self.record,self.record['stopped_dump_sha256'])
        self.record['stopped_at']=datetime.now(timezone.utc).isoformat()
        reset.confirm_stopped(self.directory,self.record,self.record['stopped_dump_sha256'])
        self.assertEqual(json.loads((self.directory/'result.json').read_text())['phase'],'stopped_pc_confirmed')

    def test_reset_requires_explicit_ack_and_pc_confirmation_before_any_io(self):
        for acknowledgment,confirmed in [(None,True),(reset.ACK,False)]:
            self.record['stopped_pc_confirmed']=confirmed
            with self.subTest(ack=acknowledgment),self.assertRaises(ValueError):
                reset.apply(self.platform,self.root,self.directory,self.record,{},acknowledgment)
        self.platform.assert_not_called();self.platform.containers.assert_not_called()

    def test_reset_rejects_changed_dump_before_database_destruction(self):
        (self.directory/'stopped.database.dump').write_bytes(b'changed')
        with patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'recreate') as destroy:
            with self.assertRaisesRegex(ValueError,'stopped_dump_changed'):
                reset.apply(self.platform,self.root,self.directory,self.record,{},reset.ACK)
            destroy.assert_not_called()

    def test_snapshot_drift_prevents_reset(self):
        with patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'private_snapshot',return_value={}),patch.object(reset,'recreate') as destroy:
            with self.assertRaisesRegex(ValueError,'stopped_database_changed'):
                reset.apply(self.platform,self.root,self.directory,self.record,{},reset.ACK)
            destroy.assert_not_called()

    def test_candidate_config_or_current_drift_prevents_reset(self):
        Path(self.record['candidate_compose']).write_bytes(b'changed config')
        with self.assertRaisesRegex(ValueError,'candidate_configuration_changed'):
            reset.no_writers(self.platform,self.record)
        (self.root/'current.json').write_text('{}')
        with patch.object(reset,'closed_edge'),patch.object(reset,'recreate') as destroy:
            with self.assertRaisesRegex(ValueError,'current_release_changed'):
                reset.apply(self.platform,self.root,self.directory,self.record,{},reset.ACK)
            destroy.assert_not_called()

    def test_migration_failure_never_restarts_old_api_or_opens_public(self):
        self.platform.compose.side_effect=RuntimeError('synthetic interruption')
        with patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'private_snapshot',return_value=self.record['snapshot']),patch.object(reset,'sql',return_value=reset.OLD_REVISION),patch.object(reset,'recreate') as destroy:
            with self.assertRaises(RuntimeError):reset.apply(self.platform,self.root,self.directory,self.record,{},reset.ACK)
        destroy.assert_called_once_with('db');self.platform.replace.assert_not_called()
        journal=json.loads((self.directory/'result.json').read_text())
        self.assertTrue(journal['reset_started']);self.assertFalse(journal['public_open'])
        self.assertEqual(journal['phase'],'apply_failed_restore_required')

    def test_successful_apply_keeps_public_closed_and_commits_candidate_last(self):
        web=self.root/'web';(web/'current').mkdir(parents=True);(web/'current/index.html').write_bytes(b'synthetic web')
        (web/'maintenance').touch()
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'private_snapshot',return_value=self.record['snapshot']),patch.object(reset,'sql',side_effect=[reset.OLD_REVISION,reset.NEW_REVISION,'0']),patch.object(reset,'recreate'),patch.object(reset,'candidate_checks'),patch.object(reset,'switch'),patch.object(reset,'validate_active'),patch.object(reset,'binary',return_value=b'synthetic web'):
            reset.apply(self.platform,self.root,self.directory,self.record,{},reset.ACK)
        self.platform.replace.assert_called_once_with(self.record['candidate_compose'])
        self.assertTrue((web/'maintenance').exists())
        self.assertFalse(json.loads((self.root/'current.json').read_text())['public_open'])
        self.assertEqual(self.record['phase'],'candidate_ready')

    def test_unchanged_old_database_after_reset_attempt_needs_no_destructive_restore(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch();self.record['reset_started']=True
        self.platform.db_revision.return_value=reset.OLD_REVISION
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'sql',return_value='1'),patch.object(reset,'private_snapshot',return_value=self.record['snapshot']),patch.object(reset,'set_pointer'),patch.object(reset,'recreate') as destroy,patch.object(reset,'binary') as restore:
            reset.rollback(self.platform,self.root,self.directory,self.record,reset.ACK)
            destroy.assert_not_called();restore.assert_not_called()
        self.platform.replace.assert_called_once_with('old.json')
        self.assertTrue((web/'maintenance').exists())
        self.assertEqual(self.record['status'],'rolled_back')

    def test_restore_after_reset_recreates_and_restores_before_old_api(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch();self.record['reset_started']=True
        self.platform.db_revision.return_value=reset.OLD_REVISION
        events=[]
        self.platform.replace.side_effect=lambda _:events.append('old_api')
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'sql',side_effect=['1','1','0']),patch.object(reset,'private_snapshot',side_effect=[{},self.record['snapshot']]),patch.object(reset,'set_pointer'),patch.object(reset,'recreate',side_effect=lambda _:events.append('recreate')),patch.object(reset,'binary',side_effect=lambda *a:events.append('restore')):
            reset.rollback(self.platform,self.root,self.directory,self.record,reset.ACK)
        self.assertEqual(events,['recreate','restore','old_api'])
        self.assertTrue((web/'maintenance').exists())

    def test_recreate_never_forces_remaining_connections_or_drops_role(self):
        with patch.object(reset,'sql') as sql:reset.recreate('db')
        statements=[c.args[1] for c in sql.call_args_list]
        self.assertEqual(statements[0],'DROP DATABASE IF EXISTS lostparty;')
        self.assertFalse(any('FORCE' in s or 'DROP ROLE' in s or 'PASSWORD' in s for s in statements))

    def test_rollback_after_publication_refused_without_stopping_api(self):
        self.record['public_open']=True
        with self.assertRaises(ValueError):reset.rollback(self.platform,self.root,self.directory,self.record,reset.ACK)
        self.platform.compose.assert_not_called()

    def test_restore_requires_unchanged_dump_and_no_unexpected_new_users(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch();self.record['reset_started']=True
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'no_writers',return_value='db'),patch.object(reset,'private_snapshot',return_value={}),patch.object(reset,'sql',side_effect=['1','1','1']),patch.object(reset,'recreate') as destroy:
            with self.assertRaisesRegex(ValueError,'unexpected_new_users'):
                reset.rollback(self.platform,self.root,self.directory,self.record,reset.ACK)
            destroy.assert_not_called();self.platform.replace.assert_not_called()
        self.assertTrue((web/'maintenance').exists())

    def test_backup_rejects_unverified_pc_copy_and_missing_archive(self):
        archive=self.root/'archive.tar';archive.write_bytes(b'synthetic')
        current={'source':'old','image':'old'}
        receipt=dict(source='old',image='old',db_revision=reset.OLD_REVISION,
                     created_at=datetime.now(timezone.utc).isoformat(),protected_files={},
                     archive=str(archive),archive_sha256=reset.checksum(archive.read_bytes()),
                     pc_archive_sha256=reset.checksum(archive.read_bytes()),pc_copy_verified=True,dump_catalog_verified=True)
        reset.check_backup(receipt,current,{})
        receipt['pc_copy_verified']=False
        with self.assertRaises(ValueError):reset.check_backup(receipt,current,{})
        receipt['pc_copy_verified']=True;archive.unlink()
        with self.assertRaises(ValueError):reset.check_backup(receipt,current,{})

    def test_open_requires_exact_joint_acceptance_and_restores_marker_on_probe_failure(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch()
        self.record['phase']='candidate_ready';(self.root/'current.json').write_text('{}')
        acceptance=dict(backend_source=self.record['manifest']['source'],web_sha256='c'*64,
                        backend_checks=True,native_checks=True,joint_publication_authorized=True)
        with self.assertRaises(ValueError):reset.open_public(self.platform,self.root,self.directory,self.record,{}, {})
        with self.assertRaises(ValueError):
            reset.open_public(self.platform,self.root,self.directory,self.record,{}, {**acceptance,'native_checks':1})
        self.platform.probes.side_effect=RuntimeError('offline')
        with patch.object(reset,'WEB',web),patch.object(reset,'candidate_checks'),patch.object(reset,'validate_active'):
            with self.assertRaises(RuntimeError):reset.open_public(self.platform,self.root,self.directory,self.record,{},acceptance)
        self.assertTrue((web/'maintenance').exists());self.assertFalse(self.record['public_open'])

    def test_restored_release_reopens_only_with_matching_acceptance(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch()
        self.record['phase']='rolled_back_under_maintenance'
        self.record['previous_good']['source']='a'*40
        (self.root/'current.json').write_text(json.dumps(self.record['previous_good']))
        self.platform.db_revision.return_value=reset.OLD_REVISION
        accepted=dict(backend_source='a'*40,web_sha256='a'*64,backend_checks=True,
                      native_checks=True,joint_publication_authorized=True)
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'pointer',return_value=self.record['previous_web']),patch.object(reset,'command',return_value='{"status":"ok","database":"ok"}'):
            with self.assertRaises(ValueError):reset.open_restored(self.platform,self.root,self.directory,self.record,{**accepted,'backend_source':'b'*40})
            self.assertTrue((web/'maintenance').exists())
            reset.open_restored(self.platform,self.root,self.directory,self.record,accepted)
        self.assertFalse((web/'maintenance').exists())
        self.assertEqual(self.record['phase'],'restored_public_open')

    def test_restored_probe_failure_recloses_public_access(self):
        web=self.root/'web';web.mkdir();(web/'maintenance').touch()
        self.record['phase']='rolled_back_under_maintenance'
        self.record['previous_good']['source']='a'*40
        (self.root/'current.json').write_text(json.dumps(self.record['previous_good']))
        self.platform.db_revision.return_value=reset.OLD_REVISION
        self.platform.probes.side_effect=RuntimeError('edge failed')
        accepted=dict(backend_source='a'*40,web_sha256='a'*64,backend_checks=True,
                      native_checks=True,joint_publication_authorized=True)
        with patch.object(reset,'WEB',web),patch.object(reset,'closed_edge'),patch.object(reset,'pointer',return_value=self.record['previous_web']),patch.object(reset,'command',return_value='{"status":"ok","database":"ok"}'):
            with self.assertRaises(RuntimeError):reset.open_restored(self.platform,self.root,self.directory,self.record,accepted)
        self.assertTrue((web/'maintenance').exists());self.assertFalse(self.record['public_open'])


if __name__=='__main__':unittest.main()
