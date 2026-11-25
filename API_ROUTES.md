# LegalLens: API routes

Reference for the backend HTTP API (FastAPI, `backend/src/legallens/main.py`). Terms in **bold** (Provision, Corpus, Query, Stage, Trust label, Citation) are defined in `GLOSSARY.md`. For what happens inside `/ask`, see `DATA_FLOW.md`.

## Overview

| Method | Path | Purpose | Rate limited | Used by |
|---|---|---|---|---|
| GET | `/health` | Liveness: the process is up | No | Uptime checks |
| GET | `/ready` | Readiness: the Corpus loads | No | Deploy probe (`deploy_space.py`) |
| GET | `/acts` | List every Act with its Provision count | No | `/law` page |
| GET | `/acts/{act}` | Index of one Act's Provisions (first-line snippets) | No | `/law/[act]` page |
| GET | `/provision/{act}/{number}` | Full text of one Provision | No | `/law/[act]/[number]` page, Citation links |
| POST | `/ask` | Answer a Query, returned as one JSON body | Yes | Scripts, evaluation, simple clients |
| POST | `/ask/stream` | Answer a Query, streamed as Server-Sent Events with progress Stages | Yes | The `/ask` screen of the frontend |
| POST | `/contracts/stream` | Upload a **Contract** and get its **Contract brief**, streamed | Daily cap | `/contracts` screen |
| GET | `/contracts` | The user's Contracts, newest first | No | `/contracts` screen |
| GET | `/contracts/{id}` | One Contract: brief, Clauses and its **Contract conversations** | No | `/contracts/[id]` page |
| DELETE | `/contracts/{id}` | Delete a Contract and everything of it | No | Contract list and page |
| POST | `/contracts/{id}/ask/stream` | Answer a Query about a Contract in a Contract conversation, streamed | Yes, and daily cap | `/contracts/[id]` page |
| GET | `/contracts/{id}/conversations/{cid}` | The turns of one Contract conversation | No | `/contracts/[id]` page |
| DELETE | `/contracts/{id}/conversations/{cid}` | Delete one Contract conversation | No | Conversation list on the Contract page |
| POST | `/webhooks/clerk` | Clerk's `user.deleted`: delete the user's data | No (Svix signature) | Clerk |

- **Base URL:** `http://localhost:8000` locally; the frontend reads it from `NEXT_PUBLIC_API_URL`.
- **Auth:** `/ask*` and `/contracts*` need a Clerk session token as `Authorization: Bearer <token>` (**401** without one). `/health`, `/ready` and the routes for reading the law need none.
- **Format:** JSON, UTF-8. No versioning prefix.
- **CORS:** allowed origins come from `CORS_ORIGINS` (comma-separated, default `http://localhost:3000`); all methods and headers allowed.
- **Docs:** FastAPI serves interactive OpenAPI docs at `/docs` and the schema at `/openapi.json`.

---

## Reading the law (no Gemini calls)

These routes read only the Corpus. They are never rate limited. If the Corpus cannot load they return `503 "The service is unavailable. Please retry shortly."`.

### `GET /acts`

Lists the Acts in the Corpus, sorted by name. The counts below are illustrative; real counts depend on the built Corpus.

```json
[
  { "act": "Constitution of India", "provisions": 123 },
  { "act": "Indian Penal Code", "provisions": 456 }
]
```

### `GET /acts/{act}`

Index of one Act in statute order (`21` before `21A` before `100`). Each entry carries only the first non-empty line of the text, cut to 160 characters, not the full text.

- `act`: the Act name exactly as returned by `/acts` (URL-encode spaces, e.g. `Indian%20Penal%20Code`).
- **404** `"No such Act in the Corpus."` when the name matches nothing.

```json
{
  "act": "Constitution of India",
  "provisions": [
    { "number": "14", "chapter": "Part III", "status": "in_force", "snippet": "The State shall not deny to any person equality before the law…" }
  ]
}
```

### `GET /provision/{act}/{number}`

One Provision, with its full verbatim text.

- `act`: Act name as above. `number`: the Provision number, e.g. `302` or `21A`. The letter may be typed in either case (`21a` finds `21A`).
- **404** `"No such Provision in the Corpus."`

Response (`Provision`):

