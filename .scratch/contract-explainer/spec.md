# Contract explainer: upload a Contract, read its brief, ask about it

Status: ready-for-agent

## Problem Statement

LegalLens answers general questions about Indian law, but the legal text a layperson most often has in front of them is their own Contract: a rent agreement, a job offer, an NDA, a loan agreement. They want to know what it says, what each side must do, and whether anything in it differs from what the law provides. Today they would have to paste pieces into `/ask` one at a time. LegalLens forgets each question, cannot quote their Contract back to them, and refuses "should I sign this?" with no help on what it *can* tell them.

LegalLens also has no users and stores nothing. Every Query is anonymous and answered on its own. Explaining someone's Contract means holding private text (names, addresses, salaries, ID numbers) for that person alone, and keeping a Contract conversation going over several Queries.

## Solution

Signed-in users (Clerk) can upload an English Contract (PDF, including scans; DOCX; or pasted text, up to about 30 pages) at `/contracts`. While it is processed, the user sees the Stages, as on `/ask`. The result is a **Contract brief**: who the parties are, what the Contract is for, its key terms (money, duration, renewal, termination, notice), what each party must do, and its **Flagged clauses**. A Flagged clause is one that differs from what Indian law provides, shown with a **Clause reference** (its verbatim text) and at least one verified Citation.

The brief opens the Contract's **Contract conversation**. The user asks follow-up Queries in English or Hindi and gets answers grounded in two sources: the Contract's Clauses (retrieved, graded, quoted verbatim and checked) and the Corpus (the existing corrective loop with the web Fallback). LegalLens never says whether to sign. It explains, quotes and cites. When the Contract is silent on something, it says so.

Only the extracted text and the Contract conversation are stored, in Postgres on Neon, with Clause vectors in pgvector (ADR 0005). The original file is discarded. Users can delete a Contract, and deleting their Clerk account deletes everything. The Indian Contract Act 1872 is added to the Corpus so the most common flags (non-compete, penalty clauses) have a Provision to cite.

Sign-in becomes required for the whole app except the landing page and `/law`.

## User Stories

1. As a visitor, I want to keep seeing the landing page and `/law` Provisions without signing in, so that I can learn what LegalLens is and follow shared Citations.
2. As a visitor who clicks Ask or Contracts, I want to be asked to sign in, so that I know an account is needed.
3. As a signed-in user, I want `/ask` to behave exactly as it does today, so that the new feature costs me nothing on quick questions.
4. As a signed-in user, I want to upload a Contract as a PDF, a scanned PDF or a DOCX, or paste its text, so that I can use whatever copy I have.
5. As a user uploading a Contract, I want to see each Stage as it runs (reading the file, finding the Clauses, indexing, writing the brief, checking Citations), so that I know a 30-page Contract is making progress.
6. As a user who uploads something that is not a Contract (a court notice, a bill), I want a clear refusal saying LegalLens only explains Contracts, so that I am not given a wrong explanation.
7. As a user who uploads a Hindi Contract, I want to be told only English Contracts are supported for now, so that I know why it was refused.
8. As a user who uploads a very long document, I want to be told the page limit, so that I can upload the relevant part.
9. As a user whose upload was refused, I want it not to count toward my daily limit, so that a mistake doesn't cost me.
10. As a user, I want a Contract brief naming the parties and what the Contract is for, so that I can confirm LegalLens read the right document.
11. As a user, I want the brief to list the key terms (amounts, dates, duration, renewal, termination, notice periods), each with its Clause reference, so that I can find them in my copy.
12. As a user, I want the brief to say what each party must do, so that I understand my obligations and theirs.
13. As a user, I want Flagged clauses listed with the Clause's text and the Provision it differs from, so that I can read both and judge for myself.
14. As a user, I want every Flagged clause backed by a Citation I can open on `/law`, so that no flag rests on the model's word alone.
15. As a user, I want to ask follow-up Queries about my Contract and get answers that quote the relevant Clauses verbatim, so that I can check them against my copy.
16. As a user, I want answers to bring in the relevant law with Citations when my Query touches it (for example, the deposit limit under the Model Tenancy Act), so that I understand my Contract in its legal context.
17. As a user, I want to be told plainly when my Contract does not address something, so that I don't mistake silence for an answer.
18. As a user, I want to ask follow-ups in Hindi and get Hindi answers with the Clause text kept in English, so that I can work in my language.
19. As a user who asks "should I sign this?", I want a polite refusal that suggests what I can ask instead, so that I still get help.
20. As a user who asks an unrelated law question in a Contract conversation, I want to be pointed to `/ask`, so that each conversation stays about its Contract.
21. As a user, I want the Trust label to show when an answer is supported by my Contract, by the statutes, by the web, or a combination, so that I know where each part came from.
22. As a returning user, I want to see my Contracts listed and reopen any Contract conversation where I left off, so that I don't have to upload again.
23. As a user, I want to delete a Contract and everything about it, so that my private text isn't kept longer than I want.
24. As a user, I want deleting my account to delete all my Contracts and Contract conversations, so that nothing of mine is left behind.
25. As a user, I want to be told when I've reached my daily limit of new Contracts or Queries, and when it resets, so that I know what happened.
26. As a user on a phone, I want upload, the brief and the Contract conversation to work at phone width, so that I can use them anywhere.

