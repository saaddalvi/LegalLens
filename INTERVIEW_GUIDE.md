# LegalLens — Project Guide for Interviews

A study guide so you can explain the project clearly. Read sections 1–3 first (the 2-minute pitch), then use the rest as depth when the interviewer drills down.

---

## 1. The 30-second pitch

> "LegalLens is a web app where a layperson asks a question about Indian law — in English or Hindi — and gets a plain-language answer **grounded in real statute text**, with **verified citations** they can check. It uses **Corrective RAG**: it retrieves legal provisions, has an LLM grade whether they actually answer the question, and if not, falls back to a web search and clearly labels the answer as less trustworthy. An automated check guarantees it never cites a legal provision that doesn't exist."

## 2. The problem it solves

- Statute text is dense, and every Act is structured differently.
- Indian criminal law changed in **July 2024**: the IPC, CrPC and Evidence Act were replaced by the BNS, BNSS and BSA. Search results mix repealed and current law.
- Generic chatbots answer confidently but **invent section numbers** (hallucinate). In law, that is dangerous.
- Many users would rather ask in **Hindi**.

**Goal:** answer in the user's language, ground every claim in real statute text, and let the user verify it.

## 3. Key design decisions (what to emphasise)

| Decision | Why | Where |
|---|---|---|
| **Corrective RAG** instead of plain RAG | Plain RAG answers from bad retrieval anyway. CRAG grades retrieval and corrects it. | ADR 0001 |
| **One chunk per legal Provision** (not fixed-size token windows) | A citation maps exactly to one retrievable unit, so the hallucination check can be *exact*. | ADR 0002 |
| Long provisions split into ~800-char pieces for embedding; search scores a provision by its best piece | The embedding model reads ~512 tokens; long sections were matched only on their opening. | ADR 0002 amendment |
| **Gemini for all LLM work**, **local multilingual embeddings** (Qwen3-Embedding-0.6B) | One provider + free tier; Hindi queries match English statute text without a paid embedding API. | ADR 0003 |
| **LLM-scored Verdict** with thresholds (≥0.7 correct, ≤0.3 incorrect, between = ambiguous) | Simple, tunable, logged for later tuning. | ADR 0004 |
| **Tavily web Fallback, official domains first** (gov.in, nic.in, prsindia.org, indiankanoon.org), open web only if those return nothing | Keeps broad recall but prefers government sources. | ADR 0004 amendment |
| **Citation check blocks hallucinations** | Every cited provision is looked up in the Corpus; one regeneration, then the answer is blocked. | `citation_check.py` |
| **Privacy by design** | No accounts, no chat history; logs hold only query *length* and language, never the query text. | `request_log.py` |

## 4. Architecture

```
Browser ──POST /ask/stream (SSE)──► Next.js frontend (Vercel)
                                        │
                                        ▼
                         FastAPI backend (Hugging Face Space, Docker)
                                        │
        Rate limit + answer cache ──► Scope check (Gemini)
                                        │ out of scope → polite refusal
                                        ▼
                    Retrieve top 10 (Chroma + Qwen3 embeddings)
                                        │
                                        ▼
                               Grader (Gemini) → score → Verdict
                  correct ─────────────┤────────── ambiguous / incorrect
                     │                                  │
                     │                        Web Fallback (Tavily)
                     ▼                                  ▼
                              Generate answer (Gemini)
                                        │
                          Citation check against the Corpus
                       valid ──► answer + Trust label + citations
                       hallucinated ──► regenerate once ──► else block
```

**Stack**
- **Backend:** Python 3.14, FastAPI, ChromaDB (vector store), sentence-transformers (Qwen3-Embedding-0.6B), LangChain + Gemini, Tavily, pydantic, pytest.
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind 4, Vitest.
- **Deploy:** Vercel (frontend) + Hugging Face Docker Space (backend).

## 5. How one question flows (the pipeline in `pipeline.py`, run by the `Answerer` in `answering.py`)

Both `/ask` and `/ask/stream` (and the evaluation) answer through one `Answerer`, which owns the answer cache, the Stage labels, cancellation and the request log line; `pipeline.py` holds the corrective-loop logic. The routes are thin adapters.

1. **Language detection** (English / Hindi).
2. **Scope check:** Gemini classifies the query as *in scope*, *not about Indian law*, or *personal advice* ("should I sue?"). The last two are politely refused with a suggested rephrasing. "What can I do?" is in scope: it gets the law and the remedies, never a choice among them.
3. **Retrieval** (`_retrieve`): Provisions the user names directly (e.g. "IPC 302") first, then top-10 semantic matches. Repealed provisions are ranked behind current ones, and each repealed provision pulls in its **superseding provision** (IPC 302 → BNS 103).
4. **Grading:** Gemini scores 0–1 how well the retrieved provisions answer the question → **Verdict**.
   - **Correct** → answer from the Corpus. Trust label `corpus`.
   - **Ambiguous** → Corpus provisions *plus* web sources. Trust label `corpus_and_fallback`.
   - **Incorrect** → web sources only, no citations. Trust label `fallback`.
   - No web sources found → honest "cannot answer" (label `none`).
