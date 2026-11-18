import json
import logging
import os
import queue
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .corpus import Corpus
from .embeddings import LocalEmbedder
from .fallback import WebFallback, default_fallback
from .language import detect_language
from .llm import LLM, GeminiLLM
from .models import AskRequest, AskResponse, Provision
from .pipeline import STAGE_LABELS, answer_query
from .rate_limit import RateLimiter

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURE = BACKEND_DIR / "fixtures" / "sample_provisions.json"


def default_corpus() -> Corpus:
    """Persistent local store, seeded from the fixture Corpus when empty."""
    path = os.environ.get("CHROMA_PATH", str(BACKEND_DIR / "data" / "chroma"))
    corpus = Corpus(path, LocalEmbedder())
    if corpus.count() == 0:
        corpus.add([Provision(**p) for p in json.loads(FIXTURE.read_text())])
    return corpus


KEEPALIVE_SECONDS = 10


class _ClientGone(Exception):
    """Raised inside the pipeline thread when the streaming client disconnected."""


def create_app(
    *,
    corpus: Corpus | None = None,
    llm: LLM | None = None,
    fallback: WebFallback | None = None,
    crag: bool = True,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    """Dependencies not supplied are built lazily on the first question.

    crag=False serves the plain-RAG baseline (no Grader, no Fallback) for evaluation.
    rate_limiter limits /ask and /ask/stream per client address; None means no limit.
    """
    app = FastAPI(title="LegalLens")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(
            ","
        ),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @lru_cache(maxsize=1)
    def deps() -> tuple[Corpus, LLM, WebFallback]:
        return (
            corpus or default_corpus(),
            llm or GeminiLLM(),
            fallback or default_fallback(),
        )

    def limit(request: Request) -> None:
        """Rejects with 429 before any work starts, so a streamed answer never begins."""
        if rate_limiter is None:
            return
        wait = rate_limiter.check(request.client.host if request.client else "unknown")
        if wait is not None:
            raise HTTPException(
                429,
                "Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(wait)},
            )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask", response_model=AskResponse, dependencies=[Depends(limit)])
    def ask(req: AskRequest) -> AskResponse:
        c, l, f = deps()
        try:
            return answer_query(req.query, corpus=c, llm=l, fallback=f, crag=crag)
        except Exception as exc:
            logging.getLogger(__name__).exception("answer generation failed")
            raise HTTPException(
                503, "The service is unavailable. Please retry shortly."
            ) from exc

    @app.post("/ask/stream", dependencies=[Depends(limit)])
    def ask_stream(req: AskRequest) -> StreamingResponse:
        try:
            c, l, f = deps()
        except Exception as exc:
            logging.getLogger(__name__).exception("dependencies unavailable")
            raise HTTPException(
                503, "The service is unavailable. Please retry shortly."
            ) from exc
        language = detect_language(req.query)
        events: queue.Queue[tuple[str, dict] | None] = queue.Queue()
        current: list[str] = []
        cancelled = threading.Event()

        def on_stage(stage_id: str) -> None:
            if cancelled.is_set():
                raise _ClientGone()
            current[:] = [stage_id]
            events.put(
                ("stage", {"id": stage_id, "label": STAGE_LABELS[stage_id][language]})
            )

        def work() -> None:
            try:
                result = answer_query(
                    req.query, corpus=c, llm=l, fallback=f, crag=crag, on_stage=on_stage
                )
                events.put(("answer", result.model_dump(mode="json")))
            except _ClientGone:
                pass
            except Exception:
                logging.getLogger(__name__).exception("answer generation failed")
                events.put(
                    (
                        "error",
                        {
                            "stage": current[0] if current else None,
                            "message": "The service is unavailable. Please retry shortly.",
                        },
                    )
                )
            finally:
                events.put(None)

        threading.Thread(target=work, daemon=True).start()

        def frames():
            try:
                while True:
                    try:
                        event = events.get(timeout=KEEPALIVE_SECONDS)
                    except queue.Empty:
                        yield ": keepalive\n\n"  # keeps proxies from idling out
                        continue
                    if event is None:
                        return
                    name, data = event
                    yield f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            finally:
                # Client left: stop the pipeline at its next Stage.
                cancelled.set()

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app(rate_limiter=RateLimiter.from_env())
