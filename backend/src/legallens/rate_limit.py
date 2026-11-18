"""Per-client request limits that protect the Gemini free tier on a public demo."""

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable

MINUTE = 60.0
DAY = 86400.0
_SWEEP_ABOVE = 10_000  # clients tracked before idle ones are dropped


class RateLimiter:
    """In-memory sliding windows, per client key: `per_minute` over 60 seconds and
    `per_day` over 24 hours. State is per process, so a restart clears it.

    Rejected requests are not recorded, so retrying early does not extend the wait.
    """

    def __init__(
        self,
        per_minute: int,
        per_day: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.per_minute = per_minute
        self.per_day = per_day
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> RateLimiter | None:
        """Reads RATE_LIMIT_PER_MINUTE (default 5) and RATE_LIMIT_PER_DAY (default 50).
        Setting both to 0 turns limiting off."""
        per_minute = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "5"))
        per_day = int(os.environ.get("RATE_LIMIT_PER_DAY", "50"))
        if per_minute <= 0 and per_day <= 0:
            return None
        return cls(per_minute, per_day)

    def check(self, key: str) -> int | None:
        """Record a request for `key`. None when allowed, else seconds until it would be."""
        now = self._clock()
        with self._lock:
            if len(self._hits) > _SWEEP_ABOVE:
                self._sweep(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= DAY:
                hits.popleft()
            waits = []
            if 0 < self.per_day <= len(hits):
                waits.append(hits[0] + DAY - now)
            if self.per_minute > 0:
                recent = [t for t in hits if now - t < MINUTE]
                if len(recent) >= self.per_minute:
                    waits.append(recent[-self.per_minute] + MINUTE - now)
            if waits:
                return max(1, math.ceil(max(waits)))
            hits.append(now)
            return None

    def _sweep(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= DAY]:
            del self._hits[key]
