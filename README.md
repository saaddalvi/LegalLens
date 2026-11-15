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

## Run locally

Secrets come from environment variables only. Copy `backend/.env.example` to `backend/.env`
and set `GOOGLE_API_KEY` (optional: `GEMINI_MODEL`, `CORS_ORIGINS`, `CHROMA_PATH`).

```bash
# backend (http://localhost:8000); seeds a small fixture Corpus on first question
cd backend && uvicorn legallens.main:app --env-file .env

# frontend (http://localhost:3000); set NEXT_PUBLIC_API_URL if the backend is elsewhere
cd frontend && npm install && npm run dev
```