| Field | Type | Notes |
|---|---|---|
| `act` | string | |
| `chapter` | string | e.g. `Part III`, `Chapter XVI` |
| `number` | string | |
| `status` | `"in_force"` \| `"repealed"` \| `"model"` | |
| `text` | string | Verbatim English Provision text |
| `superseded_by` | string \| null | Set on a repealed Provision: its replacement |
| `supersedes` | string \| null | Set on an in-force Provision: its old equivalent |

References in `superseded_by` / `supersedes` are `"<Act> <number>"`, joined by `"; "` when there are several.

---

## Asking a question

Both routes take the same body and answer through the same `Answerer` (`backend/src/legallens/answering.py`), which runs the Corrective RAG pipeline; they differ only in how the result is delivered. The routes in `main.py` are thin adapters: the `Answerer` owns the answer cache, the Stage labels, cancellation and the request log line.

### Request body (`AskRequest`)

```json
{ "query": "What is the punishment for theft?" }
```

- `query`: required string. Leading/trailing whitespace is trimmed. Must not be blank (after trimming) and at most 2000 characters. Violations return **422**.
- English and Hindi (Devanagari) Queries are supported. The language is detected automatically: Hindi when Devanagari is most of the letters, otherwise English.

### Response (`AskResponse`)

| Field | Type | Notes |
|---|---|---|
| `response_type` | `"answer"` \| `"refusal"` | `refusal` when the Query is out of scope |
| `refusal_reason` | string \| null | Set on a refusal |
| `suggested_reformulation` | string \| null | Set on a refusal: a better way to ask |
| `answer` | string | The answer text, or the refusal message |
| `answer_language` | string | `en` or `hi` |
| `trust_label` | `"corpus"` \| `"fallback"` \| `"corpus_and_fallback"` \| `"none"` | Where the answer came from; `none` means "cannot answer", no source supports it |
| `citations` | `Citation[]` | Verified against the Corpus; `text` is always the verbatim English Provision text |
| `fallback_sources` | `{ title, url, snippet }[]` | Web sources, when the Fallback was used |

A `Citation` has `act`, `chapter`, `number`, `status`, `text`, `superseded_by`, `supersedes` (same meaning as `Provision`).

A refusal is still HTTP 200 with `response_type: "refusal"` and `trust_label: "none"`.

### `POST /ask`

Blocks until the whole pipeline finishes, then returns one `AskResponse`.

- **200**: `AskResponse`.
- **429**: rate limited (see below).
- **503** `"The service is unavailable. Please retry shortly."`: the pipeline or its dependencies (Corpus, Gemini) failed.

### `POST /ask/stream`

Same pipeline, returned as `text/event-stream` (Server-Sent Events) so the UI can show progress. Response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

Rate limiting and dependency-startup failures are returned as ordinary HTTP errors (**429** / **503**) *before* the stream starts. Failures after the stream has started arrive as an `error` event.

**Events**

| Event | Data | When |
|---|---|---|
| `stage` | `{ "id": string, "label": string }` | Each time the pipeline enters a Stage. `label` is localised to the Query's language (English or Hindi) |
| `answer` | An `AskResponse` | Final result; the stream then closes |
| `error` | `{ "stage": string \| null, "message": string }` | Answering failed (`StageFailed`); `stage` is the Stage that was running; the stream then closes |
| *(comment)* `: keepalive` | none | Sent every 10 s of silence so proxies do not idle out; ignore it |

Example:

```
event: stage
data: {"id": "scope_check", "label": "Checking your question"}

event: stage
data: {"id": "retrieval", "label": "Searching the statutes"}

event: answer
data: {"response_type": "answer", "answer": "…", "trust_label": "corpus", …}
```

**Stage ids** (in pipeline order; not all appear on every request):

| id | English label | Notes |
|---|---|---|
| `scope_check` | Checking your question | Always first; out-of-scope Queries end here with a refusal |
| `retrieval` | Searching the statutes | |
| `grading` | Checking whether the statutes answer your question | Skipped in plain-RAG mode |
| `fallback` | Searching the web for more information | Only when the Grader's Verdict is ambiguous or incorrect |
| `generation` | Writing the answer | |
| `citation_check` | Verifying citations against the statutes | |
| `citation_recheck` | (re-verification) | Only when a Citation forced a rewrite |

The exact Hindi and English labels live in `_STAGE_LABELS` in `backend/src/legallens/answering.py`.

