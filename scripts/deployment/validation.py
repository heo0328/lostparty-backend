#!/usr/bin/env python3
"""Release-scoped test selection. Never changes production or accepts shell commands."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from common import REPOSITORY, TAG, checksum, require, utc

ROOT = Path(__file__).resolve().parents[2]
PLAN = 'release-validation.json'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def all_tests(root=ROOT):
    return sorted(str(p.relative_to(root)) for p in (root / 'tests').glob('test_*.py'))


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
    if plan['version'] != version or plan['mode'] not in ('selected', 'full'):
        raise ValueError('validation plan version or mode mismatch')
    require(plan['baseline_tag'], TAG)
    for key in ('change', 'impact', 'reason'):
        if not isinstance(plan[key], str) or not plan[key].strip() or len(plan[key]) > 2000:
            raise ValueError('validation rationale required')
    tests = plan['tests']
    if not isinstance(tests, list) or any(not isinstance(t, str) for t in tests):
        raise ValueError('test file list required')
    if len(tests) != len(set(tests)) or any(t not in all_tests(root) or (root / t).is_symlink() for t in tests):
        raise ValueError('only existing exact test files are allowed')
    if (plan['mode'] == 'selected' and not tests) or (plan['mode'] == 'full' and tests):
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
    return plan['tests'] if plan['mode'] == 'selected' else all_tests()


def successful(verify, regression):
    return verify == 'success' and regression == 'success'


def record(plan, verify, regression):
    if not successful(verify, regression):
        raise ValueError('chosen validation jobs must succeed')
    run_id = require(os.environ['GITHUB_RUN_ID'], r'[0-9]+')
    attempt = require(os.environ['GITHUB_RUN_ATTEMPT'], r'[0-9]+')
    return {'schema': 1, 'source': git('rev-parse', 'HEAD'),
            'version': plan['version'], 'mode': plan['mode'],
            'baseline_tag': plan['baseline_tag'], 'plan_sha256': plan['plan_sha256'],
            'change': plan['change'], 'impact': plan['impact'], 'reason': plan['reason'],
            'executed_tests': selected_tests(plan),
            'checks': {'source': 'success', 'static': 'success', 'contracts': 'success',
                       'regression': 'success',
                       'docker_replace_rollback': 'success' if plan['mode'] == 'full' else 'skipped'},
            'result': 'success', 'finished_at_utc': utc(),
            'run_url': f'https://github.com/{REPOSITORY}/actions/runs/{run_id}/attempts/{attempt}'}


def verify_record(data, plan, source):
    expected = {'schema', 'source', 'version', 'mode', 'baseline_tag', 'plan_sha256',
                'change', 'impact', 'reason', 'executed_tests', 'checks', 'result', 'finished_at_utc', 'run_url'}
    if not isinstance(data, dict) or set(data) != expected or data['schema'] != 1:
        raise ValueError('invalid validation record')
    for key in ('version', 'mode', 'baseline_tag', 'plan_sha256', 'change', 'impact', 'reason'):
        if data[key] != plan[key]:
            raise ValueError('validation plan evidence mismatch')
    checks = {'source': 'success', 'static': 'success', 'contracts': 'success', 'regression': 'success',
              'docker_replace_rollback': 'success' if plan['mode'] == 'full' else 'skipped'}
    if data['source'] != source or data['executed_tests'] != selected_tests(plan) or data['checks'] != checks or data['result'] != 'success':
        raise ValueError('successful matching validation required')
    require(data['run_url'], r'https://github\.com/heo0328/lostparty-backend/actions/runs/[0-9]+/attempts/[0-9]+')
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
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a') as stream:
                stream.write('mode=' + plan['mode'] + '\n')
                stream.write('shards=' + ('[0]' if plan['mode'] == 'selected' else '[0,1,2,3,4,5,6,7]') + '\n')
        print(json.dumps({'mode': plan['mode'], 'tests': selected_tests(plan)}))
    elif args.action == 'regress':
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
