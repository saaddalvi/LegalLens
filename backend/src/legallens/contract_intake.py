"""Taking in an uploaded Contract: read it, check it, split it into Clauses, index it.

`ContractIntake.process` is the one entry point behind `POST /contracts/stream`. It either
returns the stored Contract or raises `Refused` with a reason a user can read; nothing is
stored on a refusal, because the only write is the last step. The original file is held in
memory for the call and never written anywhere. Contract text is never logged and never put
in an error message: failures are reported by Stage and exception type only.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .clauses import count_clauses, split_clauses
from .contract_brief import BriefWriter
from .corpus import Corpus
from .db import Database
from .embeddings import Embedder
from .llm import DocumentLLM
from .models import ContractBrief

log = logging.getLogger(__name__)

MAX_PAGES = 30
CHARS_PER_PAGE = 3500  # the page-equivalent of DOCX and pasted text
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
CHECK_CHARS = 6000  # the start of the text, which is all the Contract check reads

STAGE_LABELS = {
    "reading": "Reading your file",
    "contract_check": "Checking that it is a Contract in English",
    "splitting": "Finding the Clauses",
    "indexing": "Indexing the Clauses",
}

REFUSALS = {
    "too_long": f"That document is longer than about {MAX_PAGES} pages. Please upload only the part you want explained.",
    "not_a_contract": "LegalLens only explains Contracts, such as a rent agreement, a job offer or an NDA. That document doesn't look like one.",
    "not_english": "LegalLens can only read Contracts written in English for now. That one doesn't appear to be in English.",
    "unreadable": "LegalLens couldn't find any readable text in that file. Try a clearer copy, or paste the text instead.",
    "unsupported_file": "Please upload a PDF or a DOCX file, or paste the text of the Contract.",
}


class Refused(Exception):
    """The upload cannot be explained. `code` is stable; `message` is for the user."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.message = REFUSALS[code]


@dataclass(frozen=True)
class Source:
    """What was uploaded: `kind` is "pdf" or "docx" with `data`, or "text" with `text`."""

    kind: str
    data: bytes = b""
    text: str = ""

    @classmethod
    def from_bytes(cls, data: bytes) -> Source:
        """A file, told apart by its first bytes rather than its name."""
        if data.startswith(b"%PDF"):
            return cls("pdf", data=data)
        if data.startswith(b"PK"):
            return cls("docx", data=data)
        raise Refused("unsupported_file")


@dataclass(frozen=True)
class Stored:
    id: str
    title: str
    clause_count: int
    page_count: int
    brief: ContractBrief


def _pages_for(text: str) -> int:
    return max(1, -(-len(text) // CHARS_PER_PAGE))


def _docx_text(data: bytes) -> str:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            info = z.getinfo("word/document.xml")
            if info.file_size > MAX_UPLOAD_BYTES:
                raise Refused("too_long")
            root = ElementTree.fromstring(z.read(info))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise Refused("unreadable") from exc
    lines = []
    for para in root.iter(f"{ns}p"):
        parts = []
        for el in para.iter():
            if el.tag == f"{ns}t":
                parts.append(el.text or "")
            elif el.tag == f"{ns}tab":
                parts.append("\t")
            elif el.tag == f"{ns}br":
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines)


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class ContractIntake:
    def __init__(
        self,
        *,
        llm: DocumentLLM,
        embedder: Embedder,
        database: Database,
        corpus: Corpus,
    ):
        self._llm, self._embedder, self._db = llm, embedder, database
        self._briefs = BriefWriter(llm=llm, corpus=corpus)

    async def process(
        self,
        user_id: str,
        source: Source,
        *,
        on_stage: Callable[[str, str], None] = lambda stage_id, label: None,
    ) -> Stored:
        """Reads, checks, splits, briefs and stores a Contract for `user_id`, calling `on_stage`
        (id, label) as each Stage starts. Raises Refused, or any error from a Stage."""
        text, pages, pdf = self._precheck(source)

        on_stage("reading", STAGE_LABELS["reading"])
        if pdf is not None:
            text = _clean(
                await asyncio.to_thread(self._llm.read_document, pdf, "application/pdf")
            )
        if not text:
            log.warning("no text came back from reading the %s", source.kind)
            raise Refused("unreadable")

        on_stage("contract_check", STAGE_LABELS["contract_check"])
        check = await asyncio.to_thread(self._llm.check_contract, text[:CHECK_CHARS])
        if not check.is_contract:
            raise Refused("not_a_contract")
        if not check.is_english:
            raise Refused("not_english")

        on_stage("splitting", STAGE_LABELS["splitting"])
        pieces = split_clauses(text)
        if not pieces:
            raise Refused("unreadable")

        on_stage("indexing", STAGE_LABELS["indexing"])
        vectors = await asyncio.to_thread(
            self._embedder.embed, [p.text for p in pieces], is_query=False
        )
        brief = await self._briefs.write(text, pieces, on_stage=on_stage)
        title = check.title.strip()[:120] or "Untitled Contract"
        contract_id = await self._db.add_contract(
            user_id,
            title=title,
            text=text,
            page_count=pages,
            pieces=pieces,
            vectors=vectors,
            brief=brief,
        )
        count = count_clauses(p.number for p in pieces)
        return Stored(contract_id, title, count, pages, brief)

    @staticmethod
    def _precheck(source: Source) -> tuple[str, int, bytes | None]:
        """(text so far, page count, the PDF to send to Gemini). Refuses an over-long upload
        before any model is called."""
        if source.kind == "pdf":
            try:
                pages = len(PdfReader(io.BytesIO(source.data)).pages)
            except (PyPdfError, ValueError, OSError) as exc:
                log.warning("PDF could not be parsed: %s", type(exc).__name__)
                raise Refused("unreadable") from exc
            if pages > MAX_PAGES:
                raise Refused("too_long")
            return "", pages, source.data
        text = _clean(_docx_text(source.data) if source.kind == "docx" else source.text)
        if len(text) > MAX_PAGES * CHARS_PER_PAGE:
            raise Refused("too_long")
        return text, _pages_for(text), None
