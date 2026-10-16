"""Uncached server-side transport. No logging, retry, redirects or DB writes.

Member REST transport; control proof and identity binding are separate callers.
"""
import json
from time import monotonic
from threading import BoundedSemaphore
from urllib.parse import quote

import requests

ORIGIN = 'https://developer-lostark.game.onstove.com'
MAX_BODY_BYTES = 1024 * 1024
_capacity = BoundedSemaphore(2)


class ProviderUnavailable(Exception):
    def __init__(self, reason='UPSTREAM_UNAVAILABLE'):
        # Keep exception text free of request URL, credentials and response bodies.
        super().__init__(reason)
        self.reason = reason


class LostArkProvider:
    def __init__(self, token: str, transport=None, observer=None):
        if not isinstance(token, str) or not token.strip() or '\r' in token or '\n' in token:
            raise ProviderUnavailable('UPSTREAM_NOT_CONFIGURED')
        self._observer = observer
        self._token = token
        self._transport = transport or requests

    def siblings(self, character_name: str):
        return self._fetch(character_name, 'characters', '/siblings')

    def armory(self, character_name: str):
        return self._fetch(character_name, 'armories/characters', '')

    def profile(self, character_name: str):
        return self._fetch(character_name, 'armories/characters', '/profiles')

    def _fetch(self, name, prefix, suffix):
        if not isinstance(name, str) or not name.strip() or len(name) > 64 or any(ord(c) < 32 for c in name):
            raise ValueError('INVALID_CHARACTER_NAME')
        if not _capacity.acquire(blocking=False):
            raise ProviderUnavailable('UPSTREAM_BUSY')
        try:
            deadline = monotonic() + 8
            with self._transport.get(
                f'{ORIGIN}/{prefix}/{quote(name, safe="")}{suffix}',
                headers={'Accept': 'application/json', 'Authorization': f'Bearer {self._token}'},
                timeout=(3, 5), allow_redirects=False, stream=True,
            ) as response:
                if self._observer is not None:
                    self._observer(response.status_code, response.headers)
                if response.status_code != 200:
                    reason = ('LOSTARK_KEY_REJECTED' if response.status_code in (401, 403) else
                              'UPSTREAM_RATE_LIMITED' if response.status_code == 429 else 'UPSTREAM_UNAVAILABLE')
                    raise ProviderUnavailable(reason)
                media = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
                if media != 'application/json':
                    raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
                body = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if monotonic() >= deadline:
                        raise ProviderUnavailable()
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        raise ProviderUnavailable('UPSTREAM_RESPONSE_TOO_LARGE')
                    body.extend(chunk)
                try:
                    data = json.loads(body)
                except (ValueError, UnicodeError, RecursionError):
                    raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE') from None
                if not isinstance(data, (list, dict)) or not data:
                    raise ProviderUnavailable('UPSTREAM_INVALID_RESPONSE')
                return data
        except requests.RequestException:
            raise ProviderUnavailable() from None
        finally:
            _capacity.release()
