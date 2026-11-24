"""Remembers recent answers, so a repeated Query (a landing-page example, a shared
`/ask?q=` link) costs no Gemini calls."""

import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable

from .models import AskResponse


def _normalise(query: str) -> str:
    """Spacing and letter case do not make a different Query."""
    return " ".join(query.split()).casefold()


class AnswerCache:
    """In-memory LRU with a time limit, per process. A restart clears it, which is also
    how a rebuilt Corpus takes effect."""

    def __init__(
        self,
        max_entries: int = 500,
        ttl_seconds: float = 86400,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, AskResponse]] = OrderedDict()
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> AnswerCache | None:
        """Reads ANSWER_CACHE_SIZE (default 500; 0 turns caching off) and
        ANSWER_CACHE_TTL_SECONDS (default 86400)."""
        size = int(os.environ.get("ANSWER_CACHE_SIZE", "500"))
        if size <= 0:
            return None
        return cls(size, float(os.environ.get("ANSWER_CACHE_TTL_SECONDS", "86400")))

    def get(self, query: str) -> AskResponse | None:
        key = _normalise(query)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            stored_at, response = entry
            if self._clock() - stored_at >= self.ttl_seconds:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return response

    def put(self, query: str, response: AskResponse) -> None:
        # A "cannot answer" may come from a temporary outage of the Fallback or of
        # Citation checking, and may succeed next time. A refusal of an Out-of-scope
        # query is settled, so it is kept.
        if response.response_type == "answer" and response.trust_label == "none":
            return
        key = _normalise(query)
        with self._lock:
            self._entries[key] = (self._clock(), response)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
