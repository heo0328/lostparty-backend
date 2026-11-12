"""Non-secret release contracts shared by runner and server (stdlib only)."""
import hashlib
import json
import re
from datetime import datetime, timezone

REPOSITORY = 'heo0328/lostparty-backend'
IMAGE = 'ghcr.io/' + REPOSITORY
ROOT = '/home/ubuntu/lostparty-backend'
TAG = r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
SHA = r'[0-9a-f]{40}'
DIGEST = r'sha256:[0-9a-f]{64}'


def require(value, pattern):
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise ValueError('invalid release field')
    return value


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def checksum(content):
    return hashlib.sha256(content).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def contract_names(schema):
    """Versioned artifact identities: schema1 keeps its original name meanings."""
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError('invalid manifest schema')
    return ('openapi.yaml', 'two-cycle.openapi.yaml') if schema == 1 else ('openapi.yaml', 'legacy.openapi.yaml')


def contract_probe(schema):
    """Runs in old or new images; schema1 must still hash the legacy app first."""
    contract_names(schema)
    pairs = "[('openapi.yaml', legacy), ('two-cycle.openapi.yaml', current)]" if schema == 1 else "[('openapi.yaml', current), ('legacy.openapi.yaml', legacy)]"
    return ("import json,hashlib; import app.main as entry; "
            "legacy=entry.create_legacy_app() if hasattr(entry,'create_legacy_app') else entry.app; "
            "current=entry.create_app() if hasattr(entry,'create_app') else entry.create_two_cycle_app(); "
            "print(json.dumps({n:hashlib.sha256(json.dumps(a.openapi(),sort_keys=True,separators=(',',':')).encode()).hexdigest() for n,a in " + pairs + "}))")


def validate_manifest(m):
    if set(m) != {'schema', 'repository', 'tag', 'source', 'image', 'db_revision',
                  'contract_sha256', 'compose_sha256', 'built_at_utc'}:
        raise ValueError('invalid manifest fields')
    if type(m['schema']) is not int or m['schema'] not in (1,2) or m['repository'] != REPOSITORY:
        raise ValueError('invalid manifest identity')
    require(m['tag'], TAG)
    require(m['source'], SHA)
    require(m['image'], re.escape(IMAGE) + '@' + DIGEST)
    require(m['db_revision'], r'[a-zA-Z0-9_]{1,100}')
    require(m['compose_sha256'], r'[0-9a-f]{64}')
    if not isinstance(m['contract_sha256'],dict) or set(m['contract_sha256']) != set(contract_names(m['schema'])):
        raise ValueError('invalid contracts')
    for value in m['contract_sha256'].values():
        require(value, r'[0-9a-f]{64}')
    if not isinstance(m['built_at_utc'], str) or not m['built_at_utc'].endswith('Z'):
        raise ValueError('build time must be UTC')
    datetime.fromisoformat(m['built_at_utc'].replace('Z', '+00:00'))
    return m


def validate_bundle(bundle):
    if set(bundle) != {'manifest', 'compose', 'attempt', 'run_url'}:
        raise ValueError('invalid request fields')
    validate_manifest(bundle['manifest'])
    require(bundle['attempt'], r'[0-9]+-[0-9]+')
    require(bundle['run_url'], r'https://github\.com/heo0328/lostparty-backend/actions/runs/[0-9]+/attempts/[0-9]+')
    if not isinstance(bundle['compose'], str) or len(bundle['compose']) > 65536:
        raise ValueError('invalid compose size')
    if checksum(bundle['compose'].encode()) != bundle['manifest']['compose_sha256']:
        raise ValueError('compose checksum mismatch')
    return bundle
