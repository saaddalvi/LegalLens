# 05: Readiness check and warm start

**What to build:** A deployed backend should say whether it can answer, and should not quietly answer from a 3-Provision sample Corpus if the built one is missing. The 1.1 GB embedding model should load at startup, not on the first user's question.

**Status:** done

- [x] `GET /ready` returns `{status, provisions, fixture}`, or 503 when the Corpus cannot load; `/health` stays a plain liveness check
- [x] `fixture` is true when the store holds only the sample fixture, including a fixture persisted by an earlier boot
- [x] `REQUIRE_CORPUS=1` makes an empty store an error instead of seeding the fixture; `/ready`, `/ask` and `/ask/stream` then return 503
- [x] `WARM_START=1` loads the Corpus and the embedding model at startup; a failure is logged and shows in `/ready`, and the server stays up
- [x] `/ask` returns a friendly 503, not a 500, when dependencies fail to load (it called `deps()` outside its `try`)

## Notes

- The fixture has 3 Provisions (the review notes said 5).
- Use `/ready` as the deployment health probe, since `/health` stays green when the Corpus is missing.
- `GOOGLE_API_KEY` is not checked here: a missing key still shows up on the first question.
