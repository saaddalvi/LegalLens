# 02: Follow-ups are rewritten before retrieval, and the rewrite never reaches the web

**What to build:** In `ContractAnswerer`, when the open conversation has earlier turns, a new `follow_up` Stage rewrites the Query plus that history into a standalone Query, in the Query's language (see `../spec.md`, "Follow-up rewrite" and "Fallback Query"; ADR 0006). The standalone Query drives Clause retrieval (including the "clause N" match), Clause grading, Corpus retrieval and grading. The user's own wording is still what gets saved, shown and passed to generation. If the rewrite fails, the original Query is used. The web Fallback's Query is built only from the user's own Queries in this conversation, never from answers or Clause text. The new Stage gets English and Hindi labels and frontend copy.

**Blocked by:** 01

**Status:** done

- [x] Endpoint test: a Follow-up ("what about the notice period for that?") after a turn about Clause 7 retrieves and grades with the rewritten Query, and the rewritten Query names what "that" referred to
- [x] Endpoint test: the first Query of a conversation has no `follow_up` Stage and no rewrite call
- [x] Endpoint test: the saved and returned turn holds the user's original wording, not the rewrite
- [x] Endpoint test: when the earlier answer quoted a Clause, the Fallback's web Query contains none of that Clause's text and is built only from the user's Queries
- [x] Endpoint test: a rewrite that raises falls back to the original Query, and the answer still arrives
- [x] Endpoint test: a Hindi Follow-up gets a Hindi `follow_up` label and is rewritten in Hindi
- [x] The Contract evaluation (`contract_evaluation.py`) gains at least two Follow-up cases, and its scores don't regress on the existing cases
- [x] Lint, typecheck and tests pass

## Comments

2026-11-25: 534 backend and 223 frontend tests pass, and typecheck and eslint are clean. `ruff check` and `ruff format --check` each still report the one finding noted on ticket 01, which predates this work.

No frontend code changed: the page shows whatever Stage label the backend sends.

Contract evaluation (`backend/evaluation/report.md`): the 12 first-Query cases scored in the earlier run are 10 correct both times; 15 of 18 cases correct overall, `follow_up` 2 of 3. One case flipped to wrong (job offer, "Can I work from home under this offer?"). It is a first Query, so the rewrite does not run for it; repeating the unchanged scope check refused it 3 of 6 times, with a Hindi reason for the English Query. Worth its own ticket.

Left as they were, from the review:
- A refusal's suggested reformulation is written by the model, which sees earlier answers. If the user submits it, it counts as their Query and can reach the web Fallback, now also on later Follow-ups. Decide whether ADR 0006 allows that.
- `search_fallback` logs a provider error with its traceback, which could echo the user's Queries (now earlier ones too), though no answer or Clause text.

