from pathlib import Path

import chromadb

from .embeddings import Embedder
from .models import Provision

_COLLECTION = "provisions"


class Corpus:
    """Vector store of Provisions, one Chunk each."""

    def __init__(self, path: Path | str, embedder: Embedder):
        self._embedder = embedder
        self._col = chromadb.PersistentClient(path=str(path)).get_or_create_collection(
            _COLLECTION, configuration={"hnsw": {"space": "cosine"}}
        )

    def count(self) -> int:
        return self._col.count()

    def add(self, provisions: list[Provision]) -> None:
        if not provisions:
            return
        self._col.upsert(
            ids=[f"{p.act}|{p.number}" for p in provisions],
            embeddings=self._embedder.embed([p.text for p in provisions], is_query=False),
            documents=[p.text for p in provisions],
            metadatas=[
                {
                    "act": p.act,
                    "chapter": p.chapter,
                    "number": p.number,
                    "status": p.status,
                    "superseded_by": p.superseded_by or "",
                }
                for p in provisions
            ],
        )

    def search(self, query: str, k: int = 5) -> list[Provision]:
        if self.count() == 0:
            return []
        res = self._col.query(
            query_embeddings=self._embedder.embed([query], is_query=True),
            n_results=min(k, self.count()),
        )
        return [
            Provision(
                act=m["act"],
                chapter=m["chapter"],
                number=m["number"],
                status=m["status"],
                text=doc,
                superseded_by=m["superseded_by"] or None,
            )
            for doc, m in zip(res["documents"][0], res["metadatas"][0])
        ]
