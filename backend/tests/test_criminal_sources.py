from pathlib import Path

import pytest

from legallens.ingestion import apply_mappings, build_report, parse_criminal_code
from legallens.ingestion.sources import (
    CRIMINAL_PDFS,
    load_criminal_codes,
    read_pinned_pdf_pages,
)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
HAVE_PDFS = all(
    (RAW_DIR / "criminal" / p.filename).exists() for p in CRIMINAL_PDFS.values()
)


def test_a_pdf_that_does_not_match_its_pinned_hash_is_refused(tmp_path):
    (tmp_path / "criminal").mkdir()
    (tmp_path / "criminal" / "bns_gaz.pdf").write_bytes(b"not the Gazette")
    with pytest.raises(RuntimeError, match="sha256"):
        read_pinned_pdf_pages(tmp_path, "bns")


def test_a_missing_pdf_says_which_file_to_put_where(tmp_path):
    with pytest.raises(FileNotFoundError, match="bns_gaz.pdf"):
        read_pinned_pdf_pages(tmp_path, "bns")


def test_every_source_is_pinned_by_sha256():
    assert set(CRIMINAL_PDFS) == {"bns", "bnss", "bsa", "crpc", "ncrb_bns", "ncrb_bnss"}
    for pdf in CRIMINAL_PDFS.values():
        assert len(pdf.sha256) == 64 and int(pdf.sha256, 16) >= 0


@pytest.mark.skipif(
    not HAVE_PDFS, reason="official PDFs are not in backend/data/raw/criminal"
)
def test_real_pdfs_ingest_to_the_published_section_counts_with_clean_mappings():
    records, mappings = load_criminal_codes(RAW_DIR)
    assert {k: len(v) for k, v in records.items()} == {
        "bns": 358,
        "bnss": 531,
        "bsa": 170,
        "crpc": 535,
    }
    provisions = [p for k, rs in records.items() for p in parse_criminal_code(k, rs)]
    linked = {(p.act, p.number): p for p in apply_mappings(provisions, mappings)}
    assert linked["Code of Criminal Procedure", "154"].superseded_by == (
        "Bharatiya Nagarik Suraksha Sanhita 173"
    )
    assert linked["Bharatiya Nagarik Suraksha Sanhita", "35"].supersedes == (
        "Code of Criminal Procedure 41; Code of Criminal Procedure 41A"
    )
    assert build_report(provisions).warnings == []
