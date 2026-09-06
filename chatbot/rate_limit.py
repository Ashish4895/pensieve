import time
from collections import defaultdict, deque

from django.conf import settings


_hits: dict[str, deque[float]] = defaultdict(deque)


def allow(ip: str) -> bool:
    limit = int(getattr(settings, "CHAT_RATE_LIMIT", 30))
    now = time.time()
    hits = _hits[ip]

    while hits and now - hits[0] > 3600:
        hits.popleft()

    if len(hits) >= limit:
        return False

    hits.append(now)
    return True
