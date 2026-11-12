#!/usr/bin/env python3
"""Release-scoped test selection. Never changes production or accepts shell commands."""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from common import REPOSITORY, TAG, checksum, require, utc

ROOT = Path(__file__).resolve().parents[2]
PLAN = 'release-validation.json'
# One approved release only. This is not a general skip-tests switch.
REUSE = {
    'version': '0.1.2',
    'approved_source': 'b649ccf5bd1a03f2392a27fbda7860eb058bdd92',
    'source': 'fdd51c8e9a4d9a5eda8c5f175485965a013ee99a',
    'run_id': 41417066498,
    'attempt': 1,
    'artifact_id': 13130595536,
    'record_sha256': '81c2a4302cf43a6390022a78b36f8c8be2ae915f7438c1c254be0ca9116f8fba',
}
# Explicit developer-approved local evidence, for this release only. No claim of
# a full CI run on the new source; original scoped results remain distinguishable.
LOCAL_REUSE = {
    'version': '2.0.0',
    'approved_source': 'aa23939c9e66332dd40ff39a025f2480178191a3',
    'source': '0207d0f6b9ef8734e67bbbdc0701ce75fbdc9c8c',
    'records': {
        'docs/features/rosters/bootstrap/startup-batches-verification.json':
            'b312668d7c466701dc8d503fece1798c0d10c33d287a848d76e6401af2747fae',
        'docs/features/recruitment/membership-actions/activity-continuity-verification.json':
            'e455b708c924f72f1acc6c6f5044325491f7cd60c39d0479c4cdcd96cfca000f',
    },
}
# Issue51, Native comment1: explicit user instruction to reuse verified dev
# behavior for this release. Deployment/tool changes still receive fresh checks.
LOCAL_REUSE_220 = {
    'version': '2.2.0',
    'approved_source': '9775c1e555b767b71610b5dad35ef84b272f2a32',
    'source': '8a54c4858a593a1ab945d7a6900094bfbf2392f5',
    'records': {
        'docs/engineering/operations/records/runtime-consolidation-local-rollout.json':
            'e8bdc76464a0ce2afc427121fd85faab12bc6b4273564b396bef14a90047e2a1',
    },
}
RELEASE_220_TOOLS = {
    'release-deployment.json', 'scripts/deployment/web_release.py',
    'scripts/deployment/backup.py', 'scripts/tests/test_web_release.py',
}


RELEASE_PREPARATION = {
    'VERSION', PLAN, '.github/workflows/backend-release.yml',
    'scripts/deployment/validation.py', 'scripts/tests/test_release_validation.py',
}


def documentation(path):
    return path == 'AGENTS.md' or (path.startswith('docs/') and Path(path).suffix in ('.md', '.json'))


def check_reuse_changes(validated_changes, preparation_changes, *, extra_preparation=()):
    if any(not documentation(p) for p in validated_changes):
        raise ValueError('approved source differs from tested executable source')
    if any(not documentation(p) and p not in RELEASE_PREPARATION | set(extra_preparation) for p in preparation_changes):
        raise ValueError('release preparation changes executable source')


def verify_local_proof(proof, rule=None):
    rule = LOCAL_REUSE if rule is None else rule
    expected = {k: v for k, v in rule.items() if k != 'version'}
    if not isinstance(proof, dict) or set(proof) != set(expected) | {'record_json'}:
        raise ValueError('invalid local provenance')
    if any(proof[k] != v for k, v in expected.items()):
        raise ValueError('local provenance differs from approved release')
    raw = proof['record_json']
    if not isinstance(raw, dict) or set(raw) != set(rule['records']):
        raise ValueError('local evidence missing')
    for path, digest in rule['records'].items():
        if not isinstance(raw[path], str) or checksum(raw[path].encode()) != digest:
            raise ValueError('local evidence bytes changed')
        json.loads(raw[path])
    return proof


