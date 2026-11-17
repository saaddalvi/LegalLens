# LegalLens

Indian-law assistant using Corrective RAG. See `GLOSSARY.md` and `docs/adr/`.

## Backend setup

Requires **Python 3.14** (recorded in `backend/pyproject.toml`). All dependencies, including torch,
chromadb and sentence-transformers, install from prebuilt wheels on 3.14.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The first embedding run downloads `Qwen/Qwen3-Embedding-0.6B` (about 1.1 GB) from Hugging Face.
A Corpus built with another embedding model must be rebuilt (`python -m legallens.build_corpus`); vectors from different models do not mix.
The torch wheel alone is ~140 MB, so the first install can be slow on a slow connection.

## Build the Corpus

```bash
cd backend && python -m legallens.build_corpus
```

Downloads the Constitution dataset pinned in `ingestion/sources.py` (hash-checked), applies the
corrections recorded in `backend/sources/constitution_patches.json`, prints Chunk counts per Act
and exits non-zero if a count or Chunk looks wrong. The vector store is rebuilt from scratch at
`CHROMA_PATH` (default `backend/data/chroma`).

To re-verify the text against the official Constitution of India PDF (Ministry of Law and Justice,
as on May 2022, hosted on the India Code CDN):

```bash
cd backend && python scripts/verify_constitution.py path/to/official.pdf
```

## Run locally

Secrets come from environment variables only. Copy `backend/.env.example` to `backend/.env`
and set `GOOGLE_API_KEY` and `WEB_SEARCH_API_KEY` (a Tavily key for the web Fallback; optional: `GEMINI_MODEL`, `CORS_ORIGINS`, `CHROMA_PATH`).

```bash
# backend (http://localhost:8000); uses the built Corpus; seeds a small fixture Corpus on first question if none is built
cd backend && .venv/bin/uvicorn legallens.main:app --env-file .env

# frontend (http://localhost:3000); set NEXT_PUBLIC_API_URL if the backend is elsewhere
cd frontend && npm install && npm run dev
```

## Evaluation

Compares plain RAG (retrieve and generate, no Grader, no Fallback) with CRAG on a golden set of
36 Queries in `backend/evaluation/golden_set.json`: English (15, across every Act in the Corpus),
Hindi (5), repealed-code (6), out-of-scope (5) and poor-retrieval (5, topics the Corpus does not
cover). Every case goes through the real `/ask` endpoint against the built Corpus.

```bash
cd backend && python -m legallens.evaluate   # needs GOOGLE_API_KEY, WEB_SEARCH_API_KEY and a built Corpus
```

It writes `backend/evaluation/report.md`. Requests are throttled to 15 per minute (`--per-minute`)
for the Gemini free tier, so a full run takes about 20 minutes and uses roughly 300 requests.

- **Retrieval hit-rate**: the response cites at least one of the case's expected Provisions (cases with expected Provisions only).
- **Answer accuracy**: a Gemini judge compares the answer with the case's reference points. Out-of-scope cases are correct only when refused, and Hindi cases only when answered in Hindi.
- **Citation validity (after blocking)**: no Citation in the response fails the Hallucinated-citation check against the Corpus. This is 100% by construction, because the endpoint blocks Hallucinated citations.
- **Hallucinated citations before blocking**: the share of generated answers whose first generation cited a Provision missing from the Corpus. It counts only generations that had Provisions to cite, so CRAG answers from web sources alone are not in it.

The report shows case counts per mode, because a mode that hit Gemini errors on different cases is scored on different cases.

### Results

Latest run (2026-11-17, `gemini-3.1-flash-lite`, Tavily Fallback, full Corpus of 3,501 Chunks embedded with `Qwen/Qwen3-Embedding-0.6B`, retrieval top 10).
69 of 72 case runs completed. Three CRAG runs failed on Gemini 503 errors after retries and are excluded from the metrics:
`en-mta-deposit`, `en-wages-overtime` and `rep-ipc-302`. Plain RAG is scored on all 36 cases and CRAG on 33, so the modes are
not scored on exactly the same cases, and with so few cases per category one case moves a figure by 7 to 25 points.
The model is not the one used in the previous run (`gemini-3.5-flash-lite`, whose free daily quota ran out), so the two runs are not directly comparable.

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 96% | 91% |
| Answer accuracy | 86% | 97% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

| Category (answer accuracy) | Cases (plain / CRAG) | Plain RAG | CRAG |
|---|---|---|---|
| English | 15 / 13 | 100% | 100% |
| Hindi | 5 / 5 | 100% | 100% |
| Repealed-code | 6 / 5 | 100% | 100% |
| Out-of-scope | 5 / 5 | 100% | 100% |
| Poor-retrieval | 5 / 5 | 0% | 80% |

Does CRAG beat plain RAG?

- **Ahead:** poor-retrieval Queries (0% to 80%, 4 of 5), where the Fallback to web sources answers what the Corpus cannot (divorce, domestic violence, GST, drunk driving). This is the only clear difference.
- **Level:** answer accuracy on English, Hindi, repealed-code and out-of-scope Queries (100% each). The overall gap (86% to 97%) comes entirely from the poor-retrieval category.
- **Behind on retrieval hit-rate (96% to 91%):** only because CRAG retrieves identically but its Grader sent `en-ir-strike` to the web Fallback, so the answer cited no expected Provision, although it was still correct. Not a real retrieval difference.
- Still wrong in CRAG: `poor-rti` (the Fallback returned something the judge scored as wrong; the report does not say why).

Other notes:

- The three excluded case runs show as `HTTPStatusError` in `backend/evaluation/report.md`; the cause (503) is from the run log, which is not kept in the repo.
- Retrieval with Qwen3-Embedding-0.6B puts the expected Provision in the top 10 for 23 of the 26 retrieval cases (20 with `multilingual-e5-small`; ADR 0003). FIR (BNSS 173), electronic evidence (BSA 63) and Hindi wages are now found. Still missed: Hindi tenancy deposit (`hi-mta-deposit`, which e5 found) and two repealed-code cases that rely on naming a section (IPC 302, IEA 65B). The report's hit-rate counts what the response cites, so it can differ from this retrieval count.
- Hallucinated-citation rate before blocking is 0% in both modes: nothing was blocked in this run. CRAG answers that rely on web sources alone are not in this rate.

Per-case detail is in `backend/evaluation/report.md`.
