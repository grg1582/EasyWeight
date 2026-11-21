"""Limits how often something can be tried, like signing in.

Kept in memory, which is enough for one server process. (Several servers would
share the count through the database or Redis instead.)
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, attempts: int, seconds: float, clock=time.monotonic):
        self.attempts = attempts
        self.seconds = seconds
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        """Count one attempt. Raises 429 once there were too many lately"""
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.seconds:
                hits.popleft()
            if len(hits) >= self.attempts:
                retry = int(hits[0] + self.seconds - now) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Too many attempts. Try again in {retry} seconds",
                    headers={"Retry-After": str(retry)},
                )
            hits.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


def client_address(request: Request) -> str:
    # Behind a host's proxy, uvicorn's --proxy-headers puts the real address here
    return request.client.host if request.client else "unknown"
