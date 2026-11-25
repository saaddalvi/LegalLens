"""Score an embedding model on the golden-set retrieval cases (ticket 16).

    python scripts/compare_embeddings.py MODEL (whole|pieces) [--max-len N]

Reads whole Provisions from the built Corpus (`data/chroma`), embeds them either whole or in
800-character pieces, and prints the rank of the expected Provision per case (hit = top 10),
the embedding time and the model size on disk. Does not touch the Corpus.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import chromadb
import numpy as np

from legallens.corpus import split_text

BACKEND = Path(__file__).resolve().parents[1]
CASES = ("english", "hindi", "repealed_code")


def load_provisions() -> list[dict]:
    col = chromadb.PersistentClient(path=str(BACKEND / "data/chroma")).get_collection(
        "provisions"
    )
    res = col.get(where={"piece": 0}, include=["metadatas"])
    return [m for m in res["metadatas"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("mode", choices=["whole", "pieces"])
    ap.add_argument("--max-len", type=int, default=None)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = SentenceTransformer(args.model, device=device)
    if args.max_len:
        model.max_seq_length = args.max_len
    print(f"device={device} max_seq_length={model.max_seq_length}", file=sys.stderr)
    is_e5 = "e5" in args.model
    is_qwen = "Qwen3" in args.model

    provs = load_provisions()
    units, owner = [], []
    for i, p in enumerate(provs):
        for piece in split_text(p["text"]) if args.mode == "pieces" else [p["text"]]:
            units.append(("passage: " if is_e5 else "") + piece)
            owner.append(i)
    owner = np.array(owner)

    order = np.argsort([len(u) for u in units])  # similar lengths per batch
    t0 = time.time()
    vecs = np.zeros(
        (len(units), model.get_sentence_embedding_dimension()), dtype=np.float32
    )
    vecs[order] = model.encode(
        [units[j] for j in order], batch_size=args.batch, normalize_embeddings=True
    )
    elapsed = time.time() - t0

    cases = [
        c
        for c in json.loads((BACKEND / "evaluation/golden_set.json").read_text())
        if c["category"] in CASES and c["expected_provisions"]
    ]
    qtexts = [("query: " if is_e5 else "") + c["query"] for c in cases]
    qkw = {"prompt_name": "query"} if is_qwen else {}
    qvecs = model.encode(qtexts, normalize_embeddings=True, **qkw)

    key = {(p["act"], p["number"]): i for i, p in enumerate(provs)}
    hits = 0
    out = []
    for c, q in zip(cases, qvecs):
        sims = vecs @ q
        best = np.full(len(provs), -9.0)
        np.maximum.at(best, owner, sims)
        ranking = np.argsort(-best)
        rank_of = {int(pi): r + 1 for r, pi in enumerate(ranking)}
        ranks = [
            rank_of[key[(e["act"], e["number"])]]
            for e in c["expected_provisions"]
            if (e["act"], e["number"]) in key
        ]
        r = min(ranks) if ranks else None
        hits += bool(r and r <= 10)
        out.append((c["id"], r))
    for cid, r in out:
        print(f"{cid:32} {r}{'' if r and r <= 10 else '  MISS'}")
    print(
        f"RESULT model={args.model} mode={args.mode} hits={hits}/{len(cases)} units={len(units)} embed_seconds={elapsed:.0f} device={device}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
