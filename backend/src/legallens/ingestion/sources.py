"""Fetching the pinned open dataset the Constitution is built from."""

import hashlib
import json
import urllib.request
from pathlib import Path

# civictech-India/constitution-of-india, pinned so the Corpus builds reproducibly.
DATASET_URL = (
    "https://raw.githubusercontent.com/civictech-India/constitution-of-india/"
    "48871da69fd03cf2f85aa845f0f99da815adf17b/constitution_of_india.json"
)
DATASET_SHA256 = "4ac17b53c465760709bf3a9467647ba8c32150d0c6269099f23e0893280e8b06"


def fetch_constitution(dest: Path) -> list[dict]:
    """Download the dataset to `dest` if absent, check its hash, and return the records."""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(DATASET_URL, timeout=60) as resp:
            data = resp.read()
        _check_hash(data, DATASET_URL)
        tmp = dest.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(dest)  # never leave a truncated file at the final path
    data = dest.read_bytes()
    _check_hash(data, str(dest))
    return json.loads(data.decode("utf-8"))


def _check_hash(data: bytes, where: str) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if digest != DATASET_SHA256:
        raise RuntimeError(f"{where} has sha256 {digest}, expected {DATASET_SHA256}")


def load_patches(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["patches"]
