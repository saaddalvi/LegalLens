import asyncio
import json
import logging
import os
import queue
import threading
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.formparsers import MultiPartParser
from svix.webhooks import Webhook, WebhookVerificationError

from .answer_cache import AnswerCache
from .answering import Answerer, Cancelled, Stage, StageFailed
from .auth import ClerkVerifier, InvalidToken, TokenVerifier
from .contract_intake import MAX_UPLOAD_BYTES, ContractIntake, Refused, Source
from .corpus import Corpus
from .db import Database
from .embeddings import Embedder, LocalEmbedder
from .fallback import WebFallback, default_fallback
from .llm import LLM, GeminiLLM
from .models import (
    ActIndex,
    ActSummary,
    AskRequest,
    AskResponse,
    ContractDetail,
    ContractSummary,
    Provision,
    ProvisionSummary,
)
from .rate_limit import RateLimiter
from .request_log import RequestLog

# Starlette spools an uploaded file to a temp file on disk once it passes 1MB. A Contract is
# private and its file is never kept (spec: "Upload endpoint"), so keep uploads up to the size
# limit in memory instead.
MultiPartParser.spool_max_size = MAX_UPLOAD_BYTES + 1

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


def _frame(name: str, data: dict) -> str:
    """One Server-Sent Events frame."""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _refusal(r: Refused) -> dict:
    return {"reason": r.code, "message": r.message}


def _single_event_response(name: str, data: dict) -> StreamingResponse:
    return StreamingResponse(
        iter([_frame(name, data)]), media_type="text/event-stream", headers=_SSE_HEADERS
    )


