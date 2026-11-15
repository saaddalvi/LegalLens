"""Build the Corpus from source texts: `python -m legallens.build_corpus`.

Downloads the pinned Constitution dataset (checking its hash), applies the recorded patches,
reports Chunk counts per Act, and writes a fresh vector store. Exits non-zero if any count or
Chunk looks wrong, so a bad parse is not silently shipped.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from .corpus import Corpus
from .embeddings import E5Embedder
from .ingestion import Report, build_report, parse_constitution
from .ingestion.sources import fetch_constitution, load_patches

BACKEND_DIR = Path(__file__).resolve().parents[2]


def build(
    corpus: Corpus, constitution_records: list[dict], patches: list[dict]
) -> Report:
    provisions = parse_constitution(constitution_records, patches)
    corpus.add(provisions)
    return build_report(provisions)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("CHROMA_PATH", BACKEND_DIR / "data" / "chroma")),
    )
    ap.add_argument("--raw-dir", type=Path, default=BACKEND_DIR / "data" / "raw")
    ap.add_argument(
        "--patches",
        type=Path,
        default=BACKEND_DIR / "sources" / "constitution_patches.json",
    )
    args = ap.parse_args()

    out = args.out.resolve()
    if out.exists() and not (out / "chroma.sqlite3").exists():
        print(f"Refusing to replace {out}: it is not a Chroma store", file=sys.stderr)
        return 2

    records = fetch_constitution(args.raw_dir / "constitution_of_india.json")
    # Build beside the target and swap in only a clean result, so a failed or suspicious
    # build never destroys a good store.
    staging = out.with_name(out.name + ".building")
    shutil.rmtree(staging, ignore_errors=True)
    corpus = Corpus(staging, E5Embedder())
    report = build(corpus, records, load_patches(args.patches))

    for act, n in sorted(report.counts.items()):
        print(f"  {act}: {n} Chunks")
    for warning in report.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    stored = corpus.count()
    del corpus
    if report.warnings:
        print(
            f"Not replacing {out}; the rejected build is in {staging}", file=sys.stderr
        )
        return 1
    shutil.rmtree(out, ignore_errors=True)
    staging.rename(out)
    print(f"Built Corpus at {out} ({stored} Chunks stored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
