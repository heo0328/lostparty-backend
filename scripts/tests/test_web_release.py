"""Handoff corruption and filesystem activation boundaries, using synthetic ZIPs."""
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
import web_release as web
from maintenance import candidate_config, NEW_ANDROID
from deployment_plan import load


def bundle(root, content=b'hello', *, extra=None, manifest_changes=None):
    root.mkdir(parents=True,exist_ok=True)
    manifest=dict(schema_version=1,version='2.1.0+6',source_commit='a'*40,backend_origin='https://lostparty.duckdns.org',source_dirty=False,candidate_only=False,dirty_status=[],build_mode='release',service_worker='disabled',site_directory='site',files=[dict(path='index.html',bytes=len(content),sha256=web.digest(content))])
    manifest.update(manifest_changes or {})
    raw=json.dumps(manifest).encode()
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        z.writestr('site/index.html',content);z.writestr('release-manifest.json',raw)
        if extra:z.writestr(*extra)
    archive=data.getvalue()
    (root/web.BUNDLE).write_bytes(archive)
    (root/(web.BUNDLE+'.sha256')).write_text(web.digest(archive)+'  '+web.BUNDLE+'\n')
    (root/'release-manifest.json').write_bytes(raw)
    return {'web':dict(version='2.1.0+6',source='a'*40,origin='https://lostparty.duckdns.org',bundle_sha256=web.digest(archive),bundle_bytes=len(archive),site_files=1)}


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.input=self.root/'handoff';self.output=self.root/'server'
        self.receipt=bundle(self.input)

    def test_verified_stage_switch_and_first_rollback(self):
        original=(self.input/web.BUNDLE).read_bytes()
        name=web.stage(self.input,self.receipt,self.output)
        self.assertFalse((self.output/'current').exists())
        with self.assertRaisesRegex(ValueError,'compatibility'):
            web.switch(self.output,self.receipt)
        web.switch(self.output,self.receipt,compatible=True)
        self.assertEqual((self.output/'current/index.html').read_bytes(),b'hello')
        web.validate_active(self.output,self.receipt)
        self.assertEqual((self.output/'releases'/name/web.BUNDLE).read_bytes(),original)
        web.switch(self.output,rollback=True)
        self.assertFalse((self.output/'current').exists())
        with self.assertRaises(ValueError):web.validate_active(self.output,self.receipt)

    def test_failed_activation_preserves_current_and_previous_rollback(self):
        web.stage(self.input,self.receipt,self.output);web.switch(self.output,self.receipt,compatible=True)
        first=(self.output/'current').readlink()
        other=self.root/'second';receipt=bundle(other,b'new')
        web.stage(other,receipt,self.output)
        with patch('web_release.set_pointer',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):web.switch(self.output,receipt,compatible=True)
        self.assertEqual((self.output/'current').readlink(),first)
        web.switch(self.output,receipt,compatible=True)
        self.assertEqual((self.output/'current/index.html').read_bytes(),b'new')
        web.switch(self.output,rollback=True)
        self.assertEqual((self.output/'current').readlink(),first)

    def test_untrusted_paths_and_entries(self):
        for name in ['../escape','/absolute','site\\escape','site/../escape','site//escape','SITE/index.html']:
            with self.subTest(name=name):
                receipt=bundle(self.input,extra=(name,b'bad'))
                with self.assertRaises(ValueError):web.verify(self.input,receipt)
        link=zipfile.ZipInfo('site/link');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        receipt=bundle(self.input,extra=(link,b'../outside'))
        with self.assertRaises(ValueError):web.verify(self.input,receipt)

    def test_hash_source_manifest_and_candidate_rejected(self):
        for key,value in [('schema_version',True),('source_commit','b'*40),('candidate_only',True),('source_dirty',True),('backend_origin','http://attacker')]:
            receipt=bundle(self.input,manifest_changes={key:value})
            with self.assertRaisesRegex(ValueError,'identity'):web.verify(self.input,receipt)
        receipt=bundle(self.input)
        (self.input/web.BUNDLE).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'hash'):web.verify(self.input,receipt)
        receipt=bundle(self.input)
        (self.input/'release-manifest.json').write_bytes((self.input/'release-manifest.json').read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'bytes'):web.verify(self.input,receipt)

    def test_staged_tampering_and_symlink_rejected(self):
        name=web.stage(self.input,self.receipt,self.output)
        index=self.output/'releases'/name/'site/index.html'
        index.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):web.switch(self.output,self.receipt,compatible=True)
        index.unlink();index.symlink_to(self.input/web.BUNDLE)
        with self.assertRaises(ValueError):web.switch(self.output,self.receipt,compatible=True)

    def test_receive_pins_artifact_identity_expiry_and_archive_bytes(self):
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:
            for name in web.FILES:z.writestr(name,(self.input/name).read_bytes())
        raw=archive.getvalue()
        self.receipt['web'].update(artifact_id=123,artifact_name='pinned',run_id=456,archive_sha256=web.digest(raw))
        meta=dict(id=123,name='pinned',workflow_run=dict(id=456,head_sha='a'*40),expired=False,expires_at='2099-01-01T00:00:00Z',digest='sha256:'+web.digest(raw))
        target=self.root/'received'
        with patch('web_release.subprocess.run',side_effect=[SimpleNamespace(stdout=json.dumps(meta).encode()),SimpleNamespace(stdout=raw)]):
            web.receive(self.receipt,target)
        self.assertEqual((target/web.BUNDLE).read_bytes(),(self.input/web.BUNDLE).read_bytes())
        for key,value in [('expired',True),('name','other'),('workflow_run',dict(id=999,head_sha='a'*40)),('digest','sha256:wrong')]:
            with self.subTest(key=key),patch('web_release.subprocess.run',return_value=SimpleNamespace(stdout=json.dumps({**meta,key:value}).encode())),self.assertRaises(ValueError):
                web.receive(self.receipt,self.root/'wrong')
        self.assertFalse((self.root/'wrong').exists())

    def test_existing_input_not_overwritten_and_manifest_stays_private(self):
        name=web.stage(self.input,self.receipt,self.output)
        self.assertEqual(web.stage(self.input,self.receipt,self.output),name)
        self.assertFalse((self.output/'releases'/name/'site/release-manifest.json').exists())


