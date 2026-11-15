from typing import Protocol

from .models import FallbackSource


class WebFallback(Protocol):
    def search(self, query: str) -> list[FallbackSource]: ...


class NoFallback:
    """Placeholder until the CRAG loop (ticket 05) wires a real search provider."""

    def search(self, query: str) -> list[FallbackSource]:
        return []
