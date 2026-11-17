"""Only UUID-labelled tmpfs PostgreSQL can be used by the reset integration."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deployment'))
from reset_smoke import validate_database


class ResetSmokeGuards(unittest.TestCase):
    def test_exact_ephemeral_target_and_rejections(self):
        project='lostparty-reset-smoke-0123456789ab'
        value={'HostConfig':{'Tmpfs':{'/var/lib/postgresql/data':''},'PortBindings':{},'Binds':None},
               'Mounts':[],'Config':{'Labels':{'com.docker.compose.project':project,'com.docker.compose.service':'db'}}}
        validate_database(value,project)
        for key in ('production_name','foreign_label','wrong_service','port','bind','volume','not_tmpfs'):
            candidate=copy.deepcopy(value);name=project
            if key=='production_name':name='lostparty-lightsail';candidate['Config']['Labels']['com.docker.compose.project']=name
            if key=='foreign_label':candidate['Config']['Labels']['com.docker.compose.project']='lostparty-lightsail'
            if key=='wrong_service':candidate['Config']['Labels']['com.docker.compose.service']='other'
            if key=='port':candidate['HostConfig']['PortBindings']={'5432/tcp':[{'HostPort':'5432'}]}
            if key=='bind':candidate['HostConfig']['Binds']=['/existing:/var/lib/postgresql/data']
            if key=='volume':candidate['Mounts']=[{'Type':'volume','Destination':'/var/lib/postgresql/data'}]
            if key=='not_tmpfs':candidate['HostConfig']['Tmpfs']={}
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate_database(candidate,name)


if __name__=='__main__':unittest.main()
