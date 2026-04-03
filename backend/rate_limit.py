import time
from collections import defaultdict
from threading import Lock

_store: dict = defaultdict(list)
_lock = Lock()


def rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Returns True if the request should be blocked (limit exceeded).
    key            — unique string e.g. "login:192.168.1.1"
    max_requests   — max allowed requests in the window
    window_seconds — rolling window in seconds
    """
    now = time.time()
    with _lock:
        timestamps = _store[key]
        # Remove timestamps outside the window
        _store[key] = [t for t in timestamps if now - t < window_seconds]
        if len(_store[key]) >= max_requests:
            return True
        _store[key].append(now)
        return False


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