class ConfigTests(unittest.TestCase):
    def test_only_reviewed_environment_and_web_mount_changes(self):
        baseline={'services':{'api':{'image':'old','environment':{'GOOGLE_CLIENT_ID':'574337852234-vdkvdobbq8es2rdpumc1icqt6ja3a3cr.apps.googleusercontent.com','GOOGLE_AZP_ALLOWLIST':'debug,old'},'volumes':['keys']},'db':{'image':'postgres','volumes':['data']},'caddy':{'volumes':[{'target':'/etc/caddy/Caddyfile','source':'old','read_only':True}, {'target':'/data','source':'certs'}]}}}
        old=copy.deepcopy(baseline)
        result=candidate_config(baseline,{'image':'new'},Path('/web'),Path('/private/Caddyfile'))
        self.assertEqual(baseline,old)
        self.assertEqual(result['services']['db'],old['services']['db'])
        self.assertEqual(result['services']['api']['volumes'],['keys'])
        self.assertEqual(result['services']['api']['environment']['GOOGLE_AZP_ALLOWLIST'],'debug,old,'+NEW_ANDROID)
        self.assertEqual(result['services']['caddy']['volumes'][1], {'type':'bind','source':'/web','target':'/srv/web','read_only':True,'bind':{}})

    def test_default_standard_and_explicit_maintenance_version_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.assertEqual(load(root)['mode'],'standard')
            (root/'VERSION').write_text('999.0.0')
            record=json.loads((Path(__file__).resolve().parents[2]/'release-deployment.json').read_text())
            (root/'release-deployment.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError):load(root)
