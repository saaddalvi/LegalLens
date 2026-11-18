# 04: Gemini resilience

**What to build:** Make Gemini failures less visible to users. The last evaluation lost 3 of 72 runs to Gemini 503 errors after a single retry, and each one would be a "Try again" in the live app. Retry transient errors with backoff, and optionally fall over to a second model.

**Status:** done

- [x] Gemini requests are made with `max_retries=3` (the client backs off on 429 and 503), up from 1
- [x] When `GEMINI_FALLBACK_MODEL` (or the `fallback_model` argument) names a second model, a call that still fails is tried once on that model
- [x] The second model is not called while the first works; without one, a failure is raised as before; naming the same model twice is ignored
- [x] Tests use a fake chat model through `chat_factory`, so none needs network access

## Notes

- `GEMINI_FALLBACK_MODEL` is read wherever `GeminiLLM()` is built, so it also applies to `legallens.evaluate`. Leave it unset for an evaluation run if every answer should come from one model.
- Free-tier quotas are per model, so the second model also covers a model whose daily quota is spent.
