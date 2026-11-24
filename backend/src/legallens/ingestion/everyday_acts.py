"""The consumer, tenancy and labour Acts: one Chunk per Section (ADR 0002).

They use the same section-record format as the criminal-law Acts, `{"section", "chapter",
"text"}`, so `parse_section_records` serves them. The Acts were chosen with the user (ticket 09).
"""

from ..models import Provision
from .criminal_codes import CriminalAct, parse_section_records

# Exact counts: the section totals of the pinned texts, checked against the Acts' own numbering
# by scripts/verify_everyday_acts.py. The Transfer of Property Act is Chapter V only (leases,
# sections 105-117 and the inserted 114A). The Indian Contract Act is the 192 sections in the
# Legislative Department print: 1-75 and 124-238 with the inserted 19A and 178A (Chapter VII,
# sale of goods, and Chapter XI, partnership, were repealed and have no text). All are stored as in force except the Model Tenancy Act ("model"); the four
# Labour Codes were brought into force on 21 November 2025.
EVERYDAY_ACTS: dict[str, CriminalAct] = {
    "contract": CriminalAct("Indian Contract Act", "in_force", (192, 192)),
    "cpa": CriminalAct("Consumer Protection Act", "in_force", (107, 107)),
    "tpa": CriminalAct("Transfer of Property Act", "in_force", (14, 14)),
    # A template for States to adopt, not law in force by itself (see sources/everyday_acts.json),
    # so it has its own Status.
    "mta": CriminalAct("Model Tenancy Act", "model", (47, 47)),
    "wages": CriminalAct("Code on Wages", "in_force", (69, 69)),
    "ir": CriminalAct("Industrial Relations Code", "in_force", (104, 104)),
    "ss": CriminalAct("Code on Social Security", "in_force", (164, 164)),
    "osh": CriminalAct(
        "Occupational Safety, Health and Working Conditions Code",
        "in_force",
        (143, 143),
    ),
}


def parse_everyday_act(act_key: str, records: list[dict]) -> list[Provision]:
    return parse_section_records(EVERYDAY_ACTS[act_key], records)