**Client disconnect:** if the client closes the connection, the `Answerer` is cancelled and stops at its next Stage (logged as `client_gone`), so abandoned requests stop spending Gemini quota.

**Answer cache hit:** the stream contains just a single `answer` event, with no `stage` events.

---

## Contracts

Every route here needs a bearer token and a database (`DATABASE_URL`); without a database they answer **503**. Each one reads and writes only the signed-in user's data. An id that is unknown, malformed or someone else's is **404**, so its existence is not revealed.

### `POST /contracts/stream`

`multipart/form-data` with either `file` (PDF or DOCX) or `text` (pasted), not both (**422**). A file over 20 MB is **413**. Streams `stage` events (`reading`, `contract_check`, `splitting`, `indexing`, `brief`, `citation_check`, `citation_recheck`), then one of `answer` (`{ id, title, clause_count, brief }`), `refusal` (`{ reason, message }`) or `error`. Nothing is stored unless it ends in `answer`.

### `GET /contracts`, `GET /contracts/{id}`, `DELETE /contracts/{id}`

The list gives each Contract's `id`, `title`, `created_at`, `page_count` and `clause_count`. One Contract adds:

| Field | Type | Notes |
|---|---|---|
| `clauses` | `{ number, heading, text }[]` | Verbatim, in order |
| `brief` | object \| null | The Contract brief; null for a Contract uploaded before briefs existed |
| `conversations` | `{ id, title, created_at, updated_at }[]` | Its Contract conversations, the latest asked first (`updated_at`). Empty until a first Query is answered |

`title` is the conversation's first Query on one line, shortened at a word boundary to at most 60 characters with an ellipsis. The turns are not included. `DELETE` answers **204** and removes the Contract with its Clauses and all its Contract conversations.

### `POST /contracts/{id}/ask/stream`

```json
{ "query": "What is the deposit?", "conversation_id": "…" }
```

- `query`: as for `/ask`.
- `conversation_id`: optional. Without it the Query starts a new Contract conversation; with it the Query is appended to that one, and the model is shown that conversation's last 10 turns only. One that is not this Contract's is **404**. Such a Follow-up is rewritten into a standalone Query for the searches and Graders; the saved and returned `query` stays as sent.

**404**, **429** (per-minute limit, or the daily cap, marked `X-Limit-Scope: daily`) and **503** come before the stream starts. The events are:

| Event | Data | When |
|---|---|---|
| `stage` | `{ id, label }` | `scope_check`, `follow_up` (only when the conversation has earlier turns), `clause_retrieval`, `clause_grading`, `retrieval`, `grading`, `fallback`, `generation`, `citation_check`, `citation_recheck` |
| `conversation` | `{ id, title }` | Once, just before `answer`: the conversation the Query was saved to |
| `answer` | An `AskResponse` plus `clause_references` (`{ number, text }[]`) and `redirect_to_ask` (bool) | Final result; the stream then closes |
| `error` | `{ stage, message }` | Answering failed; the stream then closes |

The Query and its answer are saved together, in the transaction that creates the conversation when there is none. A Query that fails, or whose client leaves before it is answered, saves nothing and leaves no empty conversation. `trust_label` may also be `contract`, `contract_and_corpus`, `contract_and_fallback` or `contract_corpus_and_fallback`.

### `GET /contracts/{id}/conversations/{cid}`

A list of `{ query, response }`, oldest first, where `response` is the `answer` event's data. The Contract brief is not part of it.

### `DELETE /contracts/{id}/conversations/{cid}`

**204**. Removes that conversation and its turns; the Contract and its other conversations stay.

---

## Cross-cutting behaviour

### Rate limiting (`/ask`, `/ask/stream`, Contract Queries)

Per signed-in user, in-memory sliding windows: 5 requests per minute and 50 per day by default. State is per process, so a restart clears it. Rejected requests are not counted, so retrying early does not extend the wait.

Rejection is **429** `"Too many requests. Please wait a moment and try again."` with a `Retry-After` header (seconds).

New Contracts and Contract Queries also have daily caps per user (5 and 50 by default, resetting at midnight UTC), counted in the database. Every Contract Query counts, in a new conversation or an old one.

### Answer cache (`/ask`, `/ask/stream` only)