def local_reuse_evidence(rule=None):
    rule = LOCAL_REUSE if rule is None else rule
    for base, head in ((rule['source'], rule['approved_source']),
                       (rule['approved_source'], 'HEAD')):
        if subprocess.call(['git', 'merge-base', '--is-ancestor', base, head]):
            raise ValueError('local validation ancestry changed')
    check_reuse_changes(
        git('diff', '--name-only', '--no-renames', rule['source'], rule['approved_source']).splitlines(),
        git('diff', '--name-only', '--no-renames', rule['approved_source'], 'HEAD').splitlines(),
        extra_preparation=RELEASE_220_TOOLS if rule['version']=='2.2.0' else ())
    return verify_local_proof({k: v for k, v in rule.items() if k != 'version'} |
                              {'record_json': {p: (ROOT / p).read_text() for p in rule['records']}}, rule)


def verify_reuse_proof(proof, version=None):
    if version == LOCAL_REUSE_220['version']:
        return verify_local_proof(proof, LOCAL_REUSE_220)
    if version == LOCAL_REUSE['version']:
        return verify_local_proof(proof)
    expected = {k: v for k, v in REUSE.items() if k != 'version'}
    if not isinstance(proof, dict) or set(proof) != set(expected) | {'record_json'}:
        raise ValueError('invalid reuse provenance')
    if any(proof[k] != v for k, v in expected.items()):
        raise ValueError('reuse provenance does not match approved release')
    raw = proof['record_json']
    if not isinstance(raw, str) or len(raw.encode()) > 262144 or checksum(raw.encode()) != REUSE['record_sha256']:
        raise ValueError('prior validation bytes changed')
    data = json.loads(raw)
    checks = dict.fromkeys(('source', 'static', 'contracts', 'regression', 'docker_replace_rollback'), 'success')
    url = f"https://github.com/{REPOSITORY}/actions/runs/{REUSE['run_id']}/attempts/{REUSE['attempt']}"
    if (data.get('schema') != 1 or data.get('version') != '0.1.1' or data.get('mode') != 'full'
            or data.get('source') != REUSE['source'] or data.get('result') != 'success'
            or data.get('checks') != checks or data.get('run_url') != url
            or data.get('executed_tests') != all_tests()):
        raise ValueError('prior full validation does not cover this source')
    return proof


def reuse_evidence(plan):
    if plan['mode'] == 'reuse' and plan['version'] == LOCAL_REUSE_220['version']:
        return local_reuse_evidence(LOCAL_REUSE_220)
    if plan['mode'] == 'reuse' and plan['version'] == LOCAL_REUSE['version']:
        return local_reuse_evidence()
    if plan['mode'] != 'reuse' or plan['version'] != REUSE['version']:
        raise ValueError('reuse is limited to the approved release version')
    for base, head in ((REUSE['source'], REUSE['approved_source']), (REUSE['approved_source'], 'HEAD')):
        if subprocess.call(['git', 'merge-base', '--is-ancestor', base, head]):
            raise ValueError('approved validation ancestry changed')
    check_reuse_changes(
        git('diff', '--name-only', '--no-renames', REUSE['source'], REUSE['approved_source']).splitlines(),
        git('diff', '--name-only', '--no-renames', REUSE['approved_source'], 'HEAD').splitlines())
    from release import api
    run = api(f"/actions/runs/{REUSE['run_id']}/attempts/{REUSE['attempt']}")
    if (not run or run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('head_sha') != REUSE['source']
            or run.get('repository', {}).get('full_name') != REPOSITORY
            or run.get('path') != '.github/workflows/backend-release.yml'):
        raise ValueError('approved GitHub run is not successful')
    artifact = api(f"/actions/artifacts/{REUSE['artifact_id']}")
    if (not artifact or artifact.get('expired')
            or artifact.get('name') != f"validation-{REUSE['run_id']}-{REUSE['attempt']}"
            or artifact.get('workflow_run', {}).get('id') != REUSE['run_id']
            or artifact.get('workflow_run', {}).get('head_sha') != REUSE['source']):
        raise ValueError('approved artifact unavailable')
    archive = subprocess.check_output(['gh', 'api',
        f"repos/{REPOSITORY}/actions/artifacts/{REUSE['artifact_id']}/zip"])
    if len(archive) > 1048576:
        raise ValueError('unexpected artifact size')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        if z.namelist() != ['validation.json'] or z.getinfo('validation.json').file_size > 262144:
            raise ValueError('unexpected artifact contents')
        raw = z.read('validation.json').decode()
    return verify_reuse_proof({k: v for k, v in REUSE.items() if k != 'version'} | {'record_json': raw})