## Implementation Decisions

- **Sign-in boundary.** Clerk's Next.js middleware protects `/ask` and `/contracts/**`. `/` and `/law/**` stay public. The frontend sends the Clerk session token as a bearer token to the backend. FastAPI verifies it against Clerk's JWKS (issuer and authorised party checked) and gets the Clerk user id. Every route except `/health`, `/ready`, the `/law` data endpoints and the Clerk webhook requires a valid token. The backend reads the Clerk settings from the environment, like the other secrets.
- **Rate limiting per user.** The existing `RateLimiter` is keyed by Clerk user id instead of client address. The new per-user daily caps are separate settings (defaults: 5 Contracts, 50 Queries in Contract conversations), checked before any work starts and answered with 429 and `Retry-After`. Refused uploads are not counted.
- **Persistence.** Neon Postgres, accessed with SQLAlchemy 2 (async) and psycopg, with Alembic migrations kept in the backend package and run on deploy. pgvector holds Clause vectors (1024 dimensions, Qwen3-Embedding-0.6B, ADR 0003). Tables, in outline: `users` (Clerk user id), `contracts` (owner, title, extracted text, page count, created at, brief as JSON), `clauses` (contract, number, heading, text, piece index, embedding), `contract_messages` (contract, role, Query or answer payload, created at), `usage` (user, day, counters). Foreign keys cascade on delete. Every Contract read and write is filtered by the signed-in user's id.
- **Users.** A `users` row is created the first time a signed-in request arrives. A Clerk webhook (`user.deleted`, verified with Svix signing) deletes the row and, through the cascades, all of that user's data.
- **Corpus is unchanged in kind.** The Corpus stays in Chroma and `/ask` needs no database (ADR 0005). The Indian Contract Act 1872 is added through the existing ingestion and verification path, with its Chunk count checked like the other Acts.
- **Upload endpoint.** `POST /contracts/stream` accepts a multipart file (PDF or DOCX) or pasted text and returns SSE, using the same event contract as `/ask/stream` (`stage`, then `answer` or `error`). Its Stage ids are `reading`, `contract_check`, `splitting`, `indexing`, `brief`, `citation_check` and, if needed, `citation_recheck`. The final event carries the new Contract's id and its Contract brief. The original file is held only in memory for the request.
- **Reading the file.** PDFs, including scans, go to Gemini as a document part and come back as plain text with Clause numbering preserved. DOCX is read locally. Pasted text is used as it is. More than about 30 pages (or the equivalent length for DOCX or text) is refused before reading.
- **Contract check.** One Gemini call over the start of the text decides whether it is a Contract and whether it is in English. Either "no" ends the stream with a refusal stating the reason, and nothing is stored.
- **Splitting into Clauses.** Splitting follows the Contract's own numbering (1, 1.1, 7(a) and so on). Text before the first Clause (the recitals and the parties) becomes Clause `0`. A Contract with no numbering has its paragraphs numbered in order. A long Clause is split into pieces that keep their Clause number, as long Provisions are (ADR 0002). Splitting is deterministic code, not a model call, and is tested on its own.
- **Contract brief.** It is generated once at upload from the whole Contract text, as structured JSON: `parties`, `purpose`, `key_terms[]` (label, value, Clause number), `obligations` (per party, each with Clause numbers), and `flagged_clauses[]` (Clause number, how it differs, Provisions cited). For candidate flags, the relevant Provisions are retrieved from the Corpus and given to the model. Every Clause reference is checked against the stored Clauses, and every Citation goes through the existing Citation check. A Hallucinated clause reference or Hallucinated citation causes one regeneration. After that, a flag that still lacks a verified Citation, or whose Clause reference doesn't check, is dropped rather than shown. The brief is stored and is the first message of the Contract conversation.
- **Follow-up Queries.** `POST /contracts/{id}/ask/stream` runs:
  1. The scope check, extended for Contract conversations. Personal advice is refused, and a Query about neither the Contract nor its law is refused with a pointer to `/ask`.
  2. Clause retrieval from pgvector for that Contract only, then the Grader on the Clauses.
  3. The existing corrective loop on the Corpus side (retrieval, Grader, Fallback).
  4. Generation with the last few turns of the Contract conversation as context.
  5. The Clause reference check and the Citation check.

  When the Grader finds no relevant Clause, the answer says the Contract does not address the question and may still explain the law. Hindi Queries get Hindi answers and Hindi Stage labels, with Clause text verbatim in English. Answers are not cached, because the answer cache is for `/ask` only.
