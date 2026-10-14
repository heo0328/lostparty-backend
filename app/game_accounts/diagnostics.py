"""One manual siblings request; print shape only, without DB or REST writes."""
import getpass
import json
import sys
from collections import Counter
from app.game_accounts.observations import roster
from app.game_accounts.provider import LostArkProvider, ProviderUnavailable

FIELDS = ('ServerName', 'CharacterName', 'CharacterClassName', 'CharacterLevel', 'ItemAvgLevel')
SAFE_REASONS = frozenset((
    'UPSTREAM_UNAVAILABLE', 'UPSTREAM_NOT_CONFIGURED', 'UPSTREAM_RATE_LIMITED',
    'UPSTREAM_INVALID_RESPONSE', 'UPSTREAM_RESPONSE_TOO_LARGE', 'UPSTREAM_BUSY',
))


def kind(value):
    if value is None:
        return 'null'
    if type(value) is bool:
        return 'boolean'
    if type(value) is int:
        return 'integer'
    if type(value) is float:
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return 'unknown'


def check_summary(provider, character_name):
    """Caller supplies a hidden local name; no names/values reach this report."""
    report = {'check': 'siblings_summary', 'scope': 'provider_shape_only',
              'ownership_proof': False, 'roster_completeness_proven': False}
    try:
        raw = provider.siblings(character_name)
    except ProviderUnavailable as error:
        reason = error.reason if error.reason in SAFE_REASONS else 'UPSTREAM_UNAVAILABLE'
        return 1, {**report, 'status': 'failed', 'reason': reason}
    except ValueError:
        return 1, {**report, 'status': 'failed', 'reason': 'INVALID_CHARACTER_NAME'}
    report['root_type'] = kind(raw)
    if isinstance(raw, list) and len(raw) <= 200:
        report['character_count'] = len(raw)
        report['non_object_items'] = sum(not isinstance(row, dict) for row in raw)
        report['field_types'] = {
            field: dict(sorted(Counter(
                'non_object' if not isinstance(row, dict) else
                'missing' if field not in row else kind(row[field])
                for row in raw
            ).items())) for field in FIELDS
        }
    try:
        rows = roster(raw, character_name)
    except ProviderUnavailable:
        return 1, {**report, 'status': 'failed', 'reason': 'UPSTREAM_INVALID_RESPONSE'}
    report.update(status='passed', character_count=len(rows),
                  null_item_levels=sum(row['item_level'] is None for row in rows))
    return 0, report


def main():
    # Refuse getpass's non-terminal fallback, which could echo the character.
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print(json.dumps({'status': 'not_ready', 'reason': 'INTERACTIVE_TERMINAL_REQUIRED'}))
        return 2
    try:
        token = getpass.getpass('Lost Ark JWT (hidden, local only): ')
        name = getpass.getpass('Test character name (hidden, local only): ').strip()
        code, report = check_summary(LostArkProvider(token), name)
    except (EOFError, KeyboardInterrupt):
        code, report = 2, {'status': 'cancelled'}
    except Exception:
        # No exception repr/traceback: requests may include a URL/credential.
        code, report = 1, {'status': 'failed', 'reason': 'CHECK_UNAVAILABLE'}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
