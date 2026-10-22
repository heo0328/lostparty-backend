#!/usr/bin/env python3
"""Compare the committed contract with FastAPI's schema in the Compose API."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    # JSON is a valid YAML subset; keep the contract in this format so the host
    # needs only the standard library, with no YAML package installation.
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=('legacy','two-cycle'),default='legacy')
    parser.add_argument('--container')
    parser.add_argument('--docker',default='docker')
    args=parser.parse_args()
    contract='two-cycle.openapi.yaml' if args.profile=='two-cycle' else 'openapi.yaml'
    expected=json.loads((root/'openapi'/contract).read_text())
    expression='create_two_cycle_app().openapi()' if args.profile=='two-cycle' else 'app.openapi()'
    command=[args.docker,'exec',args.container] if args.container else [args.docker,'compose','exec','-T','api']
    output=subprocess.check_output(command+['python','-c',
        'import json; from app.main import app,create_two_cycle_app; print(json.dumps('+expression+'))'],cwd=root,text=True)
    actual = json.loads(output)
    if expected != actual:
        render = lambda value: json.dumps(value, indent=2, sort_keys=True).splitlines(True)
        sys.stdout.writelines(difflib.unified_diff(
            render(expected), render(actual), fromfile="contract", tofile="FastAPI"))
        return 1
    print("PASS: OpenAPI contract matches FastAPI schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
