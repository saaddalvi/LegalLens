# Contract conversations: several threads per Contract, with real Follow-ups

Status: ready-for-agent

Revised 2026-11-25: the Contract page is now a full-window chat. This changes the Solution, user stories 7 and 8, the new stories 15 to 17 and the UI decision below. It replaces what tickets 03 and 04 say about the page's layout, including "no chat bubbles"; those tickets are left as the record of what was built then.

## Problem Statement

On a Contract's page the user can ask questions, and the Queries and answers are saved. But it doesn't feel like a chat. The question box sits under everything, the page doesn't follow new messages, and there is no way to start fresh: every Query a user has ever asked about a Contract lives in one thread.

Follow-ups also only half work. Generation sees the last 3 turns, but the Clause search, the Corpus search, both Graders and the web Fallback see only the new Query. So "what about the notice period for that?" searches for the wrong Clauses and the wrong Provisions, gets a poor Verdict and often goes to the Fallback for nothing.

## Solution

A Contract has zero or more **Contract conversations** (see `GLOSSARY.md`). Each one starts with its first Query, is titled with it, has its own URL, and is answered with only its own earlier turns as context. The Contract brief belongs to the Contract and is shown once, on its own tab of the Contract page, whichever conversation is open.

A **Follow-up** is rewritten into a standalone Query from the conversation so far before any retrieval or grading, so the searches find what the user actually means. The web Fallback never sees that rewrite. Its Query is built from the user's own Queries in the conversation only (ADR 0006).

The Contract page is a chat (like Claude or ChatGPT) that fills the window, in LegalLens's existing colours and type (`DESIGN.md`). The user's Query sits in a bubble on the right and the answer on the left. The question box stays at the bottom, only the messages scroll, and Enter sends while Shift+Enter adds a new line. A sidebar lists the Contract's conversations, newest first, under a "New conversation" button. The Contract brief and the Contract's Clauses are on tabs beside the chat. A conversation can be deleted.

## User Stories

1. As a user, I want to ask a Follow-up like "and what does the law say about that?" and get an answer about the thing I meant, so that I can talk to LegalLens without repeating myself.
2. As a user, I want to start a new conversation about the same Contract, so that a new topic doesn't get mixed up with an old one.
3. As a user, I want a new conversation to know nothing of my other conversations, so that "that" never refers to something from a different thread.
4. As a user, I want to see all of a Contract's conversations, newest first, titled by my first question, so that I can find an old one.
5. As a user, I want each conversation to have its own address, so that refreshing, going back or bookmarking brings me to the same thread.
6. As a user opening a Contract, I want its most recent conversation to open, so that I carry on where I left off.
7. As a user, I want the Contract brief shown once for the Contract, not repeated in every conversation.
8. As a user, I want the question box to stay at the bottom and the messages to scroll to my new question, with my questions on the right and answers on the left, so that it reads like a chat.
9. As a user, I want Enter to send and Shift+Enter to add a new line.
10. As a user starting an empty conversation, I want two or three starter questions built from my Flagged clauses, so that I know what to ask.
11. As a user, I want to delete a conversation after confirming, so that I can clear out threads I no longer need.
12. As a returning user, I want the Queries I asked before this change to still be there, as my first conversation.
13. As a user, I want my Contract's private text never to reach a web search, even when I ask a Follow-up.
14. As a user on a phone, I want the conversation list, the conversation and the question box to work at phone width.
15. As a user, I want an answer's sources folded behind a button that counts them, so that the conversation stays easy to read and I can still check every claim.
16. As a user, I want to move between the chat, the Contract brief and the Contract's Clauses without losing my place or stopping an answer being written.
17. As a user, I want a Clause number to take me to that Clause and back again, so that I can check an answer against my own Contract.

## Implementation Decisions

