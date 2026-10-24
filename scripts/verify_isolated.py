#!/usr/bin/env python3
"""Build/run disposable verification without using the development Compose project."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from isolated_checks import SUITES, selected_tests


def docker_environment():
    # Avoid inheriting Compose file/project/service overrides. Never read .env.
    env = {key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")}
    env["COMPOSE_DISABLE_ENV_FILE"] = "1"
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("static", "contracts", *SUITES))
    parser.add_argument("tests", nargs="*", help="Optional exact pytest nodes within the named regression set")
    parser.add_argument("--docker", default="docker", help="Docker executable, e.g. docker.exe in WSL")
    args = parser.parse_args(argv)
    if args.suite not in SUITES and args.tests:
        parser.error("This suite does not accept test selections")
    if args.suite in SUITES:
        try:
            selected_tests(args.suite, args.tests)
        except ValueError as error:
            parser.error(str(error))
    if args.suite == "static":
        for command in (
            [sys.executable, "scripts/check_documentation.py"],
            [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-v"],
        ):
            status = subprocess.call(command, cwd=ROOT)
            if status:
                return status
        return 0
    project = "lostparty-check-" + uuid.uuid4().hex[:12]
    base = [args.docker, "compose", "--project-name", project,
            "--file", str(ROOT / "compose.test.yaml")]
    env = docker_environment()
    print(f"Isolated project: {project}; suite: {args.suite}; temporary PostgreSQL only", flush=True)
    status = 1
    try:
        subprocess.run([*base, "build", "tests"], cwd=ROOT, env=env, check=True)
        if args.suite != "contracts":
            subprocess.run([*base, "up", "-d", "--wait", "--wait-timeout", "90", "test-db"],
                           cwd=ROOT, env=env, check=True)
        status = subprocess.call([*base, "run", "--rm", "--no-deps", "tests",
                                  "python", "scripts/isolated_checks.py", args.suite, *args.tests], cwd=ROOT, env=env)
    except subprocess.CalledProcessError as error:
        status = error.returncode or 1
    except KeyboardInterrupt:
        status = 130
    except OSError:
        print("Unable to execute Docker; check the selected executable and daemon access", file=sys.stderr)
    finally:
        # Only the UUID-named project created above. No volumes exist to delete.
        # Never mask test failure with cleanup success.
        try:
            cleanup = subprocess.call([*base, "down", "--remove-orphans", "--timeout", "10"], cwd=ROOT, env=env)
        except (OSError, KeyboardInterrupt):
            cleanup = 1
        if cleanup:
            print(f"Cleanup failed; inspect project {project} before retrying", file=sys.stderr)
            status = status or 1
    print(f"Verification finished: suite={args.suite}, exit={status}, project={project}", flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
