"""Explicit publication/deployment split for reviewed maintenance transitions."""
import json
from pathlib import Path


def load(root=Path('.')):
    root = Path(root)
    path = root / 'release-deployment.json'
    if not path.exists():
        return {'mode': 'standard'}
    data = json.loads(path.read_text())
    if set(data) != {'schema', 'version', 'mode', 'from_db_revision', 'to_db_revision',
                     'configuration_revision', 'web_receipt'}:
        raise ValueError('invalid deployment plan fields')
    if data['schema'] != 1 or data['version'] != (root / 'VERSION').read_text().strip():
        raise ValueError('deployment plan version mismatch')
    if data['mode'] != 'maintenance':
        raise ValueError('invalid explicit deployment mode')
    if data['from_db_revision'] != '0035_cycle_group_policy' or data['to_db_revision'] != '0036_roster_presence':
        raise ValueError('unreviewed maintenance migration')
    if data['configuration_revision'] != 'lightsail-web-2.1.0' or data['web_receipt'] != 'docs/engineering/operations/records/web-handoff-2.1.0.json':
        raise ValueError('unreviewed configuration transition')
    return data


if __name__ == '__main__':
    import os
    mode = load()['mode']
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('deployment_mode=' + mode + '\n')
