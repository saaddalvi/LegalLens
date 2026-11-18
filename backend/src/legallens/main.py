import asyncio
import json
import logging
import os
import queue
import threading
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .answer_cache import AnswerCache
from .corpus import Corpus
from .embeddings import LocalEmbedder
from .fallback import WebFallback, default_fallback
from .language import detect_language
from .llm import LLM, GeminiLLM
from .models import (
    ActIndex,
    ActSummary,
    AskRequest,
    AskResponse,
    Provision,
    ProvisionSummary,
)
from .pipeline import STAGE_LABELS, answer_query
from .rate_limit import RateLimiter
from .request_log import RequestLog

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURE = BACKEND_DIR / "fixtures" / "sample_provisions.json"


def fixture_provisions() -> list[Provision]:
    return [Provision(**p) for p in json.loads(FIXTURE.read_text())]


def default_corpus() -> Corpus:
    """Persistent local store, seeded from the fixture Corpus when empty.

    With REQUIRE_CORPUS=1 an empty store is an error instead: a deployment that lost
    its built Corpus must not quietly answer from a handful of sample Provisions.
    """
    path = os.environ.get("CHROMA_PATH", str(BACKEND_DIR / "data" / "chroma"))
    corpus = Corpus(path, LocalEmbedder())
    if corpus.count() == 0:
        if os.environ.get("REQUIRE_CORPUS") == "1":
            raise RuntimeError(
                f"REQUIRE_CORPUS is set but the Corpus at {path} is empty; "
                "build it with `python -m legallens.build_corpus`"
            )
        corpus.add(fixture_provisions())
    return corpus


SNIPPET_CHARS = 160


def _first_line(text: str) -> str:
    """The first non-empty line of a Provision, cut to fit an index listing."""
    line = next((ln.strip() for ln in text.split("\n") if ln.strip()), "")
    return line if len(line) <= SNIPPET_CHARS else line[: SNIPPET_CHARS - 1] + "…"


def is_fixture_corpus(corpus: Corpus) -> bool:
    """Whether the store holds only the sample fixture. The fixture is persisted when
    first seeded, so this looks at what is stored, not at what this process did."""
    sample = fixture_provisions()
    return corpus.count() == len(sample) and all(
        corpus.get(p.act, p.number) for p in sample
    )


KEEPALIVE_SECONDS = 10


class _ClientGone(Exception):
    """Raised inside the pipeline thread when the streaming client disconnected."""


