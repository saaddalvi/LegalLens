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

### Results (preliminary)

The only complete-enough run so far hit Gemini errors on 6 of 72 case runs; those are excluded
from the metrics, so the figures below are indicative. A full rerun is pending, after the daily
Gemini quota resets.

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 68% | 67% |
| Answer accuracy | 62% | 68% |
| Citation validity | 100% | 100% |

CRAG's gain comes from poor-retrieval Queries (0% to 40% accuracy); repealed-code and
out-of-scope cases are 100% in both modes. Several English and Hindi labour and criminal-procedure
cases miss their expected Provision in both modes, so the next step is to inspect those
retrieval misses and the golden set's expectations. See `backend/evaluation/report.md` for per-case detail.