Answers to repeated Queries are remembered in memory (keyed on the normalised Query; the cache belongs to one `Answerer`, so it is never shared between pipeline modes). Cache hits skip the pipeline and are logged with `cache_hit`. Cache hits still count against the rate limit, because the limit runs first.

### Request logging

Each `/ask` and `/ask/stream` request writes one structured log line. It holds per-Stage timings, Grader and Citation-check outcomes and how the request ended, and never the Query or the answer, only the Query's length and language (Queries can describe people's personal situations). See `request_log.py`.

### Error summary

| Status | Where | Meaning |
|---|---|---|
| 401 | `/ask*`, `/contracts*` | Missing or invalid bearer token |
| 404 | `/acts/{act}`, `/provision/...` | Act or Provision not in the Corpus |
| 404 | `/contracts/{id}...` | No such Contract or Contract conversation for this user |
| 422 | `/ask`, `/ask/stream` | Invalid body: missing, blank or over-long `query` |
| 429 | `/ask*`, `POST /contracts*` | Rate limited or daily cap reached; honour `Retry-After` |
| 503 | `/ready`, browse routes, `/ask`, pre-stream `/ask/stream` | Corpus or LLM unavailable |

---

## Configuration (environment variables)

| Variable | Default | Effect on the API |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins, comma-separated |
| `RATE_LIMIT_PER_MINUTE` | `5` | Per-user limit on `/ask`, `/ask/stream` and Contract Queries; set both limits to `0` to disable |
| `RATE_LIMIT_PER_DAY` | `50` | Per-user daily limit |
| `DAILY_CONTRACT_CAP`, `DAILY_QUERY_CAP` | `5`, `50` | New Contracts and Contract Queries per user per UTC day; `0` disables |
| `CLERK_ISSUER` | none | Verifies bearer tokens; without it every authenticated route refuses |
| `DATABASE_URL` | none | Postgres for Contracts; run `python -m legallens.migrate` against it |
| `ANSWER_CACHE_SIZE` | `500` | Cached answers; `0` disables the cache |
| `ANSWER_CACHE_TTL_SECONDS` | `86400` | Cache lifetime |
| `CHROMA_PATH` | `backend/data/chroma` | Where the Corpus store lives |
| `REQUIRE_CORPUS` | unset | `1`: fail instead of seeding the 3-Provision sample Corpus when the store is empty |
| `WARM_START` | unset | `1`: load the Corpus and embedding model at startup, so the first question is fast |
| `GOOGLE_API_KEY` | none | Gemini access for `/ask*` |
| `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL` | see `.env.example` | Primary and backup Gemini models |
| `WEB_SEARCH_API_KEY` | none | Web Fallback search (Tavily) |

---

## Health and readiness

- `GET /health` → `200 {"status": "ok"}`. Only says the process is up; touches nothing else.
- `GET /ready` → `200 {"status": "ready", "provisions": <int>, "fixture": <bool>}` once the Corpus loads. `fixture: true` means only the 3-Provision sample is loaded, which signals a deployment that lost its built Corpus. **503** `"The service is not ready."` if the Corpus fails to load (including a failed `WARM_START`).

---

## Examples

```bash
curl localhost:8000/acts
curl "localhost:8000/acts/Constitution%20of%20India"
curl "localhost:8000/provision/Constitution%20of%20India/21A"

curl -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query": "What does Article 21 protect?"}'

# -N disables curl's buffering so events print as they arrive
curl -N -X POST localhost:8000/ask/stream \
  -H 'Content-Type: application/json' \
  -d '{"query": "What does Article 21 protect?"}'
```

## Frontend usage

| Frontend file | Calls |
|---|---|
| `frontend/src/app/ask/ask-screen.tsx` | `POST /ask/stream` |
| `frontend/src/app/contracts/[id]/contract-view.tsx` | `GET /contracts/{id}` |
| `frontend/src/app/contracts/[id]/contract-conversation.tsx` | `GET .../conversations/{cid}` for the open conversation, `POST /contracts/{id}/ask/stream` |
| `frontend/src/app/contracts/confirm-delete.tsx` | `DELETE /contracts/{id}`, `DELETE .../conversations/{cid}` |
| `frontend/src/lib/law-api.ts` | `GET /acts`, `GET /acts/{act}`, `GET /provision/{act}/{number}` (server-side, cached for hours; a 404 is treated as "not found" and any other failure throws, uncached) |
