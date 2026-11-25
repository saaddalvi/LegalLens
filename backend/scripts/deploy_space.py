"""Assemble the files for a Hugging Face Docker Space, and optionally upload them.

    python scripts/deploy_space.py STAGE_DIR                  # only assemble, touch nothing remote
    python scripts/deploy_space.py STAGE_DIR --push USER/SPACE  # also create the Space and upload

The built Corpus (`data/chroma`) and the source PDFs are gitignored, so a Space cannot be built
from this repository alone. This puts the Dockerfile, the code and the built Corpus side by
side in STAGE_DIR, which is the layout the Dockerfile expects. The repository never holds the Corpus.

Secrets are not handled here: set GOOGLE_API_KEY, WEB_SEARCH_API_KEY and CORS_ORIGINS in the
Space's settings. `--push` reads the Hub token from HF_TOKEN or a prior `hf auth login`.
"""

import argparse
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "src"))

SPACE_CARD = """---
title: LegalLens API
sdk: docker
app_port: 7860
pinned: false
---

Backend for LegalLens, an assistant that answers questions about Indian law with citations
checked against statute text. API only; the interface is hosted separately.
Probe `/ready` for health: it reports whether the Corpus loaded.
"""

IGNORE = shutil.ignore_patterns("__pycache__", "*.egg-info", "*.pyc")


def check_corpus(store: Path) -> int:
    """Count the built Corpus's Provisions; refuse one that is missing or only the sample."""
    from legallens.corpus import Corpus
    from legallens.embeddings import LocalEmbedder
    from legallens.main import is_fixture_corpus

    if not (store / "chroma.sqlite3").exists():
        sys.exit(
            f"No built Corpus at {store}. Run `python -m legallens.build_corpus` first."
        )
    corpus = Corpus(store, LocalEmbedder())  # counting does not load the model
    count = corpus.count()
    if count == 0 or is_fixture_corpus(corpus):
        sys.exit(
            f"The Corpus at {store} is empty or only the sample fixture; not shipping it."
        )
    return count


def stage(dest: Path, store: Path) -> int:
    count = check_corpus(store)
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} is not empty; give an empty or new directory.")
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("Dockerfile", "constraints.txt", "pyproject.toml"):
        shutil.copy2(BACKEND_DIR / name, dest / name)
    shutil.copytree(BACKEND_DIR / "src", dest / "src", ignore=IGNORE)
    shutil.copytree(BACKEND_DIR / "fixtures", dest / "fixtures")
    shutil.copytree(store, dest / "data" / "chroma")
    (dest / "README.md").write_text(SPACE_CARD)
    return count


def push(dest: Path, repo_id: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(folder_path=str(dest), repo_id=repo_id, repo_type="space")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stage_dir", type=Path)
    ap.add_argument("--corpus", type=Path, default=BACKEND_DIR / "data" / "chroma")
    ap.add_argument(
        "--push", metavar="USER/SPACE", help="create the Space and upload to it"
    )
    args = ap.parse_args()
    count = stage(args.stage_dir, args.corpus)
    print(f"Staged {count} Provisions and the code in {args.stage_dir}")
    if args.push:
        push(args.stage_dir, args.push)
        print(f"Uploaded to https://huggingface.co/spaces/{args.push}")
    else:
        print("Nothing was uploaded. Add --push USER/SPACE to upload.")


if __name__ == "__main__":
    main()
