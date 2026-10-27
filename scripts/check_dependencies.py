#!/usr/bin/env python3
"""Check direct requirements against hashed locks; optionally verify an image's installed set."""
import argparse
from importlib import metadata
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r'([A-Za-z0-9_.-]+)(\[[A-Za-z0-9_,.-]+\])?==([A-Za-z0-9_.+!-]+)(?: --hash=sha256:([a-f0-9]{64}))?')


def canonical(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def read_pins(path, *, hashed, include):
    result = {}
    included = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('-r '):
            included.append(line[3:])
            continue
        match = PIN.fullmatch(line)
        if not match or (hashed and not match[4]):
            raise ValueError(f'{path.name}: expected exact version and SHA256 lock' if hashed else f'{path.name}: expected exact direct requirement')
        name = canonical(match[1])
        if name in result:
            raise ValueError(f'{path.name}: duplicate package {name}')
        result[name] = (match[3], match[2] or '')
    if included != include:
        raise ValueError(f'{path.name}: unexpected requirement includes')
    if not result:
        raise ValueError(f'{path.name}: empty requirements')
    return result


def locked(root=ROOT):
    runtime = read_pins(root / 'requirements.txt', hashed=True, include=[])
    additions = read_pins(root / 'requirements-dev.txt', hashed=True, include=['requirements.txt'])
    if runtime.keys() & additions.keys():
        raise ValueError('Test lock must not override runtime packages')
    test = runtime | additions
    for filename, include, pins in (
        ('requirements.in', [], runtime), ('requirements-dev.in', ['requirements.in'], test),
    ):
        direct = read_pins(root / filename, hashed=False, include=include)
        for name, pin in direct.items():
            if pins.get(name) != pin:
                raise ValueError(f'{filename}: direct requirement differs from lock: {name}')
    return runtime, test


def verify_installed(pins):
    actual = {canonical(d.metadata['Name']): d.version for d in metadata.distributions()}
    # pip is supplied by the Python base image, not an application dependency.
    actual.pop('pip', None)
    expected = {name: pin[0] for name, pin in pins.items()}
    if actual != expected:
        changed = sorted(name for name in actual.keys() | expected.keys() if actual.get(name) != expected.get(name))
        raise ValueError('Installed package set differs from lock: ' + ', '.join(changed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', choices=('runtime', 'test'))
    args = parser.parse_args(argv)
    try:
        runtime, test = locked()
        if args.installed:
            verify_installed(runtime if args.installed == 'runtime' else test)
    except ValueError as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    print(f'PASS: dependency locks (runtime={len(runtime)}, test={len(test)}, installed={args.installed or "not checked"})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
