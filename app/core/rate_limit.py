import threading
import time
from collections import OrderedDict
from app.core.errors import AuthError

limits = OrderedDict()
lock = threading.Lock()


def check(key, maximum):
    current = time.monotonic()
    with lock:
        start, count = limits.get(key, (current, 0))
        if current - start >= 60:
            start, count = current, 0
        if count >= maximum:
            raise AuthError("RATE_LIMITED", 429)
        limits[key] = (start, count + 1)
        limits.move_to_end(key)
        while len(limits) > 10000:
            limits.popitem(last=False)
