import json

import httpx
import pytest

from legallens.fallback import MAX_SNIPPET_CHARS, PREFERRED_DOMAINS, TavilyFallback


def tavily(responder):
    """A TavilyFallback whose HTTP calls go to `responder(body) -> list of results`,
    returning the fallback and the request bodies it sent."""
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(200, json={"results": responder(body)})

    client = httpx.Client(transport=httpx.MockTransport(handle))
    return TavilyFallback("key", client=client), sent


def result(url="https://rti.gov.in/fees", content="The fee is Rs 10."):
    return {"title": "RTI fees", "url": url, "content": content}


def test_official_sites_are_searched_first():
    fallback, sent = tavily(lambda body: [result()])
    sources = fallback.search("RTI fee")
    assert [s.url for s in sources] == ["https://rti.gov.in/fees"]
    assert len(sent) == 1
    assert sent[0]["include_domains"] == list(PREFERRED_DOMAINS)
    assert sent[0]["query"] == "RTI fee"


def test_only_bare_domains_are_listed_because_wildcards_are_undocumented():
    assert PREFERRED_DOMAINS
    assert all("*" not in d and "/" not in d for d in PREFERRED_DOMAINS)
    assert "gov.in" in PREFERRED_DOMAINS  # covers its subdomains, e.g. rti.sci.gov.in


def test_an_open_web_search_runs_once_when_official_sites_have_nothing():
    fallback, sent = tavily(
        lambda body: (
            [] if "include_domains" in body else [result("https://blog.example/rti")]
        )
    )
    sources = fallback.search("an obscure question")
    assert [s.url for s in sources] == ["https://blog.example/rti"]
    assert len(sent) == 2
    assert "include_domains" in sent[0]
    assert "include_domains" not in sent[1]


def test_nothing_found_anywhere_is_an_empty_list_after_two_searches():
    fallback, sent = tavily(lambda body: [])
    assert fallback.search("nothing") == []
    assert len(sent) == 2


def test_the_open_web_is_not_searched_when_official_sites_answer():
    fallback, sent = tavily(lambda body: [result()])
    fallback.search("RTI fee")
    assert all("include_domains" in body for body in sent)


def test_a_long_snippet_is_cut_short():
    fallback, _ = tavily(lambda body: [result(content="x" * 5000)])
    snippet = fallback.search("q")[0].snippet
    assert len(snippet) == MAX_SNIPPET_CHARS
    assert snippet.endswith("…")


def test_a_short_snippet_is_left_alone():
    fallback, _ = tavily(lambda body: [result(content="short")])
    assert fallback.search("q")[0].snippet == "short"


def test_a_provider_error_is_raised_for_the_pipeline_to_handle():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        TavilyFallback("key", client=client).search("q")


def test_the_api_key_is_sent_as_a_bearer_token():
    seen = {}

    def handle(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"results": [result()]})

    client = httpx.Client(transport=httpx.MockTransport(handle))
    TavilyFallback("secret-key", client=client).search("q")
    assert seen["auth"] == "Bearer secret-key"
