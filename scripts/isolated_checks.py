#!/usr/bin/env python3
"""Container entrypoint for explicit regression sets and the current schema object."""
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
    'current': ('tests/auth/test_auth.py',
                'tests/game_accounts/analysis/test_analyzer.py',
                'tests/game_accounts/analysis/test_analysis_http.py',
                'tests/game_accounts/analysis/test_server_credentials.py',
                'tests/game_accounts/analysis/test_provider_limits.py',
                'tests/game_accounts/analysis/test_analysis_migrations.py',
                'tests/member_settings/test_member_settings.py',
                'tests/raid_rooms/common/test_current_head_compatibility.py'),
    'two-cycle': ('tests/raid_rooms/admissions/test_reapplication_history.py',
                  'tests/raid_rooms/admissions/test_beta_recruitment.py'),
}

# Existing complete pytest file set, for broad regressions or additional selections.
SUITES["all"] = tuple(str(path.relative_to(ROOT)) for path in sorted((ROOT / "tests").rglob("test_*.py")))


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
    from app.main import create_app
    actual = create_app().openapi()
    expected = json.loads((ROOT / 'openapi/openapi.yaml').read_text())
    if expected != actual:
        print('FAIL: current OpenAPI differs from generated schema', flush=True)
        return 1
    print(f"PASS: current OpenAPI full object; {len(actual['paths'])} paths", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=(*SUITES, "contracts"))
    parser.add_argument("tests", nargs="*")
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--maxfail', type=int, default=0)
    parser.add_argument('--verbose', action='store_true')
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
                      "baseline": "0038_analysis_candidates; current app; disposable PostgreSQL only"}), flush=True)
    return subprocess.call([sys.executable, "-m", "pytest", "-v" if args.verbose else "-q", "--tb=short", "--maxfail", str(args.maxfail),
        *(["--collect-only"] if args.collect_only else []), "-p", "no:cacheprovider", *selected], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
