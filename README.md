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
- **Citation validity**: no Citation fails the Hallucinated-citation check against the Corpus.

### Results

Latest run (2026-11-17, `gemini-3.1-flash-lite`, Tavily Fallback, full Corpus of 3,501 Chunks).
10 of 72 case runs failed on Gemini 503 "high demand" errors after retries and are excluded from the
metrics, so the figures cover 31 cases and are indicative, not definitive.

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 57% | 52% |
| Answer accuracy | 55% | 52% |
| Citation validity | 100% | 100% |

| Category (answer accuracy) | Plain RAG | CRAG |
|---|---|---|
| English | 64% | 54% |
| Hindi | 20% | 20% |
| Repealed-code | 80% | 100% |
| Out-of-scope | 100% | 100% |
| Poor-retrieval | 0% | 0% |

Read these with care:

- CRAG did **not** beat plain RAG overall in this run. Its only clear gain is on repealed-code Queries. An earlier run on `gemini-3.5-flash-lite` (6 case runs lost to errors) showed CRAG ahead on poor-retrieval Queries (0% to 40%), so the result is sensitive to the model and to Gemini availability.
- CRAG scored 0% on poor-retrieval Queries in that run. Diagnosis: with only web sources the generation prompt made the model decline ("no Provisions provided"), and a transient Fallback failure was labelled `corpus`. After fixing the prompt and giving "cannot answer" messages their own `none` Trust label, a rerun of only the poor-retrieval cases (same model) gave plain RAG 0% and CRAG 80% (4 of 5). The table above predates that fix and the other categories have not been rerun.
- Hindi accuracy of 20% in both modes, and the many English misses on labour and criminal-procedure cases, need a look at retrieval and at the golden set's expected Provisions before drawing conclusions.
- Citation validity is 100% by construction: the endpoint blocks Hallucinated citations before they reach the response.

Per-case detail is in `backend/evaluation/report.md`.
