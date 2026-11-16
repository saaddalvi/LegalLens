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