- **Answer shape.** The Contract-conversation answer extends `AskResponse` with `clause_references[]` (number, verbatim text). The Trust label gains Contract-backed values: `contract`, `contract_and_corpus`, `contract_and_fallback`, `contract_corpus_and_fallback`. The frontend's Trust-label copy covers them.
- **Reuse the Answerer shape.** The Contract-conversation answering lives in its own deep module beside `Answerer` (`answering.py`). It takes the same collaborators (Corpus, LLM, WebFallback) plus a Clause store, and emits Stages through the same `on_stage` and `cancel` interface. The request log line covers Contract requests, with no Query text and no Contract text, as today.
- **Frontend.** `/contracts` lists the user's Contracts (title, date, Delete) and has the upload box (a file picker with drag and drop, plus a paste tab). `/contracts/[id]` shows the Contract brief, then the Contract conversation with an ask box at the bottom. Clause references render like Citations but labelled "Your Contract, Clause 7.2". Citations link to `/law` as today. Stage lists, reveal, errors and Try again reuse the `/ask` components. The not-legal-advice disclaimer is always visible.
- **Deletion.** `DELETE /contracts/{id}` removes the Contract and, by cascade, its Clauses, vectors and messages. The UI asks for confirmation first.

## Testing Decisions

- **Test external behaviour.** Backend tests go through `create_app` and `TestClient` with the existing fakes (bag-of-words embedder, fake LLM, recording Fallback), a fake Clerk verifier that accepts test tokens, and a Postgres test database with pgvector (a Neon branch or local Postgres). Tests assert on HTTP status, SSE events and what is stored, never on internal calls.
- **Auth.** Gated routes without a token get 401. One user cannot read, ask about or delete another user's Contract (404, not 403, so existence is not revealed). `/`, `/law` data and `/health` need no token. A webhook with a bad signature is rejected. A valid `user.deleted` removes all of that user's rows.
- **Splitting** is unit tested on fixture Contracts: numbered, nested-numbered, unnumbered and very long Clauses.
- **Upload Stage sequences:** a valid Contract, a non-Contract refused, a Hindi Contract refused, an over-long upload refused (nothing stored, cap not consumed), and a Hallucinated citation followed by recheck.
- **Brief guarantees:** a flag without a verified Citation is never returned, and every Clause reference in the brief matches stored Clause text.
- **Follow-ups:** a Clause-supported answer, a Contract-silent answer, a law-only answer through the Corpus, Fallback on an ambiguous Verdict, personal advice refused, an unrelated Query redirected to `/ask`, a Hindi Query, and conversation history passed to generation.
- **Caps:** the 6th Contract and the 51st Query in a day get 429 and `Retry-After`.
- **Evaluation:** the golden set gains three sample Contracts written for testing (a rent agreement with an over-limit deposit, a job offer with a post-employment non-compete, an NDA), each with expected Flagged clauses and follow-up cases. They are scored for flag recall and precision and for Clause-reference correctness.
- **Frontend:** component tests with `fetch` stubs, following the `/ask` component tests. They cover the upload Stages, refusal display, rendering the brief, the Contract conversation, Delete confirmation, and a signed-out redirect.

## Out of Scope

- Contracts in Hindi or other languages, and bilingual Contracts.
- Other legal documents (court notices, FIRs, wills, orders).
- Saving `/ask` history.
- Keeping or re-downloading the original uploaded file.
- Comparing two Contracts, or editing or redrafting a Contract.
- Advice on whether to sign, negotiate or sue.
- Teams or sharing a Contract with another user.
- The Registration Act 1908 and the Indian Stamp Act 1899 (possible later Corpus additions).

## Further Notes

- Glossary: Contract, Clause, Clause reference, Hallucinated clause reference, Contract brief, Flagged clause and Contract conversation were added for this work. Verdict, Trust label and Out-of-scope query were amended.
- ADR 0005 records why Clauses go to pgvector while the Corpus stays in Chroma.
- Privacy: Contract text must never appear in the request log, in error messages or in the Fallback's web Query. The Fallback query is built from the user's Query, not from Clause text.
- The Hugging Face Space needs the Neon connection string and the Clerk secrets as Space secrets. Vercel needs the Clerk publishable and secret keys.
