import re
from pathlib import Path

import chromadb

from .embeddings import Embedder
from .models import Provision

_COLLECTION = "provisions"


PIECE_CHARS = 800  # the embedding model reads ~512 tokens, so long Provisions are split to be searchable
_UPSERT_BATCH = 1000  # Chroma rejects a single upsert above ~5,400 records
_SEARCH_PIECES = (
    5  # pieces fetched per Provision wanted, so k distinct Provisions come back
)


def split_text(text: str, size: int = PIECE_CHARS) -> list[str]:
    """Pieces of at most about `size` characters, broken at line ends (a line is never cut)."""
    if len(text) <= size:
        return [text]
    pieces, cur = [], ""
    for line in text.split("\n"):
        if cur and len(cur) + len(line) > size:
            pieces.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        pieces.append(cur)
    return pieces


def _number_order(number: str) -> list[tuple[int, int, str]]:
    """Sort key putting "21A" after "21" and before "22", and "100" after "21A".

    Each run of digits sorts as a number and each run of letters as text, so numbers such as
    "21", "21A" and "100" come out in the order the statute prints them."""
    return [
        (0, int(part), "") if part.isdigit() else (1, 0, part.upper())
        for part in re.findall(r"\d+|\D+", number)
    ]


class Corpus:
    """Vector store of Provisions. A long Provision is stored as several searchable pieces
    (an amendment of ADR 0002); a Provision is still one unit everywhere else: `get`, `count`
    and `search` return whole Provisions, never pieces."""

    def __init__(self, path: Path | str, embedder: Embedder):
        self._embedder = embedder
        self._col = chromadb.PersistentClient(path=str(path)).get_or_create_collection(
            _COLLECTION, configuration={"hnsw": {"space": "cosine"}}
        )

    @property
    def embedder(self) -> Embedder:
        """The embedding model, shared with Contract Clauses (ADR 0005: one model for both)."""
        return self._embedder

    def count(self) -> int:
        """Number of Provisions (not pieces)."""
        return len(self._col.get(where={"piece": 0}, include=[])["ids"])

    def add(self, provisions: list[Provision]) -> None:
        if not provisions:
            return
        ids, docs, metas = [], [], []
        for p in provisions:
            for i, piece in enumerate(split_text(p.text)):
                ids.append(f"{p.act}|{p.number}|{i}")
                docs.append(piece)
                meta = {
                    "act": p.act,
                    "chapter": p.chapter,
                    "number": p.number,
                    "status": p.status,
                    "superseded_by": p.superseded_by or "",
                    "supersedes": p.supersedes or "",
                    "piece": i,
                }
                if i == 0:
                    meta["text"] = p.text  # the whole verbatim Provision
                metas.append(meta)
        for i in range(0, len(ids), _UPSERT_BATCH):
            part = slice(i, i + _UPSERT_BATCH)
            self._col.upsert(
                ids=ids[part],
                embeddings=self._embedder.embed(docs[part], is_query=False),
                documents=docs[part],
                metadatas=metas[part],
            )

    @staticmethod
    def _provision(m: dict) -> Provision:
        return Provision(
            act=m["act"],
            chapter=m["chapter"],
            number=m["number"],
            status=m["status"],
            text=m["text"],
            superseded_by=m["superseded_by"] or None,
            supersedes=m.get("supersedes") or None,
        )

    def get(self, act: str, number: str) -> Provision | None:
        res = self._col.get(ids=[f"{act}|{number}|0"])
        return self._provision(res["metadatas"][0]) if res["ids"] else None

    def act_counts(self) -> dict[str, int]:
        """Number of Provisions in each Act, by Act name."""
        metas = self._col.get(where={"piece": 0}, include=["metadatas"])["metadatas"]
        counts: dict[str, int] = {}
        for m in metas:
            counts[m["act"]] = counts.get(m["act"], 0) + 1
        return counts

    def list_act(self, act: str) -> list[Provision]:
        """Every Provision of an Act, in statute order (21 before 21A before 100)."""
        res = self._col.get(
            where={"$and": [{"act": act}, {"piece": 0}]}, include=["metadatas"]
        )
        return sorted(
            (self._provision(m) for m in res["metadatas"]),
            key=lambda p: _number_order(p.number),
        )

    def search(self, query: str, k: int = 5) -> list[Provision]:
        """The k Provisions whose best piece is closest to the Query, closest first."""
        total = self._col.count()
        if total == 0:
            return []
        res = self._col.query(
            query_embeddings=self._embedder.embed([query], is_query=True),
            n_results=min(k * _SEARCH_PIECES, total),
        )
        keys = list(
            dict.fromkeys((m["act"], m["number"]) for m in res["metadatas"][0])
        )[:k]
        return [p for key in keys if (p := self.get(*key))]
