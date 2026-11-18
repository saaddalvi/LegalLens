# 04: Mid-stream failure and Try again

**What to build:** When answering fails partway, for example on a Gemini 503 after a few Stages, the user sees which Stage failed, the friendly "service unavailable" message, and a Try again button that resubmits the same Query (see `../spec.md`, "Failure display"). If the pipeline raises, `/ask/stream` sends an `error` event `{ stage, message }` naming the Stage that was running, using the existing 503 wording, and then ends the stream. The frontend handles that event, and also a stream that drops without an `answer` event, by marking the running Stage failed.

**Blocked by:** 03 (Stage streaming end to end)

**Status:** done (landed in `ee03978`)

- [x] Endpoint test: an LLM that raises during generation produces `stage` events up to `generation`, then an `error` event naming `generation`, and the stream ends
- [x] Endpoint test: an LLM that raises during the scope check produces an `error` event naming `scope_check`
- [x] `/ask` still returns HTTP 503 on the same failures (existing tests pass)
- [x] Component test: after an `error` event, the running Stage is shown as failed, the friendly message is shown, and Try again resubmits the same Query
- [x] Component test: a stream that ends without an `answer` or `error` event is treated as a failure of the running Stage
- [x] The Try again button is keyboard reachable and the failure is announced to screen readers
- [x] Lint, typecheck and tests (backend and frontend) pass
