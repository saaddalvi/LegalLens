# 06: Follow-up Queries in a Contract conversation

**What to build:** Below the Contract brief, the user asks follow-up Queries and gets answers grounded in their Contract and the Corpus (see `../spec.md`, "Follow-up Queries", "Answer shape" and "Reuse the Answerer shape"). `POST /contracts/{id}/ask/stream` runs these steps through a new deep module beside `Answerer`, which uses the same `on_stage` and `cancel` interface:
1. The scope check, extended for Contract conversations. Personal advice is refused, and an unrelated Query is refused with a pointer to `/ask`.
2. Clause retrieval from pgvector for this Contract only, then the Grader on the Clauses.
3. The existing corrective loop for the Corpus (Fallback included).
4. Generation with the last few turns as context.
5. The Clause reference check and the Citation check.

When no Clause is relevant, the answer says the Contract does not address the question. Hindi Queries get Hindi answers and Hindi Stage labels, with Clause text verbatim in English. The response extends `AskResponse` with `clause_references[]`, and the Trust label gains the Contract-backed values. Each Query and answer is appended to `contract_messages`, and reopening the page shows the whole conversation. No answer cache.

**Blocked by:** 05 (Contract brief)

**Status:** ready-for-agent

- [ ] Endpoint tests, one per path:
  - a Clause-supported answer
  - a Contract-silent answer
  - a law-only answer from the Corpus
  - an ambiguous Verdict that goes to the Fallback
  - personal advice refused
  - an unrelated Query pointed to `/ask`
  - a Hindi Query (Hindi labels, English Clause text)
- [ ] Endpoint test: the previous turns reach generation, and turns from another Contract never do
- [ ] Endpoint test: the Fallback's web Query never contains Clause text
- [ ] Endpoint test: another user's Contract id gets 404
- [ ] Each Trust label value maps to frontend copy, and the landing page's Trust-label explanation covers the Contract-backed values
- [ ] Component tests: the conversation renders in order after reload, Stages stream for each Query, and a new Query cancels one in flight
- [ ] Lint, typecheck and tests pass
