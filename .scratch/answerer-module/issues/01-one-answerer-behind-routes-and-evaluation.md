# 01: One Answerer behind /ask, /ask/stream and the evaluation

**What to build:** A deep `Answerer` module in `backend/src/legallens/answering.py`. It owns answering a Query: the answer cache, the corrective loop, Stages with their labels, cancellation, and the request log line. `/ask`, `/ask/stream` and the evaluation become thin adapters over it. This is a refactor: answers, Trust labels, Citations, Stages and HTTP behaviour all stay the same.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

## Why

The work of answering a Query is split across the two routes in `main.py`. Each one repeats the cache lookup, dependency loading, the `answer_query` call, the cache write and `RequestLog.finish`. The pipeline reports back through two side channels: an `on_stage` callback and a mutable `trace` dict.

The stream cancels the pipeline by raising `_ClientGone` from inside `on_stage`. That works only while no Stage call ends up inside an `except Exception` block in the pipeline.

The evaluation drives the app through `TestClient` and wraps the LLM in `_GenerationRecorder` to recover a fact the pipeline already records (`citation_recheck`). That wrapper depends on the order of the calls. Finally, `answer_query` is never tested directly: every CRAG test goes through FastAPI.

## Decisions

The interface:

- `Answerer` is built with the Corpus, the LLM, the WebFallback, the mode (CRAG or plain RAG) and an optional `AnswerCache`. The mode is fixed per instance, and the cache key no longer includes it.
- `answer(query, on_stage, cancel)` returns an `Answered`: the `AskResponse` plus its Decisions (see GLOSSARY.md). The Decisions are the Grader score, the Verdict, the Fallback source count, `citation_recheck` and `citation_blocked`. The `trace` parameter goes away.
- `on_stage` receives each Stage with its `id` and its `label` already in the Query's language. The module detects the language once, and `STAGE_LABELS` becomes private to it.

Inside the module:

- **Cancellation:** `cancel` is a signal the module checks at every Stage boundary. When it is set, the module raises its own `Cancelled`, which the pipeline's error handling must let through.
- **Failures:** a failure in the corrective loop is logged with outcome `error` and raised as one typed error that names the Stage that failed. `Cancelled` is logged as `client_gone`.
- **The log line:** the module writes it for every outcome. The caller passes only a label (`ask` / `ask_stream`) for the `endpoint` field.
- **Cache hits:** no Stages are emitted, and the record has `cache_hit=true`. The answer is the cached response.
- **`answer_query`:** the routing in `pipeline.py` stays as the module's implementation and becomes an internal seam. Nothing outside `answering.py` calls `answer_query`.

Outside the module:

- **Building dependencies:** `create_app` still builds the dependencies lazily and passes them in. A failure to build them still gives a 503 before any stream starts.
- **Rate limit:** it stays in HTTP (it works per client address).
- **`/ask`:** turns the typed failure into a 503.
- **`/ask/stream`:** keeps the thread, the queue and the keepalive. It turns a client disconnect into the cancel signal and the typed failure into an `error` frame with `stage` and `message`.
- **The evaluation:** builds two `Answerer`s (plain RAG and CRAG) with no cache and calls them directly. It reads `hallucinated_before_block` from `citation_recheck` in the Decisions. That is the same value `_GenerationRecorder.first_hallucinated` gives today: both are true only when the first generation for a Query with Provisions cited a Provision missing from the Corpus.
- **`citation_validity`:** stays, labelled as a guard that is 100% by construction. The README already says so (line 168). Make sure the report row says the same.

The name: `Answerer` is an architecture name and stays out of the glossary. "Decisions" has a glossary entry under the corrective loop.

## Acceptance criteria

- [ ] `answering.py` exposes `Answerer`, `Answered`, the typed Stage failure and `Cancelled`. `main.py` and `evaluation.py` use nothing else from the corrective loop.
- [ ] Tests at the `Answerer` interface cover:
  - the Verdict routing (correct, ambiguous, incorrect, and a failed or empty Fallback)
  - plain RAG mode
  - refusal of an Out-of-scope query
  - Hindi answers and Stage labels
  - Citation recheck and block
  - cache hit and cache skip (a "cannot answer" is not cached)
  - cancellation at a Stage boundary, including inside the Fallback Stage
  - the failed Stage on the typed failure
  - the Decisions returned for each path

  The tests use a real `Corpus` on `tmp_path` with `FakeEmbedder`, and fakes for the LLM and the Fallback.
- [ ] The HTTP tests cover only what the routes do themselves:
  - 429 before any work
  - 503 before a stream starts
  - 503 on `/ask` failure
  - SSE framing and keepalive
  - the `error` frame carrying `stage`
  - a disconnect cancelling the work
  - a cache hit giving a single answer frame
- [ ] `_GenerationRecorder`, `_ask` and the evaluation's `TestClient` are deleted. `test_evaluation.py` passes against the direct calls.
- [ ] The `trace` parameter, `_ClientGone` and the route-level `RequestLog` calls are gone. The request log line has the same fields as before (`test_request_log.py` moves to the `Answerer` interface where it checks record content).
- [ ] The shared fakes (`FakeEmbedder`, `GradingStub`, `FakeLLM`, `FakeFallback`, `ART_21`, `IPC_302`) move from `test_ask.py` to `tests/conftest.py`. No test file imports from another test file.
- [ ] Old tests that checked the corrective loop through HTTP are deleted once their `Answerer` equivalents exist (replace, don't layer).
- [ ] The whole backend suite and the frontend suite pass. No change to the SSE event shapes.

## Delivery

Test-first, in four commits:

1. `Answerer` and its tests (the routes are unchanged).
2. Both routes moved onto it, and the HTTP tests shrunk.
3. The evaluation moved onto it, and `_GenerationRecorder` deleted.
4. Fakes moved to `conftest.py`, and the old tests deleted.

## Notes

- Don't rerun the evaluation: the behaviour is unchanged, and a run costs Gemini quota. Rerun it only if the user asks.
- Turning the pipeline into a generator of events was rejected. The SSE route still needs a thread so it can send keepalives during a blocking Gemini call, and a generator can't safely be closed from another thread.
- Keeping `answer_query` as a second public interface was rejected. Two interfaces over the same behaviour leave tests at whichever one someone happened to pick.
- From the architecture review of 2026-11-24 (candidate 1). Related candidate 3 (a typed Stage stream client on the frontend) reads the frames this ticket's SSE adapter produces. It is out of scope here.
