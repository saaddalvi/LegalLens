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

The first embedding run downloads `intfloat/multilingual-e5-small` from Hugging Face.
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

Latest run (2026-11-17, `gemini-3.5-flash-lite`, Tavily Fallback, full Corpus of 3,501 Chunks, retrieval top 10).
70 of 72 case runs completed. Two failed on Gemini 503 "high demand" errors after retries and are excluded
from the metrics: `en-bns-murder` (plain RAG only) and `hi-mta-deposit` (CRAG only). The figures cover 35 cases per
mode, but those two modes are not scored on exactly the same 35, and with so few cases per category one case moves a figure by 7 to 25 points.

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 80% |
| Answer accuracy | 63% | 71% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

| Category (answer accuracy) | Cases (plain / CRAG) | Plain RAG | CRAG |
|---|---|---|---|
| English | 14 / 15 | 57% | 67% |
| Hindi | 5 / 4 | 60% | 50% |
| Repealed-code | 6 / 6 | 100% | 100% |
| Out-of-scope | 5 / 5 | 100% | 100% |
| Poor-retrieval | 5 / 5 | 0% | 40% |

Does CRAG beat plain RAG?

- **Ahead:** poor-retrieval Queries (0% to 40%, 2 of 5), where the Fallback to web sources answers what the Corpus cannot (RTI, domestic violence). It also leads on English accuracy (57% to 67%, one extra case, `en-ir-strike`, and the plain RAG run of `en-bns-murder` is missing) and so overall (63% to 71%).
- **Level:** retrieval hit-rate (80% each), repealed-code (100%), out-of-scope (100%) and Citation validity. Both modes retrieve identically from the Corpus, so CRAG cannot help where the Corpus ranks the right Provision outside the top 10.
- **Behind:** Hindi (60% to 50%), but this is one case, because `hi-mta-deposit` errored in CRAG only. On the 4 Hindi cases both modes ran, the two modes score the same.
- The overall gap of 8 points is within the noise of a 35-case set. Treat CRAG as clearly better only on poor-retrieval Queries, and as no worse elsewhere.

Other notes:

- Real retrieval gaps remain. The expected Provision is not in the top 10 for theft (BNS 303), FIR (BNSS 173), electronic evidence (BSA 63), overtime wages and Hindi wages, in both modes. A larger embedding model (ADR 0003) is the likely fix and was not tried.
- Three poor-retrieval Queries (drunk driving, divorce, GST) are still answered "cannot answer" (`none`) by CRAG, which the judge scores as wrong because the Fallback found nothing usable.
- Hallucinated citations before blocking are 0% in both modes. The earlier 60-75% on Hindi came from Gemini merging the number into the Act field and went away once Provisions were listed as separate Act and Section fields. The block still protects against it, but nothing was blocked in this run. CRAG answers that rely on web sources alone are not in this rate.
- The previous preliminary figures (`gemini-3.1-flash-lite`, 31 cases, CRAG behind) are replaced. The model default has changed to `gemini-3.5-flash-lite`, so the two runs are not directly comparable.

Per-case detail is in `backend/evaluation/report.md`.