def check_results(plan):
    reuse = plan['mode'] == 'reuse'
    return {'source': 'success', 'static': 'success', 'contracts': 'reused' if reuse else 'success',
            'regression': 'reused' if reuse else 'success',
            'docker_replace_rollback': ('skipped' if plan['version'] == LOCAL_REUSE['version'] else 'reused')
            if reuse else 'success' if plan['mode'] == 'full' else 'skipped'}


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def all_tests(root=ROOT):
    return sorted(str(p.relative_to(root)) for p in (root / 'tests').rglob('test_*.py'))


def load_plan(root=ROOT):
    version = (root / 'VERSION').read_text().strip()
    require('v' + version, TAG)
    path = root / PLAN
    if not path.exists():
        return {'version': version, 'mode': 'full', 'baseline_tag': None,
                'change': 'Plan absent: complete regression', 'impact': 'unspecified',
                'reason': 'Conservative default', 'tests': [], 'plan_sha256': None}
    raw = path.read_bytes()
    plan = json.loads(raw)
    if not isinstance(plan, dict) or set(plan) != {
            'version', 'mode', 'baseline_tag', 'change', 'impact', 'reason', 'tests'}:
        raise ValueError('invalid validation plan fields')
    if plan['version'] != version or plan['mode'] not in ('selected', 'full', 'reuse'):
        raise ValueError('validation plan version or mode mismatch')
    if plan['mode'] == 'reuse' and version not in (REUSE['version'], LOCAL_REUSE['version'], LOCAL_REUSE_220['version']):
        raise ValueError('reuse is not enabled for this version')
    require(plan['baseline_tag'], TAG)
    for key in ('change', 'impact', 'reason'):
        if not isinstance(plan[key], str) or not plan[key].strip() or len(plan[key]) > 2000:
            raise ValueError('validation rationale required')
    tests = plan['tests']
    if not isinstance(tests, list) or any(not isinstance(t, str) for t in tests):
        raise ValueError('test file list required')
    if len(tests) != len(set(tests)) or any(t not in all_tests(root) or (root / t).is_symlink() for t in tests):
        raise ValueError('only existing exact test files are allowed')
    if (plan['mode'] == 'selected' and not tests) or (plan['mode'] in ('full', 'reuse') and tests):
        raise ValueError('selected needs tests; full uses all tests')
    return {**plan, 'plan_sha256': checksum(raw)}


def requires_full(path):
    p = Path(path)
    return (path.startswith(('app/auth/', 'app/core/', 'alembic/', '.github/', 'scripts/'))
            or path == 'app/main.py' or path == 'alembic.ini'
            or p.name.startswith(('Dockerfile', 'compose', 'requirements'))
            or p.name in ('pyproject.toml', 'pytest.ini', 'conftest.py', 'setup.cfg', 'setup.py', '.dockerignore')
            or (path.startswith('app/') and (p.stem.endswith('models') or
                any(word in p.stem for word in ('permission', 'authorization', 'transaction', 'policy')))))


def validate_baseline(plan):
    if plan['baseline_tag'] is None:
        return
    # Imported lazily to keep the release publisher and offline tests independent.
    from release import api
    release = api('/releases/tags/' + plan['baseline_tag'])
    if release is None or release['draft'] or release['prerelease']:
        raise ValueError('published baseline release required')
    ref = 'refs/tags/' + plan['baseline_tag']
    if subprocess.call(['git', 'merge-base', '--is-ancestor', ref + '^{commit}', 'HEAD']):
        raise ValueError('baseline must be an ancestor')
    # --no-renames includes removed/renamed protected paths in the guard.
    changed = git('diff', '--name-only', '--no-renames', ref + '^{commit}', 'HEAD').splitlines()
    if plan['mode'] == 'selected' and any(requires_full(p) for p in changed):
        raise ValueError('changed protected paths require full validation')


def selected_tests(plan):
    if plan['mode'] == 'reuse':
        return []  # Do not label the prior run's tests as newly executed.
    return plan['tests'] if plan['mode'] == 'selected' else all_tests()


def successful(verify, regression):
    return verify == 'success' and regression == 'success'