def create_app(
    *,
    corpus: Corpus | None = None,
    llm: LLM | None = None,
    fallback: WebFallback | None = None,
    crag: bool = True,
    rate_limiter: RateLimiter | None = None,
    verifier: TokenVerifier | None = None,
    cache: AnswerCache | None = None,
    database: Database | None = None,
    webhook_secret: str | None = None,
    embedder: Embedder | None = None,
) -> FastAPI:
    """Dependencies not supplied are built lazily on the first question.

    crag=False serves the plain-RAG baseline (no Grader, no Fallback) for evaluation.
    verifier turns a Clerk bearer token into a user id; /ask and /ask/stream require one, and
    with None they refuse every request.
    rate_limiter limits /ask and /ask/stream per signed-in user; None means no limit.
    cache remembers answers to repeated Queries; None means every Query is answered afresh.
    database holds users (and later Contracts); None means no database, and /ask needs none.
    webhook_secret is Clerk's Svix signing secret for /webhooks/clerk; None disables that route.
    embedder embeds Contract Clauses; None uses the Corpus's embedding model (ADR 0005).
    The /contracts routes need a database and answer 503 without one.
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
        if database is not None:
            await database.dispose()

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

    @lru_cache(maxsize=1)
    def answerer() -> Answerer:
        c, l, f = deps()
        return Answerer(corpus=c, llm=l, fallback=f, crag=crag, cache=cache)

    async def current_user(request: Request) -> str:
        """The Clerk user id behind the bearer token; 401 before any work starts. The first
        request from a user also creates their users row."""
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        token = token.strip()
        unauthorized = HTTPException(
            401,
            "Sign in to use LegalLens.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if scheme.lower() != "bearer" or not token or verifier is None:
            raise unauthorized
        try:
            # Verifying may fetch the JWKS over the network, so it stays off the event loop.
            user = await asyncio.to_thread(verifier.verify, token)
        except InvalidToken as exc:
            # The reason (expired, wrong issuer, JWKS unreachable) helps whoever runs the
            # service; the token itself is never logged.
            logging.getLogger(__name__).warning("token refused: %s", exc)
            raise unauthorized from exc
        if database is not None:
            try:
                await database.ensure_user(user)
            except Exception:
                # /ask does not need the row, so a database outage must not stop it.
                logging.getLogger(__name__).exception("could not record the user")
        return user

    def limit(user: str = Depends(current_user)) -> None:
        """Rejects with 429 before any work starts, so a streamed answer never begins."""
        if rate_limiter is None:
            return
        wait = rate_limiter.check(user)
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

    @app.post("/webhooks/clerk")
    async def clerk_webhook(request: Request) -> dict[str, str]:
        """Clerk's webhook. Authenticated by its Svix signature, not a bearer token.
        `user.deleted` deletes the user's row and, by cascade, all their data."""
        if not webhook_secret or database is None:
            raise HTTPException(503, "Webhooks are not configured.")
        body = await request.body()
        try:
            Webhook(webhook_secret).verify(body, dict(request.headers))
            event = json.loads(body)
        except (WebhookVerificationError, ValueError) as exc:
            raise HTTPException(400, "Invalid webhook signature.") from exc
        if event.get("type") == "user.deleted":
            user_id = (event.get("data") or {}).get("id")
            if isinstance(user_id, str) and user_id:
                await database.delete_user(user_id)
        return {"status": "ok"}

    UNAVAILABLE = "The service is unavailable. Please retry shortly."

    def get_answerer() -> Answerer:
        try:
            return answerer()
        except Exception as exc:
            logging.getLogger(__name__).exception("dependencies unavailable")
            raise HTTPException(503, UNAVAILABLE) from exc

    @app.post("/ask", response_model=AskResponse, dependencies=[Depends(limit)])
    def ask(req: AskRequest) -> AskResponse:
        try:
            return get_answerer().answer(req.query, endpoint="ask").response
        except StageFailed as exc:
            raise HTTPException(503, UNAVAILABLE) from exc

    @app.post("/ask/stream", dependencies=[Depends(limit)])
    def ask_stream(req: AskRequest) -> StreamingResponse:
        a = get_answerer()  # 503 here, before any stream starts
        events: queue.Queue[tuple[str, dict] | None] = queue.Queue()
        cancelled = threading.Event()

        def on_stage(stage: Stage) -> None:
            events.put(("stage", {"id": stage.id, "label": stage.label}))

        def work() -> None:
            try:
                answered = a.answer(
                    req.query,
                    endpoint="ask_stream",
                    on_stage=on_stage,
                    cancel=cancelled,
                )
                events.put(("answer", answered.response.model_dump(mode="json")))
            except Cancelled:
                pass  # the reader is gone
            except StageFailed as exc:
                events.put(("error", {"stage": exc.stage, "message": UNAVAILABLE}))
            except Exception:
                logging.getLogger(__name__).exception(
                    "answering failed outside a Stage"
                )
                events.put(("error", {"stage": None, "message": UNAVAILABLE}))
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
                # Client left: stop the work at its next Stage.
                cancelled.set()

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Contracts -------------------------------------------------------------------------

    def contracts_db() -> Database:
        if database is None:
            raise HTTPException(503, UNAVAILABLE)
        return database

    @lru_cache(maxsize=1)
    def intake() -> ContractIntake:
        db = contracts_db()
        c, l, _ = deps()
        return ContractIntake(llm=l, embedder=embedder or c.embedder, database=db)

    @app.post("/contracts/stream")
    async def upload_contract(
        file: Annotated[UploadFile | None, File()] = None,
        text: Annotated[str | None, Form()] = None,
        user: str = Depends(current_user),
    ) -> StreamingResponse:
        """Takes a PDF or DOCX file, or pasted text, and streams the Stages of reading it,
        ending in `answer` (the new Contract), `refusal` (why it cannot be explained) or
        `error`. Nothing is stored unless it ends in `answer`."""
        contracts_db()
        if (file is None) == (not (text or "").strip()):
            raise HTTPException(
                422, "Send either a file or the pasted text of the Contract."
            )
        if file is not None:
            data = await file.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "That file is too large.")
        try:
            source = (
                Source.from_bytes(data)
                if file is not None
                else Source("text", text=text)
            )
            work = intake()
        except Refused as r:
            return _single_event_response("refusal", _refusal(r))
        except Exception as exc:
            logging.getLogger(__name__).error(
                "contract intake unavailable: %s", type(exc).__name__
            )
            raise HTTPException(503, UNAVAILABLE) from exc

        rlog = RequestLog("contracts_stream", "")
        events: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()
        running: list[str] = []

        def on_stage(stage_id: str, label: str) -> None:
            running[:] = [stage_id]
            rlog.stage(stage_id)
            events.put_nowait(("stage", {"id": stage_id, "label": label}))

        async def run() -> None:
            try:
                stored = await work.process(user, source, on_stage=on_stage)
                rlog.finish("answer")
                events.put_nowait(
                    (
                        "answer",
                        {
                            "id": stored.id,
                            "title": stored.title,
                            "clause_count": stored.clause_count,
                        },
                    )
                )
            except Refused as r:
                rlog.finish("refused")
                events.put_nowait(("refusal", _refusal(r)))
            except asyncio.CancelledError:
                rlog.finish("client_gone")
                raise
            except Exception as exc:  # noqa: BLE001
                # Never the exception's text or traceback: it can quote the Contract.
                logging.getLogger(__name__).error(
                    "contract upload failed in stage %s: %s",
                    running[0] if running else None,
                    type(exc).__name__,
                )
                rlog.finish("error")
                events.put_nowait(
                    (
                        "error",
                        {
                            "stage": running[0] if running else None,
                            "message": UNAVAILABLE,
                        },
                    )
                )
            finally:
                events.put_nowait(None)

        task = asyncio.create_task(run())

        async def frames():
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(
                            events.get(), timeout=KEEPALIVE_SECONDS
                        )
                    except TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    if event is None:
                        return
                    yield _frame(*event)
            finally:
                task.cancel()  # the client left: stop at the next await

        return StreamingResponse(
            frames(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    @app.get("/contracts", response_model=list[ContractSummary])
    async def list_contracts(user: str = Depends(current_user)):
        return await contracts_db().list_contracts(user)

    @app.get("/contracts/{contract_id}", response_model=ContractDetail)
    async def get_contract(contract_id: str, user: str = Depends(current_user)):
        # 404 for a Contract that is not yours, so its existence is not revealed.
        try:
            uuid.UUID(contract_id)
        except ValueError:
            raise HTTPException(404, "No such Contract.") from None
        found = await contracts_db().get_contract(user, contract_id)
        if found is None:
            raise HTTPException(404, "No such Contract.")
        return found

    return app


app = create_app(
    rate_limiter=RateLimiter.from_env(),
    verifier=ClerkVerifier.from_env(),
    cache=AnswerCache.from_env(),
    database=Database.from_env(),
    webhook_secret=os.environ.get("CLERK_WEBHOOK_SECRET") or None,
)
