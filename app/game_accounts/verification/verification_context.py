"""Pin challenge observations, without issuing ownership or continuity evidence."""
import hashlib
import json


ASCII_UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ASCII_LOWER = 'abcdefghijklmnopqrstuvwxyz'


def ascii_name_key(value):
    """Fold input casing only; never rewrite stored canonical identity."""
    return value.translate(str.maketrans(ASCII_UPPER, ASCII_LOWER))


def resolve_input(lookup_name, rows):
    """Resolve only ASCII input casing; never normalize identity or pinned context."""
    if not isinstance(lookup_name, str) or not isinstance(rows, list):
        return None
    matches = [row.get('character_name') for row in rows if isinstance(row, dict)
               and isinstance(row.get('character_name'), str)
               and ascii_name_key(row['character_name']) == ascii_name_key(lookup_name)]
    if len(matches) != 1 or capture(matches[0], rows) is None:
        return None
    return matches[0]


def capture(lookup_name, rows):
    if not isinstance(lookup_name, str) or not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        return None
    addresses = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        pair = row.get('server_name'), row.get('character_name')
        if any(not isinstance(value, str) or not value.strip() or len(value) > 64 for value in pair):
            return None
        addresses.append(pair)
    targets = [pair for pair in addresses if pair[1] == lookup_name]
    if len(set(addresses)) != len(addresses) or len(targets) != 1:
        return None
    digest = hashlib.sha256(json.dumps(sorted(addresses), ensure_ascii=False,
                                      separators=(',', ':')).encode()).hexdigest()
    return dict(target=list(targets[0]), roster=digest)


def pending_code(snapshot, lookup_name, rows):
    expected = snapshot.get('proof_context') if isinstance(snapshot, dict) else None
    if not isinstance(expected, dict):
        # Challenges created before this boundary must restart, never gain authority.
        return 'PROVIDER_EVIDENCE_PENDING'
    actual = capture(lookup_name, rows)
    if actual is None or actual != expected:
        return 'ROSTER_EVIDENCE_PENDING'
    return None
