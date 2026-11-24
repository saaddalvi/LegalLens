"""Per-user request limits that protect the Gemini free tier on a public demo."""

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

MINUTE = 60.0
DAY = 86400.0
_SWEEP_ABOVE = 10_000  # clients tracked before idle ones are dropped


class RateLimiter:
    """In-memory sliding windows, per key (the signed-in user's id): `per_minute` over 60 seconds and
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


class DailyCaps:
    """How many new Contracts and Contract-conversation Queries one user may make per UTC day.
    A cap of 0 turns that cap off. The counts live in the database; this holds the limits and
    the clock."""

    def __init__(
        self,
        contracts: int,
        queries: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.contracts = contracts
        self.queries = queries
        self._clock = clock

    @classmethod
    def from_env(cls) -> DailyCaps:
        """Reads DAILY_CONTRACT_CAP (default 5) and DAILY_QUERY_CAP (default 50)."""
        return cls(
            int(os.environ.get("DAILY_CONTRACT_CAP", "5")),
            int(os.environ.get("DAILY_QUERY_CAP", "50")),
        )

    def limit(self, kind: str) -> int:
        """The cap for "contracts" or "queries"; 0 means no cap."""
        return {"contracts": self.contracts, "queries": self.queries}[kind]

    def today(self) -> date:
        return self._clock().astimezone(UTC).date()

    def seconds_until_reset(self) -> int:
        now = self._clock().astimezone(UTC)
        midnight = datetime.combine(
            now.date() + timedelta(days=1), datetime.min.time(), UTC
        )
        return max(1, math.ceil((midnight - now).total_seconds()))
