import os
from typing import Protocol

import httpx

from .models import FallbackSource


class WebFallback(Protocol):
    def search(self, query: str) -> list[FallbackSource]: ...


class NoFallback:
    """Used when no search provider is configured: the Fallback never yields sources."""

    def search(self, query: str) -> list[FallbackSource]:
        return []


class TavilyFallback:
    """General web search via Tavily (ADR 0004). Reads WEB_SEARCH_API_KEY."""

    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, *, max_results: int = 5, timeout: float = 10.0):
        self._key = api_key
        self._max = max_results
        self._timeout = timeout

    def search(self, query: str) -> list[FallbackSource]:
        r = httpx.post(
            self.URL,
            headers={"Authorization": f"Bearer {self._key}"},
            json={"query": query, "max_results": self._max},
            timeout=self._timeout,
        )
        r.raise_for_status()
        return [
            FallbackSource(title=x["title"], url=x["url"], snippet=x["content"])
            for x in r.json().get("results", [])
        ]


def default_fallback() -> WebFallback:
    key = os.environ.get("WEB_SEARCH_API_KEY")
    return TavilyFallback(key) if key else NoFallback()