- **Data model.** A new `contract_conversations` table: id (uuid), contract (FK, cascade on delete), title (the first Query, shortened to about 60 characters at a word boundary with an ellipsis), created at, and updated at (set on every new turn, used for "newest first"). `contract_messages` gains a `conversation_id` FK (cascade). Every read and write stays filtered by the signed-in user's id, through the Contract.
- **The brief moves to the Contract.** It is no longer a message in a conversation. The migration moves it to a new `contracts.brief` JSONB column and deletes the `brief` rows from `contract_messages`, and `add_contract` writes the column from then on. `GET /contracts/{id}` keeps returning `brief`, and no conversation's turns include it. After the migration, `contract_messages.conversation_id` is NOT NULL.
- **Migration.** One Alembic migration (`0005_…`) adds the table and column, creates one conversation per Contract that has saved Queries (titled with its first Query, dates taken from its first and last messages), points those messages at it, and handles the brief as above. Contracts with no Queries get no conversation.
- **Lazy creation.** A conversation is created by its first Query, in the same transaction as that Query and its answer. If the user leaves or the answer fails, nothing is saved and no empty conversation is left behind.
- **API.**
  - `GET /contracts/{id}` returns the brief, the Clauses and `conversations: [{id, title, created_at, updated_at}]`, newest first. It no longer returns `conversation`.
  - `GET /contracts/{id}/conversations/{cid}` returns the turns, oldest first.
  - `POST /contracts/{id}/ask/stream` takes `{query, conversation_id?}`. Without `conversation_id` it starts a new conversation. It emits a `conversation` SSE event (`{id, title}`) before the `answer` event, so the client can move to the new URL. A `conversation_id` that is not this Contract's, or not this user's, gets 404.
  - `DELETE /contracts/{id}/conversations/{cid}` returns 204.
  - `contract_evaluation.py` keeps working by starting a new conversation per case, or by passing the id it got back.
- **Follow-up rewrite.** In `ContractAnswerer`, right after the scope check (which already sees the history) and only when the conversation has earlier turns, one model call turns the Query plus the history into a standalone Query, in the Query's language. That standalone Query drives Clause retrieval (including the "clause N" match), Clause grading, Corpus retrieval and grading. The user's own wording is what gets saved, shown and passed to generation, alongside the history. The rewrite has its own Stage (`follow_up`, "Understanding your follow-up" / Hindi label). If the rewrite fails, the original Query is used rather than failing the answer.
- **Fallback Query (ADR 0006).** `search_fallback` gets a Query built from the user's own Queries in this conversation (earlier ones plus the current one, through the existing `llm.rewrite`), never from answers or Clause text. The existing endpoint test that the web Query never contains Clause text is extended to Follow-ups whose earlier answer quoted a Clause.
- **History.** `HISTORY_TURNS` goes from 3 to 10, read from the open conversation only.
- **Unchanged.** Leaving or switching mid-answer still cancels the answer and saves nothing, and a new Query in the same conversation still cancels one in flight. Every Query, Follow-up or not, counts toward the existing daily Query cap, and there is no cap on conversations. `/ask` is untouched.
- **Frontend routes.** `/contracts/[id]` redirects to its most recent conversation, or shows the empty "new conversation" state when it has none. `/contracts/[id]/conversations/[cid]` shows one conversation. "New conversation" goes to `/contracts/[id]/conversations/new`, which shows the empty state. After the first answer's `conversation` event, the URL is replaced with the real id without reloading.
- **UI.** All UI work is done with the `impeccable` skill, following `DESIGN.md` and `PRODUCT.md`.
  - There is one page per Contract, as tall as the window: a compact site header, a sidebar of conversations, and a main column with the Contract's title and the tabs **Chat**, **Brief** and **Contract**. A Contract without a brief has no Brief tab. The page opens on Chat, and choosing or starting a conversation returns to it.
  - A tab that is behind stays mounted, so it keeps its scroll position and an answer being written carries on. The chosen tab is not part of the URL.
  - Chat: the Query in a bubble on the right, the Stages and then the answer on the left with no bubble. The question box stays at the foot of the column. A saved conversation opens on its latest Query.
  - Each answer shows its Trust label, text, disclaimer and "Copy answer". Its Clause references, Citations and web sources are folded behind one "Sources" button that counts them, and says how many Citations are repealed while folded. A Provision named in the answer opens the sources on its Citation.
  - An empty conversation shows the starter questions, a way to the Contract brief with its count of Flagged clauses, and the Hindi offer.
  - A Clause link brings the Contract tab forward; the way back returns to the tab and link it came from.
  - Below 64rem the sidebar is a drawer opened from the title bar. On phones it also holds the "Ask a question" and "Browse the law" links.
  - The Contract tab shows the upload facts, the Clauses and then Delete for the Contract.

## Testing Decisions

Test behaviour at the boundaries the repo already tests: endpoint tests with fake LLM, Corpus and Fallback (`backend/tests/test_contract_conversation.py`), `Database` tests against Postgres, and component tests with Vitest and Testing Library beside each component. No tests of private helpers.

## Out of Scope

- Chat on `/ask`.
- Renaming conversations, or titles written by the model.
- Answers that keep running after the user leaves (this would need a job queue).
- Searching across conversations.
- Streaming the answer token by token from the model (the word-by-word reveal stays as it is).
