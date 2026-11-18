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


# Official and reliable sources, searched first. A bare domain also covers its subdomains
# (checked against the live API: "gov.in" returned rti.sci.gov.in and state sites such as
# gic.gujarat.gov.in), and wildcards are not documented, so none are used. "nic.in" covers
# India Code.
PREFERRED_DOMAINS = ("gov.in", "nic.in", "prsindia.org", "indiankanoon.org")

# A snippet goes into the generation prompt, so its length is capped.
MAX_SNIPPET_CHARS = 1000


def _clip(text: str) -> str:
    if len(text) <= MAX_SNIPPET_CHARS:
        return text
    return text[: MAX_SNIPPET_CHARS - 1] + "…"


class TavilyFallback:
    """General web search via Tavily (ADR 0004). Reads WEB_SEARCH_API_KEY.

    Official sources (PREFERRED_DOMAINS) are searched first. Only when they return nothing
    is the open web searched, once, so a question they do not cover is still answered.
    (An open search for the fee for an RTI application returned a YouTube video and a
    Facebook post among its first five results; the official-sites search returned only
    government pages.)
    """

    URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        *,
        max_results: int = 5,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ):
        self._key = api_key
        self._max = max_results
        self._timeout = timeout
        self._client = client or httpx.Client()

    def search(self, query: str) -> list[FallbackSource]:
        return self._search(query, PREFERRED_DOMAINS) or self._search(query)

    def _search(
        self, query: str, include_domains: tuple[str, ...] = ()
    ) -> list[FallbackSource]:
        body: dict = {"query": query, "max_results": self._max}
        if include_domains:
            body["include_domains"] = list(include_domains)
        r = self._client.post(
            self.URL,
            headers={"Authorization": f"Bearer {self._key}"},
            json=body,
            timeout=self._timeout,
        )
        r.raise_for_status()
        return [
            FallbackSource(title=x["title"], url=x["url"], snippet=_clip(x["content"]))
            for x in r.json().get("results", [])
        ]


def default_fallback() -> WebFallback:
    key = os.environ.get("WEB_SEARCH_API_KEY")
    return TavilyFallback(key) if key else NoFallback()
