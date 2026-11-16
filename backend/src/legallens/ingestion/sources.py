"""Fetching the pinned open dataset the Constitution is built from."""

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .criminal_codes import CRIMINAL_ACTS
from .mapping_tables import parse_corresponding_table
from .pdf_text import crpc_sections, gazette_sections, pdf_pages

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


@dataclass(frozen=True)
class PinnedPdf:
    filename: str  # under `<raw dir>/criminal/`
    sha256: str
    description: str


# Official texts and mapping tables the criminal-law Acts are built from. None can be fetched
# automatically (India Code returns 504s and the Gazette needs a manual download), so they sit
# gitignored in backend/data/raw/criminal/ and are pinned by hash.
CRIMINAL_PDFS: dict[str, PinnedPdf] = {
    "bns": PinnedPdf(
        "bns_gaz.pdf",
        "67c92f7869420685e6cdc29b1bdde19fff91312b10241b3ed3e1163c5399600b",
        "Bharatiya Nyaya Sanhita, 2023: Gazette of India Extraordinary 250883",
    ),
    "bnss": PinnedPdf(
        "bnss_gaz.pdf",
        "5e60e2afe30d0fe7eca4f8126301146b76c86a444e690581f81eb564843517fe",
        "Bharatiya Nagarik Suraksha Sanhita, 2023: Gazette of India Extraordinary 250884",
    ),
    "bsa": PinnedPdf(
        "bsa_gaz.pdf",
        "31ee68ea57b5303bf6697b5d8cb2004b9eb9180d7e9cbcbbdbf5bccab7cda5c1",
        "Bharatiya Sakshya Adhiniyam, 2023: Gazette of India Extraordinary 250882",
    ),
    "crpc": PinnedPdf(
        "crpc_ic.pdf",
        "5bb6514251a9ec6375b2c894cef5280dab0d1c3cca1e0f4a1e57f29b54033d72",
        "Code of Criminal Procedure, 1973: India Code handle 15272",
    ),
    "ncrb_bns": PinnedPdf(
        "ncrb_bns.pdf",
        "a83f12a93e32c9e0b39a85f75850a448dc4682b1b44b2d6bd680165bb9931549",
        "NCRB Sankalan: BNS with its corresponding-section table against the IPC",
    ),
    "ncrb_bnss": PinnedPdf(
        "ncrb_bnss.pdf",
        "b943f18662141aaae93a17f94a4387534934b5f4809bf9672ed47e10600bdec5",
        "NCRB Sankalan: BNSS with its corresponding-section table against the CrPC",
    ),
}


def read_pinned_pdf_pages(raw_dir: Path, key: str) -> list[str]:
    """The text of a pinned source PDF, page by page, after checking its hash."""
    pdf = CRIMINAL_PDFS[key]
    path = raw_dir / "criminal" / pdf.filename
    if not path.exists():
        raise FileNotFoundError(
            f"{pdf.filename} ({pdf.description}) is missing: put it at {path}"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != pdf.sha256:
        raise RuntimeError(f"{path} has sha256 {digest}, expected {pdf.sha256}")
    return pdf_pages(path)


def load_criminal_codes(raw_dir: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    """Section records for BNS, BNSS, BSA and CrPC, and the BNSS-CrPC mappings.

    The BNS-IPC and BSA-IEA mappings wait for the IPC and the consolidated Evidence Act.
    """
    records = {
        "bns": gazette_sections(read_pinned_pdf_pages(raw_dir, "bns")),
        "bnss": gazette_sections(read_pinned_pdf_pages(raw_dir, "bnss")),
        "bsa": gazette_sections(read_pinned_pdf_pages(raw_dir, "bsa")),
        "crpc": crpc_sections(read_pinned_pdf_pages(raw_dir, "crpc")),
    }
    table = parse_corresponding_table(
        read_pinned_pdf_pages(raw_dir, "ncrb_bnss"),
        new_act=CRIMINAL_ACTS["bnss"].name,
        old_act=CRIMINAL_ACTS["crpc"].name,
        old_title="Code of Criminal Procedure, 1973",
    )
    return records, table.mappings
