# 02: Rate limiting

**What to build:** Per-client request limits on `/ask` and `/ask/stream` so a public demo cannot exhaust the Gemini free tier. Requests over the limit get HTTP 429 with `Retry-After` before any work (or any stream) starts. The frontend already shows a friendly message for 429. Part of v1 ticket 12.

**Status:** done

- [x] Endpoint test: requests beyond the per-minute limit get 429 with `Retry-After`, on both endpoints, as a plain HTTP response and not an SSE event
- [x] Endpoint test: the two endpoints share one allowance; each client address is counted separately
- [x] Endpoint test: `/health` is not limited
- [x] The allowance returns after the window; the daily limit applies on its own; a rejected request does not extend the wait
- [x] `create_app(rate_limiter=None)` applies no limit, so existing tests and the evaluation harness are unaffected; only the module-level `app` reads `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_DAY` (defaults 5 and 50; both 0 turns limiting off)

## Notes

- State is per process and in memory. A single backend instance is assumed (the planned Hugging Face Space).
- The client address is `request.client.host`. Behind a proxy it is only correct when uvicorn runs with `--proxy-headers` (ticket 07).
