"""Fetching the pinned open dataset the Constitution is built from."""

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .criminal_codes import CRIMINAL_ACTS
from .everyday_acts import EVERYDAY_ACTS
from .mapping_tables import (
    parse_bns_table,
    parse_bsa_table,
    parse_corresponding_table,
)
from .pdf_text import (
    crpc_sections,
    gazette_sections,
    iea_sections,
    kanoon_ipc_sections,
    pdf_pages,
    tpa_lease_sections,
)
from .record_patches import apply_record_patches

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
    "iea": PinnedPdf(
        "iea_1872.pdf",
        "62b33659545e001223a99364447e9314d5372f1791db5cccadd87a08c267eb91",
        "Indian Evidence Act, 1872: India Code consolidated text, last updated 13-3-2020",
    ),
    "ipc": PinnedPdf(
        "ipc_ik.pdf",
        "64b4e5bacc7a0c9f49f2858b160088e927e2e51f8baf001afe26c225832669a3",
        "Indian Penal Code, 1860: Indian Kanoon print of the text as of 7 February 2022 (unofficial)",
    ),
    "ipc_ic_2012": PinnedPdf(
        "ipc_ic_2012.pdf",
        "ef8945c5d1b02904da67959e245b87bd5751ed5563d03ab0079758909f145309",
        "Indian Penal Code, 1860: India Code text from before 2013, kept to check the Kanoon text",
    ),
    "ipc_unknown_2016": PinnedPdf(
        "ipc_unknown_2016.pdf",
        "de4e710af30ef968474a17e2e7d3d147daf2175e15c98137983eb101a46ec80e",
        "Indian Penal Code, 1860: unattributed text from about 2016, kept to check the Kanoon text",
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
    "ncrb_bsa": PinnedPdf(
        "bsa_ncrb.pdf",
        "cd6f6e04eea925672f5590347cfa832c01ab0f36b26eb45800fcd30828e89334",
        "NCRB Sankalan: BSA with its corresponding-section table against the Evidence Act",
    ),
}


def read_pinned_pdf_pages(raw_dir: Path, key: str) -> list[str]:
    """The text of a pinned criminal-law source PDF, page by page, after checking its hash."""
    return _read_pinned(raw_dir / "criminal", CRIMINAL_PDFS[key])


