import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .corpus import Corpus
from .embeddings import E5Embedder
from .fallback import NoFallback, WebFallback
from .llm import LLM, GeminiLLM
from .models import AskRequest, AskResponse, Provision
from .pipeline import answer_query

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURE = BACKEND_DIR / "fixtures" / "sample_provisions.json"


def default_corpus() -> Corpus:
    """Persistent local store, seeded from the fixture Corpus when empty."""
    path = os.environ.get("CHROMA_PATH", str(BACKEND_DIR / "data" / "chroma"))
    corpus = Corpus(path, E5Embedder())
    if corpus.count() == 0:
        corpus.add([Provision(**p) for p in json.loads(FIXTURE.read_text())])
    return corpus


def create_app(
    *,
    corpus: Corpus | None = None,
    llm: LLM | None = None,
    fallback: WebFallback | None = None,
) -> FastAPI:
    """Dependencies not supplied are built lazily on the first question."""
    app = FastAPI(title="LegalLens")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @lru_cache(maxsize=1)
    def deps() -> tuple[Corpus, LLM, WebFallback]:
        return (corpus or default_corpus(), llm or GeminiLLM(), fallback or NoFallback())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        c, l, f = deps()
        try:
            return answer_query(req.query, corpus=c, llm=l, fallback=f)
        except Exception as exc:
            logging.getLogger(__name__).exception("answer generation failed")
            raise HTTPException(503, "The service is unavailable. Please retry shortly.") from exc

    return app


app = create_app()