def record(plan, verify, regression):
    if not successful(verify, regression):
        raise ValueError('chosen validation jobs must succeed')
    run_id = require(os.environ['GITHUB_RUN_ID'], r'[0-9]+')
    attempt = require(os.environ['GITHUB_RUN_ATTEMPT'], r'[0-9]+')
    proof = reuse_evidence(plan) if plan['mode'] == 'reuse' else None
    data = {'schema': 2 if proof else 1, 'source': git('rev-parse', 'HEAD'),
            'version': plan['version'], 'mode': plan['mode'],
            'baseline_tag': plan['baseline_tag'], 'plan_sha256': plan['plan_sha256'],
            'change': plan['change'], 'impact': plan['impact'], 'reason': plan['reason'],
            'executed_tests': selected_tests(plan),
            'checks': check_results(plan),
            'result': 'success', 'finished_at_utc': utc(),
            'run_url': f'https://github.com/{REPOSITORY}/actions/runs/{run_id}/attempts/{attempt}'}
    if proof:
        data['reused_validation'] = proof
    return data


def verify_record(data, plan, source):
    expected = {'schema', 'source', 'version', 'mode', 'baseline_tag', 'plan_sha256',
                'change', 'impact', 'reason', 'executed_tests', 'checks', 'result', 'finished_at_utc', 'run_url'}
    reuse = plan['mode'] == 'reuse'
    if reuse:
        expected.add('reused_validation')
        if plan['version'] not in (REUSE['version'], LOCAL_REUSE['version'], LOCAL_REUSE_220['version']):
            raise ValueError('reuse is not enabled for this version')
    if not isinstance(data, dict) or set(data) != expected or data['schema'] != (2 if reuse else 1):
        raise ValueError('invalid validation record')
    for key in ('version', 'mode', 'baseline_tag', 'plan_sha256', 'change', 'impact', 'reason'):
        if data[key] != plan[key]:
            raise ValueError('validation plan evidence mismatch')
    checks = check_results(plan)
    if data['source'] != source or data['executed_tests'] != selected_tests(plan) or data['checks'] != checks or data['result'] != 'success':
        raise ValueError('successful matching validation required')
    require(data['run_url'], r'https://github\.com/heo0328/lostparty-backend/actions/runs/[0-9]+/attempts/[0-9]+')
    if reuse:
        verify_reuse_proof(data['reused_validation'], plan['version'])
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'regress', 'record'])
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    plan = load_plan()
    if args.action == 'prepare':
        validate_baseline(plan)
        if plan['mode'] == 'reuse':
            reuse_evidence(plan)
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as stream:
                stream.write('mode=' + plan['mode'] + '\n')
                stream.write('shards=' + ('[0]' if plan['mode'] in ('selected', 'reuse') else '[0,1,2,3,4,5,6,7]') + '\n')
        print(json.dumps({'mode': plan['mode'], 'tests': selected_tests(plan)}))
    elif args.action == 'regress':
        if plan['mode'] == 'reuse':
            if args.index != 0:
                raise ValueError('reuse has one provenance check, no test shards')
            proof = reuse_evidence(plan)
            print(json.dumps({'mode': 'reuse', 'new_tests_executed': 0,
                              'validated_source': proof['source'], 'prior_run': proof.get('run_id'),
                              'local_records': list(proof.get('records', {}))}))
            return 0
        if plan['mode'] == 'full':
            from regression import shard
            tests = shard(args.index, 8)
        else:
            if args.index != 0:
                raise ValueError('selected uses one job')
            tests = plan['tests']
        if not tests:
            raise ValueError('empty validation selection')
        return subprocess.call([sys.executable, str(ROOT / 'scripts/verify_isolated.py'),
                                'all', *tests, '--docker', args.docker])
    else:
        data = record(plan, os.environ['VERIFY_RESULT'], os.environ['REGRESSION_RESULT'])
        Path('dist').mkdir(exist_ok=True)
        Path('dist/validation.json').write_text(json.dumps(data, indent=2) + '\n')
        artifact = 'validation-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                stream.write('artifact=' + artifact + '\n')
        summary = {'mode': data['mode'], 'test_files': len(data['executed_tests']),
                   'result': data['result'], 'run_url': data['run_url']}
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
                stream.write('```json\n' + json.dumps(summary, indent=2) + '\n```\n')
        print(json.dumps(summary))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit('Release validation failed; check plan fields, baseline and job outcomes') from None