def _read_pinned(folder: Path, pdf: PinnedPdf) -> list[str]:
    path = folder / pdf.filename
    if not path.exists():
        raise FileNotFoundError(
            f"{pdf.filename} ({pdf.description}) is missing: put it at {path}"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != pdf.sha256:
        raise RuntimeError(f"{path} has sha256 {digest}, expected {pdf.sha256}")
    return pdf_pages(path)


# Texts of the consumer, tenancy and labour Acts, in backend/data/raw/everyday/, pinned by hash.
# The CPA and the four Labour Codes are the Gazette of India Extraordinary prints as enacted.
# India Code serves 504s, so the Transfer of Property Act is an unofficial print instead.
EVERYDAY_PDFS: dict[str, PinnedPdf] = {
    "cpa": PinnedPdf(
        "cpa_prs.pdf",
        "0ae7f82ab5b77d50087cd4cd2dd2dbc12755c0bdb31371fdefd042b020d50756",
        "Consumer Protection Act, 2019 (No. 35 of 2019): Gazette print, via PRS India",
    ),
    "wages": PinnedPdf(
        "wages_gaz.pdf",
        "0819c6b8942ce380ecd9c2bc31daf6c0d441034cde020fb499c57dfcbab451bd",
        "Code on Wages, 2019 (No. 29 of 2019): egazette.gov.in 210356",
    ),
    "ir": PinnedPdf(
        "ir_prs.pdf",
        "43cadbd9ed08dd00dfba43571253eaf63d655f9fc411df5b9a1059de8d40ce09",
        "Industrial Relations Code, 2020 (No. 35 of 2020): Gazette print CG-DL-E-29092020-222118, via PRS India",
    ),
    "ss": PinnedPdf(
        "ss_prs.pdf",
        "975235e57b8b8c3f4a09f6c9f0dbb2bfc663c15faf3715108ea33113ef565be7",
        "Code on Social Security, 2020 (No. 36 of 2020): Gazette print CG-DL-E-29092020-222111, via PRS India",
    ),
    "osh": PinnedPdf(
        "osh_prs.pdf",
        "9ce8f68b88f725fbce4fadfb45d9ddc3ed7a5f59d92a2ebd3d5bd7ebb1c83891",
        "Occupational Safety, Health and Working Conditions Code, 2020 (No. 37 of 2020): Gazette print CG-DL-E-29092020-222112, via PRS India",
    ),
    "tpa": PinnedPdf(
        "tpa_ila.pdf",
        "56a363929cefe94696f890eb3240bcfb4aa64527e30ecfed7a8d3a1dfede1646",
        "Transfer of Property Act, 1882: International Insolvency Institute print (unofficial); only Chapter V is used",
    ),
    "ss_ic": PinnedPdf(
        "ss_ic.pdf",
        "53ad67f75fbc874fd837274e9e887fac7a21cc55c7454398b2cdb96046fd7967",
        "Code on Social Security, 2020: India Code text as on 21 November 2025, kept to check the Gazette print",
    ),
}


def read_everyday_pdf_pages(raw_dir: Path, key: str) -> list[str]:
    return _read_pinned(raw_dir / "everyday", EVERYDAY_PDFS[key])


def load_everyday_acts(raw_dir: Path) -> dict[str, list[dict]]:
    """Section records for the six consumer, tenancy and labour Acts, by `EVERYDAY_ACTS` key."""
    gazette = ("cpa", "wages", "ir", "ss", "osh")
    records = {
        key: gazette_sections(read_everyday_pdf_pages(raw_dir, key)) for key in gazette
    }
    records["tpa"] = tpa_lease_sections(read_everyday_pdf_pages(raw_dir, "tpa"))
    assert set(records) == set(EVERYDAY_ACTS)
    return records


# Fixes to the Indian Kanoon IPC text, each checked against the other IPC copies.
IPC_PATCHES = Path(__file__).resolve().parents[3] / "sources" / "ipc_patches.json"


def load_criminal_codes(
    raw_dir: Path, ipc_patches: Path = IPC_PATCHES
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Section records for all six Acts, and the BNSS-CrPC, BSA-IEA and BNS-IPC mappings.

    The IPC comes from the Indian Kanoon print, the only copy that is both complete and current,
    with the fixes in `ipc_patches`. No copy of it is official and current.
    """
    records = {
        "bns": gazette_sections(read_pinned_pdf_pages(raw_dir, "bns")),
        "bnss": gazette_sections(read_pinned_pdf_pages(raw_dir, "bnss")),
        "bsa": gazette_sections(read_pinned_pdf_pages(raw_dir, "bsa")),
        "crpc": crpc_sections(read_pinned_pdf_pages(raw_dir, "crpc")),
        "iea": iea_sections(read_pinned_pdf_pages(raw_dir, "iea")),
        "ipc": apply_record_patches(
            kanoon_ipc_sections(read_pinned_pdf_pages(raw_dir, "ipc")),
            json.loads(ipc_patches.read_text(encoding="utf-8")),
        ),
    }
    table = parse_corresponding_table(
        read_pinned_pdf_pages(raw_dir, "ncrb_bnss"),
        new_act=CRIMINAL_ACTS["bnss"].name,
        old_act=CRIMINAL_ACTS["crpc"].name,
        old_title="Code of Criminal Procedure, 1973",
    )
    bsa_table = parse_bsa_table(
        read_pinned_pdf_pages(raw_dir, "ncrb_bsa"),
        new_act=CRIMINAL_ACTS["bsa"].name,
        old_act=CRIMINAL_ACTS["iea"].name,
    )
    bns_table = parse_bns_table(
        read_pinned_pdf_pages(raw_dir, "ncrb_bns"),
        new_act=CRIMINAL_ACTS["bns"].name,
        old_act=CRIMINAL_ACTS["ipc"].name,
    )
    return records, table.mappings + bsa_table.mappings + bns_table.mappings
