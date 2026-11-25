# 01: Several Contract conversations per Contract: data model, migration and API

**What to build:** Contracts can have zero or more Contract conversations (see `../spec.md`, "Data model", "The brief moves to the Contract", "Migration", "Lazy creation" and "API"). Add `contract_conversations` and `contract_messages.conversation_id` with one Alembic migration that moves existing saved Queries into a first conversation per Contract. Take the brief out of conversation history. `POST /contracts/{id}/ask/stream` accepts an optional `conversation_id`, creates the conversation with its first Query when it is missing, and emits a `conversation` SSE event. Add `GET` and `DELETE /contracts/{id}/conversations/{cid}`, and have `GET /contracts/{id}` list conversations newest first. `ContractAnswerer` reads history from the open conversation only, and `HISTORY_TURNS` becomes 10. Keep `contract_evaluation.py` working.

The frontend change that goes with this is the minimum needed to keep the page working: it passes and receives `conversation_id` and shows the most recent conversation. The list, URLs and layout come in 03 and 04.

**Blocked by:** none

**Status:** done

- [x] The brief moves to a `contracts.brief` JSONB column, its `contract_messages` rows are deleted, and `conversation_id` ends up NOT NULL
- [x] Migration test (upgrade the test Postgres to `0004` with `migrate.upgrade(url, "0004")`, seed rows the old way, then upgrade to head): a Contract with saved Queries gets one conversation titled with its first Query, containing all its turns in order. A Contract with none gets no conversation. The brief is still returned by `GET /contracts/{id}`.
- [x] Endpoint test: a Query without `conversation_id` creates a conversation (title shortened to about 60 characters at a word boundary) and emits `conversation` before `answer`
- [x] Endpoint test: a Query with `conversation_id` appends to it, and generation sees only that conversation's turns (up to 10), never another conversation's or the brief
- [x] Endpoint test: a cancelled or failed first Query leaves no conversation behind
- [x] Endpoint test: another Contract's or another user's `conversation_id` gets 404, for ask, get and delete
- [x] Endpoint test: deleting a conversation removes its messages and leaves the Contract and its other conversations
- [x] Endpoint test: deleting a Contract removes all its conversations
- [x] `GLOSSARY.md` already matches. Update `API_ROUTES.md` and `DATA_FLOW.md` for the new routes and table.
- [x] Lint, typecheck and tests pass

## Comments

2026-11-25: Implemented in commit 31c6bb6. 524 backend and 222 frontend tests pass on the working tree, and typecheck and eslint are clean. `ruff check` still reports one issue in `llm.py` and `ruff format --check` one file, `test_llm_prompt.py`; both predate this ticket. The `API_ROUTES.md` and `DATA_FLOW.md` updates were committed in 8537ff0.

For ticket 02: `DATA_FLOW.md` section 6 says the searches, Graders and Fallback see the new Query alone. Update it when the Follow-up rewrite lands.