def _frame(name: str, data: dict) -> str:
    """One Server-Sent Events frame."""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(
    *,
    corpus: Corpus | None = None,
    llm: LLM | None = None,
    fallback: WebFallback | None = None,
    crag: bool = True,
    rate_limiter: RateLimiter | None = None,
    cache: AnswerCache | None = None,
) -> FastAPI:
    """Dependencies not supplied are built lazily on the first question.

    crag=False serves the plain-RAG baseline (no Grader, no Fallback) for evaluation.
    rate_limiter limits /ask and /ask/stream per client address; None means no limit.
    cache remembers answers to repeated Queries; None means every Query is answered afresh.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # WARM_START=1 loads the Corpus and the embedding model now, so the first
        # question does not pay for it. A failure is logged and shows in /ready.
        if os.environ.get("WARM_START") == "1":

            def warm() -> None:
                c, _, _ = deps()
                c.search("warm-up", 1)  # the first search loads the embedding model

            try:
                await asyncio.to_thread(warm)
            except Exception:
                logging.getLogger(__name__).exception("warm start failed")
        yield

    app = FastAPI(title="LegalLens", lifespan=lifespan)
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
        """Liveness: the process is up. See /ready for whether it can answer."""
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str | int | bool]:
        """Readiness: the Corpus loads, and whether it is only the sample fixture."""
        try:
            c, _, _ = deps()
            return {
                "status": "ready",
                "provisions": c.count(),
                "fixture": is_fixture_corpus(c),
            }
        except Exception as exc:
            logging.getLogger(__name__).exception("dependencies unavailable")
            raise HTTPException(503, "The service is not ready.") from exc

    def browse_corpus() -> Corpus:
        try:
            return deps()[0]
        except Exception as exc:
            logging.getLogger(__name__).exception("dependencies unavailable")
            raise HTTPException(
                503, "The service is unavailable. Please retry shortly."
            ) from exc

    # Reading the law makes no Gemini calls, so these routes are not rate limited.

    @app.get("/acts", response_model=list[ActSummary])
    def acts() -> list[ActSummary]:
        counts = browse_corpus().act_counts()
        return [ActSummary(act=a, provisions=counts[a]) for a in sorted(counts)]

    @app.get("/acts/{act}", response_model=ActIndex)
    def act_index(act: str) -> ActIndex:
        provisions = browse_corpus().list_act(act)
        if not provisions:
            raise HTTPException(404, "No such Act in the Corpus.")
        return ActIndex(
            act=act,
            provisions=[
                ProvisionSummary(
                    number=p.number,
                    chapter=p.chapter,
                    status=p.status,
                    snippet=_first_line(p.text),
                )
                for p in provisions
            ],
        )

    @app.get("/provision/{act}/{number}", response_model=Provision)
    def provision(act: str, number: str) -> Provision:
        c = browse_corpus()
        # The letter in a number such as "21A" may be typed in either case.
        found = c.get(act, number) or c.get(act, number.upper())
        if found is None:
            raise HTTPException(404, "No such Provision in the Corpus.")
        return found

    @app.post("/ask", response_model=AskResponse, dependencies=[Depends(limit)])
    def ask(req: AskRequest) -> AskResponse:
        rlog = RequestLog("ask", req.query)
        if cache and (hit := cache.get(req.query, crag)):
            rlog.finish("answer", hit, cache_hit=True)
            return hit
        try:
            c, l, f = deps()
            result = answer_query(
                req.query,
                corpus=c,
                llm=l,
                fallback=f,
                crag=crag,
                on_stage=rlog.stage,
                trace=rlog.trace,
            )
            if cache:
                cache.put(req.query, crag, result)
        except Exception as exc:
            logging.getLogger(__name__).exception("answer generation failed")
            rlog.finish("error")
            raise HTTPException(
                503, "The service is unavailable. Please retry shortly."
            ) from exc
        rlog.finish("answer", result)
        return result

    @app.post("/ask/stream", dependencies=[Depends(limit)])
    def ask_stream(req: AskRequest) -> StreamingResponse:
        rlog = RequestLog("ask_stream", req.query)
        if cache and (hit := cache.get(req.query, crag)):
            # No Stages to show: the verified answer is already known.
            rlog.finish("answer", hit, cache_hit=True)
            return StreamingResponse(
                iter([_frame("answer", hit.model_dump(mode="json"))]),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        try:
            c, l, f = deps()
        except Exception as exc:
            logging.getLogger(__name__).exception("dependencies unavailable")
            rlog.finish("error")
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
            rlog.stage(stage_id)
            events.put(
                ("stage", {"id": stage_id, "label": STAGE_LABELS[stage_id][language]})
            )

        def work() -> None:
            try:
                result = answer_query(
                    req.query,
                    corpus=c,
                    llm=l,
                    fallback=f,
                    crag=crag,
                    on_stage=on_stage,
                    trace=rlog.trace,
                )
                if cache:
                    cache.put(req.query, crag, result)
                events.put(("answer", result.model_dump(mode="json")))
                rlog.finish("answer", result)
            except _ClientGone:
                rlog.finish("client_gone")
            except Exception:
                logging.getLogger(__name__).exception("answer generation failed")
                rlog.finish("error")
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
                    yield _frame(*event)
            finally:
                # Client left: stop the pipeline at its next Stage.
                cancelled.set()

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app(rate_limiter=RateLimiter.from_env(), cache=AnswerCache.from_env())
