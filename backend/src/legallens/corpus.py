from pathlib import Path

import chromadb

from .embeddings import Embedder
from .models import Provision

_COLLECTION = "provisions"


PIECE_CHARS = 800  # the embedding model reads ~512 tokens, so long Provisions are split to be searchable
_UPSERT_BATCH = 1000  # Chroma rejects a single upsert above ~5,400 records
_SEARCH_PIECES = 5  # pieces fetched per Provision wanted, so k distinct Provisions come back


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


class Corpus:
    """Vector store of Provisions. A long Provision is stored as several searchable pieces
    (an amendment of ADR 0002); a Provision is still one unit everywhere else: `get`, `count`
    and `search` return whole Provisions, never pieces."""

    def __init__(self, path: Path | str, embedder: Embedder):
        self._embedder = embedder
        self._col = chromadb.PersistentClient(path=str(path)).get_or_create_collection(
            _COLLECTION, configuration={"hnsw": {"space": "cosine"}}
        )

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
