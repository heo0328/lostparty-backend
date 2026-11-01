#!/usr/bin/env python3
"""Deterministic disjoint file shards; every existing pytest file remains in the gate."""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from isolated_checks import SUITES


def shard(index, count):
    if not 1 <= count <= 16 or not 0 <= index < count:
        raise ValueError('invalid regression shard')
    return sorted(SUITES['all'])[index::count]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shard-index', type=int, required=True)
    parser.add_argument('--shard-count', type=int, default=8)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    tests = shard(args.shard_index, args.shard_count)
    if not tests:
        raise SystemExit('empty shard')
    return subprocess.call([sys.executable, str(SCRIPTS / 'verify_isolated.py'),
                            'all', *tests, '--docker', args.docker])


if __name__ == '__main__':
    raise SystemExit(main())
