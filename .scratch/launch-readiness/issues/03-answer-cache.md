# 03: Answer cache

**What to build:** An in-memory cache of answers, so a repeated Query (a landing-page example click, a shared `/ask?q=` link) costs no Gemini calls and returns at once. On a hit, `/ask/stream` sends only the `answer` event; the frontend already renders an answer that arrives with no Stages.

**Status:** done

- [x] Endpoint test: an identical Query, in different spacing or letter case, makes no further LLM calls
- [x] Endpoint test: a streamed hit is just the `answer` event, equal to the `/ask` body; an answer found by streaming is cached for `/ask`
- [x] Endpoint test: an answer with Trust label `none` ("cannot answer") is not cached, because it may come from a temporary outage; a refusal of an Out-of-scope query is cached
- [x] Entries expire after the TTL and the least recently used entry is evicted at the size limit
- [x] The rate limit still applies to cached answers
- [x] `create_app(cache=None)` caches nothing, so the evaluation harness and existing tests are unaffected; only the module-level `app` reads `ANSWER_CACHE_SIZE` (default 500; 0 turns it off) and `ANSWER_CACHE_TTL_SECONDS` (default 86400)

## Notes

- The ticket's first design said "do not cache Trust label `none`". Out-of-scope refusals also carry `none` since ticket 01, so the rule is "do not cache an *answer* whose label is `none`".
- Per process, in memory. A Corpus rebuild needs a backend restart anyway, which clears it.
