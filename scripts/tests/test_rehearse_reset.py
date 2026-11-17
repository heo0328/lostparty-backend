"""Reject non-ephemeral storage and foreign namespaces before a reset."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from rehearse_reset import validate_test_database

PROJECT='lostparty-rehearsal-0123456789ab'
def identity():
    return {'Config':{'Labels':{'com.docker.compose.project':PROJECT,'com.docker.compose.service':'test-db'}},
            'HostConfig':{'Tmpfs':{'/var/lib/postgresql/data':''},'Binds':None,'PortBindings':{}},'Mounts':[]}

class ResetIsolationTests(unittest.TestCase):
    def test_desktop_and_mount_tmpfs_forms(self):
        value=identity();validate_test_database(value,PROJECT)
        value['HostConfig']['Tmpfs']={}
        value['Mounts']=[{'Type':'tmpfs','Destination':'/var/lib/postgresql/data'}]
        validate_test_database(value,PROJECT)

    def test_reject_external_or_persistent_targets(self):
        for change in ('project','service','ports','bind','volume','missing_tmpfs','unapproved_project'):
            with self.subTest(change=change):
                value=identity();project=PROJECT
                if change=='project':value['Config']['Labels']['com.docker.compose.project']='lostparty-lightsail'
                if change=='service':value['Config']['Labels']['com.docker.compose.service']='db'
                if change=='ports':value['HostConfig']['PortBindings']={'5432/tcp':[{'HostPort':'5432'}]}
                if change=='bind':value['HostConfig']['Binds']=['/existing/data:/var/lib/postgresql/data']
                if change=='volume':value['Mounts']=[{'Type':'volume','Destination':'/var/lib/postgresql/data'}]
                if change=='missing_tmpfs':value['HostConfig']['Tmpfs']={}
                if change=='unapproved_project':
                    project='lostparty-backend';value['Config']['Labels']['com.docker.compose.project']=project
                with self.assertRaisesRegex(RuntimeError,'unsafe_rehearsal_db'):
                    validate_test_database(value,project)
