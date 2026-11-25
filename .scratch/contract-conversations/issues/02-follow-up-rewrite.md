# 02: Follow-ups are rewritten before retrieval, and the rewrite never reaches the web

**What to build:** In `ContractAnswerer`, when the open conversation has earlier turns, a new `follow_up` Stage rewrites the Query plus that history into a standalone Query, in the Query's language (see `../spec.md`, "Follow-up rewrite" and "Fallback Query"; ADR 0006). The standalone Query drives Clause retrieval (including the "clause N" match), Clause grading, Corpus retrieval and grading. The user's own wording is still what gets saved, shown and passed to generation. If the rewrite fails, the original Query is used. The web Fallback's Query is built only from the user's own Queries in this conversation, never from answers or Clause text. The new Stage gets English and Hindi labels and frontend copy.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Endpoint test: a Follow-up ("what about the notice period for that?") after a turn about Clause 7 retrieves and grades with the rewritten Query, and the rewritten Query names what "that" referred to
- [ ] Endpoint test: the first Query of a conversation has no `follow_up` Stage and no rewrite call
- [ ] Endpoint test: the saved and returned turn holds the user's original wording, not the rewrite
- [ ] Endpoint test: when the earlier answer quoted a Clause, the Fallback's web Query contains none of that Clause's text and is built only from the user's Queries
- [ ] Endpoint test: a rewrite that raises falls back to the original Query, and the answer still arrives
- [ ] Endpoint test: a Hindi Follow-up gets a Hindi `follow_up` label and is rewritten in Hindi
- [ ] The Contract evaluation (`contract_evaluation.py`) gains at least two Follow-up cases, and its scores don't regress on the existing cases
- [ ] Lint, typecheck and tests pass
