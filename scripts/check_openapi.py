#!/usr/bin/env python3
"""Compare the committed contract with FastAPI's schema in the Compose API."""
import difflib
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    # JSON is a valid YAML subset; keep the contract in this format so the host
    # needs only the standard library, with no YAML package installation.
    expected = json.loads((root / "openapi/openapi.yaml").read_text())
    output = subprocess.check_output(
        ["docker", "compose", "exec", "-T", "api", "python", "-c",
         "import json; from app.main import app; print(json.dumps(app.openapi()))"],
        cwd=root, text=True,
    )
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
