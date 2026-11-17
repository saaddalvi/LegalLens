# 03: Stage streaming end to end

**What to build:** While a Query is being answered, the user sees the Stages the pipeline actually goes through, in plain language and in the Query's language, then the verified answer (see `../spec.md`, "Two endpoints, one pipeline", "Event contract" and "Stages reflect the real path").

The pipeline gains an optional progress callback that is told when each Stage starts. A new `POST /ask/stream` endpoint takes the same body as `/ask` and returns Server-Sent Events: a `stage` event `{ id, label }` as each Stage starts, then one `answer` event carrying the full `AskResponse`. Stage ids are `scope_check`, `retrieval`, `grading`, `fallback`, `generation`, `citation_check` and `citation_recheck`. `fallback` appears only when the Verdict is ambiguous or incorrect, and `citation_recheck` only when the first generation had a Hallucinated citation. An Out-of-scope query emits only `scope_check` before its refusal. Labels come from a fixed English and Hindi table and never show raw Verdict words. No answer text is sent before the Citation check. `/ask` passes no callback and is unchanged.

The `/ask` page posts to `/ask/stream`, reads the response body as a stream (not `EventSource`, which cannot POST), and shows the Stage list as a polite live region: the active Stage is marked in text as well as styling, and finished Stages are marked done. When the `answer` event arrives, the existing answer card renders. HTTP errors returned before the stream starts keep the existing friendly messages. A new submission cancels any stream in flight.

**Blocked by:** 01 (Move the asking screen to `/ask`), 02 (Editorial design system, so the Stage list is built with the tokens)

**Status:** done

- [ ] Endpoint tests through `create_app` and `TestClient` with the existing fakes check the Stage sequence for each path:
  - correct Verdict
  - ambiguous Verdict
  - incorrect Verdict
  - failed Fallback
  - Hallucinated citation, then a valid one (`citation_recheck` present)
  - Hallucinated citation on both generations (blocked "cannot answer")
  - Out-of-scope query
- [ ] Endpoint test: a Hindi Query receives Hindi Stage labels
- [ ] Endpoint test: for each path, the `answer` event's payload equals the `/ask` response body for the same Query and fakes
- [ ] The existing `/ask` and evaluation tests pass unchanged
- [ ] Component tests with a `fetch` stub that streams SSE text: Stages appear in order with the active one marked, the answer card renders after the `answer` event, the disclaimer stays visible, and Citations, repealed and model-Act warnings and Fallback sources render as before
- [ ] Component tests: 429, 5xx and network failure before the stream starts show the existing messages
- [ ] Component test: submitting a new Query while one is streaming shows only the new Query's Stages and answer
- [x] Manual check against the real backend: a Query that needs the Fallback shows the "searching the web" Stage, and a Hindi Query shows Hindi Stages
- [ ] Lint, typecheck and tests (backend and frontend) pass