5. **Generation:** Gemini writes a plain-language answer in the user's language.
6. **Citation check:** every cited Act+number must exist in the Corpus. If not, regenerate once; if it still fails, block and return "cannot answer reliably".
7. The user sees **verified citations quoting the original English text**, plus a Trust label.

The `/ask/stream` endpoint streams the **Stages** (server-sent events) so the user sees "Searching the statutes…", "Verifying citations…" while waiting.

## 6. The Corpus (the data)

**3,693 provisions** across:
- **Criminal:** IPC, CrPC, Indian Evidence Act (all repealed), BNS, BNSS, BSA (in force), with a mapping table linking old ↔ new sections.
- **Constitution of India** (Articles).
- **Everyday law:** Indian Contract Act, Consumer Protection Act, Transfer of Property Act, Model Tenancy Act (status `model`, a template States may adopt), Code on Wages, Industrial Relations Code, Code on Social Security, OSH Code.

**Ingestion** (`ingestion/`): a parser per Act (they're all structured differently), hash-checked pinned sources, manual patch files for known errors, and an **ingestion report** that exits non-zero if a chunk count falls outside the expected range. Verification scripts check the text against the official PDFs.

## 7. Evaluation (strong interview material — you measured it)

A **golden set of 41 queries**: 15 English, 5 Hindi, 6 repealed-code, 4 remedies ("What can I do?"), 6 out-of-scope, 5 poor-retrieval. (The table below is from the earlier 36-query run.) Each is answered by the same `Answerer` the endpoints use; a Gemini judge scores accuracy against reference points. Compared **plain RAG vs CRAG**.

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 96% | 92% |
| Answer accuracy | 86% | 94% |
| Citation validity (after blocking) | 100% | 100% |

- **Where CRAG wins:** poor-retrieval queries (topics the Corpus doesn't cover): **0% → 80%**. The web Fallback answers what the Corpus can't. This is the only clear difference.
- **Where it's slightly worse:** one English case (`en-ir-strike`) was sent to the Fallback and the web answer was scored wrong.
- **Be honest about the sample size:** with so few cases per category, one case moves a figure by 7–25 points. Saying this shows maturity.

**Embedding model experiment (ADR 0003):** measured e5-small/base/large, bge-m3 and Qwen3 on 26 retrieval cases. Qwen3-0.6B got 23/26 hits vs 20 for e5-small and beat the larger models at lower cost. It also regressed one Hindi case, which is documented.

## 8. Engineering quality (talking points)

- **Tests:** ~35 backend test files (pytest) plus frontend tests (Vitest). The LLM, embedder and web search are behind interfaces, so tests inject fakes.
- **Rate limiting** per client IP (5/minute, 50/day by default) with HTTP 429 and `Retry-After`.
- **Answer cache** (in-memory, TTL); "cannot answer" results are never cached.
- **Resilience:** Gemini retries on 429/503, with an optional second model. A Fallback failure degrades gracefully to a Corpus-only answer or an explicit "cannot answer".
- **Prompt-injection defence:** web snippets are cut to 1,000 characters, fenced as untrusted data, and have angle brackets escaped.
- **Observability:** one structured JSON log line per request with per-stage timings, Grader score, Verdict and Trust label, and no query text.
- **Health endpoints:** `/health` (process up) and `/ready` (Corpus loaded and size, flags the sample fixture).
- **Law browsing:** `/acts`, `/acts/{act}`, `/provision/{act}/{number}` plus `/law` pages so citations link to the full text.
- **Domain docs:** `GLOSSARY.md` gives a shared vocabulary (Act, Provision, Chunk, Verdict, Fallback, Trust label…). 4 ADRs record the decisions and their trade-offs.
- **Deployment reproducibility:** pinned `constraints.txt`, because a Chroma store only loads reliably under the version that wrote it; a deploy wizard script; the deploy script refuses to ship an empty or sample Corpus.

## 9. Glossary (use these exact terms)

- **Act** — a statute/code. **Provision** — one numbered Section/Article.
- **Corpus** — all provisions it can answer from. **Chunk** — one provision stored for retrieval.
- **Verdict** — Grader's judgement: correct / ambiguous / incorrect.
- **Fallback** — web search when the Corpus doesn't answer.
- **Trust label** — `corpus`, `fallback`, `corpus_and_fallback`, or `none`.
- **Citation** — reference to a provision with its verbatim English text.
- **Hallucinated citation** — cites a provision not in the Corpus.
- **Superseding provision** — the in-force provision that replaced a repealed one.

## 10. Likely interview questions and answers

**Q: What is RAG, and why Corrective RAG?**
RAG retrieves relevant documents and gives them to an LLM so it answers from them. Plain RAG blindly trusts retrieval; if the retrieved text is irrelevant the LLM either hallucinates or answers wrongly. CRAG adds a grader that evaluates retrieval and triggers a correction (web search) when it's poor.

**Q: How do you prevent hallucinated citations?**
The LLM returns structured citations (Act and number). Each is looked up in the Corpus. If any is missing, I regenerate once, then block the answer. Because one Chunk is one Provision, the check is an exact lookup rather than fuzzy matching. The user also sees the verbatim statute text, not the LLM's paraphrase.

**Q: Why one chunk per provision?**
So citations map exactly to retrievable units. The cost is a parser per Act and very long provisions. I mitigated long ones by embedding ~800-char pieces and scoring a provision by its best piece, while still returning whole provisions.

**Q: How do Hindi queries work?**
The embedding model (Qwen3) is multilingual, so a Hindi query lands near the English statute text. Gemini detects the language and answers in it. Citations stay in verbatim English so the user can show them to a lawyer.

**Q: How did you choose the embedding model?**
I benchmarked five configurations on 26 retrieval cases (script `compare_embeddings.py`), tracking hits, embed time and disk size. Bigger wasn't better; Qwen3-0.6B won on hits (23/26) and cost.

**Q: How do you handle repealed laws?**
Each repealed provision stores its superseding provision (IPC 302 → BNS 103). Retrieval ranks current law first and pulls in the replacement. Citations add the current provision's text and flag status.

**Q: How are the Verdict thresholds chosen?**
0.7 and 0.3 are starting values. I log the Grader's score and Verdict on every request precisely so they can be tuned against real traffic and the golden set.

**Q: What are the limitations? (be candid)**
- LLM-as-judge evaluation on a small golden set; single cases move numbers a lot.
- The Grader is an LLM score, so it's not deterministic or calibrated.
- Web Fallback answers are less reliable (hence the Trust label), and have no verified citations.
- Corpus doesn't cover state laws or case law.
- Free-tier quotas and a sleeping Hugging Face Space make the first request slow.
- In-memory cache and rate limit don't scale across multiple instances.

**Q: What would you do next?**
Expand the golden set; calibrate the Grader thresholds using logged data; add case law and state laws; swap the in-memory cache and rate limit for Redis; add a retrieval re-ranker or hybrid search.

**Q: How do you protect user privacy?**
No accounts, no chat history, and the logs never store the query or answer, only its length and language, because queries can describe personal situations.

**Q: What's the not-legal-advice stance?**
A permanent disclaimer, and the scope check refuses personal-advice questions ("should I sue?") while still offering to explain the relevant law.

## 11. A suggested 3-minute walkthrough

1. **Problem** (20s): lay users, mixed repealed/current law, chatbot hallucinations, Hindi.
2. **Solution** (30s): CRAG with verified citations and Trust labels.
3. **Demo flow** (60s): ask "my landlord won't return my deposit" → Stages stream → answer cites Model Tenancy Act with verbatim text → show a poor-retrieval question that triggers the Fallback and shows a lower Trust label.
4. **Engineering depth** (40s): one-chunk-per-provision, the citation check, the embedding benchmark.
5. **Results and honesty** (30s): CRAG 94% vs plain RAG 86%, 0→80% on poor-retrieval, the small-sample caveat.

## 12. Where to find things in the repo

| Topic | File |
|---|---|
| Answering a Query (cache, Stages, cancellation, log line) | `backend/src/legallens/answering.py` |
| Corrective-loop logic | `backend/src/legallens/pipeline.py` |
| Gemini prompts (scope, grade, rewrite, generate) | `backend/src/legallens/llm.py` |
| Web Fallback | `backend/src/legallens/fallback.py` |
| Citation check | `backend/src/legallens/citation_check.py` |
| Vector store / search | `backend/src/legallens/corpus.py` |
| API endpoints, SSE streaming (thin adapters over the `Answerer`) | `backend/src/legallens/main.py` |
| Ingestion per Act | `backend/src/legallens/ingestion/` |
| Evaluation harness / golden set / results | `evaluation.py`, `backend/evaluation/` |
| Decisions | `docs/adr/0001`–`0004` |
| Vocabulary | `GLOSSARY.md` |
| Frontend | `frontend/src/app/` (`ask/`, `law/`) |
