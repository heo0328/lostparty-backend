"""Shared memo/preset wire policy. Raw values remain intact for idempotency."""
import string
import unicodedata
from app.game_accounts.support import fail

PUNCTUATION = frozenset(string.punctuation)
TEXT_POLICY = 'hangul-printable-ascii-1'
STORED_PATTERN = r'^(?! )(?!.* $)[가-힣ㄱ-ㅣ\x20-\x7e]+$(?![\s\S])'


def normalize(value, *, preset=False):
    if value is None:
        if preset:
            fail('INVALID_REQUEST', 400)
        return None
    if not isinstance(value, str):
        fail('INVALID_REQUEST', 400)
    try:
        size = len(value.encode('utf-8'))
    except UnicodeEncodeError:
        fail('INVALID_REQUEST', 400)
    if size > 4096:
        fail('REQUEST_TOO_LARGE', 413)
    normalized = unicodedata.normalize('NFC', value)
    for char in normalized:
        if not ('가' <= char <= '힣' or 'ㄱ' <= char <= 'ㅣ' or
                'A' <= char <= 'Z' or 'a' <= char <= 'z' or
                '0' <= char <= '9' or char == ' ' or char in PUNCTUATION):
            fail('INVALID_REQUEST', 400)
    normalized = normalized.strip(' ')
    if len(normalized) > 20:
        fail('APPLICATION_MEMO_TOO_LONG', 400)
    if preset and not normalized:
        fail('INVALID_REQUEST', 400)
    return normalized or None
