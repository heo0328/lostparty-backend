#!/usr/bin/env python3
"""Container entrypoint for explicit regression sets and both schema objects."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# These are named regression sets, not a claim that every project test ran.
SUITES = {
    "legacy": (
        "tests/test_auth.py", "tests/test_game_accounts.py",
        "tests/test_account_bootstrap.py", "tests/test_member_settings.py",
        "tests/test_lostark_keys.py", "tests/test_groups_http.py",
        "tests/test_raid_room_http.py",
    ),
    "two-cycle": (
        "tests/test_beta_recruitment.py", "tests/test_departure_search_minutes.py",
        "tests/test_active_room_usage.py", "tests/test_coordination_wait.py",
        "tests/test_application_composition.py", "tests/test_admission_eligibility.py",
        "tests/test_application_display.py", "tests/test_application_display_references.py",
        "tests/test_application_item_level.py", "tests/test_membership_actions.py",
        "tests/test_atomic_members.py", "tests/test_completion_corrections.py",
    ),
}

# Existing complete pytest file set, for broad regressions or additional selections.
SUITES["all"] = tuple(str(path.relative_to(ROOT)) for path in sorted((ROOT / "tests").glob("test_*.py")))


def require_test_environment():
    value = urlsplit(os.environ.get("DATABASE_URL", ""))
    if not (
        os.environ.get("LOSTPARTY_ISOLATED_TEST") == "1"
        and value.scheme == "postgresql+psycopg"
        and value.hostname == "test-db" and value.port in (None, 5432)
        and value.username == "postgres" and value.password == "test-only-password"
        and value.path == "/lostparty_test" and not value.query and not value.fragment
        and os.environ.get("AUTH_SECRET_DIR") == "/tmp/auth-test-keys"
        and os.environ.get("OWNERSHIP_WORKER_ENABLED") == "0"
        and os.environ.get("RECRUITMENT_WORKER_ENABLED") == "0"
    ):
        raise ValueError("Refusing verification outside the disposable test environment")


def selected_tests(suite, requested):
    selected = requested or list(SUITES[suite])
    for node in selected:
        path = node.split("::", 1)[0]
        if path not in SUITES[suite] or not (ROOT / path).is_file():
            raise ValueError("Test selection must belong to the selected regression set")
    return selected


def contracts():
    from app.main import app, create_two_cycle_app
    for name, application in (("openapi.yaml", app), ("two-cycle.openapi.yaml", create_two_cycle_app())):
        expected = json.loads((ROOT / "openapi" / name).read_text())
        actual = application.openapi()
        if expected != actual:
            print(f"FAIL: {name} differs from generated OpenAPI", flush=True)
            return 1
        operations = sum(method in ("get", "post", "put", "patch", "delete")
                         for path in actual["paths"].values() for method in path)
        print(f"PASS: {name}, {len(actual['paths'])} paths, {operations} operations (full object)", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=(*SUITES, "contracts"))
    parser.add_argument("tests", nargs="*")
    args = parser.parse_args(argv)
    try:
        require_test_environment()
        if args.suite == "contracts":
            if args.tests:
                raise ValueError("Contract verification does not accept test selections")
            return contracts()
        selected = selected_tests(args.suite, args.tests)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"suite": args.suite, "selection": selected,
                      "baseline": "0023; per-test fixtures migrate disposable app-role databases as needed"}), flush=True)
    return subprocess.call([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *selected], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
